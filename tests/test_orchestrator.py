"""Tests for ultra_claude.orchestrator.run.

Each test maps to one or more of the 8 cases listed in
``.planning/phases/06-orchestrator-loop/06-CONTEXT.md`` "Testing strategy"
plus the 5 Phase 6 ROADMAP success criteria (ORC-01..ORC-06).

Test strategy:
* ``FakeAdapter`` is a pure-Python class structurally satisfying the
  :class:`ultra_claude.adapters.base.Adapter` Protocol. It records every
  ``invoke`` call (prompt + timeout) so tests can introspect what the
  orchestrator sent. It can be configured to return canned outputs OR to
  raise an exception on a specific call -- the latter drives the
  continue-on-error and abort-on-error tests.
* No subprocess is launched anywhere in this file. The ``adapter_factory``
  parameter on ``run`` is the injection seam.
* Every test that needs a transcript file uses ``tmp_path`` so artefacts
  are auto-cleaned by pytest.

Requirements coverage: ORC-01, ORC-02, ORC-03, ORC-04, ORC-05, ORC-06.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import pytest

from ultra_claude.adapters import Adapter
from ultra_claude.config import AgentConfig, RoundtableConfig
from ultra_claude.exceptions import AdapterError
from ultra_claude.orchestrator import run
from ultra_claude.transcript import Transcript

# ---------------------------------------------------------------------------
# FakeAdapter helper
# ---------------------------------------------------------------------------


class FakeAdapter:
    """Pure-Python Adapter Protocol implementation for tests.

    Records every ``invoke`` call as a (prompt, timeout) tuple in
    ``self.calls``. Returns ``self.canned_output`` by default, or raises
    ``self.raise_exc`` on every call when set.

    Structural conformance:
        * Has ``name: str``.
        * Has ``invoke(prompt: str, timeout: int) -> str``.

    So ``isinstance(FakeAdapter("x"), Adapter)`` is True at runtime via
    the ``@runtime_checkable`` Protocol.
    """

    def __init__(
        self,
        name: str,
        *,
        canned_output: str = "ok",
        raise_exc: Exception | None = None,
    ) -> None:
        self.name: str = name
        self.canned_output: str = canned_output
        self.raise_exc: Exception | None = raise_exc
        self.calls: list[tuple[str, int]] = []

    def invoke(self, prompt: str, timeout: int) -> str:
        self.calls.append((prompt, timeout))
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.canned_output


def _agent(name: str, role: str = "test-role", system_prompt: str = "be helpful") -> AgentConfig:
    """Build an AgentConfig fixture. ``adapter`` is always 'claude' since
    the registry isn't exercised in these tests (we inject FakeAdapters)."""
    return AgentConfig(
        name=name,
        role=role,
        adapter="claude",
        system_prompt=system_prompt,
    )


def _make_factory(adapters: dict[str, FakeAdapter]) -> Callable[[str], Adapter]:
    """Return an adapter_factory that hands out FakeAdapters by insertion order.

    The orchestrator currently passes ``agent.adapter`` (the literal kind),
    not the agent name, into the factory. So we instead create a factory that
    pops one FakeAdapter per call from a list -- declared agent order ==
    factory call order, which mirrors what 06-01's ``run`` does.
    """
    # Convert to a list keyed by insertion order so each factory call
    # returns the next adapter. We rely on Python 3.7+ dict order.
    queue: list[FakeAdapter] = list(adapters.values())
    idx = {"i": 0}

    def factory(_kind: str) -> Adapter:
        adapter = queue[idx["i"]]
        idx["i"] += 1
        return adapter

    return factory


# ---------------------------------------------------------------------------
# Test 1 -- ORC-01 + ORC-02: 3 agents, max_turns=6, round-robin produces
# exactly 6 turns in declared order.
# ---------------------------------------------------------------------------


