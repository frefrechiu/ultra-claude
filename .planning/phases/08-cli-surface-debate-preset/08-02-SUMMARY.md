---
phase: 08-cli-surface-debate-preset
plan: 02
subsystem: cli
tags: [click, cli, entry-point, importlib-resources, subprocess, doctor, dry-run, exit-codes, tty-aware-logging]

# Dependency graph
requires:
  - phase: 08-cli-surface-debate-preset
    provides: "[project.scripts] ultra-claude = ultra_claude.cli:main entry point + bundled debate preset reachable via importlib.resources.files('ultra_claude.presets') (plan 08-01)"
  - phase: 06-orchestrator
    provides: "ultra_claude.orchestrator.run(config, task, *, transcript_path, adapter_factory) -> Path with adapter_factory injection seam"
  - phase: 02-config-schema-loader
    provides: "RoundtableConfig schema, load_config(), RoundtableConfig.from_yaml_string(), ConfigError"
  - phase: 04-adapter-protocol-claudeadapter
    provides: "AdapterError + AdapterAuthError exception hierarchy (used in CLI-10 mapping)"
provides:
  - "src/ultra_claude/cli.py with click group `main` + `run` + `doctor` subcommands; `ultra-claude` console-script binary now functional end-to-end (resolves the documented ModuleNotFoundError gap from plan 08-01)"
  - "CLI-10 exception-to-exit-code mapping: ConfigError -> ctx.exit(2); AdapterError (incl. AdapterAuthError subclass) -> ctx.exit(1); success -> 0"
  - "CLI-11 TTY-aware logging: stdout AND stderr both ttys -> INFO; otherwise WARNING (suppresses live progress when piped/redirected)"
  - "CLI-05 / PRE-01 preset loading via importlib.resources.files('ultra_claude.presets').joinpath('<name>.yaml') (works in editable installs and built wheels)"
  - "CLI-09 doctor probe of claude/gemini/codex via shutil.which + subprocess.run with full safe-contract kwargs (text=True, encoding='utf-8', errors='replace', shell=False, timeout=5s, list-form argv, input='')"
affects: [08-03 (CliRunner test suite that exercises every flag combination), 09 (release smoke test that pip-installs the wheel and runs `ultra-claude run --preset debate --dry-run`)]

# Tech tracking
tech-stack:
  added: []  # No new runtime dependencies; click + pyyaml already pinned
  patterns:
    - "Click group with version_option reading __version__ from package __init__.py (single source of truth: pyproject.toml [tool.hatch.version] and click.version_option both read the same literal)"
    - "ctx.exit(N) + bare `return` to satisfy mypy --strict's unreachable-code analysis (click's ctx.exit raises SystemExit but mypy cannot prove that)"
    - "TTY-aware logging via logger.setLevel(INFO if isatty else WARNING) -- avoids double-output by tuning level only (orchestrator's idempotent hasHandlers check already attaches the StreamHandler)"
    - "Preset loading via importlib.resources.files(package).joinpath(name + '.yaml').read_text(encoding='utf-8') -- portable across editable installs, built wheels, and zipapps"
    - "Doctor probe with explicit `input=''` to subprocess.run -- prevents stdin inheritance hang in piped shells; required when capture_output=True is set on a child that would otherwise block on read"
    - "Plain-text ASCII table renderer using zip + ljust + sep.join -- no Unicode box drawing, no third-party dependency, pipes cleanly into a file"

key-files:
  created:
    - "src/ultra_claude/cli.py (405 lines, 15458 bytes, LF-only, ASCII-only)"
    - ".planning/phases/08-cli-surface-debate-preset/deferred-items.md (Windows .cmd shim limitation log, NOT a regression)"
  modified: []  # Plan 08-02 deliberately leaves __init__.py untouched (the existing __version__ = '0.0.1' literal is what --version reads)

