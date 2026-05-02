# Phase 3: Transcript Module - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

Single source of truth for conversation state — append-as-you-go markdown plus a parseable JSONL sidecar. Adapters and stop conditions read/write turns without owning file IO.

Scope:
- `src/ultra_claude/transcript.py` — `TurnRecord` dataclass/Pydantic model + `Transcript` class with `append_turn(...)`, `read_turns() -> list[TurnRecord]`, `markdown_path: Path`, `jsonl_path: Path`
- Append-as-you-go: every `append_turn` call flushes both the markdown file AND the JSONL sidecar before returning
- Sentinel delimiter: `<!-- turn:N agent:Name -->` (HTML comment — invisible in rendered markdown, survives re-prompting)
- JSONL records: one JSON object per line with `turn`, `agent`, `role`, `prompt_hash`, `output` fields
- LF-only newlines on disk; UTF-8 encoding; tested on Windows
- `tests/test_transcript.py` covering: 3-turn synthetic round-trip, sentinel format, JSONL sidecar correctness, LF-only on disk, UTF-8 with em-dashes/smart quotes/emoji

Out of scope: orchestrator (Phase 6), adapters (Phase 4/7), stop conditions (Phase 5).

</domain>

<decisions>
## Implementation Decisions

### Locked from REQUIREMENTS.md (TRX-01 to TRX-05) and CLAUDE.md

- **`Transcript` class signature:**
  ```python
  class Transcript:
      def __init__(self, markdown_path: Path | str, *, header_task: str | None = None) -> None: ...
      @property
      def markdown_path(self) -> Path: ...
      @property
      def jsonl_path(self) -> Path: ...
      def append_turn(self, turn: int, agent: str, role: str, prompt: str, output: str) -> None: ...
      def read_turns(self) -> list[TurnRecord]: ...
      def __len__(self) -> int: ...   # number of turns written so far
  ```
  
- **`jsonl_path` derivation:** `markdown_path.with_suffix(markdown_path.suffix + ".jsonl")` — e.g. `transcript.md` → `transcript.md.jsonl`. NOT `transcript.jsonl` (avoids collisions if user names file without `.md` extension).

- **`TurnRecord`:** Pydantic model (consistent with Phase 2's pattern). Fields: `turn: int`, `agent: str`, `role: str`, `prompt_hash: str`, `output: str`. Pydantic gives us `model_dump_json()` for clean JSONL writes.

- **`prompt_hash`:** SHA-256 of the prompt text, hex-encoded. Lets later phases verify the same prompt didn't get sent twice. Not the prompt itself — the prompt may contain user secrets.

- **Markdown format:**
  ```
  # Transcript: <task header text or "Untitled">
  
  *Started: 2026-05-02T01:23:45Z*
  
  ---
  
  <!-- turn:1 agent:Architect -->
  ## Turn 1 — Architect (high-level design)
  
  <agent output here>
  
  ---
  
  <!-- turn:2 agent:Critic -->
  ## Turn 2 — Critic (skeptic)
  
  <agent output>
  
  ---
  ```
  Each turn is appended atomically: open file `mode="a"`, write the block (sentinel + heading + body + `\n---\n\n`), close. On Windows, `newline="\n"` argument passed to `open(...)` to force LF-only.

- **Header is written on first `append_turn`:** if the markdown file doesn't exist or is empty, write the `# Transcript:` header + `*Started: <iso8601>*` + `---` block first, THEN the first turn block. This avoids needing a separate `init()` step.

- **JSONL append:** For each turn, also append one line to the sidecar via `json.dumps(record_dict) + "\n"` written with `newline="\n"`. The JSONL file does NOT have a header — pure append-only.

- **`read_turns()` reads the JSONL sidecar** (not the markdown). Returns a list of `TurnRecord` instances. If sidecar doesn't exist, returns `[]`.

- **Atomicity:** For v1, simple `open / write / close` per call is sufficient. We accept that a crash between markdown-write and jsonl-write leaves them desynced — orchestrator can detect and warn, but the transcript-IS-the-memory invariant means crash recovery is rare and the user can rerun.

- **Idempotent file creation:** Creating a `Transcript` for a path whose markdown file already exists does NOT erase it. Future `append_turn` calls append. (This means orchestrator restart/resume scenarios work — out of scope for v1 but the IO contract supports it.)

- **Path.parent must exist:** `__init__` raises `OSError` (or a custom `TranscriptError`) if the parent directory doesn't exist. Don't auto-create — that's the orchestrator's job.

- **No `TranscriptError` for v1:** Reuse stdlib exceptions (`OSError`, `ValueError`) to keep the surface small. Phase 4 introduces `AdapterError`, Phase 9 may consolidate.

### Module structure (after this phase)

```
src/ultra_claude/
├── __init__.py
├── config.py
├── exceptions.py        # ConfigError (Phase 2)
└── transcript.py        # NEW
```

### Testing strategy

- **Test file:** `tests/test_transcript.py`
- **Fixtures:** `tmp_path` (pytest built-in) for isolated file IO per test
- **Cross-platform check:** Read raw bytes (`Path.read_bytes()`) and assert no `\r\n` sequences. This catches Windows newline issues.
- **UTF-8 check:** Write a turn whose output contains em-dashes (`—`), smart quotes (`""''`), and emoji (`🚀`). Read back and assert exact match.
- **Sentinel format check:** Use anchored regex on the rendered markdown to assert each turn has a `<!-- turn:N agent:Name -->` comment.
- **JSONL round-trip:** After 3 turns, `Transcript.read_turns()` returns 3 `TurnRecord` instances with the right values.

### Claude's Discretion

- Whether to expose `markdown_text()` and `jsonl_text()` helpers — recommend: yes, useful for debugging and CLI `--dry-run`
- Whether to support an optional `started_at` parameter to `__init__` for deterministic test outputs — recommend: yes (use `dt.datetime.now(dt.timezone.utc)` as default)
- Specific commit message: not Claude's discretion — must include the phase number prefix per existing convention

</decisions>

<code_context>
## Existing Code Insights

After Phases 1 and 2:
- `src/ultra_claude/__init__.py` exports `__version__`
- `src/ultra_claude/config.py` defines `AgentConfig`, `RoundtableConfig`, `load_config`
- `src/ultra_claude/exceptions.py` defines `ConfigError`
- `tests/test_config.py` provides a model for new test files (pytest, tmp_path, parametrize)
- pyproject.toml has pydantic >= 2.13.3 and pytest >= 8.4 already wired

The pattern established by Phase 2 (Pydantic v2 model + careful Path handling + UTF-8 + LF newlines + grep-verifiable tests) should be replicated here.

</code_context>

<specifics>
## Specific Ideas

- The 4 success criteria from ROADMAP are mostly testable as automated assertions — no manual verification needed.
- Phase 3 owns the cross-platform newline discipline per ROADMAP's Cross-Platform Concerns table (LF newlines on disk + UTF-8 encoding for transcript writes).
- Architecture from research/ARCHITECTURE.md says transcript IS the memory — this module is the only durable state ultra-claude maintains across runs.

</specifics>

<deferred>
## Deferred Ideas

- Concurrent-write protection (file locking) — not needed in v1; orchestrator is single-threaded
- Atomic two-file commit (markdown + jsonl together) — accepted desync risk for v1
- Transcript truncation/rotation — not needed, transcripts are short-lived debate artifacts
- Custom `TranscriptError` exception — deferred to Phase 9 if needed during consolidation

</deferred>

---

*Phase: 03-transcript-module*
*Context auto-generated 2026-05-02 (autonomous mode)*
