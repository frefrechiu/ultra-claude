"""Tests for ultra_claude.stop_conditions.

Covers the 4 ROADMAP success criteria for Phase 5 (STP-01..STP-05) plus
Pitfall #4 (anchored regex defeats naive substring matching) -- the
defining concern of this phase.

Tests construct real Transcript instances on tmp_path (NOT mocks) so the
unanimity-window logic is exercised against actual JSONL sidecar reads.
This catches a class of bug that mock-based tests cannot: a regression
where Keyword inspects the wrong field, reads from markdown instead of
JSONL, or mis-handles empty transcripts.

Requirements coverage: STP-01, STP-02, STP-03, STP-04, STP-05.
"""

from __future__ import annotations

from pathlib import Path

from ultra_claude.stop_conditions import AnyOf, Keyword, MaxTurns, StopCondition
from ultra_claude.transcript import Transcript

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_transcript(tmp_path: Path) -> Transcript:
    """Construct a fresh Transcript at tmp_path/transcript.md."""
    return Transcript(tmp_path / "transcript.md")


def _append(
    transcript: Transcript,
    *,
    turn: int,
    agent: str,
    output: str,
    role: str = "test-role",
    prompt: str = "test-prompt",
) -> None:
    """Convenience writer so tests stay focused on the assertion."""
    transcript.append_turn(
        turn=turn,
        agent=agent,
        role=role,
        prompt=prompt,
        output=output,
    )


# ---------------------------------------------------------------------------
# Test 1 -- STP-01: Protocol structural typing (duck-typed isinstance check)
# ---------------------------------------------------------------------------


def test_stop_condition_protocol_structural(tmp_path: Path) -> None:
    """A duck-typed class with `check(transcript)` is a StopCondition (STP-01)."""

    class FakeStop:
        def check(self, transcript: Transcript) -> bool:
            return False

    class HalfBaked:
        # No check method -- must NOT pass the isinstance probe.
        pass

    assert isinstance(FakeStop(), StopCondition)
    assert not isinstance(HalfBaked(), StopCondition)

    # The three bundled strategies all also satisfy the Protocol.
    assert isinstance(Keyword(["AGREED"]), StopCondition)
    assert isinstance(MaxTurns(12), StopCondition)
    assert isinstance(AnyOf([MaxTurns(12)]), StopCondition)


# ---------------------------------------------------------------------------
# Test 2 -- STP-02 + Pitfall #4: anchored regex rejects naive substring
# ---------------------------------------------------------------------------


def test_keyword_anchored_regex_rejects_substring(tmp_path: Path) -> None:
    """Keyword must NOT fire on prose that contains the keyword (Pitfall #4).

    A naive `"AGREED" in output` check would return True for the sycophancy
    bait line below; the anchored multiline regex `^AGREED\\s*$` rejects it.
    We lower m=1 to isolate the regex from the unanimity-window logic --
    if Keyword fires on this transcript, it's the regex that's broken,
    not the unanimity window.
    """
    transcript = _make_transcript(tmp_path)
    _append(
        transcript,
        turn=1,
        agent="Architect",
        output="I am NOT going to say AGREED yet.",
    )

    # m=1 to disable the unanimity-window safety net for THIS test.
    keyword = Keyword(["AGREED"], n=2, m=1)
    assert keyword.check(transcript) is False


# ---------------------------------------------------------------------------
# Test 3 -- STP-03: unanimity-window happy path (n=2 turns, m=2 distinct agents)
# ---------------------------------------------------------------------------


def test_keyword_unanimity_two_agents_two_turns(tmp_path: Path) -> None:
    """Two distinct agents both saying AGREED in the last 2 turns triggers stop."""
    transcript = _make_transcript(tmp_path)
    _append(
        transcript,
        turn=1,
        agent="Architect",
        output="## Decision\nAGREED",
    )
    _append(
        transcript,
        turn=2,
        agent="Critic",
        output="## Decision\nAGREED",
    )

    # Defaults n=2, m=2.
    keyword = Keyword(["AGREED"])
    assert keyword.check(transcript) is True


# ---------------------------------------------------------------------------
# Test 4 -- STP-03 negative: single agent saying AGREED twice does NOT stop
# ---------------------------------------------------------------------------


def test_keyword_single_agent_self_stop_blocked(tmp_path: Path) -> None:
    """One agent voting itself off the island does NOT trigger stop (STP-03 defense).

    Two turns BOTH from "Architect" both ending in AGREED. The unanimity
    window of m=2 distinct agents requires a SECOND agent to also agree
    before stopping -- this is the entire reason the unanimity-window
    exists.
    """
    transcript = _make_transcript(tmp_path)
    _append(
        transcript,
        turn=1,
        agent="Architect",
        output="On reflection,\nAGREED",
    )
    _append(
        transcript,
        turn=2,
        agent="Architect",
        output="Yes, again:\nAGREED",
    )

    # Defaults n=2, m=2. Only 1 distinct agent in the window -> False.
    keyword = Keyword(["AGREED"])
    assert keyword.check(transcript) is False


# ---------------------------------------------------------------------------
# Test 5 -- STP-04: MaxTurns triggers exactly at the boundary
# ---------------------------------------------------------------------------


def test_max_turns_equality(tmp_path: Path) -> None:
    """MaxTurns(12).check is False at 11 turns, True at 12 turns (STP-04)."""
    transcript = _make_transcript(tmp_path)
    cap = MaxTurns(12)

    # Append 11 turns -- still under cap.
    for i in range(1, 12):
        _append(transcript, turn=i, agent=f"agent-{i}", output=f"turn {i} output")

    assert len(transcript) == 11
    assert cap.check(transcript) is False

    # Append the 12th turn -- now at cap.
    _append(transcript, turn=12, agent="agent-12", output="turn 12 output")

    assert len(transcript) == 12
    assert cap.check(transcript) is True


# ---------------------------------------------------------------------------
# Test 6 -- STP-05: AnyOf short-circuits on first match
# ---------------------------------------------------------------------------


def test_anyof_short_circuit(tmp_path: Path) -> None:
    """AnyOf returns True on the first wrapped match, even with no AGREED in output (STP-05).

    Three turns with no AGREED keyword anywhere. MaxTurns(3) fires at
    turn 3; AnyOf then returns True without needing Keyword to also fire.
    Validates that lazy any(...) evaluation works as documented.
    """
    transcript = _make_transcript(tmp_path)
    _append(transcript, turn=1, agent="Architect", output="design proposal")
    _append(transcript, turn=2, agent="Critic", output="critique")
    _append(transcript, turn=3, agent="Implementer", output="code")

    composite = AnyOf([MaxTurns(3), Keyword(["AGREED"])])
    assert composite.check(transcript) is True

    # Sanity: with MaxTurns(99) (won't fire) AND no AGREED, AnyOf is False.
    composite_loose = AnyOf([MaxTurns(99), Keyword(["AGREED"])])
    assert composite_loose.check(transcript) is False