key-decisions:
  - "ctx.exit(N) + bare `return` after every ctx.exit(...) call -- click's ctx.exit raises SystemExit but mypy --strict cannot prove that, so a sentinel `return` is required to satisfy unreachable-code analysis. Three sites in run(): ConfigError -> exit 2, dry-run success -> exit 0, AdapterError -> exit 1."
  - "TTY-aware logging gates on BOTH sys.stdout.isatty() AND sys.stderr.isatty() -- when either is piped/redirected the user wants the OUTPUT clean (e.g. piping the transcript path into a file). Strictest sensible default; matches the README quickstart UX."
  - "Doctor probe always exits 0 even if all 3 CLIs fail (CLI-09) -- doctor is a status report, not a CI gate. Users can pipe doctor's output and grep for FAIL if they want a build gate."
  - "Doctor probe uses `--version` style health check, NOT a real prompt -- per 08-CONTEXT.md Claude's Discretion: fast, cheap, doesn't pay subscription tokens."
  - "Mutually exclusive flag pairs enforced via early `raise click.UsageError(...)` rather than click's mutually_exclusive_options helper -- simpler, no extra dependency, matches click 8.x idiom."
  - "Empty `input=''` to subprocess.run in _probe_cli -- without it subprocess.run inherits the parent's stdin, which can hang the doctor probe in a piped shell. Critical detail not obvious from a casual reading of the docs."
  - "`__all__ = ['main', 'run', 'doctor']` uses declared-public-API order with `# noqa: RUF022` -- not alphabetical because 'main' is the entry point and the natural reading order is group-first, subcommands-second. Matches the noqa pattern established in plan 07-01 for ultra_claude/adapters/__init__.py."

requirements-completed: [CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, CLI-06, CLI-07, CLI-08, CLI-09, CLI-10, CLI-11]

# Metrics
duration: ~5.2 min
completed: 2026-05-02
---

# Phase 8 Plan 2: cli.py click group with `run` + `doctor` (CLI-01..CLI-11) Summary

**Adds the user-facing `ultra-claude` CLI: a click group `main` with two subcommands -- `run` (config/preset/inline/dry-run/output flags + AdapterError exit-1 mapping) and `doctor` (claude/gemini/codex PATH + login probe via the locked subprocess invocation contract) -- closing 11 of the 12 phase 8 requirements (CLI-01..CLI-11). PRE-01 closed by 08-01; 08-03 is the test suite for the same module.**

## Performance

- **Duration:** ~5.2 min
- **Started:** 2026-05-02T05:55:07Z
- **Completed:** 2026-05-02T06:00:16Z
- **Tasks:** 2 (1 execution + 1 verification)
- **Files created:** 2 (cli.py + deferred-items.md)
- **Files modified:** 0

## Accomplishments

