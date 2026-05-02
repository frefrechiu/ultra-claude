---
phase: 02-config-schema-yaml-loader
plan: 02
subsystem: config
tags: [config, pydantic-v2, yaml-loader, validation, tests, pytest]

# Dependency graph
requires:
  - phase: 02-config-schema-yaml-loader
    plan: 01
    provides: ConfigError exception class importable from ultra_claude.exceptions
provides:
  - "AgentConfig Pydantic model (name, role, adapter Literal['claude','gemini','codex'], system_prompt)"
  - "RoundtableConfig Pydantic model (agents min_length=2, task, max_turns=12 ge=2, stop_keywords=[AGREED,DONE], transcript_path, turn_order='round_robin' Literal, abort_on_error=False)"
  - "load_config(path: Path | str) -> RoundtableConfig — YAML+schema validated loader raising ConfigError"
  - "RoundtableConfig.from_yaml_string(s: str) classmethod — in-memory loader for tests + future --inline CLI flag"
  - "format_validation_error(err, source_path) -> str — converts pydantic.ValidationError into one header + indented field-path-named lines"
  - "tests/ package with 8 pytest test functions covering CFG-01..CFG-05"
affects:
  - "Phase 3 (Transcript) and Phase 4 (Adapters) can now import RoundtableConfig and trust shape"
  - "Phase 8 (CLI) maps ConfigError -> exit code 2 (CLI-10) without importing pydantic/yaml"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic v2 BaseModel + ConfigDict(extra='forbid') on both models — typos like 'max_turn' surface as 'extra inputs are not permitted' instead of being silently dropped."
    - "Field(min_length=1) on every required string — empty strings would otherwise pass `str` validation."
    - "Literal['round_robin'] for turn_order locks the only legal v1 value at the type level (CFG-04)."
    - "Wrap pydantic.ValidationError in ConfigError at every entry point — Phase 8 CLI never sees a ValidationError, can map ConfigError -> exit 2 without importing pydantic."
    - "Wrap yaml.YAMLError in ConfigError at every entry point — same isolation for the CLI."
    - "Top-level type guard before model_validate (`if not isinstance(raw, dict)`) — top-level scalars/lists get a friendly message instead of a misleading 'agents: required field' downstream error."
    - "from __future__ import annotations + PEP 604 unions (str | None) — works on Python 3.10 floor."
    - "Inline YAML strings in tests (no fixtures dir) — keeps the failing-input visible right next to the assertion."
    - "Anti-leakage assertions: each error-path test asserts not isinstance(err, yaml.YAMLError|ValidationError) and 'Traceback'/'pydantic_core' not in str(err)."

key-files:
  created:
    - "src/ultra_claude/config.py (9714 bytes, 267 lines)"
    - "tests/__init__.py (0 bytes, empty package marker)"
    - "tests/test_config.py (8763 bytes, 276 lines, 8 test functions)"
  modified: []

key-decisions:
  - "Kept RoundtableConfig.from_yaml_string classmethod (CONTEXT 'recommend: yes') — exercises in-memory path for tests + future --inline CLI flag, avoids tmp_path overhead for cases 1-5."
  - "Declared __all__ = [AgentConfig, RoundtableConfig, load_config, format_validation_error, ConfigError] (CONTEXT 'recommend: yes') — tightens `from ultra_claude.config import *`."
  - "No model_validator for cross-field rules (CONTEXT 'recommend: no') — kept validation per-field for v1; max_turns >= len(agents) and similar are deferred."
  - "Specialised error wording for literal_error and missing types in format_validation_error — produces the CONTEXT-mandated 'agents[0].adapter: invalid value clade (expected ...)' shape rather than Pydantic's raw 'Input should be ...' phrasing. Other error types fall through to Pydantic's msg verbatim."
  - "stop_keywords default uses lambda factory (default_factory=lambda: ['AGREED', 'DONE']) — Pydantic v2 requires callable defaults for mutable types."
  - "_format_loc renders Pydantic loc tuple ('agents', 0, 'adapter') as 'agents[0].adapter' (CFG-03 wire format)."
  - "_format_yaml_error renders MarkedYAMLError with 1-indexed line/column (Pydantic stores 0-indexed; humans read 1-indexed)."
  - "if raw is None and if not isinstance(raw, dict) guards before model_validate — yaml.safe_load('') returns None; top-level lists/scalars get friendly error instead of Pydantic 'input should be a dict'."

patterns-established:
  - "Input-boundary validation: every external input (config file, CLI args, transcript file) is parsed at the package edge into a Pydantic model; downstream code consumes the typed model and trusts its shape."
  - "Exception isolation: feature modules wrap third-party exceptions (ValidationError, YAMLError) in their own ConfigError/AdapterError so the CLI layer never imports those third parties."