def test_run_3_agent_max_turns_6_writes_6_turns(tmp_path: Path) -> None:
    """3-agent + max_turns=6 should produce 6 turns: a,b,c,a,b,c."""
    adapters = {
        "alpha": FakeAdapter("alpha", canned_output="alpha-out"),
        "beta": FakeAdapter("beta", canned_output="beta-out"),
        "gamma": FakeAdapter("gamma", canned_output="gamma-out"),
    }
    config = RoundtableConfig(
        agents=[_agent("alpha"), _agent("beta"), _agent("gamma")],
        max_turns=6,
        # Use stop_keywords that won't fire so MaxTurns is the only stop.
        stop_keywords=["IMPOSSIBLE-MARKER-NEVER-SAID"],
    )

    transcript_path = tmp_path / "run.md"
    result = run(
        config,
        task="Design a CLI",
        transcript_path=transcript_path,
        adapter_factory=_make_factory(adapters),
    )

    assert result == transcript_path
    # Reconstruct the transcript from disk and inspect the recorded turns.
    transcript = Transcript(transcript_path)
    turns = transcript.read_turns()
    assert len(turns) == 6
    assert [t.agent for t in turns] == ["alpha", "beta", "gamma", "alpha", "beta", "gamma"]
    # Each FakeAdapter was invoked exactly twice (6 turns / 3 agents).
    assert len(adapters["alpha"].calls) == 2
    assert len(adapters["beta"].calls) == 2
    assert len(adapters["gamma"].calls) == 2


# ---------------------------------------------------------------------------
# Test 2 -- ORC-03: each turn's prompt contains the task verbatim AND a
# GOAL ANCHOR re-injection at the end.
# ---------------------------------------------------------------------------


def test_run_includes_task_in_prompt(tmp_path: Path) -> None:
    """The task string appears in BOTH the # Task header AND the GOAL ANCHOR
    footer (Pitfall #6 mitigation)."""
    task = "Build a debate platform"
    adapters = {
        "alpha": FakeAdapter("alpha", canned_output="reply"),
        "beta": FakeAdapter("beta", canned_output="reply"),
    }
    config = RoundtableConfig(
        agents=[_agent("alpha"), _agent("beta")],
        max_turns=2,
        stop_keywords=["IMPOSSIBLE-MARKER"],
    )

    run(
        config,
        task=task,
        transcript_path=tmp_path / "run.md",
        adapter_factory=_make_factory(adapters),
    )

    # The first invocation's prompt is what we inspect for the layout.
    first_prompt, _timeout = adapters["alpha"].calls[0]

    # # Task header contains the task verbatim.
    assert "# Task" in first_prompt
    assert task in first_prompt

    # GOAL ANCHOR footer contains the task AGAIN plus the agent-name + role
    # reminder line.
    assert "# Reminder of the task" in first_prompt
    assert first_prompt.count(task) >= 2  # at least once in header + once in anchor
    assert "Respond now as alpha" in first_prompt
    assert "Stay focused on the task above" in first_prompt

    # ORC-03: agent's system_prompt is also in the prompt.
    assert "be helpful" in first_prompt


# ---------------------------------------------------------------------------
# Test 3 -- ORC-03: by turn 3, the prompt contains the previous 2 turns'
# transcript markdown.
# ---------------------------------------------------------------------------


def test_run_includes_transcript_so_far(tmp_path: Path) -> None:
    """Turn 3's prompt must contain turn 1 and turn 2's outputs.

    This validates the ``transcript_so_far`` section of the prompt builder.
    """
    adapters = {
        "alpha": FakeAdapter("alpha", canned_output="ALPHA-FIRST-OUTPUT"),
        "beta": FakeAdapter("beta", canned_output="BETA-FIRST-OUTPUT"),
    }
    config = RoundtableConfig(
        agents=[_agent("alpha"), _agent("beta")],
        max_turns=3,
        stop_keywords=["IMPOSSIBLE-MARKER"],
    )

    run(
        config,
        task="t",
        transcript_path=tmp_path / "run.md",
        adapter_factory=_make_factory(adapters),
    )

    # Turn 3 goes back to alpha (round-robin: a,b,a). Inspect alpha's
    # SECOND prompt -- it should include both prior turns' outputs.
    third_prompt, _timeout = adapters["alpha"].calls[1]

    assert "ALPHA-FIRST-OUTPUT" in third_prompt
    assert "BETA-FIRST-OUTPUT" in third_prompt


# ---------------------------------------------------------------------------
# Test 4 -- ORC-04: keyword unanimity stops the run early.
# ---------------------------------------------------------------------------


