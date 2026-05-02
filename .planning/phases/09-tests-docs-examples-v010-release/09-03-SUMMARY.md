---
phase: 09-tests-docs-examples-v010-release
plan: 03
subsystem: documentation
tags: [docs, readme, contributing, examples, release-prep, v0.1.0]
dependency_graph:
  requires:
    - "src/ultra_claude/presets/debate.yaml (verbatim copy source for examples/debate.yaml)"
    - "src/ultra_claude/adapters/base.py::Adapter Protocol + _SubprocessAdapterMixin (cited by README + CONTRIBUTING)"
    - "src/ultra_claude/transcript.py::TurnRecord schema (mirrored by examples/transcripts/sample-debate.md.jsonl)"
    - "src/ultra_claude/config.py::load_config (validates examples/debate.yaml at gate time)"
  provides:
    - "README.md: PyPI project-page rendering target after twine upload (DOC-01)"
    - "CONTRIBUTING.md: developer onboarding / v1 policy / PR checklist (DOC-02)"
    - "examples/: copyable config + synthetic transcript demonstrating the on-disk format (PRE-02)"
  affects:
    - "PyPI 0.1.0 release: README is what pip / pypi.org renders for the package"
    - "GitHub repo landing card: README is the rendered tile content"
tech-stack:
  added: []
  patterns:
    - "Path.write_bytes(content.encode('utf-8')) to defeat core.autocrlf=true on Windows"
    - "ascii-only enforcement scan on every text artifact before commit"
    - "byte-equality between examples/debate.yaml and src/ultra_claude/presets/debate.yaml (anti-drift)"
key-files:
  created:
    - "CONTRIBUTING.md (5608 bytes / 92 lines / LF-only / ASCII-only)"
    - "examples/README.md (1771 bytes / 24 lines / LF-only / ASCII-only)"
    - "examples/debate.yaml (1033 bytes / 30 lines / byte-identical to src/ultra_claude/presets/debate.yaml)"
    - "examples/transcripts/sample-debate.md (2857 bytes / 63 lines / 3 TRX-02 sentinels)"
    - "examples/transcripts/sample-debate.md.jsonl (3096 bytes / 3 lines / 3 TurnRecord-shaped JSON objects)"
  modified:
    - "README.md (was: 12-line Phase 1 stub. Is: 6313 bytes / 130 lines / 7 required sections + Links + Status)"
    - ".planning/REQUIREMENTS.md (DOC-01 / DOC-02 / PRE-02 checkboxes flipped + 3 traceability rows updated to Complete)"
decisions:
  - "Synthetic transcript over real capture: real captures need claude/gemini/codex installed and authenticated, which is environment-specific and not reproducible in repository fixtures. The synthetic transcript is structurally identical (same TRX-02 sentinels, same TurnRecord schema) so it accurately demonstrates the on-disk format users will see after a real run."
  - "examples/debate.yaml is a byte-identical copy of src/ultra_claude/presets/debate.yaml (T-09-12 mitigation). Drift between the two would mean the documented copyable example diverges from what --preset debate actually loads. Future bundled-preset edits MUST also update examples/debate.yaml; a repo-level diff check is deferred to v2 per the threat model."
  - "Pre-existing ruff errors (4) in src/ultra_claude/config.py + tests/test_config.py NOT fixed: per executor scope-boundary rule, only auto-fix issues caused by current task changes. These were documented as deferred since Phase 7 in .planning/phases/07-gemini-codex-adapters/deferred-items.md and stay deferred."
metrics:
  duration: "~12 min"
  completed: "2026-05-02"
  tasks: 3
  commits: 3
  files_created: 5
  files_modified: 1
  bytes_total: "~20.7 KB across 6 files"
  rule_n_deviations: 1
---

# Phase 9 Plan 03: README + CONTRIBUTING + examples/ Summary

Replaced the 12-line Phase 1 stub README with a full v0.1.0 PyPI-renderable README, created `CONTRIBUTING.md` with the 6 required sections (dev setup / adapter guide / v1 policy / PR checklist / issue template / architecture corrections), and populated `examples/` with a copyable config and a synthetic 3-turn transcript demonstrating the on-disk markdown sentinel format and JSONL sidecar shape.

## Outcome

3 atomic commits on `master` close DOC-01, DOC-02, PRE-02:

| Commit  | Type   | Files | Closes |
| ------- | ------ | ----- | ------ |
| `078dc7c` | docs(09-03) | README.md (rewrite from 12-line stub to 130-line full README) | DOC-01 |
| `180be45` | docs(09-03) | CONTRIBUTING.md (new, 92 lines) | DOC-02 |
| `2ab93b7` | docs(09-03) | examples/README.md + examples/debate.yaml + examples/transcripts/sample-debate.md + examples/transcripts/sample-debate.md.jsonl (4 new files) | PRE-02 |

## Artifacts

### README.md (DOC-01)

| Metric | Value |
|--------|-------|
| Size before | 12 lines / 591 bytes (Phase 1 stub) |
| Size after | 130 lines / 6313 bytes |
| Encoding | UTF-8, ASCII-only (zero non-ASCII bytes) |
| Newlines | LF-only on disk and in staged blob (despite `core.autocrlf=true`) |
| Sections (in order) | (1) 1-line pitch under H1; (2) PyPI/Python/License badges; (3) GIF placeholder HTML comment; (4) Quickstart with 3 commands + per-CLI install/login table; (5) Why this exists (3-bullet value prop); (6) Config example with verbatim debate.yaml + field reference table; (7) Extending to new CLIs with 10-line MyAdapter example; (8) Trademark disclaimer; (9) Links (PyPI/GitHub/License/Changelog/Contributing); (10) Status |
| Key cross-references | `src/ultra_claude/presets/debate.yaml` (config example embeds verbatim), `src/ultra_claude/adapters/base.py::_SubprocessAdapterMixin` (Extending section cites + `Adapter` Protocol + `runtime_checkable`), `openai/codex#19945` (empty-stdout defense citation), `CONTRIBUTING.md` (v1 policy backlink) |

### CONTRIBUTING.md (DOC-02)

| Metric | Value |
|--------|-------|
| Size | 92 lines / 5608 bytes |
| Encoding | UTF-8, ASCII-only |
| Newlines | LF-only on disk and in staged blob |
| Sections | (1) Dev setup; (2) Adding an adapter (minimal `_SubprocessAdapterMixin` example + 5-bullet contract list); (3) v1 policy (core ships only 3 adapters); (4) PR checklist (7 items); (5) Filing an issue (5-item bug report template); (6) Architecture corrections from original spec; (7) Code of Conduct |
| Adapter contract enumerated | stdin pipe (Windows ~8 KB cmd.exe argv defense); encoding+errors=replace; mandatory timeout + cross-platform process-tree kill; empty-stdout defense citing openai/codex#19945; auth-marker detection raising AdapterAuthError |
| v1 policy reasoning | (a) the 3 vendor CLIs are the official LLM CLIs that matter for v1's value prop; (b) every bundled adapter is a maintenance burden as vendor CLIs change; (c) structural Adapter Protocol means third-party adapters do NOT need to merge into core |

### examples/ tree (PRE-02)

| File | Bytes | Lines | Purpose |
|------|-------|-------|---------|
| `examples/README.md` | 1771 | 24 | Orientation + synthetic-vs-real explanation + capture-your-own instructions |
| `examples/debate.yaml` | 1033 | 30 | **Byte-identical copy** of `src/ultra_claude/presets/debate.yaml` |
| `examples/transcripts/sample-debate.md` | 2857 | 63 | Synthetic 3-turn debate (Architect → Critic → Implementer on "Should we add an undo button?") with TRX-02 markdown sentinel format |
| `examples/transcripts/sample-debate.md.jsonl` | 3096 | 3 | Matching JSONL sidecar, 3 records, each schema-validates against `ultra_claude.transcript.TurnRecord` |
| **TOTAL** | **8757 bytes** | **120 lines** | |

## Validations performed

