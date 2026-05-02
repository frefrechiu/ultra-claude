---
phase: 08-cli-surface-debate-preset
plan: 03
subsystem: testing
tags: [pytest, click, click.testing.CliRunner, monkeypatch, FakeAdapter, end-to-end, doctor, dry-run, exit-codes, stdout-stderr-discipline]

# Dependency graph
requires:
  - phase: 08-cli-surface-debate-preset
    provides: "src/ultra_claude/cli.py with click group `main` + `run` + `doctor` subcommands and exit-code mapping (plan 08-02); src/ultra_claude/presets/debate.yaml bundled preset (plan 08-01)"
  - phase: 06-orchestrator-loop
    provides: "ultra_claude.orchestrator imports `get_adapter` at module top level so monkeypatch.setattr(orch_module, 'get_adapter', ...) is the canonical adapter-injection seam for CLI end-to-end tests"
  - phase: 04-adapter-protocol-claudeadapter
    provides: "AdapterError raised by FakeAdapter.invoke triggers the CLI's exit-1 mapping path (used in test_adapter_error_with_abort_on_error_exits_with_code_one)"
provides:
  - "tests/test_cli.py with 11 test functions, one per CLI requirement (CLI-01..CLI-11) plus PRE-01 (the bundled debate preset is loadable end-to-end). 83/83 full suite PASS (was 72; +11 new). TST-05 lint stays 3/3 PASS."
  - "Pattern: monkeypatch.setattr(ultra_claude.orchestrator, 'get_adapter', fake_factory) replaces the orchestrator's module-level binding so the CLI's run() pipeline uses FakeAdapters end-to-end without any real subprocess launched."
  - "Pattern: doctor probe testing via monkeypatch.setattr(cli_module.shutil, 'which', ...) + monkeypatch.setattr(cli_module.subprocess, 'run', fake_run) -- fake_run additionally asserts safe-contract kwargs (text=True, encoding='utf-8', errors='replace', shell=False, timeout=...) are present, defense-in-depth alongside TST-05 lint."
  - "Pattern: stdout-only discipline test reads result.stdout (not result.output) -- click 8.3+ splits stdout/stderr automatically; the deprecated mix_stderr=False parameter is unnecessary and would raise TypeError on click >= 8.3."
affects: [09-tests-docs-examples-release (test suite scaffolding extension; the 11-test pattern + FakeAdapter mirroring proves the CliRunner approach for any future CLI surface additions); ROADMAP closure (Phase 8 fully closed: 12/12 requirements both IMPLEMENTATION + TEST verified)]

# Tech tracking
tech-stack:
  added: []  # No new dependencies; click + pytest already pinned, click.testing.CliRunner is part of click stdlib
  patterns:
    - "click.testing.CliRunner.invoke for in-process CLI testing -- no shell, no subprocess, no env-leakage; test file launches ZERO real CLIs"
    - "FakeAdapter mirrored across test files (tests/test_cli.py and tests/test_orchestrator.py) rather than imported -- each test file is independently runnable in isolation (`pytest tests/test_cli.py -x` works without test_orchestrator.py being collected)"
    - "Adapter-injection seam via `monkeypatch.setattr(orch_module, 'get_adapter', fake_factory)` -- the orchestrator imports `get_adapter` from .registry at module top level, so patching the symbol on the orchestrator module replaces the binding the run() loop uses"
    - "Safe-contract validation in fake_run -- the doctor test's fake_run callable asserts `kwargs.get('text') is True`, `encoding=='utf-8'`, `errors=='replace'`, `shell=False`, `timeout` present on every call. If a future cli.py refactor drops a required kwarg, this test fires alongside TST-05 lint"
    - "click 8.3+ stdout/stderr always-split semantics -- `result.stdout` and `result.stderr` are independent attributes by default; no `mix_stderr=False` parameter required (the parameter was removed in click 8.3 as the new default)"
    - "monkeypatch.chdir(tmp_path) for cwd-relative defaults like `./ultra-claude.yaml` -- keeps test artefacts hermetic, no repo pollution"

