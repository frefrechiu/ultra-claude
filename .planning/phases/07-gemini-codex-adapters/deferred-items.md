# Deferred Items — Phase 7

Logged during plan 07-01 execution (2026-05-02). These are pre-existing,
out-of-scope ruff violations in files NOT touched by plan 07-01. They
were present BEFORE this plan started and are NOT regressions.

Per executor scope boundary: only auto-fix issues DIRECTLY caused by the
current task's changes. These belong to a future cleanup plan (likely
Phase 9 quality-bar pass) or a dedicated fixup commit.

## Pre-existing ruff violations (verified via `git stash` round-trip)

1. **`src/ultra_claude/config.py:38`** — RUF022: `__all__` is not sorted.
   Same pattern that motivates `# noqa: RUF022` elsewhere; this file lacks
   the suppression. Fix: add `# noqa: RUF022` on the opening bracket line
   of `__all__ = [`.

2. **`src/ultra_claude/config.py:110`** — UP037: Remove quotes from type
   annotation `"RoundtableConfig"` in `from_yaml_string` return. With
   `from __future__ import annotations` already present at the top of
   the file, the forward reference quotes are unnecessary.

3. **`tests/test_config.py:12`** — I001: Import block is un-sorted or
   un-formatted. Run `ruff check --fix tests/test_config.py` to repair.

4. **`tests/test_config.py:24`** — F401: `format_validation_error`
   imported but unused. Either remove the import or add a usage.

These four errors are **stable across the plan-07-01 boundary**: running
`ruff check src/ultra_claude tests` on the pre-plan-07-01 commit
(`4a09f27` reverted to no working-tree changes) reports the same 4
violations. None are introduced by gemini.py / codex.py / the
__init__.py rewrite / the registry.py rewrite.