| Gate | Command | Result |
|------|---------|--------|
| 1. README well-formed | `python -c "from pathlib import Path; data = Path('README.md').read_bytes(); assert b'\\r\\n' not in data; assert b'## Quickstart' in data"` | PASS |
| 2. CONTRIBUTING well-formed | `python -c "from pathlib import Path; data = Path('CONTRIBUTING.md').read_bytes(); assert b'\\r\\n' not in data; assert b'## Dev setup' in data"` | PASS |
| 3. examples/debate.yaml validates via project loader | `python -c "from ultra_claude.config import load_config; load_config('examples/debate.yaml')"` returns `RoundtableConfig(agents=3, max_turns=9, stop_keywords=['AGREED','SHIP IT'])` | PASS |
| 4. JSONL parses with TurnRecord schema | `[json.loads(line) for line in ...]` produces 3 records, each with the 5-field key set `{turn, agent, role, prompt_hash, output}` and a 64-char lowercase-hex prompt_hash | PASS |
| 5. Markdown sentinels match TRX-02 | All 3 expected sentinels (`<!-- turn:1 agent:Architect -->` / `<!-- turn:2 agent:Critic -->` / `<!-- turn:3 agent:Implementer -->`) present in `examples/transcripts/sample-debate.md` | PASS |
| 6. Full test suite still green | `pytest tests/` | **86/86 PASS in 3.88s** (zero regression — this plan adds zero source/test code, only documentation artefacts) |
| 7. ruff still clean (within plan scope) | `ruff check` on the 6 files this plan modified | PASS for all 6 plan files. `ruff check` repo-wide reports 4 errors in `src/ultra_claude/config.py` and `tests/test_config.py` -- these are PRE-EXISTING since Phase 2, documented in `.planning/phases/07-gemini-codex-adapters/deferred-items.md` since Phase 7, and OUT OF SCOPE per the executor scope-boundary rule (only auto-fix issues caused by the current task's changes; ruff scope on documentation files is moot because pyproject.toml's `[tool.ruff]` does not lint markdown/yaml) |
| 8. byte-equality between examples/debate.yaml and presets/debate.yaml | `Path('src/ultra_claude/presets/debate.yaml').read_bytes() == Path('examples/debate.yaml').read_bytes()` | PASS (1033 bytes both sides; T-09-12 mitigation confirmed) |
| 9. JSONL records validate against actual TurnRecord pydantic | `for r in records: TurnRecord.model_validate(r)` -- all 3 succeed (turn ge=1; agent / role min_length=1; prompt_hash 64 chars; output present) | PASS |
| 10. Cross-platform line endings | All 6 plan files: `git cat-file -p :<path>` shows 0 CRLF in staged blob; `Path(p).read_bytes().count(b'\\r\\n') == 0` on disk | PASS for all 6 files despite `core.autocrlf=true` host -- write path used `Path.write_bytes(content.encode('utf-8'))` which bypasses the autocrlf filter |
| 11. ASCII-only on disk | All 6 plan files: zero bytes `> 127` (no smart quotes, no em-dashes, no emoji) | PASS for all 6 files |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Bash heredoc + Python single-quote collision**

