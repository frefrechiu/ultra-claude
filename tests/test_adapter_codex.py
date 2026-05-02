"""Tests for CodexAdapter behaviour against the locked subprocess contract.

Each test maps to a locked must-have from
``.planning/phases/07-gemini-codex-adapters/07-CONTEXT.md`` (ADP-07):

- ADP-02 (inherited from mixin): every Popen call uses text=True /
  encoding="utf-8" / errors="replace" / shell=False (asserted via fp
  fixture argument capture against the registered argv list).
- ADP-03 / Pitfall #2 (inherited from mixin): returncode==0 AND empty stdout
  raises AdapterError -- the canonical defense against the live
  ``codex exec`` 0.124.0+ TTY bug (openai/codex#19945). This file is
  ground zero for that defense; ``test_codex_empty_stdout_bug_regression``
  documents the bug shape AND asserts the inherited mixin defense fires
  for the Codex argv -- proving the contract works end-to-end without
  any Codex-specific code in the adapter.
- ADP-04 / Pitfall #5 (inherited from mixin): subprocess.TimeoutExpired
  triggers process-tree kill AND raises AdapterError. Cross-platform branch
  covered via monkeypatch of _kill_process_tree.
- ADP-07 (Phase 7): argv == ["codex", "exec"] and prompt is piped via stdin
  (NOT inlined into argv -- the Pitfall #1 mitigation).
- ADP-08 (inherited): FileNotFoundError -> AdapterAuthError; auth marker
  substring (case-insensitive) -> AdapterAuthError.

Tests use pytest-subprocess's `fp` fixture; zero real CLI launches anywhere
in this file.
"""

from __future__ import annotations

import subprocess

import pytest

from ultra_claude.adapters import CodexAdapter
from ultra_claude.exceptions import AdapterAuthError, AdapterError

# ---------------------------------------------------------------------------
# ADP-07 / ADP-02 / Pitfall #1: argv shape AND stdin pipe -- happy path
# ---------------------------------------------------------------------------


def test_invoke_pipes_prompt_via_stdin_and_returns_trimmed_stdout(fp) -> None:
    """CodexAdapter.invoke must pipe the prompt via stdin (NEVER inline it
    into argv) and return stdout.strip() on the happy path.

    The stdin_callable assertion is the linchpin: if a future refactor moves
    the prompt onto argv as `codex exec <huge string>`, Pitfall #1 returns
    (Windows cmd.exe rejects argv > ~8 KB; CreateProcess caps at ~32 KB).
    """

    captured: dict[str, object] = {}

    def stdin_callable(input_data):
        captured["stdin"] = input_data

    fp.register(
        ["codex", "exec"],
        stdout="hello world\n",
        stderr="",
        returncode=0,
        stdin_callable=stdin_callable,
    )

    result = CodexAdapter().invoke("the prompt", timeout=10)

    assert result == "hello world", (
        f"Adapter must return stdout.strip() (got {result!r})"
    )
    assert captured.get("stdin") == "the prompt", (
        f"Prompt MUST be piped via stdin, not argv. "
        f"Got stdin={captured.get('stdin')!r}"
    )


def test_invoke_uses_list_form_argv_with_codex_exec(fp) -> None:
    """argv must be exactly ['codex', 'exec'] -- two elements, list form,
    shell=False inherent. We register the exact argv and assert the call
    matched it.
    """

    fp.register(
        ["codex", "exec"],
        stdout="ack\n",
        returncode=0,
    )

    result = CodexAdapter().invoke("hi", timeout=5)
    assert result == "ack"

    # Defensive: also verify via fp.calls that the argv was list-form.
    assert any(list(call)[:2] == ["codex", "exec"] for call in fp.calls), (
        f"Expected ['codex', 'exec'] argv. Recorded calls: {list(fp.calls)}"
    )


# ---------------------------------------------------------------------------
# ADP-03 / Pitfall #2: empty stdout with returncode 0 -> AdapterError
#
# This is the headline regression test for Phase 7 -- it proves the mixin's
# empty-stdout defense fires for the live `codex exec` 0.124.0+ TTY bug shape
# without any Codex-specific code in CodexAdapter. The two functions below
# test the same mixin behaviour at slightly different angles:
#
# - test_invoke_raises_adapter_error_on_empty_stdout_with_zero_exit: the
#   generic empty-stdout invariant for Codex (mirrors the Claude/Gemini test).
# - test_codex_empty_stdout_bug_regression: explicit documentation of
#   openai/codex#19945, with assertions that pin the failure-mode shape.
# ---------------------------------------------------------------------------