requirements-completed: [CFG-01, CFG-02, CFG-03, CFG-04, CFG-05]

# Metrics
duration: 4min
completed: 2026-05-02
---

# Phase 2 Plan 02: Config Schema & YAML Loader Summary

**Pydantic v2 schema (`AgentConfig`, `RoundtableConfig`) + YAML loader (`load_config`, `format_validation_error`) + 8-test pytest suite landed; all five CFG requirements (CFG-01..CFG-05) closed; Phase 2 complete.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-02T02:35:56Z
- **Completed:** 2026-05-02T02:39:52Z
- **Tasks:** 2
- **Files created:** 3
- **Test functions:** 8 (covering 6 CONTEXT cases + wire format + file-not-found)

## Accomplishments

- New file `src/ultra_claude/config.py` (9714 bytes, 267 lines, LF-only, ASCII-only):
  - `class AgentConfig(BaseModel)` — name/role/adapter Literal['claude','gemini','codex']/system_prompt, all required, all `min_length=1`, `extra='forbid'` rejects unknown keys.
  - `class RoundtableConfig(BaseModel)` — agents (`min_length=2`), task (optional), max_turns (default 12, `ge=2`), stop_keywords (default `['AGREED','DONE']`, `min_length=1`), transcript_path (optional), turn_order (`Literal['round_robin']`, default `'round_robin'`), abort_on_error (default `False`).
  - `def load_config(path: Path | str) -> RoundtableConfig` — reads UTF-8, catches `yaml.YAMLError` + `pydantic.ValidationError`, raises `ConfigError` with field-path-named messages.
  - `def format_validation_error(err, source_path) -> str` — one header + indented per-error lines naming each field path; specialised wording for `literal_error` and `missing` types.
  - `RoundtableConfig.from_yaml_string(s: str)` classmethod — in-memory loader for tests + future `--inline` CLI flag.
  - `_format_loc` helper — converts Pydantic `('agents', 0, 'adapter')` -> `'agents[0].adapter'`.
  - `_format_yaml_error` helper — renders `MarkedYAMLError` with 1-indexed line/column.
  - `__all__ = ['AgentConfig', 'RoundtableConfig', 'load_config', 'format_validation_error', 'ConfigError']`.
- New file `tests/__init__.py` (0 bytes) — empty package marker for pytest discovery.
- New file `tests/test_config.py` (8763 bytes, 276 lines, 8 test functions, LF-only, ASCII-only).

## Test Results

`python -m pytest tests/test_config.py -v` output:

```
tests/test_config.py::test_valid_yaml_parses_into_typed_config PASSED                    [ 12%]
tests/test_config.py::test_missing_agent_field_names_offending_field_path PASSED         [ 25%]
tests/test_config.py::test_invalid_adapter_literal_is_rejected_with_field_path PASSED    [ 37%]
tests/test_config.py::test_non_round_robin_turn_order_is_rejected PASSED                 [ 50%]
tests/test_config.py::test_defaults_for_max_turns_and_stop_keywords PASSED               [ 62%]
tests/test_config.py::test_malformed_yaml_produces_human_readable_error PASSED           [ 75%]
tests/test_config.py::test_format_validation_error_produces_field_path_per_line PASSED   [ 87%]
tests/test_config.py::test_missing_config_file_raises_config_error PASSED                [100%]

============================== 8 passed in 0.11s ==============================
```

| # | Test name | CFG mapping | Status |
|---|-----------|-------------|--------|
| 1 | `test_valid_yaml_parses_into_typed_config` | CFG-01 (happy path) | PASSED |
| 2 | `test_missing_agent_field_names_offending_field_path` | CFG-02 (missing required field) | PASSED |
| 3 | `test_invalid_adapter_literal_is_rejected_with_field_path` | CFG-02 (bad Literal value) | PASSED |
| 4 | `test_non_round_robin_turn_order_is_rejected` | CFG-04 (turn_order Literal) | PASSED |
| 5 | `test_defaults_for_max_turns_and_stop_keywords` | CFG-04 (max_turns default) + CFG-05 (stop_keywords default) | PASSED |
| 6 | `test_malformed_yaml_produces_human_readable_error` | CFG-03 (YAML syntax error wrapping) | PASSED |
| 7 | `test_format_validation_error_produces_field_path_per_line` | CFG-03 (formatter wire format) | PASSED |
| 8 | `test_missing_config_file_raises_config_error` | extra coverage (file-not-found path) | PASSED |

All 6 CONTEXT-mandated cases plus 2 extras (wire format + file-not-found). All 5 CFG requirements (CFG-01..CFG-05) referenced in test file and exercised by at least one assertion.

## Task Commits