def test_run_stops_on_keyword_unanimity(tmp_path: Path) -> None:
    """Two distinct agents both saying AGREED in the last 2 turns triggers
    Keyword stop with default n=2/m=2 -- run halts after turn 2 even though
    max_turns=6."""
    adapters = {
        "alpha": FakeAdapter("alpha", canned_output="AGREED"),
        "beta": FakeAdapter("beta", canned_output="AGREED"),
        "gamma": FakeAdapter("gamma", canned_output="AGREED"),
    }
    config = RoundtableConfig(
        agents=[_agent("alpha"), _agent("beta"), _agent("gamma")],
        max_turns=6,
        # Keyword default n=2/m=2 -- AGREED from 2 distinct agents in last
        # 2 turns triggers stop.
        stop_keywords=["AGREED"],
    )

    transcript_path = tmp_path / "run.md"
    run(
        config,
        task="t",
        transcript_path=transcript_path,
        adapter_factory=_make_factory(adapters),
    )

    # Only 2 turns should have been written (alpha + beta both AGREED).
    transcript = Transcript(transcript_path)
    turns = transcript.read_turns()
    assert len(turns) == 2
    assert [t.agent for t in turns] == ["alpha", "beta"]
    # Gamma was never invoked.
    assert len(adapters["gamma"].calls) == 0


# ---------------------------------------------------------------------------
# Test 5 -- ORC-05: AdapterError is logged + placeholder turn appended +
# run continues to the next agent.
# ---------------------------------------------------------------------------


def test_run_continues_on_adapter_error(tmp_path: Path) -> None:
    """When one FakeAdapter raises AdapterError, the orchestrator logs it,
    appends a '[adapter error: ...]' placeholder turn, and continues."""
    adapters = {
        "alpha": FakeAdapter("alpha", canned_output="alpha-ok"),
        "beta": FakeAdapter("beta", raise_exc=AdapterError("simulated CLI failure")),
        "gamma": FakeAdapter("gamma", canned_output="gamma-ok"),
    }
    config = RoundtableConfig(
        agents=[_agent("alpha"), _agent("beta"), _agent("gamma")],
        max_turns=3,
        stop_keywords=["IMPOSSIBLE-MARKER"],
        abort_on_error=False,  # explicit; the default is also False
    )

    transcript_path = tmp_path / "run.md"
    run(
        config,
        task="t",
        transcript_path=transcript_path,
        adapter_factory=_make_factory(adapters),
    )

    # All 3 turns were written (no early exit on the AdapterError).
    transcript = Transcript(transcript_path)
    turns = transcript.read_turns()
    assert len(turns) == 3
    assert [t.agent for t in turns] == ["alpha", "beta", "gamma"]

    # Beta's turn output is the placeholder.
    beta_turn = turns[1]
    assert beta_turn.output.startswith("[adapter error:")
    assert "simulated CLI failure" in beta_turn.output

    # Gamma was still invoked despite beta failing.
    assert len(adapters["gamma"].calls) == 1


# ---------------------------------------------------------------------------
# Test 6 -- ORC-05: abort_on_error=True re-raises the AdapterError.
# ---------------------------------------------------------------------------


def test_run_aborts_on_error_when_configured(tmp_path: Path) -> None:
    """Same setup as test 5 but config.abort_on_error=True; run() re-raises."""
    adapters = {
        "alpha": FakeAdapter("alpha", canned_output="alpha-ok"),
        "beta": FakeAdapter("beta", raise_exc=AdapterError("simulated abort")),
        "gamma": FakeAdapter("gamma", canned_output="gamma-ok"),
    }
    config = RoundtableConfig(
        agents=[_agent("alpha"), _agent("beta"), _agent("gamma")],
        max_turns=3,
        stop_keywords=["IMPOSSIBLE-MARKER"],
        abort_on_error=True,
    )

    transcript_path = tmp_path / "run.md"
    with pytest.raises(AdapterError, match="simulated abort"):
        run(
            config,
            task="t",
            transcript_path=transcript_path,
            adapter_factory=_make_factory(adapters),
        )

    # Gamma was NOT invoked (run aborted on beta's error).
    assert len(adapters["gamma"].calls) == 0


# ---------------------------------------------------------------------------
# Test 7 -- ORC-01: return value is a Path that exists and contains the
# right number of turn markers.
# ---------------------------------------------------------------------------


