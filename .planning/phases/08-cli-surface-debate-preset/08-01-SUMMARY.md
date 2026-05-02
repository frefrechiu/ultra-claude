---
phase: 08-cli-surface-debate-preset
plan: 01
subsystem: packaging
tags: [pyproject, console-script, hatchling, importlib-resources, yaml, preset, click]

# Dependency graph
requires:
  - phase: 02-config-schema-loader
    provides: RoundtableConfig pydantic schema (src/ultra_claude/config.py) — debate.yaml must validate against it
  - phase: 01-project-skeleton-pypi-name-reservation
    provides: pyproject.toml hatchling layout with `[tool.hatch.build.targets.wheel] packages = ["src/ultra_claude"]` (auto-includes the new presets/ subtree)
provides:
  - "[project.scripts] ultra-claude = ultra_claude.cli:main entry point declared in pyproject.toml"
  - "Bundled debate preset at src/ultra_claude/presets/debate.yaml (3 agents, max_turns=9, stop_keywords=[AGREED, SHIP IT])"
  - "Package data namespace ultra_claude.presets reachable via importlib.resources for plan 08-02's --preset flag"
affects: [08-02 (cli module that resolves the entry point), 08-03 (cli tests that exercise --preset debate), 09 (release smoke must `pip install` the wheel and find the YAML)]

# Tech tracking
tech-stack:
  added: []  # No new runtime dependencies; pure config + data
  patterns:
    - "Bundled YAML presets shipped as package data, addressed via importlib.resources.files() — works in editable installs and built wheels alike"
    - "PEP 621 [project.scripts] declared between [project.optional-dependencies] and [project.urls] to keep [project.*] tables grouped"

key-files:
  created:
    - "src/ultra_claude/presets/debate.yaml"
  modified:
    - "pyproject.toml"

key-decisions:
  - "stop_keywords default in the debate preset is [AGREED, SHIP IT] (overrides RoundtableConfig schema default [AGREED, DONE]) — reads more naturally for a debate-flavored preset; both still satisfy min_length=1 constraint"
  - "max_turns=9 (3 agents x 3 rounds) locked by 08-CONTEXT.md decisions"
  - "presets/ directory is shipped via the pre-existing [tool.hatch.build.targets.wheel] packages = [src/ultra_claude] rule (auto-include); no [tool.hatch.build] include = [...] rule needed"
  - "presets/ is a namespace subpackage (no __init__.py) — importlib.resources.files('ultra_claude.presets') still resolves it for resource discovery"
  - "Entry point names module ultra_claude.cli:main that does NOT exist yet — plan 08-02 closes that gap; pip install -e . succeeds, but invoking ultra-claude before 08-02 raises ModuleNotFoundError (expected and acceptable)"

patterns-established:
  - "Bundled presets pattern: ship YAML at src/ultra_claude/presets/<name>.yaml; resolve at runtime via importlib.resources.files('ultra_claude.presets').joinpath(name + '.yaml').read_text() — extensible to additional presets in v2"
  - "Console-script entry point pattern: declare in pyproject.toml [project.scripts]; module path resolution deferred to install time so the binary reflects the live editable install"

requirements-completed: [PRE-01]

# Metrics
duration: ~2.5 min
completed: 2026-05-02
---

# Phase 8 Plan 1: pyproject [project.scripts] entry point + bundled debate preset

**Adds the `ultra-claude = ultra_claude.cli:main` console-script entry point and ships the 3-agent debate preset (Architect/Critic/Implementer on claude/gemini/codex) as package data so plan 08-02's `--preset debate` flag has both a binary to launch and a YAML to load.**

## Performance

- **Duration:** ~2.5 min
- **Started:** 2026-05-02T05:45:36Z
- **Completed:** 2026-05-02T05:48:03Z
- **Tasks:** 2
- **Files modified:** 2 (1 modified: pyproject.toml; 1 created: src/ultra_claude/presets/debate.yaml)

## Accomplishments

- Declared `[project.scripts] ultra-claude = "ultra_claude.cli:main"` in `pyproject.toml`. After re-running `pip install -e ".[dev]"`, the `ultra-claude` console script binary appears on PATH inside the venv (binary works structurally; calling it raises `ModuleNotFoundError` until 08-02 lands `cli.py`, which is the documented expected state).
- Created `src/ultra_claude/presets/debate.yaml` (1033 bytes, 30 lines, LF-only, ASCII-only) bundling a 3-agent roundtable: **Architect** on `claude`, **Critic** on `gemini`, **Implementer** on `codex`. `max_turns=9`, `stop_keywords=[AGREED, SHIP IT]`. Validates cleanly through `RoundtableConfig.from_yaml_string()` and `importlib.resources.files('ultra_claude.presets').joinpath('debate.yaml')` is reachable end-to-end.
- Zero Python source code added — this plan is config and data only. 72/72 tests still pass (zero regression).
- Hatchling auto-includes the new `presets/` subtree via the pre-existing `[tool.hatch.build.targets.wheel] packages = ["src/ultra_claude"]` rule (no extra `include` directive needed); confirmed via `importlib.resources.files()` lookup roundtrip.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add `[project.scripts]` entry point to pyproject.toml** — `481c8e9` (feat)
2. **Task 2: Create `src/ultra_claude/presets/debate.yaml`** — `7331fc7` (feat)

**Plan metadata:** _(this commit, after SUMMARY/STATE/ROADMAP land)_

## Files Created/Modified

- `pyproject.toml` — Added `[project.scripts]` table with `ultra-claude = "ultra_claude.cli:main"` between `[project.optional-dependencies]` (line 60) and `[project.urls]` (now line 65). Total file size: 2592 bytes, 110 LF, 0 CRLF.
- `src/ultra_claude/presets/debate.yaml` — NEW. 3-agent debate roundtable with non-empty `system_prompt` for each agent. `max_turns=9`, `stop_keywords=[AGREED, SHIP IT]`. ASCII-only, LF-only.