key-files:
  created:
    - "tests/test_cli.py (457 lines, 15515 bytes, LF-only, ASCII-only, UTF-8) -- 11 test functions (one per CLI-01..CLI-11) plus PRE-01 verified by case 4 (`--preset debate` end-to-end)"
  modified: []  # Plan 08-03 is test-only -- no source changes

key-decisions:
  - "FakeAdapter mirrored, NOT imported from tests/test_orchestrator.py -- mirroring keeps the test file independently runnable in isolation. The 17-line class is small enough that DRY-via-shared-conftest.py would add more coupling than it removes. Plan instruction (note 1); applied verbatim."
  - "Doctor probe test asserts safe-contract kwargs in fake_run -- defense-in-depth alongside TST-05 lint. The lint catches missing kwargs at AST-walk time; the runtime assertion catches them at test-time. Both layers fire if a future cli.py refactor drops a kwarg. Plan note 2; applied verbatim."
  - "Stdout-discipline test uses default `CliRunner()` rather than `CliRunner(mix_stderr=False)` -- the latter would raise `TypeError: __init__() got an unexpected keyword argument 'mix_stderr'` on click 8.3.3 (the version pinned in pyproject.toml >=8.3.3). click 8.3 removed `mix_stderr` because stdout/stderr split is now the default. Documented as a Rule 3 deviation below."
  - "monkeypatch.setattr on the orchestrator module's `get_adapter` symbol (NOT on `registry.get_adapter`) -- the orchestrator imports the function once at module load and uses the module-local binding inside run(). Patching `registry.get_adapter` would NOT affect the orchestrator's already-cached reference. The test's seam is `ultra_claude.orchestrator.get_adapter`, period."
  - "11 test functions, exactly -- one per CLI requirement (CLI-01..CLI-11). PRE-01 is verified by case 4 (`test_run_with_preset_debate_loads_bundled_yaml`) which exercises `--preset debate`. No 12th test for PRE-01 separately; the preset works iff case 4 passes."
  - "Plan note 11: no emojis or Unicode in the test file -- all 15515 bytes are ASCII (verified via `len([b for b in data if b > 127]) == 0`). Per CLAUDE.md Critical Constraint #6."

requirements-completed: [CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, CLI-06, CLI-07, CLI-08, CLI-09, CLI-10, CLI-11, PRE-01]

# Metrics
duration: ~3.9 min
completed: 2026-05-02
---

# Phase 8 Plan 3: tests/test_cli.py via click.testing.CliRunner (CLI-01..CLI-11 + PRE-01) Summary

**11-test CliRunner suite covering every CLI flag and exit-code path -- including end-to-end pipeline via FakeAdapter injection through `monkeypatch.setattr(orch_module, 'get_adapter', ...)` -- closing Phase 8 (12/12 requirements both IMPLEMENTATION + TEST verified) and unblocking Phase 9 (release prep).**

## Performance

- **Duration:** ~3.9 min
- **Started:** 2026-05-02T06:08:03Z
- **Completed:** 2026-05-02T06:11:54Z
- **Tasks:** 1
- **Files created:** 1 (tests/test_cli.py)
- **Files modified:** 0

## Accomplishments

