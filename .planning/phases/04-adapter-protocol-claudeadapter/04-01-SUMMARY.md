---
phase: 04-adapter-protocol-claudeadapter
plan: 01
subsystem: adapters
tags: [protocol, subprocess, mixin, runtime_checkable, popen, taskkill, killpg, codex-bug-defense, auth-error]

# Dependency graph
requires:
  - phase: 02-config-schema-yaml-loader
    provides: src/ultra_claude/exceptions.py with ConfigError; established LF/UTF-8/ASCII discipline; pyproject.toml ruff/mypy config
provides:
  - AdapterError + AdapterAuthError exception classes (AdapterAuthError subclasses AdapterError so continue-on-error catches both)
  - Adapter typing.Protocol decorated @runtime_checkable (name: str, invoke(prompt: str, timeout: int) -> str)
  - _SubprocessAdapterMixin with _run_subprocess (the only sanctioned subprocess.Popen path) and _kill_process_tree helper
  - Cross-platform Popen contract: text=True, encoding="utf-8", errors="replace", shell=False, list-form argv, mandatory timeout, stdin-piped prompt
  - Empty-stdout defense (Pitfall #2 / openai/codex#19945) lifted into the mixin so every adapter inherits it for free
  - Process-tree kill (Pitfall #5): POSIX os.killpg(getpgid, SIGKILL) after start_new_session=True; Windows taskkill /T /F /PID after CREATE_NEW_PROCESS_GROUP
  - FileNotFoundError -> AdapterAuthError mapping ("CLI not found on PATH; run `<cli> login`")
  - auth_error_markers (case-insensitive substring on stdout+stderr) -> AdapterAuthError
affects: [04-02 (ClaudeAdapter), 04-03 (tests + TST-05 lint test), Phase 7 (Gemini/Codex adapters), Phase 6 (orchestrator catches AdapterError per turn), Phase 8 (CLI maps exceptions to exit codes)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Adapter contract is a typing.Protocol, not an ABC -- structural typing, third parties never inherit"
    - "@runtime_checkable so isinstance(obj, Adapter) works for Phase 8 doctor subcommand discovery"
    - "_SubprocessAdapterMixin enforces the safe-subprocess contract once; bundled adapters call _run_subprocess and never touch subprocess directly"
    - "Cross-platform process-tree kill: POSIX killpg, Windows taskkill /T /F (half-measures leak orphans / burn quota)"
    - "Empty-stdout-with-returncode-zero is a hard error (defends against Codex live TTY bug for ALL adapters)"
    - "contextlib.suppress for swallow-on-cleanup paths (ruff SIM105)"
    - "Per-platform Popen calls (no dict-spread) so mypy --strict picks the right overload"
    - "Custom exceptions live in a dedicated module (no Pydantic / subprocess imports needed by CLI layer)"

key-files:
  created:
    - "src/ultra_claude/adapters/__init__.py (923 bytes, 21 lines, LF-only, ASCII-only) -- package marker re-exporting Adapter and _SubprocessAdapterMixin"
    - "src/ultra_claude/adapters/base.py (11805 bytes, 269 lines, LF-only, ASCII-only) -- Adapter Protocol + _SubprocessAdapterMixin._run_subprocess + _kill_process_tree"
  modified:
    - "src/ultra_claude/exceptions.py (3569 bytes, 80 lines, LF-only, ASCII-only) -- added AdapterError and AdapterAuthError; __all__ extended in intentional Phase-2-then-Phase-4 order; module docstring tense updated"

key-decisions:
  - "Use subprocess.Popen (not subprocess.run) inside _run_subprocess so we can catch TimeoutExpired and call _kill_process_tree BEFORE re-raising as AdapterError; subprocess.run wraps Popen+communicate but raises before our cleanup runs"
  - "Empty-stdout defense lives in the mixin (not just CodexAdapter) so every adapter -- including ClaudeAdapter -- inherits the protection automatically; future regressions of the same shape (silent failures with successful exit codes) cannot slip through any adapter"
  - "FileNotFoundError on Popen is mapped to AdapterAuthError, not a generic 'install me' error; treating 'binary missing' as an auth/setup problem matches the user's intent to fix it (run the install/login flow)"
  - "auth_error_markers is a tuple per adapter (each adapter declares its own); matched case-insensitively against stdout+stderr concatenated; matched marker is included in the error message for debuggability"
  - "Per-platform Popen calls instead of one call with a dict[str, object] kwargs spread so mypy --strict can resolve the correct Popen[str] overload without # type: ignore[arg-type]"
  - "POSIX-only os.getpgid / os.killpg / signal.SIGKILL get # type: ignore[attr-defined] because mypy on Windows cannot see them; the type-ignore is scoped to two lines on the POSIX branch only, NOT a module-wide suppression"
  - "Order of __all__ in exceptions.py is intentional (ConfigError = Phase 2, AdapterError + AdapterAuthError = Phase 4) -- ruff RUF022 silenced with a justifying comment + noqa rather than alphabetised; this matches the chronological-by-introduction convention used elsewhere in the codebase"
  - "AdapterAuthError subclasses AdapterError so callers that only catch AdapterError still catch the auth case (continue-on-error semantics apply uniformly); callers that want re-auth-specific handling can catch AdapterAuthError first"

patterns-established:
  - "Choke-point mixin: every adapter's path to subprocess goes through _SubprocessAdapterMixin._run_subprocess; no concrete adapter calls subprocess directly. This will be enforced by the TST-05 lint test in 04-03."
  - "Cross-platform branching done at Popen call time (not after) so platform-specific creationflags / start_new_session / encoding flags are baked in from the start and the corresponding kill helper has the right preconditions"
  - "Drain-after-kill: after _kill_process_tree, do a 2-second proc.communicate() under contextlib.suppress to let the OS reap pipes cleanly even if the kill races the timeout"

requirements-completed: [ADP-01, ADP-02, ADP-03, ADP-04, ADP-08]

# Metrics
duration: 7min
completed: 2026-05-02
---

# Phase 4 Plan 01: Adapter Protocol + _SubprocessAdapterMixin Summary

**Locked the safe-subprocess invocation contract for every ultra-claude adapter in a single mixin: stdin-piped prompts, UTF-8/replace decoding, mandatory timeout, cross-platform process-tree kill (POSIX killpg / Windows taskkill /T /F), and empty-stdout-with-returncode-zero defense (openai/codex#19945) -- so ClaudeAdapter (04-02) and Phase 7 Gemini / Codex adapters all inherit the same battle-tested contract automatically.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-05-02T03:17:46Z
- **Completed:** 2026-05-02T03:24:44Z
- **Tasks:** 2 / 2
- **Files created:** 2 (`adapters/__init__.py`, `adapters/base.py`)
- **Files modified:** 1 (`exceptions.py`)

## Accomplishments

- **Adapter typing.Protocol** decorated `@runtime_checkable` (`name: str`, `invoke(prompt: str, timeout: int) -> str`) -- third-party adapters do NOT need to inherit; `isinstance(obj, Adapter)` works at runtime for Phase 8 `doctor` subcommand adapter discovery.
- **`_SubprocessAdapterMixin._run_subprocess`** is THE choke point for every ultra-claude adapter. Concrete adapters call it; they MUST NOT call `subprocess` directly. The Phase 4-03 lint test (TST-05) will fail the build if any new `subprocess.run` / `subprocess.Popen` call in `src/ultra_claude/` lacks the safe-contract keywords.
- **All four critical pitfalls mitigated** in a single method body:
  1. **Pitfall #1 (argv > 8 KB on Windows cmd.exe):** prompt piped via stdin, never on argv.
  2. **Pitfall #2 (codex exec 0.124.0+ TTY bug):** empty stdout with `returncode == 0` raises `AdapterError` naming `openai/codex#19945` -- the defense lives in the mixin so EVERY adapter (not just Codex) inherits it for free.
  3. **Pitfall #3 (cp1252 vs UTF-8 on Windows):** `text=True, encoding="utf-8", errors="replace"` on every `Popen`.
  4. **Pitfall #5 (orphaned children burning subscription quota):** mandatory `timeout`, then on `TimeoutExpired` a process-tree kill via POSIX `os.killpg(getpgid(pid), SIGKILL)` (after `start_new_session=True`) or Windows `taskkill /T /F /PID` (after `CREATE_NEW_PROCESS_GROUP`).
- **`AdapterError` + `AdapterAuthError`** added to `exceptions.py`; `AdapterAuthError` subclasses `AdapterError` so the orchestrator's continue-on-error semantics apply uniformly while the CLI layer can still show a re-auth-specific message.
- **Auth detection** via two paths: `FileNotFoundError` (CLI binary not on PATH) and case-insensitive substring match of `auth_error_markers` against `stdout + stderr`.
- **`_kill_process_tree`'s own `subprocess.run` taskkill call** also passes the full safe-contract kwargs (`text=True, encoding="utf-8", errors="replace", shell=False`) so the 04-03 lint test will not flag the helper itself.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend `exceptions.py` with `AdapterError` and `AdapterAuthError`** -- `e4423d0` (feat)
2. **Task 2: Create `adapters/` package with `__init__.py` and `base.py`** -- `eceb9da` (feat)

_Plan metadata commit will follow this SUMMARY._

## Files Created/Modified

- `src/ultra_claude/exceptions.py` (modified) -- 80 lines, 3569 bytes; added `AdapterError`, `AdapterAuthError`; updated module docstring from "Phase 4 will append" to past tense; `__all__` extended to `["ConfigError", "AdapterError", "AdapterAuthError"]` with `# noqa: RUF022` and a justifying comment about the intentional Phase-2-then-Phase-4 ordering.
- `src/ultra_claude/adapters/__init__.py` (created) -- 21 lines, 923 bytes; package marker re-exporting `Adapter` and `_SubprocessAdapterMixin`.
- `src/ultra_claude/adapters/base.py` (created) -- 269 lines, 11805 bytes; `Adapter` Protocol + `_SubprocessAdapterMixin` + `_run_subprocess` + `_kill_process_tree`. The single longest file in the package so far, but tightly scoped: every line implements one of the seven contract guarantees.

## Verification

All 5 plan-level verification commands PASS:

- `python -c "from ultra_claude.exceptions import AdapterError, AdapterAuthError; from ultra_claude.adapters import Adapter, _SubprocessAdapterMixin; print('OK')"` -> `OK`
- `python -m mypy --strict src/ultra_claude/exceptions.py src/ultra_claude/adapters/` -> `Success: no issues found in 3 source files`
- `python -m ruff check src/ultra_claude/exceptions.py src/ultra_claude/adapters/` -> `All checks passed!`
- `python -m pytest tests/ -x` -> `16 passed in 0.26s` (8 config + 8 transcript; zero regression)
- LF-only check on all 3 files -> `LF-only OK`

Plus 6 inline integration smoke checks exercised the full contract via `unittest.mock.patch('subprocess.Popen', ...)`:

| # | Scenario | Expected | Actual |
|---|----------|----------|--------|
| 1 | `Popen` raises `FileNotFoundError` | `AdapterAuthError` mentioning `cli_name` and "not found on PATH" | PASS |
| 2 | Empty stdout + `returncode == 0` | `AdapterError` mentioning `19945` | PASS |
| 3 | `auth_error_markers` substring in stdout | `AdapterAuthError` mentioning "not authenticated" + the matched marker | PASS |
| 4 | Happy path (`returncode == 0`, non-empty stdout) | trimmed stdout returned | PASS |
| 5 | Non-zero exit | `AdapterError` mentioning the exit code | PASS |
| 6 | `TimeoutExpired` from `communicate` | `_kill_process_tree` called, then `AdapterError` mentioning `timed out after Ns` | PASS |

## Deviations from Plan

The plan executed largely as written. Three Rule-3 deviations needed to make the deliverables pass `mypy --strict` and `ruff check` cleanly:

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Refactored Popen call to per-platform branches**
- **Found during:** Task 2 mypy verification.
- **Issue:** The plan's literal code used a single `subprocess.Popen(argv, **popen_kwargs)` call where `popen_kwargs: dict[str, object]` accumulated platform-specific keys. mypy --strict cannot match `dict[str, object]` to any of `Popen`'s eight overloads -> `call-overload` error, which transitively poisoned the return type to `Any` (-> `no-any-return` error on `return stdout.strip()`).
- **Fix:** Split into two explicit `subprocess.Popen(...)` calls inside an `if os.name == "nt":` / `else:` block. Each call passes literal kwargs (`stdin=subprocess.PIPE, ..., creationflags=...` or `..., start_new_session=True`) so mypy resolves to the `Popen[str]` overload directly. The `# type: ignore[arg-type]` from the plan is no longer needed.
- **Files modified:** `src/ultra_claude/adapters/base.py`.
- **Commit:** `eceb9da`.

**2. [Rule 3 - Blocking] mypy --strict cannot see POSIX-only os attributes on Windows**
- **Found during:** Task 2 mypy verification.
- **Issue:** `os.getpgid`, `os.killpg`, `signal.SIGKILL` are POSIX-only. mypy running on Windows reports `attr-defined` errors on the POSIX branch of `_kill_process_tree`.
- **Fix:** Added `# type: ignore[attr-defined]` to the two affected lines (POSIX branch only, NOT a module-wide suppression). The runtime guard `if os.name == "nt":` ensures the POSIX branch only runs on POSIX hosts.
- **Files modified:** `src/ultra_claude/adapters/base.py`.
- **Commit:** `eceb9da`.

**3. [Rule 3 - Blocking] ruff SIM105 on three try/except/pass blocks**
- **Found during:** Task 2 ruff verification.
- **Issue:** ruff SIM105 flagged three `try: ...; except (...): pass` blocks in `_run_subprocess` (drain after kill) and `_kill_process_tree` (last-ditch direct kill). The plan's literal code used the verbose `try/except/pass` shape.
- **Fix:** Replaced with `with contextlib.suppress(...):` (functionally identical, no behavioral change). Added `import contextlib`.
- **Files modified:** `src/ultra_claude/adapters/base.py`.
- **Commit:** `eceb9da`.

**4. [Rule 3 - Blocking] ruff RUF022 on `__all__` order in exceptions.py**
- **Found during:** Task 1 ruff verification.
- **Issue:** ruff RUF022 ("`__all__` is not sorted") flagged `["ConfigError", "AdapterError", "AdapterAuthError"]` because alphabetical order would put `Adapter*` first. The plan acceptance criteria explicitly demand this exact order ("Phase 2 base, then Phase 4 additions"), and Phase 2 already shipped a similarly non-alphabetical `__all__` in `config.py`.
- **Fix:** Added a justifying comment plus `# noqa: RUF022` on the `__all__` line. ruff now passes cleanly while the chronological-by-introduction order requested by the plan is preserved.
- **Files modified:** `src/ultra_claude/exceptions.py`.
- **Commit:** `e4423d0`.

No Rule-1 (bug), Rule-2 (missing critical functionality), or Rule-4 (architectural) deviations were needed. The plan's contract was complete and correct as written; the deviations above were all about making the source acceptable to the project's strict lint/type tooling without changing semantics.

## Authentication Gates

None. This plan does not invoke any external CLIs at execution time (those land in 04-02 / 04-03 with mocked subprocess via `pytest-subprocess`).

## Threat Flags

None. This plan adds source surface inside `src/ultra_claude/` only. The `subprocess.Popen` and `subprocess.run` calls introduced by this plan are the canonical safe-contract calls that future code will be linted against (TST-05); they are NOT new threat surface, they are the choke point that REDUCES future threat surface by giving every adapter one sanctioned path to subprocess.

## Self-Check: PASSED

Verified files exist:
- FOUND: `src/ultra_claude/exceptions.py`
- FOUND: `src/ultra_claude/adapters/__init__.py`
- FOUND: `src/ultra_claude/adapters/base.py`

Verified commits exist:
- FOUND: `e4423d0` (Task 1)
- FOUND: `eceb9da` (Task 2)
