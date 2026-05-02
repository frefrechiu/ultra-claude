---
phase: 01-project-skeleton-pypi-name-reservation
plan: 02
subsystem: infra
tags: [packaging, pyproject-toml, hatchling, pep-621, dynamic-version, src-layout, ruff, mypy, pytest]

# Dependency graph
requires:
  - "01-01 (LICENSE for SPDX MIT alignment, README.md for [project].readme, src/ultra_claude/__init__.py for [tool.hatch.version] path)"
provides:
  - "pyproject.toml at repo root with PEP 621 metadata + hatchling build config + tool tables"
  - "Buildable project skeleton — `pip install -e .[dev]` and `python -m build` are unblocked for plan 01-03"
  - "Locked runtime/dev dependency floor that every later phase relies on"
  - "Dynamic version wiring: hatchling regex-reads __version__ from src/ultra_claude/__init__.py (single source of truth)"
affects: [01-03, 02-deps-bootstrap, 04-subprocess-mixin, 09-release]

# Tech tracking
tech-stack:
  added:
    - "hatchling >= 1.29 (build backend; declared, not yet installed)"
    - "click >= 8.3.3 (runtime, declared)"
    - "pydantic >= 2.13.3 (runtime, declared)"
    - "pyyaml >= 6.0.3 (runtime, declared)"
    - "ruff >= 0.13 (dev, declared)"
    - "mypy >= 1.18 (dev, declared)"
    - "pytest >= 8.4 (dev, declared)"
    - "pytest-mock >= 3.15, pytest-cov >= 6.0, pytest-subprocess >= 1.5 (dev, declared)"
    - "types-PyYAML, build >= 1.2, twine >= 5.1 (dev, declared)"
  patterns:
    - "PEP 621 [project] table with SPDX-string license = \"MIT\" (modern PEP 639 form)"
    - "Dynamic version: dynamic = [\"version\"] + [tool.hatch.version] path = src/ultra_claude/__init__.py"
    - "src layout target: [tool.hatch.build.targets.wheel] packages = [\"src/ultra_claude\"]"
    - "Explicit sdist include list to prevent .planning/ leakage into PyPI release artifact"
    - "Tool config co-located in pyproject.toml: [tool.ruff], [tool.mypy], [tool.pytest.ini_options]"
    - "NO [project.scripts] yet — CLI entry deferred to Phase 8 (locked by 01-CONTEXT.md)"

key-files:
  created:
    - "pyproject.toml"
  modified: []

key-decisions:
  - "Build backend = hatchling >= 1.29 (NOT full hatch CLI — `pip install -e .[dev]` is sufficient per CLAUDE.md)"
  - "Dynamic version via [tool.hatch.version] path — never duplicate the version string in pyproject.toml; __init__.py is single source of truth"
  - "Development Status :: 1 - Planning classifier (NOT 3 - Alpha) — 0.0.1 is a name-reservation stub, not a usable alpha; bumps to 4 - Beta at v0.1.0 in Phase 9"
  - "[tool.mypy] files = [\"src/ultra_claude\"] — strict mypy scoped to package only, NOT to tests/ (per Phase 9 TST-06)"
  - "[tool.pytest.ini_options] addopts = \"-ra\" only — NO --cov yet (no source to cover meaningfully); coverage flags re-enabled in Phase 9 TST-04"
  - "[tool.ruff.format] line-ending = \"lf\" — locks LF endings cross-platform per CLAUDE.md UTF-8/LF discipline"
  - "[tool.hatch.build.targets.sdist] explicit include = LICENSE, README.md, CHANGELOG.md, pyproject.toml, src/ultra_claude — prevents .planning/ documentation from bloating the PyPI sdist"
  - "Dev deps include pytest-subprocess and types-PyYAML up front even though no tests/types exist yet — keeps `pip install -e .[dev]` reproducible across phases"
  - "build >= 1.2 and twine >= 5.1 in dev extra — plan 01-03's manual upload path uses them without a global pip install"