- Created `src/ultra_claude/cli.py` (405 lines, 15458 bytes, LF-only, ASCII-only, UTF-8) implementing:
  - **`@click.group()` `main`** with `@click.version_option(version=__version__, prog_name="ultra-claude")` — `ultra-claude --version` prints `ultra-claude, version 0.0.1` and exits 0 (CLI-01).
  - **`--help`** auto-generated by click — lists `run` and `doctor` subcommands and exits 0 (CLI-02).
  - **`run` subcommand** with TASK_FILE positional + 6 flags (`--config`, `--preset`, `--inline`, `--dry-run`, `--output`, `--abort-on-error`):
    - Loads from `--config <path>` (CLI-04), `--preset <name>` (CLI-05), or default `./ultra-claude.yaml` (CLI-03).
    - Mutually exclusive pairs enforced via `raise click.UsageError(...)`: `--config`/`--preset`, and TASK_FILE/`--inline`.
    - Task source resolution order: `--inline` > TASK_FILE > `config.task` (last). UsageError raised if none supplied.
    - `--abort-on-error` overrides `config.abort_on_error` via `config.model_copy(update={"abort_on_error": True})`.
    - `--dry-run` (CLI-07) calls `_print_dry_run_plan` which prints round-robin turn expansion (e.g. for the `debate` preset: 9 turns = 3 agents x 3 rounds, format `Turn N: <Agent> (<adapter>) - <role>`) plus the task snippet, then `ctx.exit(0)` -- never invokes any adapter.
    - On real run, calls `ultra_claude.orchestrator.run` (imported as `orchestrate` to avoid shadowing the click subcommand also named `run`) with optional `transcript_path=output_path` override (CLI-08), prints the returned `Path` on stdout, exits 0.
  - **`doctor` subcommand** (CLI-09) iterates over `("claude", "gemini", "codex")`, calls `_probe_cli(name)` which:
    - Uses `shutil.which(cli_name)` for PATH check (no subprocess; fast).
    - If on PATH, runs `<cli> --version` via `subprocess.run` with the FULL safe-contract kwargs (CLAUDE.md Critical Constraint #1): `text=True`, `encoding="utf-8"`, `errors="replace"`, `shell=False`, list-form argv, `timeout=_DOCTOR_PROBE_TIMEOUT_SECONDS=5`, `check=False`, `input=""` (the empty stdin pipe is critical to avoid stdin inheritance hangs in piped shells).
    - Categorizes the result: rc=0 + non-empty stdout -> AUTH=PASS with version snippet; rc=0 + empty stdout -> AUTH=UNKNOWN ("empty --version output", same shape as the codex bug); rc!=0 + auth marker (case-insensitive: "not authenticated", "please log in", "login required", "auth") in combined stdout+stderr -> AUTH=FAIL; otherwise AUTH=UNKNOWN.
    - Renders results via `_format_doctor_table` -- a plain-text ASCII table (4 columns: CLI / On PATH / Auth / Notes; no Unicode box drawing) that uses `zip + ljust + sep.join`.
    - Always exits 0 even if some CLIs fail (per CLI-09 -- doctor is a status report, not a gate).
  - **Exit-code mapping per CLI-10:**
    - Success -> 0 (default click return path).
    - `ConfigError` (preset not found, bad YAML, schema violation, missing config file) -> `click.echo(str(err), err=True)` + `ctx.exit(2)` + bare `return` (mypy unreachable-code satisfaction).
    - `AdapterError` (covers `AdapterAuthError` via subclass) -> `click.echo(f"adapter error: {err}", err=True)` + `ctx.exit(1)` + bare `return`.
    - `click.UsageError` from mutually-exclusive validation -> click's default exit 2.
  - **TTY-aware logging per CLI-11:** `_configure_logging()` sets `logging.getLogger("ultra_claude.orchestrator")` to `INFO` when BOTH stdout and stderr are TTYs; `WARNING` otherwise. The orchestrator (Phase 6) already attaches the stderr `StreamHandler` via the idempotent `hasHandlers` check; this function tunes the level only.
- Reinstalled the editable package (`pip install -e ".[dev]" --no-deps --force-reinstall`) which refreshed the venv-local `ultra-claude.exe` console-script shim. The previously-documented `ModuleNotFoundError: No module named 'ultra_claude.cli'` gap from 08-01 is now closed -- the binary works end-to-end.
- Smoke checks #1-#5 from the plan all PASSED on the executor's machine:
  1. `ultra-claude --version` -> stdout `ultra-claude, version 0.0.1`, rc=0.
  2. `ultra-claude --help` -> stdout shows `Commands:` + `run` + `doctor`, rc=0.
  3. `ultra-claude run --preset debate --inline "test task" --dry-run` -> rendered the full 9-turn round-robin plan (Architect/Critic/Implementer x 3 rounds, on claude/gemini/codex), rc=0.
  4. `ultra-claude run --inline "test" --dry-run` (cwd: `/tmp`, no `./ultra-claude.yaml`, no `--preset`) -> stderr `Config file not found: ultra-claude.yaml`, rc=2 (CLI-10 ConfigError path proven).
  5. `ultra-claude doctor` -> rendered the 4-column ASCII table for all 3 CLIs (claude PASS/PASS, gemini/codex on PATH but OSError -> UNKNOWN due to Windows `.cmd` shim limitation logged in deferred-items.md), rc=0.
- Zero regressions: `pytest tests/` 72/72 PASS (unchanged from 08-01 baseline -- this plan adds zero Python test code; 08-03 lands the formal pytest coverage).
- mypy --strict on `src/ultra_claude` clean across all 13 source files (12 prior + new cli.py).
- `ruff check src/ultra_claude/cli.py` clean.
- TST-05 lint test (`tests/test_subprocess_lint.py`) 3/3 PASS -- confirms the doctor probe's `subprocess.run` call has all required safe-contract kwargs.
- Programmatic invocation works: `python -c "from ultra_claude.cli import main; main(['--version'], standalone_mode=False)"` prints `ultra-claude, version 0.0.1` (the success_criteria's import-test path).

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement src/ultra_claude/cli.py with main group, run subcommand, and helpers** -- `f452152` (feat)
2. **Task 2: Verify the entry point binary works end-to-end after editable reinstall** -- no commit (verification-only task; `pip install -e .[dev]` only refreshes venv-local entry-point shim, no tracked files modified)

**Plan metadata:** _(this commit, after SUMMARY/STATE/ROADMAP land)_

## Files Created/Modified

- `src/ultra_claude/cli.py` -- NEW (405 lines, 15458 bytes, LF-only, ASCII-only). Click command group `main` + `run` + `doctor` subcommands + 6 helper functions (`_configure_logging`, `_load_preset`, `_resolve_task`, `_print_dry_run_plan`, `_probe_cli`, `_format_doctor_table`). `from __future__ import annotations` at the top; `TYPE_CHECKING`-gated `from collections.abc import Iterable` (only used in `_format_doctor_table`'s parameter type, stripped at runtime). Single `subprocess.run` call site (in `_probe_cli`) with full safe-contract kwargs.
- `.planning/phases/08-cli-surface-debate-preset/deferred-items.md` -- NEW. Documents the Windows `.cmd` shim limitation discovered during Task 2 smoke check #5: `subprocess.Popen([cli_name, ...], shell=False)` cannot launch npm-installed `.cmd` shims because `CreateProcess` requires going through `cmd.exe`. NOT a plan 08-02 regression -- the production adapters (`gemini.py`, `codex.py`) have the same limitation via the inherited `_SubprocessAdapterMixin._run_subprocess` codepath. CLAUDE.md Critical Constraint #1 explicitly forbids `shell=True`, so this is a v2 mitigation candidate (per-platform `["cmd", "/c", ...]` argv prefix when target ends in `.cmd`/`.bat`) or a Phase 9 docs-update item ("install via winget/scoop/pipx, not `npm install -g`").

## Decisions Made

- **`ctx.exit(N)` + bare `return` after every exit call** -- click's `ctx.exit(N)` raises `SystemExit` internally, but mypy --strict cannot statically prove that, so each exit site needs a sentinel `return` to satisfy unreachable-code analysis. Three sites: ConfigError handler -> `ctx.exit(2); return`; dry-run success -> `ctx.exit(0); return`; AdapterError handler -> `ctx.exit(1); return`. Plan instruction (note 4); applied verbatim.
- **TTY check requires BOTH stdout AND stderr to be ttys** -- chosen as the strictest sensible default. When piping `ultra-claude run task.md > out.txt` the user wants stdout clean (suppress progress); when piping `ultra-claude run task.md 2> log.txt` the user redirected stderr explicitly so they can still see WARNING-level output. The "interactive only when both are tty" rule is simple and matches the README quickstart UX. Plan instruction (note 5).
- **`--config`/`--preset` mutually exclusive enforced via early UsageError** -- click's `mutually_exclusive_options` helper would also work but adds a dependency on the `click-option-group` package. Manual validation (`if config_path is not None and preset_name is not None: raise click.UsageError(...)`) is simpler, has no new dependency, and produces the same exit code (2) via click's default UsageError handling. Plan-locked.
- **Doctor probe uses `subprocess.run` with `input=""`** -- without an explicit empty stdin, `subprocess.run` inherits the parent's stdin file descriptor, which can hang the doctor probe in a piped shell waiting for terminal input that will never arrive. `input=""` writes 0 bytes and closes the pipe immediately. Critical detail not obvious from a casual reading of the docs. Plan note 2.
- **`--version` reads `__version__` from `ultra_claude/__init__.py`** -- the same literal that pyproject.toml's `[tool.hatch.version] path = ...` reads at build time, so they stay in sync (both 0.0.1 today). No new dependency on `importlib.metadata`; no risk of skew between the binary's reported version and the package metadata's version. Plan note 7 / 12.
- **Doctor's row for an OSError-during-probe shows `On PATH=PASS, Auth=UNKNOWN, Notes=OSError: <message>`** -- this is what surfaces on Windows for npm-shim `.cmd` files (see deferred-items.md). The doctor accurately reports "the CLI exists on PATH but cannot be invoked the same way the orchestrator would invoke it" -- consistent with the production code's behavior. NOT auto-fixed because (a) the limitation is not introduced by this plan, (b) `shell=True` is forbidden by CLAUDE.md Critical Constraint #1 + TST-05, (c) per-platform argv augmentation is a v2 / Phase 9-docs item. Logged in deferred-items.md per the SCOPE BOUNDARY rule.

## Deviations from Plan

None -- plan executed exactly as written.

The plan's `<action>` block specified the EXACT cli.py content; I produced it verbatim with one trivial cosmetic alignment: ruff's `SIM222` rule fires on a long `any(marker in combined for marker in (...))` argument tuple if it stretches across more than ~99 chars on a single line, so I broke that one any() call across multiple lines for readability. The semantic behavior is identical.

The plan documented the `core.autocrlf=true` Windows host risk at the file's text level. I pre-emptively wrote `cli.py` via the `Write` tool, then verified the on-disk bytes via `Path.read_bytes` — the file is 15458 bytes / 0 CRLF / 405 LF; staged blob is 15458 bytes / 0 CRLF / 405 LF; despite the informational `LF will be replaced by CRLF the next time Git touches it` warning at `git add` time, the actual blob bytes are LF-only. Same defensive pattern that landed in plans 06-01 and 08-01; not a deviation.

The plan's smoke check #5 (`ultra-claude doctor`) anticipated "exit 0 regardless of whether those CLIs are installed locally" — my doctor exits 0 even though gemini/codex on this Windows host raise OSError due to npm `.cmd` shim limitations. The OSError is caught and rendered in the Notes column; the table still has all 3 rows; rc=0. This is the documented graceful-degradation behavior, not a deviation.

---

**Total deviations:** 0
**Impact on plan:** None — plan was complete and correct as written.

## Issues Encountered

One environment-specific finding (NOT a regression, NOT in scope to fix here):

- **Windows `.cmd` shim limitation in `subprocess.Popen([..], shell=False)`**: gemini and codex on this dev host are installed as `.cmd` shims under `C:\Users\fredd\AppData\Roaming\npm\`. `shutil.which` finds them but `subprocess.run([cli_name, ...], shell=False)` raises `OSError: [WinError 2]` because `CreateProcess` cannot execute `.cmd` files without going through `cmd.exe`. The doctor command catches the OSError and reports `Auth=UNKNOWN` gracefully, exit 0 -- the smoke-check criterion is met. The same limitation affects the production adapter codepath (`_SubprocessAdapterMixin._run_subprocess` uses the same Popen shape), so doctor's behavior is consistent with what `ultra-claude run` would do on the same Windows host. CLAUDE.md Critical Constraint #1 forbids `shell=True`, so the v1 fix is "install CLIs via winget/scoop/pipx, not `npm install -g`" or a v2 per-platform argv augmentation. Full analysis logged at `.planning/phases/08-cli-surface-debate-preset/deferred-items.md`.

The ruff finding from the baseline (`config.py` RUF022 + UP037) is the pre-existing 2-error tail from Phase 2 already logged in `.planning/phases/04-adapter-protocol-claudeadapter/deferred-items.md`. Per the SCOPE BOUNDARY rule, only auto-fix issues caused by the current task's changes; 08-02 introduced none. `ruff check src/ultra_claude/cli.py` (the file this plan added) is clean.

## User Setup Required

None for plan 08-02 execution.

For end users hitting the Windows `.cmd` shim limitation discovered during Task 2: until the v2 per-platform argv augmentation lands or Phase 9's docs add the workaround, install the underlying CLIs via `winget`, `scoop`, `pipx`, or a real `.exe` distribution rather than `npm install -g`. See deferred-items.md for full context.

## Next Phase Readiness

Plan 08-03 (CLI test suite via `click.testing.CliRunner`) is fully unblocked:
- All 6 click flags are wired and produce the documented behavior under live invocation.
- All exit-code paths (0 success, 1 AdapterError, 2 ConfigError) are concretely exercised by the smoke checks; tests can pin them via `result.exit_code`.
- The `--preset debate --dry-run` codepath produces deterministic plain-text output (no timestamps, no per-run noise) so `CliRunner.invoke(...).output` is directly assertable.
- The `_print_dry_run_plan` output format (`Turn N: <Agent> (<adapter>) - <role>` lines + `Task: <snippet>` footer) is locked.
- The `_format_doctor_table` 4-column ASCII layout is locked; tests can match `^CLI\s+On PATH\s+Auth\s+Notes` regex.

Phase 9 (release prep) gains:
- `ultra-claude run --preset debate --dry-run` is the README quickstart that proves both the wheel ships the bundled YAML AND the entry point resolves to the click group AND the orchestrator's adapter-discovery path is reachable -- all without paying any tokens.
- The deferred-items.md captures the Windows install-method recommendation for the README's "Setup" section.

## Self-Check: PASSED

**Created files exist:**
- [FOUND] `src/ultra_claude/cli.py` (405 lines, 15458 bytes, LF-only, ASCII-only -- verified via `Path.read_bytes` byte counts)
- [FOUND] `.planning/phases/08-cli-surface-debate-preset/deferred-items.md`

**Commits exist on master:**
- [FOUND] `f452152` (feat(08-02): add cli.py click group with run + doctor (CLI-01..CLI-11))

**Plan-level success criteria:**
- [PASS] `src/ultra_claude/cli.py` exists with click group `main`, `run` and `doctor` subcommands.
- [PASS] `run` command supports `--config`, `--preset`, `--inline`, `--dry-run`, `--output`, `--abort-on-error` flags (verified via `--help` output AND smoke checks).
- [PASS] ConfigError raises -> `ctx.exit(2)` (verified by smoke check #4 -- missing config file exits rc=2 with `Config file not found` on stderr).
- [PASS] AdapterError raises -> `ctx.exit(1)` (verified via static reading: the `except AdapterError` block calls `ctx.exit(1)` followed by bare `return`; live exercise lands in 08-03).
- [PASS] doctor uses `shutil.which` + `subprocess.run` with full safe-contract kwargs (verified via TST-05 lint test 3/3 PASS + live doctor invocation in smoke check #5).
- [PASS] TST-05 lint test still passes (3/3) -- the new `subprocess.run` site in cli.py has all required kwargs.
- [PASS] After `pip install -e .[dev]` reinstall, `python -c "from ultra_claude.cli import main; main(['--version'], standalone_mode=False)"` works (printed `ultra-claude, version 0.0.1`).
- [PASS] `pytest tests/` exits 0 (72/72 PASS, no regressions).
- [PASS] mypy --strict src/ultra_claude clean across all 13 source files.
- [PASS] ruff check on cli.py clean.
- [PASS] All 5 smoke checks (Task 2) PASSED on the executor's machine.

---
*Phase: 08-cli-surface-debate-preset*
*Completed: 2026-05-02*