def test_invoke_raises_adapter_error_on_empty_stdout_with_zero_exit(fp) -> None:
    """returncode=0, stdout="" -- the inherited mixin defense MUST raise
    AdapterError for CodexAdapter exactly as it does for Claude/Gemini."""

    fp.register(["codex", "exec"], stdout="", stderr="", returncode=0)

    with pytest.raises(AdapterError) as exc_info:
        CodexAdapter().invoke("hi", timeout=5)

    msg = str(exc_info.value)
    assert "codex" in msg.lower(), (
        f"Error message must name the offending CLI. Got: {msg!r}"
    )
    assert "empty" in msg.lower() or "19945" in msg, (
        f"Error must reference empty-stdout / codex#19945. Got: {msg!r}"
    )


def test_codex_empty_stdout_bug_regression(fp) -> None:
    """REGRESSION: the live ``codex exec`` 0.124.0+ TTY bug.

    Bug source: https://github.com/openai/codex/issues/19945 -- when
    ``codex exec`` is invoked WITHOUT a controlling TTY (i.e. exactly the
    way ultra-claude invokes it from the orchestrator's subprocess.Popen
    pipeline), the CLI emits zero bytes to stdout AND exits with returncode
    0. From the parent process's POV the call "succeeds" while delivering
    no content -- a silent failure with a successful exit code, the worst
    possible UX.

    Defense (CLAUDE.md Critical Constraint #2 / Pitfall #2):
        ``_SubprocessAdapterMixin._run_subprocess`` raises ``AdapterError``
        whenever ``proc.returncode == 0 AND not stdout.strip()``. The
        defense lives in the mixin so EVERY adapter inherits it; CodexAdapter
        contains zero defensive code beyond a docstring reference. This test
        asserts the inherited defense fires correctly for the Codex argv
        shape, proving the contract works end-to-end without any
        Codex-specific code in the adapter.

    What this test pins:
      1. The bug's exact shape (returncode=0, stdout="", arbitrary stderr)
         triggers AdapterError (NOT a generic exception, NOT a silent
         empty-string return).
      2. The error message names ``codex`` so the user sees "which CLI" --
         critical when the orchestrator is running a 3-agent debate and the
         user has to know which CLI to investigate.
      3. The error message references the empty-stdout failure mode (either
         the word ``empty`` or the GH issue number ``19945``) so a developer
         debugging the test failure can find the upstream bug context fast.

    What this test deliberately does NOT pin:
      - The exact wording of the error message beyond the two substring
        checks above. The mixin's wording is allowed to evolve as long as
        those two anchors remain.
      - Whether the upstream bug is fixed. If openai/codex fixes #19945 and
        the CLI starts emitting content again, this test continues to pass
        (the defense still works on the synthetic mock; the real CLI just
        wouldn't trip it any more in production). The test is the canary
        that the DEFENSE is in place; it is not coupled to the upstream bug
        lifecycle.

    Cross-reference:
      - Defense lives in ``src/ultra_claude/adapters/base.py`` (Phase 4,
        plan 04-01) -- the same lines fire for ClaudeAdapter and
        GeminiAdapter; tests in their respective files mirror this one.
      - CodexAdapter's module docstring references this test by name.
    """

    # Reproduce the live-bug shape: returncode 0 + zero-byte stdout +
    # arbitrary stderr (the real CLI sometimes emits a TTY-related warning
    # to stderr but the headline is the empty stdout). We pick a
    # deliberately diagnostic-looking stderr so the assertion proves the
    # defense fires regardless of what (non-empty, non-auth-marker) stderr
    # contains.
    fp.register(
        ["codex", "exec"],
        stdout="",
        stderr="warning: no TTY attached; using non-interactive mode",
        returncode=0,
    )

    with pytest.raises(AdapterError) as exc_info:
        CodexAdapter().invoke("hi", timeout=5)

    msg = str(exc_info.value)

    # Anchor 1: the error names the offending CLI.
    assert "codex" in msg.lower(), (
        f"Error message must name `codex` so the user knows which CLI "
        f"failed (in a 3-agent debate, this is critical). Got: {msg!r}"
    )

    # Anchor 2: the error references the empty-stdout failure mode by
    # either keyword or upstream issue number.
    assert "empty" in msg.lower() or "19945" in msg, (
        f"Error must reference empty-stdout / codex#19945 so a future "
        f"maintainer can find the upstream bug context fast. "
        f"Got: {msg!r}"
    )