patterns-established:
  - "PEP 621 SPDX-string license declaration (license = \"MIT\") — adopted by hatchling 1.29+ and modern PyPI"
  - "tomllib-based static verification (Python 3.11+ stdlib) — used in this plan's verify block, will be reused by Phase 4's CI lint test (TST-05) and Phase 9's release sanity check"

requirements-completed: [PKG-02, PKG-07]

# Metrics
duration: ~1.5min
completed: 2026-05-02
---

# Phase 1 Plan 2: pyproject.toml with Hatchling Backend Summary

**PEP 621 pyproject.toml at repo root with hatchling >= 1.29 backend, dynamic version reading `__version__` from `src/ultra_claude/__init__.py`, pinned runtime deps (click >= 8.3.3, pydantic >= 2.13.3, pyyaml >= 6.0.3), pinned dev deps (ruff >= 0.13, mypy >= 1.18, pytest >= 8.4 + auxiliaries), src-layout wheel target, and ruff/mypy/pytest tool tables — making the project buildable and installable.**

## Performance

- **Duration:** ~1.5 min
- **Started:** 2026-05-02T01:54:42Z
- **Completed:** 2026-05-02T01:56:12Z
- **Tasks:** 1
- **Files modified:** 1 (newly created)

## Accomplishments

- `pyproject.toml` at repo root with valid PEP 621 metadata + hatchling build configuration + tool tables.
- `[build-system].build-backend = "hatchling.build"` and `requires = ["hatchling>=1.29"]` declared per locked decision.
- `[project]` block: `name = "ultra-claude"`, `requires-python = ">=3.10"`, `license = "MIT"`, `authors = [Freddy Chiu]`, comprehensive `keywords` and `classifiers` (PyPI discoverability), `Development Status :: 1 - Planning` (NOT 3 - Alpha — this is a stub).
- `[project] dynamic = ["version"]` + `[tool.hatch.version] path = "src/ultra_claude/__init__.py"` — single-source-of-truth wiring; hatchling will regex-read the `__version__ = "0.0.1"` literal landed by plan 01-01.
- Runtime dependency floor pinned: `click>=8.3.3`, `pydantic>=2.13.3`, `pyyaml>=6.0.3` — exact minimums from CLAUDE.md tech stack lock.
- Dev dependency floor pinned: `ruff>=0.13`, `mypy>=1.18`, `pytest>=8.4`, plus `pytest-mock>=3.15`, `pytest-cov>=6.0`, `pytest-subprocess>=1.5`, `types-PyYAML`, `build>=1.2`, `twine>=5.1`.
- `[project.urls]` block: Homepage/Repository/Issues/Changelog all point at `https://github.com/frefrechiu/ultra-claude`.
- `[tool.hatch.build.targets.wheel] packages = ["src/ultra_claude"]` — wires the src layout established by plan 01-01.
- `[tool.hatch.build.targets.sdist] include = [...]` — explicit include list (LICENSE, README.md, CHANGELOG.md, pyproject.toml, src/ultra_claude); prevents `.planning/` documentation from leaking into the PyPI sdist.
- `[tool.ruff]` configured: line-length 100, target py310, src/+tests, lint rules E/F/I/B/UP/SIM/RUF (ignore E501), format LF + double quotes.
- `[tool.mypy]` configured: strict, py310, scoped to `src/ultra_claude` only.
- `[tool.pytest.ini_options]` configured: minversion 8.4, testpaths tests, addopts `-ra` (no `--cov` yet — re-enabled in Phase 9).
- **NO `[project.scripts]` table** — CLI entry point deferred to Phase 8 per locked CONTEXT decision; adding it now would break `pip install` of the 0.0.1 stub since `cli:main` does not exist yet.

## Task Commits

Each task committed atomically:

1. **Task 1: Write pyproject.toml with hatchling backend, pinned deps, and tool config** — `b9bf3c5` (feat)

**Plan metadata commit:** pending after this SUMMARY is written.

## Files Created/Modified

- `pyproject.toml` — PEP 621 metadata + hatchling build config + ruff/mypy/pytest tool tables. 2,534 bytes, LF-only, 107 insertions.

## Build Backend Confirmation