1. **Task 1: Create src/ultra_claude/config.py with AgentConfig, RoundtableConfig, load_config, format_validation_error** — `e97325a` (`feat(02-02): add config schema and YAML loader`)
2. **Task 2: Create tests/__init__.py and tests/test_config.py with 6+ test cases** — `5c272f0` (`test(02-02): add config validation test suite`)

## ConfigError Identity (No Shadowing)

Verified that `ConfigError` re-exported from `ultra_claude.config` is the SAME CLASS OBJECT as the one defined in `ultra_claude.exceptions`:

```python
from ultra_claude.config import ConfigError as CE_cfg
from ultra_claude.exceptions import ConfigError as CE_exc
assert CE_cfg is CE_exc   # PASS — exception-identity-OK
```

This guarantees that downstream code (Phase 8 CLI, future test suites) can `except ConfigError` from either import path and catch every config-validation failure.

## Error Isolation (No Pydantic / YAML Leakage)

Verified at three layers:

1. **`format_validation_error` always reformats** — never re-raises `ValidationError`, so callers of `load_config`/`from_yaml_string` see only `ConfigError` instances.
2. **Test 6 asserts** `not isinstance(excinfo.value, yaml.YAMLError)` and `not isinstance(excinfo.value, ValidationError)`.
3. **Plan-level verification command 7** (`error-isolation-OK`) re-asserts at the plan boundary: `ConfigError is not ValidationError` (and not a subclass).

CFG-03's "no raw Python tracebacks reach the user" contract holds. The Phase 8 CLI can map `ConfigError -> exit 2` without ever importing Pydantic or YAML.

## Decisions Made (Claude's Discretion from CONTEXT)

CONTEXT.md flagged four "Claude's Discretion" items. Decisions made:

| Item | CONTEXT recommendation | Decision |
|------|------------------------|----------|
| `from_yaml_string` classmethod | yes | **Kept.** Used by 6/8 tests + future `--inline` CLI flag. |
| `__all__` declaration | yes | **Kept.** Lists 5 public symbols. Verified by command 3 (`public-api-OK`). |
| `model_validator` for cross-field rules (e.g. `max_turns >= len(agents)`) | no | **Skipped.** Per-field validation only for v1. |
| Exact wording of error messages | flexible | **Specialised `literal_error` and `missing`** to match the CONTEXT example shape (`agents[0].adapter: invalid value 'clade' (expected ...)`). Other types fall through to Pydantic's `msg` verbatim, plus the input value when scalar. |

## Self-Check Verification

All 9 plan-level verification commands PASSED post-commit:

1. **Full test suite** — `pytest tests/ -x -q` exits 0 with `8 passed in 0.11s`.
2. **CFG references** — all five `CFG-0[1-5]` strings present in `tests/test_config.py` (`all-CFG-OK`).
3. **Public API symbols** — `__all__ == ['AgentConfig', 'RoundtableConfig', 'load_config', 'format_validation_error', 'ConfigError']` and all 5 importable (`public-api-OK`).
4. **ConfigError identity** — `from ultra_claude.config import ConfigError is from ultra_claude.exceptions import ConfigError` (`exception-identity-OK`).
5. **Defaults** — `max_turns=12`, `stop_keywords=['AGREED','DONE']`, `turn_order='round_robin'` for minimal config (`defaults-OK`).
6. **turn_order rejection** — `'speaker_chooses'` rejected with field path + value in message (`turn-order-OK`).
7. **Error isolation** — `ConfigError` is not a `ValidationError` subclass (`error-isolation-OK`).
8. **LF-only on disk** — zero `\r\n` byte sequences in all 3 files (`LF-OK`).
9. **Static parse** — `ast.parse()` accepts both Python files (`parse-OK`).

Additional checks:

- **ASCII-only content** — no chars with `ord(c) > 127` in any file.
- **Required substrings present in config.py** — `class AgentConfig(BaseModel)`, `class RoundtableConfig(BaseModel)`, `def load_config`, `def format_validation_error`, `Literal["claude", "gemini", "codex"]`.
- **Test count** — `tests/test_config.py` contains exactly 8 `def test_` definitions.
- **Git index LF** — `git show :path` returns LF-only bytes for both `src/ultra_claude/config.py` (9714 bytes) and `tests/test_config.py` (8763 bytes); `tests/__init__.py` is exactly 0 bytes.

## Deviations from Plan

**One Rule 3 deviation (auto-fix blocking issue):**

