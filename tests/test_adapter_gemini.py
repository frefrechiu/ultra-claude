"""Tests for GeminiAdapter behaviour against the locked subprocess contract.

Each test maps to a locked must-have from
``.planning/phases/07-gemini-codex-adapters/07-CONTEXT.md`` (ADP-06):

- ADP-02 (inherited from mixin): every Popen call uses text=True /
  encoding="utf-8" / errors="replace" / shell=False (asserted via fp
  fixture argument capture against the registered argv list).
- ADP-03 / Pitfall #2 (inherited from mixin): returncode==0 AND empty stdout
  raises AdapterError. The defense lives in the mixin so all three adapters
  inherit it; this file proves it for GeminiAdapter.
- ADP-04 / Pitfall #5 (inherited from mixin): subprocess.TimeoutExpired
  triggers process-tree kill AND raises AdapterError. Cross-platform branch
  covered via monkeypatch of _kill_process_tree.
- ADP-06 (Phase 7): argv == ["gemini", "-p"] and prompt is piped via stdin
  (NOT inlined into argv -- the Pitfall #1 mitigation).
- ADP-08 (inherited): FileNotFoundError -> AdapterAuthError; auth marker
  substring (case-insensitive) -> AdapterAuthError.

Tests use pytest-subprocess's `fp` fixture (already in pyproject.toml
[project.optional-dependencies] dev). The `fp` fixture mocks BOTH
subprocess.run and subprocess.Popen, so we don't need to choose; the mixin
uses Popen for child launching, and the lint/taskkill paths use run, both
are intercepted.
"""

from __future__ import annotations

import subprocess

import pytest

from ultra_claude.adapters import GeminiAdapter
from ultra_claude.exceptions import AdapterAuthError, AdapterError

# ---------------------------------------------------------------------------
# ADP-06 / ADP-02 / Pitfall #1: argv shape AND stdin pipe -- happy path
# ---------------------------------------------------------------------------


def test_invoke_pipes_prompt_via_stdin_and_returns_trimmed_stdout(fp) -> None:
    """GeminiAdapter.invoke must pipe the prompt via stdin (NEVER inline it
    into argv) and return stdout.strip() on the happy path.

    The stdin_callable assertion is the linchpin: if a future refactor moves
    the prompt onto argv as `gemini -p <huge string>`, Pitfall #1 returns
    (Windows cmd.exe rejects argv > ~8 KB; CreateProcess caps at ~32 KB).
    """

    captured: dict[str, object] = {}

    def stdin_callable(input_data):
        # pytest-subprocess passes whatever was sent to proc.communicate(input=...)
        # Our mixin uses text=True so input_data is str.
        captured["stdin"] = input_data

    fp.register(
        ["gemini", "-p"],
        stdout="hello world\n",
        stderr="",
        returncode=0,
        stdin_callable=stdin_callable,
    )

    result = GeminiAdapter().invoke("the prompt", timeout=10)

    assert result == "hello world", (
        f"Adapter must return stdout.strip() (got {result!r})"
    )
    assert captured.get("stdin") == "the prompt", (
        f"Prompt MUST be piped via stdin, not argv. "
        f"Got stdin={captured.get('stdin')!r}"
    )


def test_invoke_uses_list_form_argv_with_gemini_dash_p(fp) -> None:
    """argv must be exactly ['gemini', '-p'] -- two elements, list form,
    shell=False inherent. We register the exact argv and assert the call
    matched it.
    """

    fp.register(
        ["gemini", "-p"],
        stdout="ack\n",
        returncode=0,
    )

    # If argv mismatched, fp.register would not match the call and
    # pytest-subprocess would raise a ProcessNotRegisteredError -- that
    # itself is the assertion.
    result = GeminiAdapter().invoke("hi", timeout=5)
    assert result == "ack"

    # Defensive: also verify via fp.calls that the argv was list-form.
    assert any(list(call)[:2] == ["gemini", "-p"] for call in fp.calls), (
        f"Expected ['gemini', '-p'] argv. Recorded calls: {list(fp.calls)}"
    )


# ---------------------------------------------------------------------------
# ADP-03 / Pitfall #2: empty stdout with returncode 0 -> AdapterError
# ---------------------------------------------------------------------------


def test_invoke_raises_adapter_error_on_empty_stdout_with_zero_exit(fp) -> None:
    """The codex exec 0.124.0+ TTY bug shape: returncode=0, stdout="".
    The mixin's empty-stdout defense MUST raise AdapterError for ANY adapter
    with this signature -- GeminiAdapter inherits the protection for free.

    See openai/codex#19945. The defense lives in the mixin so future
    regressions of the same shape (silent failures with successful exit
    codes) are caught automatically across all three adapters.
    """

    fp.register(["gemini", "-p"], stdout="", stderr="", returncode=0)

    with pytest.raises(AdapterError) as exc_info:
        GeminiAdapter().invoke("hi", timeout=5)

    msg = str(exc_info.value)
    assert "gemini" in msg.lower(), (
        f"Error message must name the offending CLI. Got: {msg!r}"
    )
    assert "empty" in msg.lower() or "19945" in msg, (
        f"Error must reference empty-stdout / codex#19945. Got: {msg!r}"
    )