```toml
[build-system]
requires = ["hatchling>=1.29"]
build-backend = "hatchling.build"
```

`tomllib.loads(...)` parses cleanly; `data['build-system']['build-backend'] == "hatchling.build"`.

## Runtime Dependency Floor (PKG-02)

```toml
[project.dependencies]
"click>=8.3.3"
"pydantic>=2.13.3"
"pyyaml>=6.0.3"
```

Exact minimums from CLAUDE.md tech stack lock. Even though the 0.0.1 stub does not import these packages, declaring them ensures `pip install ultra-claude==0.0.1` resolves the same env as later versions — and the stub serves as a smoke-test that the dep tree resolves at all.

## Dev Dependency Floor (PKG-07)

```toml
[project.optional-dependencies.dev]
"ruff>=0.13"
"mypy>=1.18"
"pytest>=8.4"
"pytest-mock>=3.15"
"pytest-cov>=6.0"
"pytest-subprocess>=1.5"
"types-PyYAML"
"build>=1.2"
"twine>=5.1"
```

`pytest-subprocess` and `types-PyYAML` are declared up front (no tests/types yet) for reproducibility across phases. `build` and `twine` live in the dev extra so plan 01-03's manual upload step has them without requiring a global pip install.

## NO [project.scripts] (Locked)

Verified absent: `data.get('project', {}).get('scripts') is None`. `01-CONTEXT.md` locks: "NO CLI entry point yet (Phase 8 ships that). NO functional imports. The 0.0.1 release exists only to squat the name." Adding `[project.scripts]` now would break `pip install` of the stub because `cli:main` does not exist.

## Static Cross-Check: pyproject.toml ↔ src/ultra_claude/__init__.py

```text
__init__.py __version__ = '0.0.1'
[tool.hatch.version].path = 'src/ultra_claude/__init__.py'
[project].name = 'ultra-claude'
OK static metadata aligned
```