- Created `tests/test_cli.py` (457 lines, 15515 bytes, LF-only, ASCII-only, UTF-8) with exactly 11 test functions covering every CLI surface element:
  1. `test_version_flag_prints_version_and_exits_zero` (CLI-01) -- `ultra-claude --version` prints `__version__` substring on stdout, rc=0.
  2. `test_help_flag_lists_subcommands_and_exits_zero` (CLI-02) -- `--help` shows `run`, `doctor`, and a `Commands` section, rc=0.
  3. `test_run_with_inline_task_dry_run_validates_and_exits_zero` (CLI-06 + CLI-07) -- `run --inline ... --dry-run` works without a real adapter; output contains `Turn 1:` and the inline task string.
  4. `test_run_with_preset_debate_loads_bundled_yaml` (CLI-05 + PRE-01) -- `run --preset debate --inline ... --dry-run` works in any cwd (no local `ultra-claude.yaml`); output contains all 3 agent names (Architect, Critic, Implementer) AND all 3 adapter literals (claude, gemini, codex).
  5. `test_run_with_config_path_overrides_default` (CLI-04) -- `--config <path>` loads a custom YAML successfully.
  6. `test_run_dry_run_outputs_full_turn_order` (CLI-07) -- with `max_turns=4` and 2 agents, dry-run prints `Turn 1:` through `Turn 4:` (round-robin Alpha/Beta/Alpha/Beta).
  7. `test_doctor_command_prints_status_table` (CLI-09) -- mocks `shutil.which` and `subprocess.run`; prints 4-column ASCII table (CLI / On PATH / Auth / Notes) for all 3 CLIs; rc=0; the `fake_run` callable additionally asserts safe-contract kwargs (text=True, encoding='utf-8', errors='replace', shell=False, timeout=...) on every call (defense-in-depth alongside TST-05 lint).
  8. `test_config_error_exits_with_code_two` (CLI-10) -- malformed YAML (string list entry where mapping required) -> rc=2.
  9. `test_adapter_error_with_abort_on_error_exits_with_code_one` (CLI-10) -- FakeAdapter raises `AdapterError` on every invoke; with `--abort-on-error`, the CLI's `except AdapterError` handler fires `ctx.exit(1)`; rc=1 verified.
  10. `test_run_end_to_end_with_fake_adapters_writes_transcript` (CLI-03 + CLI-08) -- full CLI -> orchestrator -> transcript pipeline with FakeAdapters injected via `monkeypatch.setattr(orch_module, 'get_adapter', ...)`. Transcript file is written at `--output` path; contains both agent names; the path appears in stdout.
  11. `test_stdout_only_contains_transcript_path_on_success` (CLI-11) -- on success, `result.stdout.strip() == str(output)` (only the transcript path on stdout); `str(output) not in result.stderr` (the path is a stdout-only signal). Uses click 8.3+'s default split semantics (no `mix_stderr=False` parameter -- it was removed in click 8.3).
- All 11 tests use `click.testing.CliRunner.invoke(main, [...])` -- in-process invocation, NO real subprocess, NO real CLI installed required.
- The doctor probe test mocks `shutil.which` to return `/fake/bin/<cli>` for all 3 CLIs and mocks `subprocess.run` to return a synthesized success result -- the test passes regardless of host PATH state and additionally asserts the safe-contract kwargs are present on every call.
- The end-to-end test produces a real transcript on disk (in `tmp_path`) by feeding FakeAdapters through the orchestrator's module-level `get_adapter` reference -- proving the full CLI -> orchestrator -> transcript pipeline works end-to-end without any real subprocess.
- Full pytest suite: **83/83 PASS in 1.17s** (72 prior + 11 new; zero regression).
- TST-05 lint: **3/3 PASS** (the new test file uses monkeypatch.setattr only -- zero direct subprocess.run/Popen calls in the file; the AST walker only scans `src/ultra_claude/`, so test files are out of scope by design, but the file is also clean).
- mypy --strict on `src/ultra_claude`: **clean across 13 source files** (zero source changes in this plan).
- ruff: **clean on tests/test_cli.py** (one I001 import-organization auto-fix applied during execution; final state passes).
- File properties verified via `Path.read_bytes`: 15515 bytes, 0 CRLF, 457 LF, 0 non-ASCII, UTF-8 decodes cleanly. Staged git blob: identical (15515 bytes / 0 CRLF / 457 LF) -- the `core.autocrlf=true` warning at `git add` time is informational; the actual blob bytes are LF-only, matching the defensive pattern established in plans 06-01, 08-01, and 08-02.
- Smoke check #5 from plan verification re-confirmed: `ultra-claude run --preset debate --inline "ship it" --dry-run` (via CliRunner) -- exit 0, 9 turns rendered with Architect/Critic/Implementer on claude/gemini/codex. 08-01 + 08-02 wiring is intact.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tests/test_cli.py with 11 test functions covering CLI-01..CLI-11 + PRE-01** -- `4ada905` (test)

