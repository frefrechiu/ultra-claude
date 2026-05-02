# Phase 4 Deferred Items

Out-of-scope discoveries logged during plan execution. Do NOT fix in this phase
unless the user requests it; track here for a future chore plan.

## Pre-existing ruff lint errors (discovered during 04-03 verification, 2026-05-02)

Running `python -m ruff check src/ultra_claude tests/` from the repo root after
04-03 lands surfaces 4 errors in files NOT touched by Phase 4:

1. **`src/ultra_claude/config.py:38` -- RUF022** `__all__` not sorted.
   Same issue Phase 4 has already fixed in `exceptions.py` and
   `adapters/__init__.py` via `# noqa: RUF022` + a justifying comment.
   Suggested fix: add `# noqa: RUF022` plus a comment explaining the
   chronological-by-introduction ordering.

2. **`src/ultra_claude/config.py:110` -- UP037** quoted forward-reference
   in a method return type. `def from_yaml_string(cls, source: str) ->
   "RoundtableConfig"` should be `-> RoundtableConfig` because the file
   has `from __future__ import annotations` (or because the class is
   defined later in the same module and PEP 563 makes the quotes
   redundant).

3. **`tests/test_config.py:12` -- I001** import block is un-sorted /
   un-formatted (cosmetic; ruff `--fix` resolves it).

4. **`tests/test_config.py:24` -- F401** `format_validation_error`
   imported but unused. The test file imports it from
   `ultra_claude.config` but never references it -- safe to drop.

### Why deferred

These errors exist in Phase 2 commits (`e97325a`, `5c272f0`) and were not
introduced or surfaced by Phase 4 plan 04-03. Per the executor scope
boundary rule (only auto-fix issues directly caused by the current task's
changes), they are logged here rather than fixed inline. A future small
chore plan can knock them out together with the
`core.autocrlf=true`/`.gitattributes` item already logged in
`.planning/phases/02-config-schema-yaml-loader/deferred-items.md`.

### Verification before logging

- `python -m ruff check tests/test_adapters_base.py
  tests/test_adapter_claude.py tests/test_subprocess_lint.py` -- all clean
- `python -m ruff check src/ultra_claude/adapters` -- all clean
- The 4 pre-existing errors only surface when ruff is run against
  `src/ultra_claude` and `tests/` together (the plan's verification
  scope), proving they pre-date 04-03.