The `[tool.hatch.version] path` resolves to a file that exists (plan 01-01's deliverable) and contains `__version__ = "0.0.1"`. The `[project] name` matches the PyPI name to be reserved in plan 01-03. Plan 01-03 will verify this dynamically by running `pip install -e ".[dev]"` followed by `python -c "import ultra_claude; print(ultra_claude.__version__)"` and checking the output is exactly `0.0.1`.

## Tool Tables Present (Out-of-the-box Tooling)

- `[tool.ruff]` — line-length 100, target-version py310, src = ["src", "tests"]
- `[tool.ruff.lint]` — select = E, F, I, B, UP, SIM, RUF; ignore = E501
- `[tool.ruff.format]` — quote-style "double", indent-style "space", line-ending "lf"
- `[tool.mypy]` — python_version "3.10", strict, warn_unused_ignores, warn_return_any, files = ["src/ultra_claude"]
- `[tool.pytest.ini_options]` — minversion 8.4, testpaths ["tests"], addopts "-ra"

Once plan 01-03 runs `pip install -e ".[dev]"`, all three tools work without extra config files.

## Decisions Made

All decisions were pre-locked in `01-CONTEXT.md` and CLAUDE.md and were followed verbatim. No new decisions needed in this plan.

The only minor judgment calls (already encoded in the plan's `<action>` block) were:
- `Development Status :: 1 - Planning` (NOT `3 - Alpha`) — this is a name-reservation stub.
- `addopts = "-ra"` only — no `--cov` because there is no source to cover yet (re-enabled in Phase 9 TST-04).
- Explicit sdist `include` list — prevents `.planning/` from bloating the PyPI tarball.

## Deviations from Plan

None — plan executed exactly as written. The `pyproject.toml` was created via the `Write` tool with the exact content specified in Task 1's `<action>` block. All 26 success criteria from the plan prompt and all assertions in the plan's `<verify>` and `<verification>` blocks pass:

- `pyproject.toml` exists at repo root ✓
- `[build-system].build-backend == "hatchling.build"` ✓
- `[build-system].requires` contains `"hatchling>=1.29"` ✓
- `[project].name == "ultra-claude"` ✓
- `[project].description` set ✓
- `[project].requires-python == ">=3.10"` ✓
- `[project].license == "MIT"` ✓
- `[project].authors` includes Freddy Chiu ✓
- `[project].dynamic` contains `"version"` ✓
- `[tool.hatch.version].path == "src/ultra_claude/__init__.py"` ✓
- Runtime deps pinned (click >= 8.3.3, pydantic >= 2.13.3, pyyaml >= 6.0.3) ✓
- Dev deps pinned (ruff >= 0.13, mypy >= 1.18, pytest >= 8.4, pytest-mock, pytest-cov, pytest-subprocess, types-PyYAML, build, twine) ✓
- `[project.urls].Homepage == "https://github.com/frefrechiu/ultra-claude"` ✓
- NO `[project.scripts]` table ✓
- `[tool.hatch.build.targets.wheel].packages == ["src/ultra_claude"]` ✓
- `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]` tables present ✓
- LF-only at byte level (verified `b'\r\n' not in open('pyproject.toml','rb').read()`) ✓
- Static metadata aligned: `[tool.hatch.version].path` → `src/ultra_claude/__init__.py` → `__version__ = "0.0.1"` ✓

## Issues Encountered

**Verification command encoding (informational only):** The plan's `<verification>` block uses `open('src/ultra_claude/__init__.py').read()` without an explicit encoding. On this Windows host, Python's default encoding is `cp950` (legacy CJK codepage), which raises `UnicodeDecodeError` on any non-ASCII byte. The fix in this run was to invoke the verifier with `PYTHONIOENCODING=utf-8` and pass `encoding='utf-8'` to `open(...)`. The pyproject.toml file itself contains only ASCII bytes (verified) and parses cleanly via `tomllib.loads(open('pyproject.toml','rb').read().decode('utf-8'))`. This is a verifier-script ergonomics issue, not a defect in the plan output. Phase 4's CI lint test (TST-05) should adopt the explicit-encoding form to avoid the same surprise on Windows runners.

**Git autocrlf warning (informational only):** Same as plan 01-01 — Git emitted `LF will be replaced by CRLF the next time Git touches it` on `git add`. The on-disk file is LF-only at the byte level (verified before commit), and Git stores LF in the index/repo. No action needed; expected Windows-cross-platform behavior.

## User Setup Required

None — no external services configured in this plan. Plan 01-03 will require the user's PyPI API token / `~/.pypirc` for the manual `twine upload` step.

## Next Phase Readiness

**Plan 01-03 (manual PyPI upload of 0.0.1 stub) is unblocked.** Plan 01-03 will:

1. Create a clean virtualenv (or use the user's existing one).
2. Run `pip install -e ".[dev]"` — should succeed (this plan's pyproject.toml + plan 01-01's `__init__.py` make the install resolvable).
3. Run `python -c "import ultra_claude; print(ultra_claude.__version__)"` — should print exactly `0.0.1` (dynamic version verification).
4. Run `python -m build` — should produce `dist/ultra_claude-0.0.1.tar.gz` and `dist/ultra_claude-0.0.1-py3-none-any.whl`.
5. Reach a `checkpoint:human-action` for the user to run `twine upload dist/ultra_claude-0.0.1*` with their PyPI credentials.

Phases 2-9 will all read this `pyproject.toml` for dependency resolution.

## Self-Check: PASSED

Verified after writing SUMMARY.md:

- `pyproject.toml` exists ✓ (FOUND on disk at `C:\Users\fredd\Desktop\project\Ultra-claude\pyproject.toml`, present in commit `b9bf3c5`)
- Commit `b9bf3c5` exists in git log ✓ (`git log --oneline | grep b9bf3c5` returns 1 match: `feat(01-02): add pyproject.toml with hatchling backend, pinned deps, tool config`)
- All 26 plan-prompt success criteria pass via tomllib introspection ✓
- LF-only at byte level ✓
- Static cross-check (pyproject.toml ↔ __init__.py) passes ✓

---
*Phase: 01-project-skeleton-pypi-name-reservation*
*Completed: 2026-05-02*