- **Found during:** Task 3 first attempt
- **Issue:** Wrote a single-shot `python <<'PYEOF' ... PYEOF` bash heredoc to generate all 4 examples/* files in one shell invocation. The shell heredoc parser failed with `unexpected EOF while looking for matching '` because the embedded Python source contains apostrophe-d English contractions (`I'd`, `they'll`, `that's`, `it's`, `we're`, etc.) inside Python string literals. Bash interpreted the first apostrophe as opening a new single-quoted string, expected a closing apostrophe, never found one (because the rest of the heredoc body is Python source, not bash strings), and bailed.
- **Fix:** Wrote the multi-file generator script to a real `_build_examples.py` file via the `Write` tool (where backslashes and quote characters survive untouched), executed it via `python _build_examples.py`, then deleted the helper before staging.
- **Files modified:** None in production scope; the helper file was created and deleted in the same execution session and never reached a commit.
- **Commit:** N/A (helper not committed)

### Out-of-scope items NOT fixed (documented for transparency)

**Pre-existing ruff errors in src/ultra_claude/config.py + tests/test_config.py**

`ruff check` repo-wide reports 4 errors:
- `src/ultra_claude/config.py:38` -- RUF022 (`__all__` not sorted)
- `src/ultra_claude/config.py:110` -- UP037 (quoted type annotation `"RoundtableConfig"`)
- `tests/test_config.py:12` -- I001 (import block formatting)
- `tests/test_config.py` -- F401 (unused import)

These were present before plan 09-03 started, documented as deferred since plan 07-01 (commit `4a09f27` reasoning, `.planning/phases/07-gemini-codex-adapters/deferred-items.md`), and live in files this plan did not touch. Per the executor scope-boundary rule (only auto-fix issues directly caused by the current task's changes), they remain deferred. A future cleanup plan or fixup commit will address them.

## Authentication Gates

None encountered. This plan is pure documentation; no live CLI invocations, no external services.

## Threat Model Outcomes

| Threat ID | Disposition | Status |
|-----------|-------------|--------|
| T-09-10 | mitigate | DONE -- author email NOT in README/CONTRIBUTING; only the GitHub URL `https://github.com/frefrechiu/ultra-claude` and the project author name (already in pyproject.toml) appear |
| T-09-11 | accept | DONE -- transcript is hand-written from scratch; zero LLM output flows through; cannot leak by construction |
| T-09-12 | mitigate | DONE -- `examples/debate.yaml` is byte-identical to `src/ultra_claude/presets/debate.yaml` (verified by Gate 8 above); future drift can be caught by a deferred v2 repo-level diff check |
| T-09-13 | mitigate | DONE -- README has a dedicated "Trademark disclaimer" paragraph naming Anthropic / Google / OpenAI explicitly with a "third-party orchestrator" clarification |
| T-09-14 | mitigate | DONE -- `examples/README.md` has a prominent "Synthetic, not real" section explaining the source; the synthetic transcript itself is plain text any reader can inspect |

## Threat Flags

None. Plan 09-03 modifies only documentation artifacts -- zero new network endpoints, zero auth paths, zero file-access patterns, zero schema changes at trust boundaries.

## Rule-N Deviations Summary

| Rule | Count | Description |
|------|-------|-------------|
| Rule 1 (auto-fix bug) | 0 | -- |
| Rule 2 (auto-add critical missing functionality) | 0 | -- |
| Rule 3 (auto-fix blocker) | 1 | Bash heredoc + Python apostrophe collision in Task 3 first attempt -- worked around by writing the generator to a `.py` helper via the `Write` tool, executing, and deleting the helper |
| Rule 4 (architectural ask) | 0 | -- |

Plan 09-03 is the cleanest documentation pass in this phase; the only friction was the multi-quote-character heredoc plumbing.

## Self-Check: PASSED

Verification of all claims in this SUMMARY against the actual filesystem and git log:

| Claim | Verification | Result |
|-------|--------------|--------|
| README.md exists at 6313 bytes / 130 lines | `Path('README.md').read_bytes()` -> 6313 bytes / 130 newlines | FOUND |
| CONTRIBUTING.md exists at 5608 bytes / 92 lines | `Path('CONTRIBUTING.md').read_bytes()` -> 5608 bytes / 92 newlines | FOUND |
| examples/README.md exists at 1771 bytes / 24 lines | `Path('examples/README.md').read_bytes()` -> 1771 bytes / 24 newlines | FOUND |
| examples/debate.yaml exists at 1033 bytes / 30 lines | `Path('examples/debate.yaml').read_bytes()` -> 1033 bytes / 30 newlines | FOUND |
| examples/transcripts/sample-debate.md exists at 2857 bytes / 63 lines | `Path('examples/transcripts/sample-debate.md').read_bytes()` -> 2857 bytes / 63 newlines | FOUND |
| examples/transcripts/sample-debate.md.jsonl exists at 3096 bytes / 3 lines | `Path('examples/transcripts/sample-debate.md.jsonl').read_bytes()` -> 3096 bytes / 3 newlines | FOUND |
| Commit 078dc7c (Task 1) exists | `git log --oneline --all \| grep 078dc7c` returns the docs(09-03) README rewrite line | FOUND |
| Commit 180be45 (Task 2) exists | `git log --oneline --all \| grep 180be45` returns the docs(09-03) CONTRIBUTING line | FOUND |
| Commit 2ab93b7 (Task 3) exists | `git log --oneline --all \| grep 2ab93b7` returns the docs(09-03) examples line | FOUND |
| 86/86 tests pass | `pytest tests/` -> `86 passed in 3.88s` | FOUND (zero regression) |
| examples/debate.yaml byte-equal to bundled preset | `Path('src/ultra_claude/presets/debate.yaml').read_bytes() == Path('examples/debate.yaml').read_bytes()` -> True | FOUND |
| All 4 example files load via project tooling | `load_config('examples/debate.yaml')` returns RoundtableConfig with 3 agents; `TurnRecord.model_validate(rec)` succeeds for all 3 JSONL records | FOUND |

All claims in this SUMMARY are verified against the actual repo state.
