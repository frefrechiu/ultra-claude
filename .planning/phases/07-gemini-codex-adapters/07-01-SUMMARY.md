---
phase: 07-gemini-codex-adapters
plan: 01
subsystem: adapters
tags: [subprocess, adapter, protocol, mixin, gemini, codex, cli, registry]

# Dependency graph
requires:
  - phase: 04-adapter-protocol-claudeadapter
    provides: "_SubprocessAdapterMixin (safe-subprocess contract: stdin-piped prompt, UTF-8/replace, mandatory timeout, process-tree kill, empty-stdout defense, auth-marker detection); Adapter typing.Protocol; AdapterError/AdapterAuthError exceptions"
  - phase: 06-orchestrator-loop
    provides: "registry.get_adapter dispatch function (NotImplementedError branch for gemini/codex stub now removed)"
provides:
  - "GeminiAdapter concrete adapter wrapping `gemini -p` (ADP-06)"
  - "CodexAdapter concrete adapter wrapping `codex exec` (ADP-07) with openai/codex#19945 documentation in module docstring"
  - "Updated adapters/__init__.py with 5-entry __all__ in roadmap-introduction order"
  - "Updated registry.get_adapter dispatching all three adapter literals to real instances (NotImplementedError branch removed)"
affects: [phase-07-02, phase-08-cli-surface, phase-09-release]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Concrete adapter mirrors ClaudeAdapter pattern: 4 deltas only (class name, name/cli_name literal, auth_error_markers tuple, argv list literal)"
    - "Module docstring as architectural traceability anchor: codex.py docstring references openai/codex#19945 for the live-bug context (D-03)"
    - "Distinct auth_error_markers per CLI vendor (D-02): no shared constants because real-world auth-failure phrasing varies"

key-files:
  created:
    - "src/ultra_claude/adapters/gemini.py (94 lines, 4123 bytes, LF-only, ASCII-only)"
    - "src/ultra_claude/adapters/codex.py (100 lines, 4339 bytes, LF-only, ASCII-only)"
  modified:
    - "src/ultra_claude/adapters/__init__.py (40 lines, 1798 bytes, LF-only, ASCII-only) - extended __all__ from 3 to 5 entries"
    - "src/ultra_claude/registry.py (51 lines, 1998 bytes, LF-only, ASCII-only) - replaced NotImplementedError branch with concrete instantiation"

key-decisions:
  - "Both adapters one-line invoke() bodies delegate to _run_subprocess(argv, prompt, timeout); no defensive code added on top of mixin"
  - "Codex module docstring includes openai/codex#19945 reference (D-03 traceability marker for the live-bug context that the inherited mixin defense is what makes CodexAdapter safe)"
  - "auth_error_markers KEPT DISTINCT per vendor (D-02): GeminiAdapter has 4 markers ('not logged in', 'please run `gemini auth login`', 'authentication required', 'no credentials'), CodexAdapter has 3 ('not logged in', 'please run `codex login`', 'authentication required')"
  - "__all__ ordering preserves architectural narrative (base Protocol+mixin first, then concrete adapters in roadmap-introduction order Claude->Gemini->Codex), with `# noqa: RUF022` on the opening bracket line"
  - "Registry now uses three explicit `if adapter_kind == ...` branches plus a final ValueError; NotImplementedError branch deleted entirely"

patterns-established:
  - "Multi-line `__all__` with `# noqa: RUF022` placement: noqa goes on the OPENING bracket line, not closing (ruff 0.15.8 specific)"
  - "Concrete adapter file template (gemini.py, codex.py) is now proven 3 times; future Phase-N adapters can mirror unchanged"

requirements-completed: [ADP-06, ADP-07]

# Metrics
duration: 4min
completed: 2026-05-02
---

# Phase 7 Plan 1: Gemini + Codex Adapter Source Files + Registry Update Summary

**GeminiAdapter and CodexAdapter source files plus adapters/__init__.py + registry.py wiring, all reusing _SubprocessAdapterMixin unchanged from Phase 4 -- ADP-06 and ADP-07 closed at IMPLEMENTATION level**

## Performance

- **Duration:** ~4 min (278 seconds)
- **Started:** 2026-05-02T05:04:31Z
- **Completed:** 2026-05-02T05:09:09Z
- **Tasks:** 2/2 complete (autonomous, no checkpoints)
- **Files modified:** 4 (2 new + 2 modified)

## Accomplishments

