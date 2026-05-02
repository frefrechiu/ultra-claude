"""Tests for ultra_claude.transcript.

Covers the four success criteria for Phase 3 (TRX-01..TRX-05) plus three
auxiliary cases locked by ``03-CONTEXT.md``:

* D-08: ``read_turns()`` returns ``[]`` when the JSONL sidecar is missing.
* D-10: Constructing a Transcript at a path with existing markdown does not
  erase it -- subsequent ``append_turn`` calls extend rather than truncate.
* D-11: Constructing a Transcript whose parent directory does not exist raises
  ``OSError`` -- the orchestrator is responsible for ``mkdir``, not us.

Tests use pytest's ``tmp_path`` fixture for isolated file IO per test, mirror
the layout of ``tests/test_config.py``, and assert against raw bytes for the
LF-only-on-disk check so a regression on Windows surfaces as a clear failure
rather than a string-equality false positive.

Requirements coverage: TRX-01, TRX-02, TRX-03, TRX-04, TRX-05.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from ultra_claude.transcript import Transcript, TurnRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _three_turn_payload() -> list[dict[str, str]]:
    """Synthetic 3-turn fixture used by several tests."""
    return [
        {
            "agent": "Architect",
            "role": "high-level design",
            "prompt": "Design the system",
            "output": "I propose a layered architecture with X and Y.",
        },
        {
            "agent": "Critic",
            "role": "skeptic",
            "prompt": "Find flaws",
            "output": "Layer X duplicates concerns from layer Y.",
        },
        {
            "agent": "Implementer",
            "role": "hands-on coder",
            "prompt": "Write code",
            "output": "Here is the consolidated module.",
        },
    ]


# ---------------------------------------------------------------------------
# Test 1 -- TRX-01: append (not rewrite) after every turn
# ---------------------------------------------------------------------------


def test_three_turn_round_trip_appends_to_markdown(tmp_path: Path) -> None:
    """Each append_turn call must strictly grow the markdown file (TRX-01)."""
    md = tmp_path / "transcript.md"
    transcript = Transcript(md, header_task="Synthetic 3-turn test")

    sizes: list[int] = []
    for turn_index, payload in enumerate(_three_turn_payload(), start=1):
        transcript.append_turn(
            turn=turn_index,
            agent=payload["agent"],
            role=payload["role"],
            prompt=payload["prompt"],
            output=payload["output"],
        )
        sizes.append(md.stat().st_size)

    # Strictly increasing -- proves we appended each time, not rewrote.
    assert sizes[0] < sizes[1] < sizes[2], f"file did not grow monotonically: {sizes}"

    # All three outputs are present in order.
    text = md.read_text(encoding="utf-8")
    architect_pos = text.index("layered architecture")
    critic_pos = text.index("duplicates concerns")
    implementer_pos = text.index("consolidated module")
    assert architect_pos < critic_pos < implementer_pos, "outputs not in turn order"

    # Header was written exactly once.
    assert text.count("# Transcript: Synthetic 3-turn test") == 1


# ---------------------------------------------------------------------------
# Test 2 -- TRX-02: HTML-comment sentinel per turn
# ---------------------------------------------------------------------------


def test_each_turn_has_html_comment_sentinel(tmp_path: Path) -> None:
    """Each turn must be delimited by ``<!-- turn:N agent:Name -->`` (TRX-02)."""
    md = tmp_path / "transcript.md"
    transcript = Transcript(md)

    for turn_index, payload in enumerate(_three_turn_payload(), start=1):
        transcript.append_turn(
            turn=turn_index,
            agent=payload["agent"],
            role=payload["role"],
            prompt=payload["prompt"],
            output=payload["output"],
        )

    text = md.read_text(encoding="utf-8")
    # Anchored multiline regex -- mirror what stop conditions will use later.
    matches = re.findall(r"^<!-- turn:(\d+) agent:(\S+) -->$", text, re.MULTILINE)
    assert matches == [
        ("1", "Architect"),
        ("2", "Critic"),
        ("3", "Implementer"),
    ], matches


# ---------------------------------------------------------------------------
# Test 3 -- TRX-03: JSONL sidecar fields and prompt_hash correctness
# ---------------------------------------------------------------------------


def test_jsonl_sidecar_records_match_schema(tmp_path: Path) -> None:
    """The JSONL sidecar must yield one TurnRecord per turn with all 5 fields (TRX-03)."""
    md = tmp_path / "transcript.md"
    transcript = Transcript(md)

    payload = _three_turn_payload()
    for turn_index, item in enumerate(payload, start=1):
        transcript.append_turn(
            turn=turn_index,
            agent=item["agent"],
            role=item["role"],
            prompt=item["prompt"],
            output=item["output"],
        )

    jsonl_path = transcript.jsonl_path
    assert jsonl_path.name == "transcript.md.jsonl", jsonl_path.name

    records = transcript.read_turns()
    assert len(records) == 3
    assert all(isinstance(r, TurnRecord) for r in records)

    for index, (record, item) in enumerate(zip(records, payload, strict=True), start=1):
        assert record.turn == index
        assert record.agent == item["agent"]
        assert record.role == item["role"]
        assert record.output == item["output"]
        # prompt_hash is the SHA-256 hex digest of the UTF-8-encoded prompt.
        expected_hash = hashlib.sha256(item["prompt"].encode("utf-8")).hexdigest()
        assert record.prompt_hash == expected_hash
        assert len(record.prompt_hash) == 64
        assert record.prompt_hash == record.prompt_hash.lower()  # hex is lowercase

    # Raw JSONL parse: 3 lines, each is a complete JSON object with exactly
    # the 5 expected keys (no extras leak in via Pydantic).
    raw_lines = [ln for ln in jsonl_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(raw_lines) == 3
    for raw in raw_lines:
        decoded = json.loads(raw)
        assert set(decoded.keys()) == {"turn", "agent", "role", "prompt_hash", "output"}


# ---------------------------------------------------------------------------
# Test 4 -- TRX-04: LF-only newlines on disk on every platform
# ---------------------------------------------------------------------------


def test_lf_only_on_disk(tmp_path: Path) -> None:
    """Both files must contain zero CRLF sequences on disk (TRX-04).

    This is the cross-platform discipline check. On Windows, default
    ``open(...)`` translates ``\\n`` writes to ``\\r\\n`` on disk; passing
    ``newline="\\n"`` suppresses that. If a regression introduces CRLF, this
    test fails immediately with the raw byte count -- not a string-equality
    false positive.
    """
    md = tmp_path / "transcript.md"
    transcript = Transcript(md, header_task="LF check")

    for turn_index, payload in enumerate(_three_turn_payload(), start=1):
        transcript.append_turn(
            turn=turn_index,
            agent=payload["agent"],
            role=payload["role"],
            prompt=payload["prompt"],
            output=payload["output"],
        )

    md_bytes = md.read_bytes()
    jsonl_bytes = transcript.jsonl_path.read_bytes()

    # Note: pre-compute the CRLF count outside the f-string -- Python 3.11 forbids
    # backslashes inside the {expression} part of an f-string (PEP 701 lifts this
    # in 3.12, but the project floor is 3.10/3.11).
    crlf = b"\r\n"
    md_crlf_count = md_bytes.count(crlf)
    jsonl_crlf_count = jsonl_bytes.count(crlf)

    assert crlf not in md_bytes, f"markdown file has CRLF: count={md_crlf_count}"
    assert crlf not in jsonl_bytes, f"jsonl file has CRLF: count={jsonl_crlf_count}"
    # Both must also decode cleanly as UTF-8 (TRX-05 lives next door).
    md_bytes.decode("utf-8")
    jsonl_bytes.decode("utf-8")


# ---------------------------------------------------------------------------
# Test 5 -- TRX-05: UTF-8 round trip with em-dashes, smart quotes, and emoji
# ---------------------------------------------------------------------------


def test_utf8_round_trip(tmp_path: Path) -> None:
    """LLM-style output (em-dashes, smart quotes, emoji) must round-trip cleanly (TRX-05).

    This payload is the exact pattern Pitfall #3 calls out: cp1252-invalid
    bytes that surface UnicodeDecodeError on Windows when encoding is
    unspecified. Forcing ``encoding="utf-8"`` on every open() makes this
    work everywhere.
    """
    md = tmp_path / "transcript.md"
    transcript = Transcript(md)

    fancy_output = (
        "Here’s the plan — we ship it. "  # noqa: RUF001 right single quote + em dash (intentional payload)
        "“Quality” ‘matters’. "  # noqa: RUF001 curly double + curly single (intentional payload)
        "\U0001f680 to production!"  # rocket emoji
    )

    transcript.append_turn(
        turn=1,
        agent="Architect",
        role="design",
        prompt="Make the call",
        output=fancy_output,
    )

    # 1. JSONL round-trip preserves the exact string.
    records = transcript.read_turns()
    assert len(records) == 1
    assert records[0].output == fancy_output

    # 2. Markdown contains the exact same Unicode characters.
    md_text = md.read_text(encoding="utf-8")
    assert fancy_output in md_text

    # 3. Raw bytes decode as UTF-8 without errors.
    md.read_bytes().decode("utf-8")  # would raise on bad bytes
    transcript.jsonl_path.read_bytes().decode("utf-8")


# ---------------------------------------------------------------------------
# Test 6 -- D-08: empty list when sidecar absent
# ---------------------------------------------------------------------------


def test_read_turns_returns_empty_list_when_sidecar_missing(tmp_path: Path) -> None:
    """A fresh Transcript with no appends yet returns [] from read_turns (D-08)."""
    md = tmp_path / "transcript.md"
    transcript = Transcript(md)

    assert transcript.read_turns() == []
    assert len(transcript) == 0
    assert not transcript.jsonl_path.exists()


# ---------------------------------------------------------------------------
# Test 7 -- D-11: missing parent directory raises OSError
# ---------------------------------------------------------------------------


def test_init_raises_oserror_when_parent_missing(tmp_path: Path) -> None:
    """Constructing with a non-existent parent dir must raise OSError (D-11).

    The orchestrator is responsible for ensuring the parent directory exists
    before constructing a Transcript -- auto-mkdir would hide path typos.
    """
    bad_path = tmp_path / "no_such_dir" / "transcript.md"
    with pytest.raises(OSError) as excinfo:
        Transcript(bad_path)

    assert "no_such_dir" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Test 8 -- D-10: idempotent re-open does not erase existing markdown
# ---------------------------------------------------------------------------


def test_idempotent_creation_does_not_erase_existing_markdown(tmp_path: Path) -> None:
    """Re-constructing a Transcript at the same path preserves prior content (D-10)."""
    md = tmp_path / "transcript.md"

    first = Transcript(md, header_task="Run A")
    first.append_turn(
        turn=1,
        agent="Architect",
        role="design",
        prompt="hello",
        output="initial design",
    )
    bytes_after_first = md.read_bytes()
    jsonl_bytes_after_first = first.jsonl_path.read_bytes()
    assert b"initial design" in bytes_after_first

    # Re-open the same path with a different header. Existing files MUST be
    # preserved untouched (D-10) -- the new header_task is only used if/when
    # the markdown file is empty, which it is not.
    second = Transcript(md, header_task="Run B (should never appear)")
    assert md.read_bytes() == bytes_after_first
    assert second.jsonl_path.read_bytes() == jsonl_bytes_after_first

    # Appending a 2nd turn through the new instance extends rather than
    # truncates either file.
    second.append_turn(
        turn=2,
        agent="Critic",
        role="skeptic",
        prompt="critique it",
        output="needs more rigor",
    )

    final_records = second.read_turns()
    assert len(final_records) == 2
    assert final_records[0].agent == "Architect"
    assert final_records[1].agent == "Critic"

    # Header was NOT re-written.
    text = md.read_text(encoding="utf-8")
    assert text.count("# Transcript: Run A") == 1
    assert "Run B" not in text
