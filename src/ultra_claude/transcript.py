"""Transcript writer for ultra-claude debates.

This module owns the single source of truth for conversation state. Every
``append_turn`` call writes to BOTH a human-readable markdown file (canonical,
re-promptable, ``tail -f``-friendly) AND a parseable JSONL sidecar (one
record per turn, schema-stable for v2 resume tooling). Adapters and stop
conditions read/write through this module so they never own file IO.

Phase 3 success criteria (from ROADMAP and ``03-CONTEXT.md``):

1. Running a 3-turn synthetic test produces a markdown file that is appended
   (not rewritten) after each turn -- ``tail -f`` works (TRX-01).
2. Each turn is delimited by a non-markdown HTML-comment sentinel
   ``<!-- turn:N agent:Name -->`` so re-prompting does not collide with content
   markdown (TRX-02). Mitigates Pitfall #8 (markdown-in-markdown corruption).
3. A JSONL sidecar at ``<markdown_path>.jsonl`` is written in parallel with
   ``turn``, ``agent``, ``role``, ``prompt_hash``, and ``output`` fields per
   record (TRX-03).
4. Files use LF-only newlines (``newline="\\n"``) on every platform (TRX-04)
   and are encoded UTF-8 (TRX-05). Mitigates Pitfall #3 (Windows encoding
   triple-trap) on the file-write side.

The transcript IS the memory: per the project's "no API keys, no persistent
state" stance, this file is the only durable artefact ultra-claude maintains
across runs.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["Transcript", "TurnRecord"]


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class TurnRecord(BaseModel):
    """One row in the JSONL sidecar.

    All five fields are required. ``prompt_hash`` is the lowercase SHA-256
    hex digest of the prompt's UTF-8 bytes -- the prompt itself is *not*
    stored, because it may contain user secrets pulled in from the task
    file or earlier transcript turns (per ``03-CONTEXT.md`` D-04).
    """

    model_config = ConfigDict(extra="forbid")

    turn: int = Field(ge=1, description="1-indexed turn number within the run.")
    agent: str = Field(min_length=1, description="Display name of the agent that produced this turn.")
    role: str = Field(min_length=1, description="Short role label (e.g. 'high-level design').")
    prompt_hash: str = Field(
        min_length=64,
        max_length=64,
        description="SHA-256 hex digest of the prompt that produced this output.",
    )
    output: str = Field(description="Raw stdout from the adapter for this turn.")


# ---------------------------------------------------------------------------
# Transcript writer
# ---------------------------------------------------------------------------


class Transcript:
    """Append-as-you-go markdown + JSONL writer for a single roundtable run.

    Construct once per run with the desired markdown path, then call
    ``append_turn`` after each agent reply. Every call flushes BOTH files
    before returning so ``tail -f`` on the markdown file streams content as
    turns arrive (TRX-01).

    The ``jsonl_path`` is derived as ``markdown_path.with_suffix(suffix + ".jsonl")``
    so a path like ``debate.md`` maps to ``debate.md.jsonl`` and a path like
    ``transcript`` (no suffix) maps to ``transcript.jsonl``. This avoids
    collisions if the user passes a suffix-less path (per ``03-CONTEXT.md`` D-02).

    Idempotency:
        * Constructing a Transcript whose markdown file already exists does
          not erase it. Subsequent ``append_turn`` calls append to the existing
          content. (D-10)
        * Constructing a Transcript whose parent directory does not exist
          raises ``OSError``; auto-creating directories is the orchestrator's
          job, not ours. (D-11)

    Atomicity:
        v1 uses simple ``open / write / close`` per file per call. A crash
        between the markdown write and the JSONL write leaves the two files
        desynced by at most one record; the orchestrator can detect and warn,
        but since the transcript IS the memory, recovery is rare and
        re-running is cheap. (D-09)
    """

    def __init__(
        self,
        markdown_path: Path | str,
        *,
        header_task: str | None = None,
        started_at: dt.datetime | None = None,
    ) -> None:
        self._markdown_path = Path(markdown_path)
        self._header_task = header_task
        self._started_at = started_at if started_at is not None else dt.datetime.now(dt.timezone.utc)

        # D-11: parent directory must already exist; we don't auto-mkdir.
        parent = self._markdown_path.parent
        if not parent.exists():
            raise OSError(
                f"Transcript parent directory does not exist: {parent} "
                f"(orchestrator should mkdir before constructing Transcript)"
            )

        # D-10: do NOT truncate existing markdown. Idempotent re-open.
        # We don't touch either file in __init__; the first append_turn writes
        # the header if (and only if) the markdown file is empty/missing.

    # ------------------------------------------------------------------
    # Public read-only path properties
    # ------------------------------------------------------------------

    @property
    def markdown_path(self) -> Path:
        return self._markdown_path

    @property
    def jsonl_path(self) -> Path:
        # ``Path("foo.md").with_suffix(".md.jsonl")`` would replace ".md", not
        # append. We want literal-append semantics so "foo.md" -> "foo.md.jsonl"
        # and "transcript" (no suffix) -> "transcript.jsonl". (D-02)
        suffix = self._markdown_path.suffix
        return self._markdown_path.with_suffix(suffix + ".jsonl")

    # ------------------------------------------------------------------
    # Append API
    # ------------------------------------------------------------------

    def append_turn(
        self,
        turn: int,
        agent: str,
        role: str,
        prompt: str,
        output: str,
    ) -> None:
        """Append one turn to BOTH the markdown file and the JSONL sidecar.

        Both files are flushed and closed before this method returns, so a
        reader doing ``tail -f`` (or ``Path.read_text()``) sees the new content
        immediately on every platform.
        """

        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        record = TurnRecord(
            turn=turn,
            agent=agent,
            role=role,
            prompt_hash=prompt_hash,
            output=output,
        )

        self._write_markdown_block(turn=turn, agent=agent, role=role, output=output)
        self._write_jsonl_record(record)

    def read_turns(self) -> list[TurnRecord]:
        """Parse the JSONL sidecar and return one ``TurnRecord`` per line.

        Returns ``[]`` if the sidecar does not yet exist (per D-08). Empty or
        whitespace-only lines are skipped so a trailing newline does not
        produce a phantom record.
        """

        path = self.jsonl_path
        if not path.exists():
            return []

        records: list[TurnRecord] = []
        with open(path, encoding="utf-8", newline="\n") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                records.append(TurnRecord.model_validate_json(stripped))
        return records

    def __len__(self) -> int:
        """Number of turns currently written to the JSONL sidecar."""

        return len(self.read_turns())

    # ------------------------------------------------------------------
    # Convenience read-back helpers (for --dry-run debugging, per D-13)
    # ------------------------------------------------------------------

    def markdown_text(self) -> str:
        """Return the full markdown file contents as a string, or '' if missing."""

        if not self._markdown_path.exists():
            return ""
        with open(self._markdown_path, encoding="utf-8", newline="\n") as handle:
            return handle.read()

    def jsonl_text(self) -> str:
        """Return the full JSONL sidecar contents as a string, or '' if missing."""

        if not self.jsonl_path.exists():
            return ""
        with open(self.jsonl_path, encoding="utf-8", newline="\n") as handle:
            return handle.read()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _write_markdown_block(
        self, *, turn: int, agent: str, role: str, output: str
    ) -> None:
        """Append the markdown block for one turn (header on first call)."""

        # If the file is missing or empty, prepend the header. Both branches
        # use mode="a" so concurrent reads via tail -f never see a truncated
        # file. ``newline="\n"`` forces LF on every platform (TRX-04).
        existing_size = (
            self._markdown_path.stat().st_size if self._markdown_path.exists() else 0
        )

        with open(
            self._markdown_path,
            mode="a",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            if existing_size == 0:
                handle.write(self._render_header())
            handle.write(self._render_turn_block(turn=turn, agent=agent, role=role, output=output))

    def _write_jsonl_record(self, record: TurnRecord) -> None:
        """Append one JSON line to the sidecar."""

        line = record.model_dump_json() + "\n"
        with open(
            self.jsonl_path,
            mode="a",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(line)

    def _render_header(self) -> str:
        """Render the one-time markdown header block (per D-05/D-06)."""

        title = self._header_task if self._header_task else "Untitled"
        # ISO 8601 in UTC, second precision (no microseconds) for clean test output.
        started_iso = self._started_at.replace(microsecond=0).isoformat()
        return (
            f"# Transcript: {title}\n"
            f"\n"
            f"*Started: {started_iso}*\n"
            f"\n"
            f"---\n"
            f"\n"
        )

    def _render_turn_block(
        self, *, turn: int, agent: str, role: str, output: str
    ) -> str:
        """Render one turn block: sentinel + heading + body + separator (per D-05).

        The HTML-comment sentinel is the single source of truth for re-prompting:
        it is invisible in rendered markdown, contains no markdown special
        characters, and survives round-tripping through any sane markdown
        parser. This is the Pitfall #8 mitigation -- never embed turn metadata
        as ``## Turn N`` headings alone, because LLM output regularly contains
        its own ``##`` headings that would shadow the boundaries.
        """

        # ``json.dumps(agent)`` would over-quote; we just trust ``agent`` to be
        # a single token (no spaces) per the locked sentinel format. The
        # AgentConfig.name field has min_length=1, but Phase 6's orchestrator
        # is responsible for ensuring no whitespace ends up in agent names if
        # this becomes a problem; for v1 we keep the sentinel simple.
        return (
            f"<!-- turn:{turn} agent:{agent} -->\n"
            f"## Turn {turn} — {agent} ({role})\n"
            f"\n"
            f"{output}\n"
            f"\n"
            f"---\n"
            f"\n"
        )