- **GeminiAdapter**: New file `src/ultra_claude/adapters/gemini.py` (94 lines) defining `class GeminiAdapter(_SubprocessAdapterMixin)` with `name="gemini"`, `cli_name="gemini"`, distinct 4-entry `auth_error_markers` tuple, and a one-line `invoke()` delegating to `self._run_subprocess(["gemini", "-p"], prompt, timeout)`. Zero direct subprocess imports. Satisfies the `Adapter` Protocol via runtime_checkable structural typing. Mirrors the proven ClaudeAdapter pattern with vendor-specific deltas only.
- **CodexAdapter**: New file `src/ultra_claude/adapters/codex.py` (100 lines) defining `class CodexAdapter(_SubprocessAdapterMixin)` with `name="codex"`, `cli_name="codex"`, distinct 3-entry `auth_error_markers` tuple, and a one-line `invoke()` delegating to `self._run_subprocess(["codex", "exec"], prompt, timeout)`. Module docstring references `openai/codex#19945` (D-03 traceability) documenting why the inherited empty-stdout defense matters specifically here. Zero direct subprocess imports.
- **Adapters package extended**: `src/ultra_claude/adapters/__init__.py` extended from a 3-entry `__all__` to a 5-entry `__all__` (Adapter, _SubprocessAdapterMixin, ClaudeAdapter, GeminiAdapter, CodexAdapter), preserving roadmap-introduction order via `# noqa: RUF022`. The import block above `__all__` is sorted alphabetically (.base, .claude, .codex, .gemini) per ruff's `I` rules; `__all__` order is intentional and documented in the comment block.
- **Registry now dispatches all three literals**: `src/ultra_claude/registry.py` replaces the `NotImplementedError` raise with concrete instantiation; `get_adapter("claude")` -> `ClaudeAdapter()`, `get_adapter("gemini")` -> `GeminiAdapter()`, `get_adapter("codex")` -> `CodexAdapter()`, anything else -> `ValueError`. Module docstring tense updated from forward-looking to past/present.
- **Zero regression**: 50/50 full test suite PASS (same count as before plan; new adapters are not yet test-covered -- that lands in plan 07-02).

## Task Commits

Each task was committed atomically:

1. **Task 1: Create gemini.py and codex.py concrete adapters** - `4a09f27` (feat)
2. **Task 2: Wire GeminiAdapter and CodexAdapter into __init__.py and registry.py** - `5f067c1` (feat)

**Plan metadata commit (final):** to be captured after this SUMMARY + STATE updates land

## Files Created/Modified

### Created

- `src/ultra_claude/adapters/gemini.py` (94 lines, 4123 bytes) - `GeminiAdapter` wrapping `gemini -p`; argv `["gemini", "-p"]`; auth markers (not logged in, please run `gemini auth login`, authentication required, no credentials)
- `src/ultra_claude/adapters/codex.py` (100 lines, 4339 bytes) - `CodexAdapter` wrapping `codex exec`; argv `["codex", "exec"]`; auth markers (not logged in, please run `codex login`, authentication required); module docstring references openai/codex#19945

### Modified

- `src/ultra_claude/adapters/__init__.py` (40 lines, 1798 bytes) - 5-entry `__all__` in introduction order; imports for `.codex` and `.gemini` added; module docstring updated to describe all three concrete adapters
- `src/ultra_claude/registry.py` (51 lines, 1998 bytes) - `NotImplementedError` branch removed; `if adapter_kind == "gemini": return GeminiAdapter()` and `if adapter_kind == "codex": return CodexAdapter()` branches added; module docstring tense changed to past/present; Raises: section drops `NotImplementedError`

## Decisions Made

- **D-01 (locked from plan)**: GeminiAdapter argv is exactly `["gemini", "-p"]`; CodexAdapter argv is exactly `["codex", "exec"]`. Prompt piped via stdin (delegated to mixin).
- **D-02 (locked from plan)**: `auth_error_markers` KEPT DISTINCT per CLI vendor -- no shared constant. Real-world auth-failure phrasing varies by CLI.
- **D-03 (locked from plan)**: codex.py module docstring references `openai/codex#19945`. The defense itself is inherited from the Phase 4 mixin; this is documentation-only payload.
- **Multi-line `__all__` noqa placement**: ruff 0.15.8 RUF022 + RUF100 rules require `# noqa: RUF022` on the OPENING bracket line of a multi-line `__all__`, not the closing bracket. The plan body suggested closing-bracket placement; this was corrected during execution and tracked as Rule 3 deviation (below).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `# noqa: RUF022` placement on multi-line `__all__`**
- **Found during:** Task 2 (Wire GeminiAdapter/CodexAdapter into __init__.py and registry.py)
- **Issue:** The plan-suggested form placed `# noqa: RUF022` on the closing bracket line of a multi-line `__all__` (`]  # noqa: RUF022`). Under ruff 0.15.8 with the project's `select = [..., "I", ..., "RUF"]` config, this triggered TWO errors: (a) **RUF022** "`__all__` is not sorted" because ruff didn't see the noqa as covering the violation; (b) **RUF100** "Unused `noqa` directive" because ruff considered the noqa orphan. The plan's reference example for `exceptions.py` works because that `__all__` is single-line, so the noqa naturally lives on the same line as the violation. Multi-line `__all__` requires the noqa on the OPENING line.
- **Fix:** Moved `# noqa: RUF022` from the closing bracket line `]  # noqa: RUF022` to the opening bracket line `__all__ = [  # noqa: RUF022`. Single-character relocation, no semantic change.
- **Files modified:** `src/ultra_claude/adapters/__init__.py`
- **Verification:** `ruff check src/ultra_claude/adapters/__init__.py` PASS after fix; full `ruff check src/ultra_claude/adapters/__init__.py src/ultra_claude/adapters/gemini.py src/ultra_claude/adapters/codex.py src/ultra_claude/registry.py` PASS.
- **Committed in:** `5f067c1` (Task 2 commit) -- the corrected form is what landed; the broken form was never committed.

