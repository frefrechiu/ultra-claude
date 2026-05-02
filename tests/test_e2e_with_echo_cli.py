"""End-to-end orchestrator test using a real Python child process (TST-03 / TST-04).

This test is the difference between "subprocess.Popen was mocked and the
assertions passed" and "the OS pipe between Popen and the child IS wired
correctly on this machine". Every other test in the suite mocks subprocess
at some layer; this one deliberately does not.

The fake CLI is `tests/fixtures/echo_cli.py` -- a standalone Python script
that reads stdin and prints `echo: <stdin>` to stdout. The `EchoAdapter`
defined below inherits from `_SubprocessAdapterMixin` and invokes that
script via `[sys.executable, str(echo_cli_path)]`, exercising the SAME
production code path that `ClaudeAdapter` / `GeminiAdapter` / `CodexAdapter`
use against their respective vendor CLIs.

Why two tests:
    1. test_run_against_echo_cli_writes_real_transcript -- happy path,
       proves the orchestrator drives a real Popen pipeline to completion.
    2. test_echo_cli_handles_utf8_round_trip -- defends against Windows
       cp1252 regression at the mixin level (Pitfall #3). LLMs emit smart
       quotes / em-dashes / emoji constantly; if the mixin's encoding="utf-8"
       were ever silently dropped, this test would fail loudly on Windows.

Requirements coverage: TST-03, TST-04.
"""

from __future__ import annotations

import sys
from pathlib import Path

from ultra_claude.adapters.base import Adapter, _SubprocessAdapterMixin
from ultra_claude.config import AgentConfig, RoundtableConfig
from ultra_claude.orchestrator import run as orchestrate
from ultra_claude.transcript import Transcript

# ---------------------------------------------------------------------------
# Fixture path: the standalone echo_cli.py script (lives next door)
# ---------------------------------------------------------------------------

_ECHO_CLI_PATH: Path = Path(__file__).parent / "fixtures" / "echo_cli.py"


# ---------------------------------------------------------------------------
# EchoAdapter -- inherits from _SubprocessAdapterMixin so the SAME safe-
# subprocess code path the production adapters use is exercised here.
# ---------------------------------------------------------------------------


class EchoAdapter(_SubprocessAdapterMixin):
    """Adapter that invokes `python <echo_cli.py>` instead of a vendor CLI.

    Structurally satisfies the `Adapter` Protocol (has `name: str` and
    `invoke(prompt, timeout) -> str`) AND inherits the safe-subprocess
    contract from `_SubprocessAdapterMixin`. So the production
    `_run_subprocess` method is what actually launches the child process,
    pipes the prompt via stdin, and reads stdout.

    The two mixin requirements:
        * `cli_name: str` -- used in error messages (we set "echo")
        * `auth_error_markers: tuple[str, ...]` -- empty here because
          the echo script never emits auth markers. The mixin's
          case-insensitive substring loop on an empty tuple is a no-op.
    """

    name: str = "echo"
    cli_name: str = "echo"
    auth_error_markers: tuple[str, ...] = ()

    def invoke(self, prompt: str, timeout: int) -> str:
        return self._run_subprocess(
            [sys.executable, str(_ECHO_CLI_PATH)],
            prompt,
            timeout,
        )


def _agent(name: str) -> AgentConfig:
    """Build an AgentConfig fixture. ``adapter`` is 'claude' purely as a
    valid Literal value; the registry is bypassed via adapter_factory."""
    return AgentConfig(
        name=name,
        role="echoer",
        adapter="claude",
        system_prompt="echo whatever you receive",
    )


# ---------------------------------------------------------------------------
# Test 1 -- happy path: real Popen, real pipe, real stdout round trip.
# ---------------------------------------------------------------------------


