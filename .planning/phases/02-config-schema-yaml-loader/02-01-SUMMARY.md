---
phase: 02-config-schema-yaml-loader
plan: 01
subsystem: config
tags: [exceptions, config-error, foundation, pep257]

# Dependency graph
requires:
  - phase: 01-project-skeleton-pypi-name-reservation
    provides: src/ultra_claude/ package skeleton with __init__.py and src-layout pyproject.toml
provides:
  - "ConfigError exception class importable as `from ultra_claude.exceptions import ConfigError`"
  - "src/ultra_claude/exceptions.py module — single home for all custom exceptions in the package"
  - "Forward-declared landing pad for Phase 4 AdapterError + AdapterAuthError (no churn to config.py when those land)"
affects: [02-02 (config.py uses ConfigError), 04-* (AdapterError lands here), 08-* (CLI maps ConfigError -> exit code 2 per CLI-10)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Custom exceptions live in their own module (exceptions.py), decoupled from Pydantic/YAML/subprocess machinery so the CLI exit-code mapper can import them without those deps."
    - "`from __future__ import annotations` even in zero-annotation files — defensive for future Phase 4 additions."
    - "Class body containing only a docstring (PEP 257 allows this; no `pass` placeholder needed)."

key-files:
  created:
    - "src/ultra_claude/exceptions.py (1387 bytes, 34 lines)"
  modified: []

key-decisions:
  - "ConfigError carries human-readable message via str(err); no custom __init__ or `cause` attribute — Python's stdlib `raise ... from underlying_err` already preserves the chain."
  - "Module is dependency-free: zero imports from pydantic, yaml, or any third-party package. Verified via `dir(module)` scan (clean-OK)."
  - "ConfigError class body is just a docstring — no `pass`, no methods. PEP 257 allows this and avoids dead-code lint hits."
  - "`__all__ = [\"ConfigError\"]` declared so `from ultra_claude.exceptions import *` is well-defined when Phase 4 appends AdapterError/AdapterAuthError."

patterns-established:
  - "Exception module isolation: keep custom exception classes out of feature modules so the CLI layer can import them without dragging in Pydantic/YAML/subprocess. Phase 4 AdapterError/AdapterAuthError will land in this same file."

requirements-completed: [CFG-03]

# Metrics
duration: 2min
completed: 2026-05-02
---

# Phase 2 Plan 01: ConfigError Exception Class Summary

**Created the `ConfigError` exception class in a dedicated `exceptions.py` module — decoupling custom exception types from Pydantic/YAML so the CLI exit-code mapper (Phase 8) can consume them without third-party imports.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-02T02:28:34Z
- **Completed:** 2026-05-02T02:30:33Z
- **Tasks:** 1
- **Files created:** 1

## Accomplishments

- New file `src/ultra_claude/exceptions.py` (1387 bytes, 34 lines, LF-only, ASCII-only).
- `class ConfigError(Exception)` with a docstring documenting the three failure modes it wraps (`yaml.YAMLError`, `pydantic.ValidationError`, `FileNotFoundError`).
- Module docstring foreshadows Phase 4 additions (`AdapterError`, `AdapterAuthError`) so future plans append to this same file without restructuring.
- `__all__ = ["ConfigError"]` declared — clean public surface even when Phase 4 lands more classes.
- All 6 verification checks (parse, import, behavior, __all__, LF-only, no third-party leakage) PASS.

## Task Commits

1. **Task 1: Create src/ultra_claude/exceptions.py with ConfigError** — `ddfca71` (`feat(02-01): add ConfigError exception class`)

_Single-task plan; no test phase (pure data class with no behavior beyond stdlib `Exception`)._

## Files Created/Modified

- `src/ultra_claude/exceptions.py` (created, 1387 bytes) — Single home for all custom exception classes in the `ultra_claude` package. Currently exposes `ConfigError`; Phase 4 will append `AdapterError` and `AdapterAuthError` to this same module.

## Decisions Made

- **Dependency-free module:** Zero imports from `pydantic`, `yaml`, or any third party. Verified via `dir(module)` scan returning no `pydantic`/`yaml` symbols. Rationale: keeps the CLI layer's exit-code mapping (CLI-10, lands in Phase 8) able to `import ConfigError` without dragging Pydantic into the CLI bootstrap path.
- **No custom `__init__`, no `cause` attribute:** Python's stdlib `raise ConfigError(msg) from underlying_err` already preserves the chain via `__cause__`. Adding a custom `cause=` kwarg would be redundant.
- **Class body is just a docstring:** PEP 257 allows this; ruff is happy with it; avoids a no-op `pass` line that would only signal "this class is unfinished".
- **`from __future__ import annotations` even with no annotations:** Defensive — when Phase 4 appends `AdapterError(ConfigError)` or similar with PEP 604 union types, the future-import is already in place.

## No Pydantic/YAML Import Leakage

Verified explicitly via `dir(ultra_claude.exceptions)`: zero symbols match `pydantic` or `yaml` (case-insensitive). The 5th plan-level verification check (`clean-OK`) confirms this.

## Forward-Declaration Note

Phase 4 (Adapter Protocol & ClaudeAdapter) will append two more classes to this same file:
- `class AdapterError(Exception)` — non-auth subprocess failures (timeouts, empty-stdout, non-zero exit codes).
- `class AdapterAuthError(AdapterError)` — auth-specific subprocess failures (re-auth instructions in the message).

The module docstring already documents this. `__all__` will be extended at that point.

## Deviations from Plan

None — plan executed exactly as written. The plan file specified the literal file content and the executor wrote it verbatim. All 6 verification commands (parse-OK, import-OK, behavior-OK, all-OK, LF-OK, clean-OK) passed on first try.

**Total deviations:** 0
**Impact on plan:** None — clean execution.

## Issues Encountered

- **Out-of-scope discovery (logged, not fixed):** Git's `core.autocrlf=true` on the Windows host emitted a warning during `git add` that future checkouts on Windows could materialise CRLF in the working tree. The git index has the file as LF (verified via `git show :path` — 1387 bytes, no `\r\n`), and the on-disk file is currently LF. This is a project-wide concern (would affect every Python source file Phase 2+ creates), not specific to this plan. Logged to `.planning/phases/02-config-schema-yaml-loader/deferred-items.md` with a recommended `.gitattributes` fix.

## Self-Check Verification

All 6 plan verification commands passed post-commit:

1. `parse-OK` — `ast.parse()` accepts the file as valid Python.
2. `import-OK` — `from ultra_claude.exceptions import ConfigError` succeeds with `src/` on `PYTHONPATH`.
3. `behavior-OK` — `isinstance(ConfigError("msg"), Exception)` is `True` and `str(ConfigError("hello"))` returns `"hello"`.
4. `all-OK` — `module.__all__ == ['ConfigError']`.
5. `LF-OK` — `pathlib.Path(file).read_bytes()` contains zero `\r\n` byte sequences.
6. `clean-OK` — `dir(module)` returns no symbols containing `pydantic` or `yaml`.

Additionally:
- ASCII-only content verified (no chars with `ord(c) > 127`).
- Required substrings present: `class ConfigError(Exception):`, `__all__ = ["ConfigError"]`, `from __future__ import annotations`.
- Commit `ddfca71` exists in `git log` and contains exactly one new file (no accidental deletions).
- File size: 1387 bytes (matches index).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Plan 02-02 unblocked.** `src/ultra_claude/config.py` can now `from .exceptions import ConfigError` and use it to wrap `yaml.YAMLError`, `pydantic.ValidationError`, and `FileNotFoundError`.
- **Phase 4 forward-declaration locked in.** When the adapter layer lands, `AdapterError` and `AdapterAuthError` append to this same file with no restructuring.
- **CLI exit-code mapping (Phase 8, CLI-10) is unblocked from a dependency standpoint.** Importing `ConfigError` does not pull in Pydantic, YAML, or subprocess — verified by the `clean-OK` check.

## Self-Check: PASSED

- Created file present at expected path: `src/ultra_claude/exceptions.py` — FOUND (1387 bytes).
- Commit hash present in git log: `ddfca71` — FOUND.
- All 6 plan verification commands re-ran post-commit: 6/6 PASS.
- No stub patterns detected.
- No new threat surface introduced (pure data class, no I/O, no network, no subprocess).

---
*Phase: 02-config-schema-yaml-loader*
*Completed: 2026-05-02*