**Total deviations:** 1 auto-fixed (1 Rule 3 blocking).
**Impact on plan:** Negligible (cosmetic fix; intent preserved). The roadmap-introduction order in `__all__` is preserved as the plan and CONTEXT.md require.

## Plan-Level Verification Gates (all PASS)

| Gate | Result |
|------|--------|
| Headline structural / registry check (`isinstance(GeminiAdapter(), Adapter)` etc.) | OK: structural / registry checks pass |
| `mypy --strict src/ultra_claude` | Success: no issues found in 12 source files (was 10) |
| `ruff check` on the 4 modified/new files | All checks passed! |
| `pytest tests/` | 50 passed in 0.95s (zero regression -- 50/50 prior tests still PASS) |
| `pytest tests/test_subprocess_lint.py -x` | 3 passed in 0.03s (TST-05 lint catches no new violations) |
| LF-only on disk (`b"\r\n" not in path.read_bytes()`) | True for all 4 files (gemini.py, codex.py, __init__.py, registry.py) |
| ASCII-only on disk | True for all 4 files |
| No direct `import subprocess` / `from subprocess` | Confirmed absent in gemini.py and codex.py |
| `openai/codex#19945` literal in codex.py module docstring | Confirmed present (D-03) |
| Staged blob LF-only despite `core.autocrlf=true` | Verified for all 4 files via `git cat-file blob`: 0 CRLF in each blob |
| Working-tree changes after the plan | 4 (2 new files: gemini.py, codex.py; 2 modified files: __init__.py, registry.py) -- matches plan success criterion exactly |

## Issues Encountered

- **4 pre-existing ruff violations** in `src/ultra_claude/config.py` (RUF022, UP037) and `tests/test_config.py` (I001, F401) — verified via `git stash` round-trip that these existed BEFORE plan 07-01. Out-of-scope per executor scope-boundary rule. Logged to `.planning/phases/07-gemini-codex-adapters/deferred-items.md` for a future cleanup pass (likely the Phase 9 quality-bar pass).

## Carry-Forward Note for Plan 07-02

Plan 07-02 will land:
- `tests/test_adapter_gemini.py` mirroring `tests/test_adapter_claude.py` (5-6 tests via `pytest-subprocess` `fp` fixture: argv assertion, stdin payload, empty-stdout, FileNotFoundError, auth marker, TimeoutExpired+process-tree kill).
- `tests/test_adapter_codex.py` with the same set of cases PLUS the headline `test_codex_empty_stdout_bug_regression` documenting Pitfall #2 / openai/codex#19945 -- proving the inherited mixin defense fires correctly when the Codex CLI returns `(returncode=0, stdout="")`.
- Zero source changes in plan 07-02; the new test files only.

After 07-02 lands, ADP-06 and ADP-07 will be both IMPLEMENTATION-verified (this plan) and TEST-verified, closing Phase 7.

## Next Phase Readiness

Phase 7 plan 07-01 closes the SOURCE side. Plan 07-02 closes the TEST side. Phase 8 (CLI Surface) depends on both 07-01 and 07-02 because `ultra-claude doctor` will probe each registered adapter via `get_adapter("gemini")` / `get_adapter("codex")` -- those calls now return real instances (this plan), and 07-02's tests confirm the contract holds against mocked subprocesses.

## Self-Check: PASSED

Verified:
- `src/ultra_claude/adapters/gemini.py` exists (4123 bytes)
- `src/ultra_claude/adapters/codex.py` exists (4339 bytes)
- `src/ultra_claude/adapters/__init__.py` modified with 5-entry __all__
- `src/ultra_claude/registry.py` modified with concrete instantiation for gemini/codex
- Commit `4a09f27` exists in `git log` (Task 1)
- Commit `5f067c1` exists in `git log` (Task 2)
- All plan-level verification gates PASS

---
*Phase: 07-gemini-codex-adapters*
*Completed: 2026-05-02*