**Plan metadata:** _(this commit, after SUMMARY/STATE/ROADMAP land)_

## Files Created/Modified

- `tests/test_cli.py` -- NEW (457 lines, 15515 bytes, LF-only, ASCII-only, UTF-8). 11 test functions + 1 FakeAdapter class + 1 helper (`_make_yaml`) + 1 module-level `_MINIMAL_YAML` constant. `from __future__ import annotations` at the top; imports organized by ruff into 3 groups (stdlib / third-party / local). Imports `cli_module` (for `cli_module.shutil` and `cli_module.subprocess` monkeypatch targets) and `orch_module` (for the `get_adapter` injection seam) as module objects, plus `from ultra_claude.cli import main` for the click entry point.

## Decisions Made

- **FakeAdapter mirrored, NOT shared via conftest.py** -- the 17-line class is small enough that the import coupling cost (every test file that touched FakeAdapter would need to import from a shared module) outweighs the DRY benefit. Mirroring keeps each test file independently runnable in isolation. Plan instruction (note 1); applied verbatim.
- **Doctor probe test asserts safe-contract kwargs in `fake_run`** -- defense-in-depth alongside TST-05 lint. The lint catches missing kwargs at AST-walk time on `src/ultra_claude/`; the runtime assertion in `fake_run` catches them when cli.py's doctor probe actually executes. Both layers fire if a future refactor drops a kwarg. Plan note 2; applied verbatim.
- **`monkeypatch.setattr(orch_module, "get_adapter", ...)` -- patching ON THE ORCHESTRATOR MODULE, not on `registry.get_adapter`** -- the orchestrator imports the function once at module load (line 57 of orchestrator.py: `from .registry import get_adapter`) and uses the module-local binding inside `run()` (line 211: `factory = adapter_factory if adapter_factory is not None else get_adapter`). Patching `registry.get_adapter` would have NO effect because the orchestrator's reference was already resolved. The test's seam is `ultra_claude.orchestrator.get_adapter`, period. Verified at execution time via a smoke test before writing the production tests.
- **No `CliRunner(mix_stderr=False)` parameter** -- click 8.3.3 (the version pinned in `pyproject.toml >= 8.3.3`) removed `mix_stderr` from the constructor signature. Verified via `inspect.signature(CliRunner.__init__)`: parameters are `['self', 'charset', 'env', 'echo_stdin', 'catch_exceptions']`. In click 8.3+, `result.stdout` and `result.stderr` are split by default; the deprecated parameter would raise `TypeError`. Documented as Rule 3 below.
- **11 test functions, exactly -- one per CLI requirement** -- PRE-01 is verified by case 4 (`test_run_with_preset_debate_loads_bundled_yaml`). The plan's "Testing strategy" in 08-CONTEXT.md lists exactly 11 cases; producing 12 (one for PRE-01 alone) would have been redundant since the preset works iff case 4 passes. Plan note 10; applied verbatim.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `CliRunner(mix_stderr=False)` parameter removed in click 8.3 -- updated to default-split semantics**