**[Rule 3 - Blocking issue] Editable install required for pytest collection**
- **Found during:** Task 2 verify step (`python -m pytest tests/test_config.py -x -q`).
- **Issue:** First pytest run failed with `ModuleNotFoundError: No module named 'ultra_claude'`. The plan's note acknowledged this possibility (`User likely needs pip install -e ".[dev]" to be in effect`). Phase 1 plan 01-03's smoke test ran in `.smoke-venv/` which has been since reverted, so the system Python had pydantic/pyyaml/pytest installed but no `ultra_claude` package.
- **Fix:** Ran `python -m pip install -e ".[dev]" --quiet` against the system Python. Editable install resolves to `src/ultra_claude/__init__.py` (`installed at C:\\Users\\fredd\\Desktop\\project\\Ultra-claude\\src\\ultra_claude\\__init__.py`) so test imports of `from ultra_claude.config import ...` work.
- **Files modified:** None. Editable install is a runtime-only operation that produces no working-tree changes (no `.smoke-venv/` created; no `egg-info` artifacts in source — they live in site-packages).
- **Commit:** None (no working-tree changes).

**Rationale for not asking permission:** Plan explicitly states `User likely needs pip install -e ".[dev]" to be in effect for pytest to find pydantic and pyyaml. ... assume the dev install is active per Phase 1's verification`. The plan's verify command (`python -m pytest tests/test_config.py -x -q`) cannot succeed without the editable install, so this is a Rule 3 unblocking action with explicit plan permission.

**Total deviations:** 1 (Rule 3, no working-tree changes).
**Impact on plan:** None — verification proceeded as written; all 9 plan-level verification commands passed.

**No Rule 1 (bug) or Rule 2 (missing critical functionality) deviations were needed.** The plan-supplied source code was accepted verbatim and worked on first parse + smoke test + pytest run.

## Issues Encountered

- **Out-of-scope discovery (logged, not fixed):** Same `core.autocrlf=true` warning that 02-01 hit on `git add` for `src/ultra_claude/config.py` and `tests/test_config.py` (`warning: in the working copy of '...', LF will be replaced by CRLF the next time Git touches it`). Verified the git index stored LF for both files via `git show :path | python -c 'count(b"\\r\\n")' == 0`. Working tree on disk is also LF-only. The cross-platform CRLF risk on future Windows checkouts is the same project-wide concern logged in `.planning/phases/02-config-schema-yaml-loader/deferred-items.md`. No additional action taken in this plan.
- **No stub patterns detected** — every default has a value, every required field has `min_length=1`, every error path raises `ConfigError`.
- **No new threat surface introduced** — pure parsing/validation, no I/O beyond `Path.read_text()`, no network, no subprocess.

## User Setup Required

None — no external service configuration required. All deps already pinned in `pyproject.toml`.

For future contributors: running `pip install -e ".[dev]"` from the repo root (in a venv of choice) is the prerequisite for `pytest tests/`. No new dev deps were added by this plan.

## Carry-Forward Notes

- **Phase 2 closes with this plan.** All five CFG requirements (CFG-01..CFG-05) are implemented and tested. Phase 3 (Transcript Module) and Phase 4 (Adapters) can begin independently.
- **Phase 3 / 4 import contract:** `from ultra_claude.config import RoundtableConfig, AgentConfig` and trust the shape. The orchestrator function in Phase 6 will accept a `RoundtableConfig` and treat each `AgentConfig.adapter` as a key into a `dict[Literal["claude","gemini","codex"], Adapter]` registry.
- **Phase 8 CLI exit-code mapping (CLI-10):** `from ultra_claude.exceptions import ConfigError` maps to exit code 2. The CLI layer does not need to import Pydantic or PyYAML — error formatting is fully encapsulated in `config.py`.
- **`from_yaml_string` is the integration point for future `--inline` CLI flag.** Phase 8 can pipe inline YAML directly to this classmethod without round-tripping through a temp file.

## Self-Check: PASSED

- All 3 expected files present:
  - `src/ultra_claude/config.py` — FOUND (9714 bytes, 267 lines)
  - `tests/__init__.py` — FOUND (0 bytes)
  - `tests/test_config.py` — FOUND (8763 bytes, 276 lines)
- Both task commits present in git log:
  - `e97325a` (`feat(02-02): add config schema and YAML loader`) — FOUND
  - `5c272f0` (`test(02-02): add config validation test suite`) — FOUND
- All 9 plan-level verification commands re-ran post-commit: 9/9 PASS.
- pytest run: 8/8 tests PASSED in 0.11s.
- LF-only verified on disk and in git index for all 3 files.
- ASCII-only verified (no chars > 127) in all 3 files.
- ConfigError identity verified (no shadowing).
- ValidationError + yaml.YAMLError isolation verified at 3 layers.
- No stub patterns detected.
- No new threat surface introduced (pure parsing/validation, no I/O beyond `Path.read_text`, no network, no subprocess).

---
*Phase: 02-config-schema-yaml-loader*
*Completed: 2026-05-02*
