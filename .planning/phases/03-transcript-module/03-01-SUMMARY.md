---
phase: 03-transcript-module
plan: 01
subsystem: transcript
tags: [pydantic, hashlib, sha256, jsonl, markdown, utf-8, lf-newlines, html-comment-sentinel]

# Dependency graph
requires:
  - phase: 02-config-schema-yaml-loader
    provides: "Pydantic v2 + ConfigDict(extra='forbid') pattern; src layout with src/ultra_claude/"
provides:
  - "Transcript class — append-as-you-go markdown + JSONL writer; markdown_path/jsonl_path properties; append_turn / read_turns / __len__ / markdown_text / jsonl_text"
  - "TurnRecord Pydantic v2 schema — turn/agent/role/prompt_hash/output (extra=forbid)"
  - "HTML-comment turn sentinel format `<!-- turn:N agent:Name -->` (Pitfall #8 mitigation, locked for Phase 5 stop conditions)"
  - "LF-only-on-disk + UTF-8 cross-platform discipline at the transcript layer (TRX-04 + TRX-05)"
  - "SHA-256 prompt-hash convention (D-04) — prompt itself never persisted"
  - "Idempotent re-open + missing-parent OSError contract (D-10, D-11)"
affects: [04-adapter-protocol, 05-stop-conditions, 06-orchestrator-loop]

# Tech tracking
tech-stack:
  added: [hashlib (stdlib), datetime (stdlib)]
  patterns:
    - "TurnRecord follows the Phase 2 Pydantic v2 pattern: BaseModel + ConfigDict(extra='forbid') + Field(min_length=...)"
    - "Every open() in this module passes encoding='utf-8' AND newline='\\n' (cross-platform LF discipline)"
    - "Read-only path properties via @property — no setter; jsonl_path derives from markdown_path"
    - "Two-file write per append_turn (markdown then JSONL); each is its own with-block; both flush+close before return"
    - "Header-on-first-write pattern: stat().st_size == 0 -> write header; else append turn block only"

key-files:
  created:
    - "src/ultra_claude/transcript.py (295 lines, 11708 bytes, LF-only, UTF-8)"
    - "tests/test_transcript.py (337 lines, 12880 bytes, LF-only, UTF-8)"
    - ".planning/phases/03-transcript-module/03-01-SUMMARY.md (this file)"
  modified: []

key-decisions:
  - "TurnRecord is a Pydantic BaseModel (consistent with AgentConfig/RoundtableConfig) — gets free model_dump_json + model_validate_json"
  - "jsonl_path = markdown_path.with_suffix(suffix + '.jsonl') — literal append, not replace, so 'foo.md' -> 'foo.md.jsonl' (not 'foo.jsonl')"
  - "prompt_hash is the lowercase SHA-256 hex digest of prompt.encode('utf-8') — 64 chars, validated by min_length=64+max_length=64 on the field"
  - "No TranscriptError class — reuse stdlib OSError per D-12 (keeps exception surface minimal)"
  - "Header is written on first append_turn when markdown stat().st_size == 0 — no separate init() step needed; idempotent re-open trivially preserved"
  - "Python 3.11 f-string-no-backslash limitation requires lifting CRLF byte literals out of f-string {expression} parts (Rule 1 deviation)"

patterns-established:
  - "LF-only-on-disk discipline: every open() in writer modules MUST pass newline='\\n' so Windows doesn't translate \\n -> \\r\\n on write"
  - "UTF-8-everywhere: every open() also passes encoding='utf-8' — no implicit cp1252 on Windows"
  - "Raw-bytes assertion for newline tests: b'\\r\\n' not in path.read_bytes() catches Windows regressions that string-equality false-positives miss"
  - "HTML-comment sentinel for re-prompt-safe turn delimiters: invisible in rendered markdown, contains zero markdown special characters, survives any sane parser"
  - "Auto-fix Rule 1 (bug): pre-compute byte-literal counts when they appear inside f-string expressions on Python <3.12"

requirements-completed: [TRX-01, TRX-02, TRX-03, TRX-04, TRX-05]

# Metrics
duration: ~6 min
completed: 2026-05-02
---

# Phase 3 Plan 01: Transcript Module Summary