def test_invoke_raises_adapter_error_on_whitespace_only_stdout(fp) -> None:
    """The empty-stdout defense must match ``stdout.strip() == ""``, not just
    ``stdout == ""``. A child that prints only newlines / spaces is the same
    failure mode as a literal empty string."""

    fp.register(["gemini", "-p"], stdout="   \n\t\n  ", returncode=0)

    with pytest.raises(AdapterError):
        GeminiAdapter().invoke("hi", timeout=5)


# ---------------------------------------------------------------------------
# ADP-08 path 1: FileNotFoundError -> AdapterAuthError
# ---------------------------------------------------------------------------


def test_invoke_raises_adapter_auth_error_when_cli_not_on_path(monkeypatch) -> None:
    """If the ``gemini`` binary is not on PATH, Popen raises FileNotFoundError.
    The mixin must catch that and re-raise as AdapterAuthError with a hint
    that names the CLI by cli_name.

    We use monkeypatch on subprocess.Popen rather than fp here because
    pytest-subprocess's default behaviour is to allow unregistered calls
    through to the real subprocess module -- by monkeypatching Popen
    directly to raise FileNotFoundError, we emulate the "binary missing"
    OS-level failure exactly.
    """

    def _raise_fnf(*args, **kwargs):
        raise FileNotFoundError(2, "No such file or directory: 'gemini'")

    monkeypatch.setattr(subprocess, "Popen", _raise_fnf)

    with pytest.raises(AdapterAuthError) as exc_info:
        GeminiAdapter().invoke("hi", timeout=5)

    msg = str(exc_info.value)
    assert "gemini" in msg.lower()
    # The mixin's hint should mention re-auth or installation.
    assert (
        "login" in msg.lower()
        or "install" in msg.lower()
        or "path" in msg.lower()
    ), f"AuthError must hint at re-auth/install. Got: {msg!r}"


# ---------------------------------------------------------------------------
# ADP-08 path 2: auth marker substring -> AdapterAuthError
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stderr_text",
    [
        "Error: not logged in",                          # exact lowercase marker
        "ERROR: NOT LOGGED IN",                          # uppercase variant
        "Authentication required to continue",           # different marker
        "no credentials available for this session",     # marker buried in message
        "Please run `gemini auth login` to continue",    # vendor-specific marker
    ],
)
def test_invoke_raises_adapter_auth_error_on_auth_marker_in_output(
    fp, stderr_text: str
) -> None:
    """When the CLI exits 0 (or non-zero) but its output contains a known
    auth-error marker, the mixin must raise AdapterAuthError -- not a generic
    AdapterError, because the user-facing message differs (re-auth instructions
    vs runtime failure dump).

    Markers are matched case-insensitively as substrings of stdout+stderr
    combined, so all five variants above must trigger AdapterAuthError. The
    fifth variant exercises a Gemini-specific marker (``please run `gemini
    auth login```) verifying that backticks in the marker do not break
    substring matching.
    """

    fp.register(
        ["gemini", "-p"],
        stdout="",
        stderr=stderr_text,
        returncode=1,
    )

    with pytest.raises(AdapterAuthError) as exc_info:
        GeminiAdapter().invoke("hi", timeout=5)

    assert "gemini" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# ADP-04 / Pitfall #5: TimeoutExpired -> process-tree kill + AdapterError
# ---------------------------------------------------------------------------


def test_invoke_kills_process_tree_and_raises_on_timeout(fp, monkeypatch) -> None:
    """When the child times out, the mixin MUST:
      1. Call _kill_process_tree(proc) before re-raising.
      2. Re-raise as AdapterError (not bare TimeoutExpired) with the cli_name
         in the message.

    We register a fake process whose callback raises TimeoutExpired (the
    pytest-subprocess thread re-raises it on communicate's _finalize_thread),
    then monkeypatch _kill_process_tree to record that it was called. This
    proves the cleanup path runs without us needing to fork a real child on
    POSIX or Windows in CI.
    """

    kill_calls: list[object] = []

    from ultra_claude.adapters import _SubprocessAdapterMixin as Mixin

    def fake_kill(proc) -> None:
        kill_calls.append(proc)

    monkeypatch.setattr(Mixin, "_kill_process_tree", staticmethod(fake_kill))

    def timeout_callback(process):
        raise subprocess.TimeoutExpired(cmd=["gemini", "-p"], timeout=1)

    fp.register(
        ["gemini", "-p"],
        callback=timeout_callback,
    )

    with pytest.raises(AdapterError) as exc_info:
        GeminiAdapter().invoke("hi", timeout=1)

    assert len(kill_calls) >= 1, (
        "Mixin must call _kill_process_tree on TimeoutExpired before re-raising"
    )
    msg = str(exc_info.value)
    assert "gemini" in msg.lower()
    assert "tim" in msg.lower(), f"Timeout message expected. Got: {msg!r}"