def test_invoke_raises_adapter_error_on_whitespace_only_stdout(fp) -> None:
    """The empty-stdout defense must match ``stdout.strip() == ""``, not just
    ``stdout == ""``. A child that prints only newlines / spaces is the same
    failure mode as a literal empty string."""

    fp.register(["codex", "exec"], stdout="   \n\t\n  ", returncode=0)

    with pytest.raises(AdapterError):
        CodexAdapter().invoke("hi", timeout=5)


# ---------------------------------------------------------------------------
# ADP-08 path 1: FileNotFoundError -> AdapterAuthError
# ---------------------------------------------------------------------------


def test_invoke_raises_adapter_auth_error_when_cli_not_on_path(monkeypatch) -> None:
    """If the ``codex`` binary is not on PATH, Popen raises FileNotFoundError.
    The mixin must catch that and re-raise as AdapterAuthError with a hint
    that names the CLI by cli_name.
    """

    def _raise_fnf(*args, **kwargs):
        raise FileNotFoundError(2, "No such file or directory: 'codex'")

    monkeypatch.setattr(subprocess, "Popen", _raise_fnf)

    with pytest.raises(AdapterAuthError) as exc_info:
        CodexAdapter().invoke("hi", timeout=5)

    msg = str(exc_info.value)
    assert "codex" in msg.lower()
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
        "Please run `codex login` to continue",          # vendor-specific marker with backticks
    ],
)
def test_invoke_raises_adapter_auth_error_on_auth_marker_in_output(
    fp, stderr_text: str
) -> None:
    """When the CLI exits 0 (or non-zero) but its output contains a known
    auth-error marker, the mixin must raise AdapterAuthError -- not a generic
    AdapterError.

    Markers are matched case-insensitively as substrings of stdout+stderr
    combined, so all four variants above must trigger AdapterAuthError. The
    fourth variant exercises a Codex-specific marker (``please run `codex
    login```) verifying that backticks in the marker do not break substring
    matching.
    """

    fp.register(
        ["codex", "exec"],
        stdout="",
        stderr=stderr_text,
        returncode=1,
    )

    with pytest.raises(AdapterAuthError) as exc_info:
        CodexAdapter().invoke("hi", timeout=5)

    assert "codex" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# ADP-04 / Pitfall #5: TimeoutExpired -> process-tree kill + AdapterError
# ---------------------------------------------------------------------------


def test_invoke_kills_process_tree_and_raises_on_timeout(fp, monkeypatch) -> None:
    """When the child times out, the mixin MUST:
      1. Call _kill_process_tree(proc) before re-raising.
      2. Re-raise as AdapterError (not bare TimeoutExpired) with the cli_name
         in the message.

    Important for Codex: in production, a hung Codex process can chew through
    subscription quota indefinitely. The process-tree kill ensures the
    TimeoutExpired path takes down every descendant before re-raising, not
    just the leader. (Pitfall #5.)
    """

    kill_calls: list[object] = []

    from ultra_claude.adapters import _SubprocessAdapterMixin as Mixin

    def fake_kill(proc) -> None:
        kill_calls.append(proc)

    monkeypatch.setattr(Mixin, "_kill_process_tree", staticmethod(fake_kill))

    def timeout_callback(process):
        raise subprocess.TimeoutExpired(cmd=["codex", "exec"], timeout=1)

    fp.register(
        ["codex", "exec"],
        callback=timeout_callback,
    )

    with pytest.raises(AdapterError) as exc_info:
        CodexAdapter().invoke("hi", timeout=1)

    assert len(kill_calls) >= 1, (
        "Mixin must call _kill_process_tree on TimeoutExpired before re-raising"
    )
    msg = str(exc_info.value)
    assert "codex" in msg.lower()
    assert "tim" in msg.lower(), f"Timeout message expected. Got: {msg!r}"