**Append-as-you-go markdown + JSONL transcript writer with HTML-comment turn sentinels, SHA-256 prompt hashing, and locked LF/UTF-8 cross-platform discipline.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-02T02:53:30Z (approximate, plan kickoff)
- **Completed:** 2026-05-02T02:59:22Z
- **Tasks:** 2/2 (both autonomous, both TDD)
- **Files modified:** 2 created (1 source, 1 test)

## Accomplishments

- `TurnRecord` Pydantic v2 model with `turn` / `agent` / `role` / `prompt_hash` / `output` (extra=forbid; prompt_hash strict 64-char hex via min/max length).
- `Transcript` class with `append_turn(turn, agent, role, prompt, output)` writing to BOTH the markdown file AND the JSONL sidecar before returning — `tail -f` works on every platform (TRX-01).
- HTML-comment sentinel `<!-- turn:N agent:Name -->` precedes every turn block (Pitfall #8 mitigation; mirrors what Phase 5 stop conditions will anchor on).
- Cross-platform LF-only discipline at the writer layer — `newline="\n"` on every `open()` (TRX-04), `encoding="utf-8"` on every `open()` (TRX-05).
- SHA-256 hex digest prompt hashing — the prompt itself is never persisted (D-04 — prompts may carry user secrets pulled from task files).
- Idempotent re-open: existing markdown file is preserved on construction (D-10); subsequent `append_turn` calls extend rather than truncate.
- OSError on missing parent directory (D-11) — orchestrator owns `mkdir`, not the transcript layer.
- 8 pytest tests covering all 5 TRX requirements + 3 locked decisions (D-08, D-10, D-11). Full suite: 16/16 PASS (8 Phase 2 + 8 Phase 3 — zero regression).

## Task Commits

Each task was committed atomically:

1. **Task 1: Create src/ultra_claude/transcript.py** — `88b6186` (feat: TurnRecord + Transcript classes, ~280 lines, mypy --strict clean, ruff clean)
2. **Task 2: Create tests/test_transcript.py** — `6230667` (test: 8 tests, all PASS, ruff clean; includes Rule 1 fix for Python 3.11 f-string limitation)

_Note: Task 1 had no separate test commit because Task 2 explicitly creates the test file in its own commit — this matches the plan's `<output>` guidance ("atomic per task: feat(03-01): add transcript module + test(03-01): add transcript test suite")._

**Plan metadata commit:** Will follow this SUMMARY (covers SUMMARY.md, STATE.md, ROADMAP.md, REQUIREMENTS.md updates).

## Files Created/Modified

- `src/ultra_claude/transcript.py` (295 lines, 11708 bytes) — `TurnRecord` Pydantic schema + `Transcript` class with full append-as-you-go writer, read-back helpers, idempotent re-open, OSError-on-missing-parent contract.
- `tests/test_transcript.py` (337 lines, 12880 bytes) — 8 tests:
  - `test_three_turn_round_trip_appends_to_markdown` — TRX-01 (strictly increasing file size between calls)
  - `test_each_turn_has_html_comment_sentinel` — TRX-02 (anchored multiline regex)
  - `test_jsonl_sidecar_records_match_schema` — TRX-03 (5 fields, SHA-256 hex match, exact key set)
  - `test_lf_only_on_disk` — TRX-04 (raw bytes check on both `.md` and `.md.jsonl`)
  - `test_utf8_round_trip` — TRX-05 (em-dash, smart quotes, rocket emoji)
  - `test_read_turns_returns_empty_list_when_sidecar_missing` — D-08
  - `test_init_raises_oserror_when_parent_missing` — D-11
  - `test_idempotent_creation_does_not_erase_existing_markdown` — D-10

## Decisions Made

- **Followed plan as specified** for the architectural surface (TurnRecord schema, jsonl_path derivation, sentinel format, header rendering, two-file write order).
- **Rule 1 deviation (Python 3.11 f-string limitation):** Lifted CRLF byte literal counts out of f-string `{expression}` parts in `test_lf_only_on_disk` — Python 3.11 raises `SyntaxError: f-string expression part cannot include a backslash`. PEP 701 lifts this in 3.12, but the project floor is 3.10/3.11 per CLAUDE.md. The fix pre-computes `md_crlf_count`/`jsonl_crlf_count` as locals before interpolating into the assert message. Functionally equivalent; arguably cleaner.
- **Ruff cleanup at commit time** (treated as part of the same auto-fix work, not a separate deviation):
  - I001: removed an extra blank line after the import block (auto-fix).
  - B905: added `strict=True` to `zip(records, payload)` — guarantees the test fails loudly if records and payload diverge instead of silently truncating.
  - RUF001 x3: added `# noqa: RUF001` on the smart-quote test fixtures — the whole point of `test_utf8_round_trip` is to verify ambiguous-unicode characters round-trip cleanly, so flagging them as "ambiguous" is a false positive in this context.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Python 3.11 f-string-no-backslash SyntaxError in test_lf_only_on_disk**
- **Found during:** Task 2 (test suite first pytest run; collection failed with `SyntaxError: f-string expression part cannot include a backslash` at line 203)
- **Issue:** The plan's `<action>` template wrote `f"markdown file has CRLF: count={md_bytes.count(b'\\r\\n')}"` — the `\\r\\n` inside the `{expression}` part is a backslash, which Python 3.11's parser rejects. PEP 701 lifts this restriction in 3.12, but `pyproject.toml [tool.mypy] python_version = "3.10"` and the project floor (CLAUDE.md tech stack) targets 3.10/3.11 — the live runtime here is 3.11.9.
- **Fix:** Lifted the byte literal into a local (`crlf = b"\r\n"`), pre-computed `md_crlf_count`/`jsonl_crlf_count`, then interpolated the locals into clean f-strings with no backslashes inside expressions. Behavior is identical.
- **Files modified:** `tests/test_transcript.py`
- **Verification:** `python -m pytest tests/test_transcript.py -v` collected and passed 8/8 after the fix. Locally re-checked under `python -m ruff check` (no new lint), `python -m pytest tests/ -v` (16/16 PASS, no Phase 2 regression).
- **Committed in:** `6230667` (Task 2 commit — test file lands as a single artifact with the fix already in place; no intermediate broken commit was published).

**2. [Rule 3 - Blocking] Ruff lint cleanups before commit**
- **Found during:** Task 2 (ruff check ran before commit)
- **Issue:** Default ruff config enables `I/B/RUF` rule families. The plan template tripped 5 lints: `I001` (extra blank line after imports), `B905` (`zip()` without `strict=`), and `RUF001` x3 (ambiguous unicode in test payload).
- **Fix:** Removed extra blank line; added `strict=True` to `zip(records, payload, strict=True)` (records/payload are guaranteed equal length here, so `strict=True` makes accidental truncation an immediate failure rather than a silent test-shorter-than-expected pass); added `# noqa: RUF001` on the two smart-quote payload lines (the smart quotes ARE the test fixture — flagging them as "ambiguous" is a category error in this specific context).
- **Files modified:** `tests/test_transcript.py`
- **Verification:** `python -m ruff check tests/test_transcript.py` reports zero issues; `python -m pytest tests/test_transcript.py -v` still 8/8 PASS.
- **Committed in:** `6230667` (folded into the Task 2 commit message).

---

**Total deviations:** 2 auto-fixed (1 Rule 1 bug, 1 Rule 3 blocking).
**Impact on plan:** Both auto-fixes were necessary for the test file to even collect under Python 3.11 + the project's configured ruff ruleset. Functional surface is unchanged from the plan's spec; only the form of the assert message and a few lint-suppress comments changed. No scope creep.

## Issues Encountered

- **`git add` warning about CRLF replacement on next checkout** (Windows host with `core.autocrlf=true`). Confirmed via `git show :path | python -c "...count(b'\\r\\n')"` that the git index stores LF-only for both `transcript.py` (CRLF count = 0) and `test_transcript.py` (CRLF count = 0). The warning describes future-checkout-on-other-machine risk only — the current commit is correct. This was already logged in `.planning/phases/02-config-schema-yaml-loader/deferred-items.md` as a project-wide concern; not actioned here per executor SCOPE BOUNDARY policy. Recommended fix (a `.gitattributes` file forcing `eol=lf`) remains queued for a small chore plan.

## Verification Output

All plan-level `<verification>` block commands executed and PASS:

| Command | Result |
|---------|--------|
| `python -c "from ultra_claude.transcript import Transcript, TurnRecord; print('OK')"` | `OK` |
| `python -m pytest tests/ -v` | `16 passed in 0.25s` (8 Phase 2 + 8 Phase 3) |
| `python -c "...assert b'\\r\\n' not in src.read_bytes() and ...test.read_bytes()..."` | `OK: LF-only on disk for both files` |
| `python -m mypy --strict src/ultra_claude/transcript.py` | `Success: no issues found in 1 source file` |
| `python -m ruff check src/ultra_claude/transcript.py tests/test_transcript.py` | `All checks passed!` |
| Sentinel-format grep (`<!-- turn:{turn} agent:{agent} -->` in transcript.py) | `OK: locked sentinel format` |

Per-task `<verify>` blocks all PASS:

**Task 1:**
- AST class definition check: `OK: classes defined`
- Import check: `OK: importable`
- Grep sanity (newline arg, encoding arg, sha256, model_dump_json, model_validate_json, sentinel string, class names, __all__, no CRLF on disk, no os.linesep, no errors=, no mode="w", no TranscriptError): `OK: all grep checks pass + LF on disk + negative checks pass`
- mypy --strict: `Success: no issues found in 1 source file`
- ruff check: `All checks passed!`

**Task 2:**
- All 8 test names defined: `OK: all 8 tests defined`
- LF-only on disk: `OK: LF-only on disk`
- pytest tests/test_transcript.py: 8 PASSED
- pytest tests/: 16 PASSED (no Phase 2 regression)
- ruff check: `All checks passed!`

## Requirements → Test Mapping

| Requirement | Test |
|-------------|------|
| TRX-01 (append, not rewrite — `tail -f` works) | `test_three_turn_round_trip_appends_to_markdown` (asserts `sizes[0] < sizes[1] < sizes[2]`) |
| TRX-02 (HTML-comment sentinel per turn) | `test_each_turn_has_html_comment_sentinel` (anchored multiline regex returns exactly the expected agent list) |
| TRX-03 (JSONL sidecar with 5 fields) | `test_jsonl_sidecar_records_match_schema` (filename `transcript.md.jsonl`, 3 records, SHA-256 hex match, exact key set) |
| TRX-04 (LF-only newlines on every platform) | `test_lf_only_on_disk` (raw bytes check on both `.md` and `.md.jsonl`) |
| TRX-05 (UTF-8 encoded on disk) | `test_utf8_round_trip` (em-dash + smart quotes + rocket emoji round-trip cleanly through both files) |
| D-08 (read_turns returns [] when sidecar missing) | `test_read_turns_returns_empty_list_when_sidecar_missing` |
| D-10 (idempotent re-open does not erase markdown) | `test_idempotent_creation_does_not_erase_existing_markdown` |
| D-11 (missing parent dir raises OSError) | `test_init_raises_oserror_when_parent_missing` |

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Phase 3 CLOSED. TRX-01..TRX-05 all complete.

Phase 4 (Adapter Protocol & ClaudeAdapter) and Phase 5 (Stop Conditions) are now unblocked:

- **Phase 4** consumes nothing from `transcript.py` directly during ADAPTER work itself, but the Phase 4 mixin needs to know where transcript writes happen so the orchestrator (Phase 6) can wire them together. Phase 4 can begin immediately.
- **Phase 5** (`StopCondition.check(transcript)`) consumes `Transcript.read_turns() -> list[TurnRecord]` and the `<!-- turn:N agent:Name -->` sentinel format for anchored multiline regex matches. Both are now locked and tested.
- **Phase 6** (orchestrator) will consume `Transcript.append_turn` per turn and `Transcript.markdown_path` as the return value of `run(config, task) -> Path`.

Carried-forward concerns (no action this plan):

- The `core.autocrlf=true` git checkout risk remains queued (documented in `.planning/phases/02-config-skeleton-yaml-loader/deferred-items.md`); recommend a small chore plan adding repo-root `.gitattributes` before Phase 9 release-gate work.
- PKG-05 (twine upload of v0.0.1 stub) still pending user action per `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md`. Independent of Phase 3.

## Self-Check: PASSED

All claimed files and commits verified to exist:

- `src/ultra_claude/transcript.py` — FOUND (295 lines, 11708 bytes, LF-only, mypy --strict clean, ruff clean)
- `tests/test_transcript.py` — FOUND (337 lines, 12880 bytes, LF-only, ruff clean, 8/8 PASS)
- Commit `88b6186` (feat: add transcript module) — FOUND in `git log`
- Commit `6230667` (test: add transcript test suite) — FOUND in `git log`

---

*Phase: 03-transcript-module*
*Completed: 2026-05-02*