- **Found during:** Task 1 (writing the stdout-discipline test, case 11)
- **Issue:** The plan's `<action>` block specified `runner = CliRunner(mix_stderr=False)` for the stdout-discipline test, then `result.stdout` and `result.stderr` to assert split semantics. The pinned click version (8.3.3, verified via `python -c "import click; print(click.__version__)"`) REMOVED the `mix_stderr` parameter from `CliRunner.__init__`; supplying it raises `TypeError: __init__() got an unexpected keyword argument 'mix_stderr'`. This would have caused case 11 to fail at construction, before any CLI assertion ran.
- **Fix:** Replaced `CliRunner(mix_stderr=False)` with the default `CliRunner()`. In click 8.3+, `result.stdout` and `result.stderr` are split by default (verified via a 5-line smoke test: `click.echo("on stdout"); click.echo("on stderr", err=True)` -- `result.stdout == "on stdout\n"`, `result.stderr == "on stderr\n"`). The semantic intent of the plan's test (asserting stdout-only contains the path) is preserved exactly; only the constructor argument is dropped. Updated the test's docstring to call out the click 8.3 default-split behavior so future readers don't add `mix_stderr=False` back.
- **Files modified:** `tests/test_cli.py` (case 11 only -- one constructor change + one docstring update)
- **Verification:** `pytest tests/test_cli.py::test_stdout_only_contains_transcript_path_on_success -x -v` PASS; `result.stdout.strip() == str(output)` AND `str(output) not in result.stderr` both hold.
- **Committed in:** `4ada905` (Task 1 commit)

**2. [Rule 3 - Blocking] ruff I001 import organization auto-fix**

- **Found during:** Task 1 (post-write `ruff check tests/test_cli.py` invocation)
- **Issue:** ruff's I001 (`Import block is un-sorted or un-formatted`) fired on the import block. The plan's `<action>` block specified an exact import order; ruff's organizer prefers a slightly different group ordering. The diagnostic is auto-fixable.
- **Fix:** Ran `ruff check --fix tests/test_cli.py`. ruff applied a one-blank-line reorganization across the existing 3 import groups (stdlib / third-party / local). Re-ran `ruff check` -- clean. Re-ran the full pytest suite -- 83/83 PASS. The semantic behavior is identical (the same modules are imported under the same names in the same scopes).
- **Files modified:** `tests/test_cli.py` (import block only)
- **Verification:** `ruff check tests/test_cli.py` -> "All checks passed!"; `pytest tests/test_cli.py -x -v` -> 11 PASS.
- **Committed in:** `4ada905` (Task 1 commit -- the auto-fix landed before the commit so the committed file is already clean)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - Blocking)
**Impact on plan:** Both auto-fixes essential for the file to land green. The first (mix_stderr=False removal) was a click 8.3 API change post-dating the plan's drafting; the second (ruff I001) is cosmetic. Neither alters the test's semantic contract -- all 11 test functions assert exactly what the plan specified, only the constructor argument and import block layout differ.

## Issues Encountered

None.

The plan's `<action>` block specified the EXACT test file content; I produced it verbatim except for the two auto-fixed deviations documented above. No discoveries during execution required logic changes.

The pre-existing 4 untracked files (`.planning/phases/01-project-skeleton-pypi-name-reservation/01-VERIFICATION.md`, `.planning/phases/08-cli-surface-debate-preset/08-02-PLAN.md`, `.planning/phases/08-cli-surface-debate-preset/08-03-PLAN.md`, `zen_mcp_architecture.svg`, plus `M .planning/config.json`) are NOT from this plan -- they pre-date the executor's start time (visible in `git status --short` at the very first inspection). Per the SCOPE BOUNDARY rule, only files DIRECTLY caused by the current task's changes are in scope; these are out of scope. Logged for awareness only.

## User Setup Required

None for plan 08-03 execution. The new test file requires no external services, no env vars, no CLI installations -- by design (the entire premise of the test file is "zero real subprocess, zero real CLIs required"). `pytest tests/test_cli.py` runs green on a clean machine with only the dev dependencies installed.

## Next Phase Readiness