def test_run_against_echo_cli_writes_real_transcript(tmp_path: Path) -> None:
    """orchestrator.run() drives a real Popen pipeline to completion.

    NO subprocess mocking. NO pytest-subprocess fp fixture. The bytes
    really do flow:
        orchestrator -> EchoAdapter.invoke -> _SubprocessAdapterMixin._run_subprocess
            -> subprocess.Popen([python, echo_cli.py]) -> echo_cli stdout
            -> back into orchestrator -> Transcript.append_turn

    Asserts:
        * The returned path exists
        * Exactly max_turns turns recorded
        * Every recorded output starts with the literal `echo: `
        * Each turn's prompt was successfully piped through stdin
          (otherwise the echo prefix would be present but the body would
          be empty)
    """
    config = RoundtableConfig(
        agents=[_agent("alpha"), _agent("beta")],
        max_turns=4,
        # Stop_keyword that the echo script can never emit so MaxTurns
        # is the only stop trigger -- "echo: <prompt>" never starts with
        # exactly "AGREED" alone on a line.
        stop_keywords=["IMPOSSIBLE-MARKER-NEVER-ECHOED"],
    )

    transcript_path = tmp_path / "echo-run.md"
    result = orchestrate(
        config,
        task="Please respond with a one-line answer.",
        transcript_path=transcript_path,
        adapter_factory=lambda _kind: EchoAdapter(),
    )

    # Returned path matches the requested transcript path.
    assert result == transcript_path
    assert result.exists()

    # Reconstruct the recorded turns and inspect each one.
    transcript = Transcript(transcript_path)
    turns = transcript.read_turns()
    assert len(turns) == 4, f"expected 4 turns, got {len(turns)}"

    # Round-robin order: alpha, beta, alpha, beta.
    assert [t.agent for t in turns] == ["alpha", "beta", "alpha", "beta"]

    # Every turn's output starts with `echo: ` -- proving bytes round-tripped.
    for idx, turn in enumerate(turns, start=1):
        assert turn.output.startswith("echo:"), (
            f"turn {idx} output did not start with 'echo:': "
            f"{turn.output[:80]!r}"
        )
        # And contains the original task somewhere downstream of the echo
        # prefix (the orchestrator includes the task in the prompt; the
        # echo script returns the prompt verbatim).
        assert "Please respond with a one-line answer." in turn.output, (
            f"turn {idx} output did not contain the task verbatim"
        )


# ---------------------------------------------------------------------------
# Test 2 -- UTF-8 round trip through the real Popen pipe.
# ---------------------------------------------------------------------------


def test_echo_cli_handles_utf8_round_trip(tmp_path: Path) -> None:
    """em-dash + smart quotes + emoji + Chinese ideograph survive the round trip.

    Defends against silent Windows cp1252 corruption at the mixin layer
    (Pitfall #3). If `_SubprocessAdapterMixin._run_subprocess` ever loses
    its `encoding="utf-8"` kwargs, this test fails loudly on Windows.

    The Python world being Python, on POSIX this test passes regardless
    because the default locale is usually UTF-8. The value is on
    Windows -- which is exactly the platform v0.1.0 must support.
    """
    # The test source stays ASCII-only on disk by expressing every non-
    # ASCII codepoint via Python `\uXXXX` / `\U0001XXXX` escape sequences.
    # At parse time these decode to the corresponding UTF-8 byte
    # sequences in memory; the echo script must round-trip those bytes
    # unmodified through the OS pipe.
    #   \u201c \u201d   -- LEFT/RIGHT DOUBLE QUOTATION MARK (smart curly)
    #   \u2014          -- EM DASH
    #   \U0001F680      -- ROCKET (commonly emitted emoji)
    #   \u4e2d \u6587   -- the two ideographs for "Chinese"
    utf8_task = (
        "Compare \u201cundo\u201d vs \u2014 reset \U0001F680 \u4e2d\u6587"
    )

    config = RoundtableConfig(
        agents=[_agent("alpha"), _agent("beta")],
        max_turns=2,
        stop_keywords=["IMPOSSIBLE-MARKER-NEVER-ECHOED"],
    )

    transcript_path = tmp_path / "utf8-run.md"
    orchestrate(
        config,
        task=utf8_task,
        transcript_path=transcript_path,
        adapter_factory=lambda _kind: EchoAdapter(),
    )

    transcript = Transcript(transcript_path)
    turns = transcript.read_turns()
    assert len(turns) == 2

    # Each turn's output contains the full UTF-8 task verbatim -- no
    # `?` placeholder bytes, no U+FFFD REPLACEMENT CHARACTERs.
    replacement_char = "\ufffd"
    for turn in turns:
        assert utf8_task in turn.output, (
            f"UTF-8 task did not survive round trip; got: {turn.output!r}"
        )
        # Defensive: no replacement characters (means errors='replace'
        # had to swap a byte; that is a regression).
        assert replacement_char not in turn.output


# ---------------------------------------------------------------------------
# Self-check: EchoAdapter structurally satisfies the Adapter Protocol.
# ---------------------------------------------------------------------------


def test_echo_adapter_satisfies_adapter_protocol() -> None:
    """EchoAdapter must satisfy the Adapter Protocol at runtime.

    The orchestrator does not check this -- it duck-types -- but if it
    ever did (or if a future plan wires runtime_checkable Protocol
    isinstance into the orchestrator), this test makes the constraint
    explicit.
    """
    adapter = EchoAdapter()
    assert isinstance(adapter, Adapter)
    assert adapter.name == "echo"