## Decisions Made

- **Placement of `[project.scripts]` between `[project.optional-dependencies]` and `[project.urls]`** — plan instruction; PEP 621 keeps `[project.*]` tables grouped together and the upstream Python packaging guide shows this ordering.
- **`stop_keywords: [AGREED, SHIP IT]` instead of the schema default `[AGREED, DONE]`** — `SHIP IT` reads more naturally for a debate-flavored preset; both satisfy the schema's `min_length=1` constraint. Note: the production-grade keyword *unanimity* defense (Pitfall #4) is enforced by `Keyword` in `stop_conditions.py` regardless of which keyword strings the preset declares.
- **`presets/` is a namespace subpackage** — no `__init__.py` was created, deliberately. `importlib.resources.files('ultra_claude.presets')` still resolves it for resource discovery in Python 3.11+ (verified end-to-end). Avoids polluting the package surface with an empty module just to satisfy old-style `pkgutil` discovery.
- **No `[tool.hatch.build]` `include = [...]` rule added** — the existing `[tool.hatch.build.targets.wheel] packages = ["src/ultra_claude"]` directive already auto-ships every file under that subtree, including the new `presets/*.yaml`. Verified that `importlib.resources` finds the file in the editable install; phase 9's release smoke will re-verify against a built wheel.

## Deviations from Plan

None — plan executed exactly as written.

The plan documented one potential Windows-host concern up front: `core.autocrlf=true` could rewrite LF to CRLF on the working tree, which the project's house style forbids. I pre-emptively wrote `debate.yaml` via `Path.write_bytes(content.encode("utf-8"))` (the same defensive pattern that landed in plan 06-01) so neither the working tree nor the staged blob carries a CRLF. Verification confirmed: working tree 30 LF / 0 CRLF; staged blob 1033 bytes / 30 LF / 0 CRLF. This was anticipated by the plan's `<done>` criteria ("File is LF-only and ASCII-only on disk") — applying the established pattern is not a deviation.

The Git `core.autocrlf=true` warning printed at `git add` time is informational; the staged blob's actual bytes are LF-only, which is what the plan's verification command checked.

---

**Total deviations:** 0
**Impact on plan:** None — plan was complete and correct as written.

## Issues Encountered

None. All plan-level verifications passed first try:
- `python -c "import tomllib; ..."` confirmed `pyproject.toml` is valid TOML and contains the entry point.
- `RoundtableConfig.from_yaml_string(...)` accepted the preset and produced a 3-agent config with the expected attributes.
- `importlib.resources.files('ultra_claude.presets').joinpath('debate.yaml').read_text(...)` returned the YAML contents end-to-end (proves package data reachable via the API plan 08-02's `--preset` flag will use).
- `pytest tests/` 72/72 PASS (zero regression — this plan added zero Python code).

The only ruff finding (`config.py` RUF022 + UP037) is a pre-existing 2-error tail from Phase 2 already logged in `.planning/phases/04-adapter-protocol-claudeadapter/deferred-items.md`. Per the SCOPE BOUNDARY rule, only auto-fix issues caused by the current task's changes; 08-01 introduced none.

## User Setup Required

None — no external service configuration required.

The `ultra-claude` console-script binary is structurally installed by `pip install -e ".[dev]"`, but invoking it before plan 08-02 lands `cli.py` raises `ModuleNotFoundError: No module named 'ultra_claude.cli'`. This is the documented expected state at the end of 08-01 (per the plan's `<verification>` section). Plan 08-02 closes that gap.

## Next Phase Readiness

Plan 08-02 is fully unblocked:
- Entry point points at `ultra_claude.cli:main` — 08-02 creates that module with the click `main` group.
- Bundled preset is reachable via `importlib.resources.files("ultra_claude.presets").joinpath("debate.yaml").read_text()` — 08-02's `--preset debate` flag uses exactly this API.
- 72/72 test suite is green so 08-03's CLI test additions land on a clean baseline.

Plan 08-03 (CLI tests) gains:
- A schema-valid bundled preset for the `test_run_with_preset` test case (08-CONTEXT.md test #4) — no need for tests to bring their own YAML.

## Self-Check: PASSED

**Created files exist:**
- `[FOUND] src/ultra_claude/presets/debate.yaml` (1033 bytes, LF-only, ASCII-only — verified)

**Modified files contain expected content:**
- `[FOUND] pyproject.toml` contains `[project.scripts]` block with `ultra-claude = "ultra_claude.cli:main"` (verified via `tomllib.loads`)

**Commits exist on master:**
- `[FOUND] 481c8e9` (feat(08-01): add ultra-claude console-script entry point)
- `[FOUND] 7331fc7` (feat(08-01): add bundled debate preset (PRE-01))

**Plan-level success criteria:**
- `[PASS] pyproject.toml has [project.scripts] ultra-claude = "ultra_claude.cli:main"` and is still valid TOML
- `[PASS] src/ultra_claude/presets/debate.yaml` exists with 3-agent debate roundtable; loads cleanly via RoundtableConfig.from_yaml_string
- `[PASS] 72/72 tests still pass (zero regression)`
- `[PASS] Hatchling auto-includes the YAML under existing packages = ["src/ultra_claude"] rule (no [tool.hatch.build] include edits needed)`
- `[PASS] Plan 08-02 unblocked — importlib.resources.files("ultra_claude.presets").joinpath("debate.yaml") roundtrip works`

---
*Phase: 08-cli-surface-debate-preset*
*Completed: 2026-05-02*