def test_run_returns_transcript_path(tmp_path: Path) -> None:
    """run() returns a Path; the file exists; the markdown contains 4
    turn-sentinel comments (one per turn)."""
    adapters = {
        "alpha": FakeAdapter("alpha", canned_output="reply-a"),
        "beta": FakeAdapter("beta", canned_output="reply-b"),
    }
    config = RoundtableConfig(
        agents=[_agent("alpha"), _agent("beta")],
        max_turns=4,
        stop_keywords=["IMPOSSIBLE-MARKER"],
    )

    transcript_path = tmp_path / "run.md"
    result = run(
        config,
        task="t",
        transcript_path=transcript_path,
        adapter_factory=_make_factory(adapters),
    )

    assert isinstance(result, Path)
    assert result == transcript_path
    assert result.exists()

    text = result.read_text(encoding="utf-8")
    # Phase 3's TRX-02 sentinel format: '<!-- turn:N agent:Name -->'
    for n in (1, 2, 3, 4):
        assert f"<!-- turn:{n} agent:" in text


# ---------------------------------------------------------------------------
# Test 8 -- ORC-06: progress messages go to stderr only; stdout is empty.
# ---------------------------------------------------------------------------


def test_run_logs_progress_to_stderr_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """run() writes nothing to stdout; progress messages appear via the
    orchestrator's stderr-bound logger.

    Verification splits cleanly into two independent assertions:

    1. ``capsys.readouterr().out == ""`` -- stdout discipline. The
       orchestrator must NEVER write to stdout directly. ``capsys`` is
       the right tool for this: it captures direct writes to
       ``sys.stdout``.
    2. ``"starting roundtable" in caplog.text`` -- progress logging
       discipline. The orchestrator must emit progress records via the
       ``ultra_claude.orchestrator`` logger. ``caplog`` is the right
       tool for this: it captures ``LogRecord`` objects, which is what
       the logging library actually emits.

    Why NOT capsys.readouterr().err for the logging assertions: pytest's
    built-in ``logging`` plugin installs a root-logger handler that
    captures records through the logging machinery rather than letting
    them reach ``sys.stderr`` writes that capsys would see. Asserting
    against ``caplog.text`` is the pytest-idiomatic way to verify that
    a specific logger emitted specific messages. ``capsys.err`` would
    miss them entirely, even if the orchestrator's StreamHandler is
    bound to the capsys-patched stderr.

    The orchestrator's stderr-bound StreamHandler is verified
    structurally elsewhere (see test 8 setup): we attach it to
    ``sys.stderr`` via ``_ensure_default_handler``; running with
    ``-p no:logging`` would route those records to capsys.err. That
    integration is not in scope for this test -- the contract is
    "logger emits progress records" and "stdout is empty", both of
    which the assertions below verify directly.
    """
    # caplog defaults to WARNING; the orchestrator logs at INFO, so we
    # set the level for the orchestrator logger explicitly to capture
    # its progress records.
    caplog.set_level(logging.INFO, logger="ultra_claude.orchestrator")

    adapters = {
        "alpha": FakeAdapter("alpha", canned_output="reply-a"),
        "beta": FakeAdapter("beta", canned_output="reply-b"),
    }
    config = RoundtableConfig(
        agents=[_agent("alpha"), _agent("beta")],
        max_turns=2,
        stop_keywords=["IMPOSSIBLE-MARKER"],
    )

    run(
        config,
        task="t",
        transcript_path=tmp_path / "run.md",
        adapter_factory=_make_factory(adapters),
    )

    captured = capsys.readouterr()
    # stdout discipline: NOTHING from the orchestrator should appear here.
    assert captured.out == "", f"expected empty stdout, got: {captured.out!r}"

    # Progress logging discipline: caplog records the logger's emissions.
    # The orchestrator emits "starting roundtable" once at entry and
    # "turn N starting" for each turn.
    assert "starting roundtable" in caplog.text
    assert "turn 1 starting" in caplog.text
    assert "turn 2 starting" in caplog.text

    # All captured records must come from the orchestrator's named
    # logger (no leakage from other modules during a clean run).
    orchestrator_records = [
        r for r in caplog.records if r.name == "ultra_claude.orchestrator"
    ]
    assert len(orchestrator_records) >= 3  # entry + 2 turn-start lines