Phase 8 is now FULLY CLOSED:
- 3/3 plans complete (08-01, 08-02, 08-03)
- 12/12 requirements both IMPLEMENTATION + TEST verified (CLI-01..CLI-11 + PRE-01)
- 83/83 full test suite PASS
- TST-05 lint 3/3 PASS
- mypy --strict on src clean (13 source files)
- ruff clean on all source + test files

Phase 9 (Tests, Docs, Examples & v0.1.0 Release) is now FULLY UNBLOCKED. Concrete leverage Phase 9 inherits from this plan:
- The 11-test CliRunner pattern is the template for any future CLI surface additions in Phase 9 (e.g., a `--verbose` flag, a `history` subcommand). Each new flag gets one CliRunner test.
- The FakeAdapter + `monkeypatch.setattr(orch_module, 'get_adapter', ...)` pattern is the template for any new end-to-end test that exercises the CLI -> orchestrator -> transcript pipeline without paying tokens or requiring CLIs installed. Phase 9's wheel-install smoke test can use the same pattern after `pip install ultra_claude-0.1.0-py3-none-any.whl`.
- The doctor probe test's safe-contract kwargs assertion is reusable for any future subprocess invocation site that Phase 9 adds (e.g., a `version-check` subcommand). Drop-in copy of the `fake_run` body.
- The `--preset debate --dry-run` smoke check is locked as the README quickstart line: "After install, run `ultra-claude run --preset debate --inline "ship it" --dry-run` -- you should see a 9-turn plan with Architect/Critic/Implementer." Verified working in this plan; the README in Phase 9 can use it verbatim.

## Self-Check: PASSED

**Created files exist:**
- [FOUND] `tests/test_cli.py` (457 lines, 15515 bytes, LF-only, ASCII-only -- verified via `Path.read_bytes` byte counts)

**Commits exist on master:**
- [FOUND] `4ada905` (test(08-03): add CLI test suite via click CliRunner (CLI-01..CLI-11 + PRE-01))

**Plan-level success criteria:**
- [PASS] `tests/test_cli.py` contains exactly 11 test functions, one per CLI requirement (verified via `ast.walk` enumerating `FunctionDef` nodes starting with `test_`).
- [PASS] `pytest tests/test_cli.py -x -v` reports 11/11 PASS in 0.41s (well under 30s budget).
- [PASS] `pytest tests/` reports 83/83 PASS in 1.17s (72 prior + 11 new; zero regression).
- [PASS] `pytest tests/test_subprocess_lint.py -x` reports 3/3 PASS (TST-05 stays clean).
- [PASS] `ruff check tests/test_cli.py` reports "All checks passed!" (post auto-fix).
- [PASS] `mypy --strict src/ultra_claude` reports "Success: no issues found in 13 source files" (zero source changes in this plan).
- [PASS] No real subprocess launched during test execution -- doctor test mocks `shutil.which` + `subprocess.run`; end-to-end test injects FakeAdapters via `monkeypatch.setattr(orch_module, 'get_adapter', ...)`.
- [PASS] File is LF-only + ASCII-only + UTF-8 on disk (verified via `Path.read_bytes`: 15515 bytes / 0 CRLF / 457 LF / 0 non-ASCII / UTF-8 decodes cleanly).
- [PASS] Staged git blob is also LF-only (15515 bytes / 0 CRLF / 457 LF via `git cat-file -p HEAD:tests/test_cli.py`).
- [PASS] All 12 Phase 8 requirements (CLI-01..CLI-11 + PRE-01) now both IMPLEMENTATION verified (08-02) AND TEST verified (this plan).
- [PASS] Smoke check #5 (`ultra-claude run --preset debate --inline "ship it" --dry-run`) -- exit 0, 9 turns rendered with Architect/Critic/Implementer on claude/gemini/codex.

---
*Phase: 08-cli-surface-debate-preset*
*Completed: 2026-05-02*
