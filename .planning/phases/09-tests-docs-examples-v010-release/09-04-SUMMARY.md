---
phase: 09-tests-docs-examples-v010-release
plan: 04
subsystem: release-build
tags: [release, build, twine, smoke-test, coverage, ruff, mypy, pypi, wheel, sdist, v0.1.0]
requirements: [PKG-01, PKG-06, TST-01, TST-02, TST-06, TST-07]
dependency_graph:
  requires:
    - 09-01 complete (0.1.0 literal in src/ultra_claude/__init__.py + py.typed marker + CHANGELOG [0.1.0] section)
    - 09-02 complete (echo CLI fixture + E2E test landed; full suite at 86 tests)
    - 09-03 complete (README.md replacement, CONTRIBUTING.md, examples/ tree)
  provides:
    - dist/ultra_claude-0.1.0-py3-none-any.whl (40407 bytes; pure-Python wheel; consumed by user `twine upload`)
    - dist/ultra_claude-0.1.0.tar.gz (33618 bytes; sdist; PyPI fallback)
    - PUBLISH.md v0.1.0 release runbook (consumed by user; closes PKG-06 + PKG-01 after upload)
    - Project-wide ruff cleanup (4 pre-existing Phase 2 errors cleared; v0.1.0 quality gate now green)
  affects:
    - User must run `python -m twine upload dist/ultra_claude-0.1.0*` to close PKG-06 (manual step; runbook in PUBLISH.md)
    - All future Phase 9+ work runs against a clean ruff baseline (zero project-wide errors)
tech_stack:
  added: []
  patterns:
    - "Hatchling build pipeline: pyproject.toml [tool.hatch.version] reads __version__ from __init__.py at build time; [tool.hatch.build.targets.wheel] packages = ['src/ultra_claude'] auto-bundles py.typed + presets/debate.yaml"
    - "Smoke install pattern: python -m venv -> pip install --no-cache-dir wheel -> verify --version + --dry-run -> rm -rf venv (no leftover; gitignored via .smoke-venv-*/)"
    - "PUBLISH.md additive convention: never delete historical instructions; append new top-level sections separated by ---"
key_files:
  created:
    - dist/ultra_claude-0.1.0-py3-none-any.whl (40407 bytes; pure-Python wheel; gitignored via dist/; not committed)
    - dist/ultra_claude-0.1.0.tar.gz (33618 bytes; sdist; gitignored via dist/; not committed)
  modified:
    - .gitignore (added `.smoke-venv-*/` pattern to cover venv variants beyond Phase 1's `.smoke-venv/`)
    - src/ultra_claude/config.py (RUF022 noqa added with rationale; UP037 quotes removed from forward-reference annotation)
    - tests/test_config.py (I001 import-block reorganized; F401 unused `format_validation_error` removed)
    - .planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md (6719 -> 12923 bytes; appended `# Publishing v0.1.0 (the FIRST FUNCTIONAL release)` section preserving original 0.0.1 content verbatim)
decisions:
  - Pre-existing ruff errors (4 since Phase 2, deferred since 07-01 to "a future cleanup plan / likely Phase 9 quality-bar pass") fixed in this plan as Rule 3 deviation -- v0.1.0 must_have explicitly demands "ruff check passes with zero errors project-wide"
  - Smoke venv name `.smoke-venv-09` chosen per executor prompt success_criteria; .gitignore extended with glob `.smoke-venv-*/` to also cover plan's stated `.smoke-venv-0.1.0-verify` (created and torn down by Task 2 verify script)
  - PUBLISH.md modified additively: new top-level `# Publishing v0.1.0` section after `---` separator; original 0.0.1 sub-headings (`##`) preserved; rationale: Keep-a-Changelog convention applied to release runbooks (never delete history)
  - Build artefacts NOT committed to git (dist/ gitignored since Phase 1; re-buildable from source; PUBLISH.md is the canonical pointer to the on-disk artefacts)
metrics:
  duration: "~9.5 min (2026-05-02T07:20:03Z -> 2026-05-02T07:29:33Z)"
  start: "2026-05-02T07:20:03Z"
  end: "2026-05-02T07:29:33Z"
  completed_date: "2026-05-02"
  tasks_completed: 3
  files_changed: 4
  commits: 2
---

# Phase 9 Plan 4: Build v0.1.0 + smoke + verification + PUBLISH.md update Summary

**One-liner:** Built `dist/ultra_claude-0.1.0-py3-none-any.whl` + `dist/ultra_claude-0.1.0.tar.gz` via hatchling, validated via `twine check` + clean-venv smoke install (`ultra-claude --version` -> `0.1.0`; `ultra-claude run --preset debate --inline "test" --dry-run` -> 9-turn schedule with Architect/Critic/Implementer); ran the v0.1.0 quality gates (pytest 86/86 PASS in 4.77s with TOTAL coverage 85% via pytest-cov; ruff check clean project-wide; mypy --strict on src/ultra_claude/ zero errors); cleared 4 pre-existing Phase 2 ruff errors as Rule-3 blocking deviation (deferred-items.md from 07-01 explicitly nominated Phase 9 as the cleanup destination); appended a new `# Publishing v0.1.0 (the FIRST FUNCTIONAL release)` section to `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md` documenting the user-action `python -m twine upload dist/ultra_claude-0.1.0*` runbook to close PKG-06 + PKG-01.

## What Changed

### 1. `dist/` -- two new artefacts (gitignored; not committed)

```
$ ls -la dist/ultra_claude-0.1.0*
-rw-r--r-- 1 fredd 197609 40407 May  2 15:20 dist/ultra_claude-0.1.0-py3-none-any.whl
-rw-r--r-- 1 fredd 197609 33618 May  2 15:20 dist/ultra_claude-0.1.0.tar.gz
```

Built via `python -m build` from a clean `dist/` directory (the `rm -rf dist/ && mkdir -p dist/` step removed the stale Phase 1 `0.0.1` artefacts -- T-09-19 mitigation: PUBLISH.md's `dist/ultra_claude-0.1.0*` glob can no longer accidentally match a 0.0.1 file).

Hatchling read `__version__ = "0.1.0"` from `src/ultra_claude/__init__.py` (literal placed by 09-01) and packaged the entire `src/ultra_claude/` tree per `[tool.hatch.build.targets.wheel] packages = ["src/ultra_claude"]`.

**Wheel contents (20 files):**
- `ultra_claude-0.1.0.dist-info/{METADATA, RECORD, WHEEL, entry_points.txt, licenses/LICENSE}` (5 metadata files)
- `ultra_claude/{__init__, cli, config, exceptions, orchestrator, registry, stop_conditions, transcript}.py` (8 source modules)
- `ultra_claude/adapters/{__init__, base, claude, codex, gemini}.py` (5 adapter modules)
- `ultra_claude/presets/debate.yaml` (1033 bytes; the bundled preset; T-09-15 mitigation -- confirmed present so `--preset debate` works after pip install)
- `ultra_claude/py.typed` (0 bytes; PEP 561 marker; T-09-15 mitigation -- confirmed present so downstream typed users see the package as type-checked)

**Sdist contents (22 files):** all of the above plus `LICENSE`, `README.md`, `CHANGELOG.md`, `pyproject.toml`, `.gitignore`, `examples/README.md`, `PKG-INFO`. Verified per the plan's Step 5 assertions.

**twine check:**
```
Checking dist/ultra_claude-0.1.0-py3-none-any.whl: PASSED
Checking dist/ultra_claude-0.1.0.tar.gz: PASSED
```

Both PASS -- README markdown content-type metadata round-trips correctly (the 09-03 README is markdown; pyproject.toml's `readme = "README.md"` directive correctly attached `Description-Content-Type: text/markdown` to the wheel/sdist METADATA).

### 2. Clean-venv smoke install -- 5 PASS / 5 (Task 2 Steps 1-5)

Created `.smoke-venv-09` (gitignored via the new `.smoke-venv-*/` pattern), installed the wheel via `pip install --no-cache-dir dist/ultra_claude-0.1.0-py3-none-any.whl` (which resolved 8 transitive deps: click 8.3.3 / pydantic 2.13.3 / pyyaml 6.0.3 / pydantic-core 2.46.3 / typing-extensions 4.15.0 / typing-inspection 0.4.2 / annotated-types 0.7.0 / colorama 0.4.6), and ran the four checks:

```
$ .smoke-venv-09/Scripts/ultra-claude.exe --version
ultra-claude, version 0.1.0

$ .smoke-venv-09/Scripts/ultra-claude.exe run --preset debate --inline "should we add an undo button?" --dry-run
Planned roundtable (max_turns=9, stop_keywords=['AGREED', 'SHIP IT']):
  Turn 1: Architect (claude) - high-level design
  Turn 2: Critic (gemini) - skeptic
  Turn 3: Implementer (codex) - hands-on coder
  Turn 4: Architect (claude) - high-level design
  Turn 5: Critic (gemini) - skeptic
  Turn 6: Implementer (codex) - hands-on coder
  Turn 7: Architect (claude) - high-level design
  Turn 8: Critic (gemini) - skeptic
  Turn 9: Implementer (codex) - hands-on coder
Task: should we add an undo button?

$ .smoke-venv-09/Scripts/python.exe -c "import ultra_claude; print(ultra_claude.__version__); assert ultra_claude.__version__ == '0.1.0'"
0.1.0
```

Then `rm -rf .smoke-venv-09` -- venv removed; no leftover.

The plan's `<verify>` automated check ALSO ran a separate venv `.smoke-venv-0.1.0-verify` to programmatically re-execute the same smoke gates with `subprocess.run` + timeouts (T-09-18 mitigation; pip-install at 180s, --version at 15s, --dry-run at 15s; all completed in seconds). That venv was also `rm -rf`'d post-test. Final `git status --short` shows zero leftover smoke venvs.

### 3. Quality gates in dev venv -- 3 PASS / 3 (Task 2 Steps 6-8)

```
$ pytest --cov=src/ultra_claude --cov-report=term-missing
86 passed in 4.77s
TOTAL                                     503     74    85%

$ ruff check
All checks passed!

$ mypy
Success: no issues found in 13 source files
```

Per-module coverage (sorted high to low):
- `src/ultra_claude/__init__.py`: 100%
- `src/ultra_claude/adapters/__init__.py`: 100%
- `src/ultra_claude/adapters/claude.py`: 100%
- `src/ultra_claude/adapters/codex.py`: 100%
- `src/ultra_claude/adapters/gemini.py`: 100%
- `src/ultra_claude/exceptions.py`: 100%
- `src/ultra_claude/stop_conditions.py`: 97%
- `src/ultra_claude/transcript.py`: 93%
- `src/ultra_claude/orchestrator.py`: 92%
- `src/ultra_claude/config.py`: 89%
- `src/ultra_claude/cli.py`: 77%
- `src/ultra_claude/adapters/base.py`: 73% (process-tree-kill paths in lines 241-269 are platform-conditional and not hit in unit tests; covered by 09-02's E2E test indirectly)
- `src/ultra_claude/registry.py`: 36% (the `register_adapter` and lookup-error branches in lines 42-48 are not exercised by tests; only the registry init path is tested)

`TOTAL = 503 stmts / 74 miss / 85%` -- exceeds the 80% gate by 5 percentage points. The two lowest-coverage modules (registry.py 36% and adapters/base.py 73%) are platform-conditional / lookup-error branches that would require synthetic tests; deemed out of scope for the v0.1.0 ship since the headline 80% gate passes comfortably.

### 4. `.gitignore` update

Added `.smoke-venv-*/` pattern below the existing `.smoke-venv/` pattern (line 56):

```diff
 .smoke-venv/
+.smoke-venv-*/
```

Reason: Phase 1's `.gitignore` only covered the literal `.smoke-venv/` directory; this plan creates `.smoke-venv-09` and `.smoke-venv-0.1.0-verify` as part of Task 2 verification. The glob `.smoke-venv-*/` covers all current and future smoke-venv variants without committing to a specific suffix.

Verified via `git check-ignore`: `.smoke-venv-09-test/` matches `.gitignore:56:.smoke-venv-*/`; `git status --short` against the temp test dir produces zero output.

### 5. `src/ultra_claude/config.py` + `tests/test_config.py` -- ruff cleanup (Rule 3 deviation)

Cleared 4 pre-existing ruff errors documented in `.planning/phases/07-gemini-codex-adapters/deferred-items.md` since 07-01:

**`src/ultra_claude/config.py:38` (RUF022):**
```diff
-__all__ = [
+__all__ = [  # noqa: RUF022 -- chronological-by-introduction (AgentConfig and RoundtableConfig before helpers; ConfigError last as a re-export) to match the conventions in stop_conditions.py / adapters/__init__.py / exceptions.py
     "AgentConfig",
     "RoundtableConfig",
     "load_config",
     "format_validation_error",
     "ConfigError",
 ]
```

**`src/ultra_claude/config.py:110` (UP037):**
```diff
-    def from_yaml_string(cls, source: str) -> "RoundtableConfig":
+    def from_yaml_string(cls, source: str) -> RoundtableConfig:
```

The forward-reference quotes were redundant: `from __future__ import annotations` is active at the top of the file (line 27), so all annotations are PEP 563 string-deferred regardless of quoting.

**`tests/test_config.py:12` (I001) + `tests/test_config.py:24` (F401):** ran `ruff check tests/test_config.py --fix`. Result: import-block reorganized (one-blank-line gap collapsed) and unused `format_validation_error` import removed. The bonus test at line 227 (`test_format_validation_error_produces_field_path_per_line`) still validates the formatter's wire format via `str(excinfo.value)` after `RoundtableConfig.from_yaml_string` raises ConfigError -- the formatter is called internally by `from_yaml_string` so no direct import is needed.

All 4 fixes verified as ruff-auto-fixable. After: `ruff check` reports `All checks passed!`.

### 6. `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md` -- v0.1.0 section appended

Original 0.0.1 content (6719 bytes / 156 LF / 0 CRLF) preserved verbatim. New section appended (6204 bytes / 148 LF / 0 CRLF / ASCII-only). Final file: 12923 bytes / 304 LF / 0 CRLF.

Structure:
```
# Publishing the 0.0.1 Stub to PyPI                  (line 1, original)
  ## Prerequisites                                   (line 9, original)
  ## Upload command                                  (line 38, original)
  ## Expected output                                 (line 77, original)
  ## Verify the reservation worked                   (line 100, original)
  ## Post-upload follow-ups                          (line 119, original)
  ## What can go wrong                               (line 136, original)
  ## Sanity checklist before running                 (line 148, original)
---                                                  (separator)
# Publishing v0.1.0 (the FIRST FUNCTIONAL release)   (line 160, NEW)
  ## Prerequisites for v0.1.0 upload                 (NEW)
  ## Upload command (3 options)                      (NEW)
  ## Expected output                                 (NEW)
  ## Verify the v0.1.0 reservation worked            (NEW)
  ## Post-upload follow-ups                          (NEW; PKG-06+PKG-01 closure + git tag)
  ## What can go wrong                               (NEW; v0.1.0-specific error table)
  ## Sanity checklist before running v0.1.0 upload   (NEW; 6-item checklist)
```

The exact `twine upload` command the user must run to close PKG-06:
```bash
python -m twine upload dist/ultra_claude-0.1.0*
```

Three options documented (Option A interactive, Option B env-var, Option C `~/.pypirc`); plus the verification step (`pip install ultra-claude==0.1.0` in a fresh venv -> `ultra-claude --version` prints `0.1.0`).

## Atomic Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | (no commit; dist/ artefacts gitignored) | `python -m build` produced dist/ultra_claude-0.1.0.{whl,tar.gz} |
| 2 | `e462b8f` | `fix(09-04): clear pre-existing ruff errors blocking v0.1.0 quality gate` (Rule 3 deviation; merges Task 1's `.gitignore` extension) |
| 3 | `1e4d2f3` | `docs(09-04): append v0.1.0 release section to PUBLISH.md` |

Two commits land code/docs changes. Task 1 produces only artefacts (dist/) that are gitignored per the plan's design (`dist/` is rebuildable from source; PUBLISH.md tells the user to re-run `python -m build` if dist/ is empty).

## Verification Gate Results

All 8 plan-spec verification checks PASS:

| # | Gate | Result |
|---|------|--------|
| 1 | `ls -la dist/ultra_claude-0.1.0*` -- both wheel + sdist exist | PASS (2 files; 40407 + 33618 bytes) |
| 2 | `python -m twine check dist/ultra_claude-0.1.0*` | PASS (both PASSED) |
| 3 | Wheel contents include `ultra_claude/py.typed` AND `ultra_claude/presets/debate.yaml` | PASS |
| 4 | `pytest --cov=src/ultra_claude --cov-report=term-missing` -- TOTAL > 80% | PASS (86/86 in 4.77s; TOTAL 85%) |
| 5 | `ruff check` -- All checks passed | PASS (after Rule 3 cleanup) |
| 6 | `mypy` -- Success: no issues found in 13 source files | PASS |
| 7 | PUBLISH.md has BOTH "Publishing v0.1.0" + "Publishing the 0.0.1 Stub to PyPI" | PASS (1 occurrence each) |
| 8 | No stale 0.0.1 artefacts in dist/ | PASS (0 occurrences) |

Bonus end-to-end gates (Task 2 smoke install in dedicated venv):
- `pip install --no-cache-dir dist/ultra_claude-0.1.0-py3-none-any.whl` in fresh venv -> exit 0
- `ultra-claude --version` -> `ultra-claude, version 0.1.0`
- `ultra-claude run --preset debate --inline "should we add an undo button?" --dry-run` -> 9-turn schedule rendered with Architect/Critic/Implementer on claude/gemini/codex; exit 0
- `python -c "import ultra_claude; assert ultra_claude.__version__ == '0.1.0'"` -> PASS
- Smoke venv cleanup -> `rm -rf .smoke-venv-09` -- no leftover

## Threat Register Mitigations Applied

| Threat ID | Mitigation Status |
|-----------|-------------------|
| T-09-15 (Tampering, dist/*.whl content drift) | MITIGATED -- twine check PASSED for both artefacts; wheel content assertion confirmed `ultra_claude/py.typed` (PEP 561) + `ultra_claude/presets/debate.yaml` (preset) + 4 source files ALL present |
| T-09-16 (Information Disclosure, smoke venv cred caching) | MITIGATED -- venv created with `python -m venv` (no inherited credentials); `pip install --no-cache-dir` flag prevents pip's HTTP cache; venv `rm -rf`'d after test |
| T-09-17 (Tampering, PUBLISH.md instruction injection) | ACCEPTED (per plan) -- file is committed/reviewable; the user trusts the source-controlled file; this commit is auditable as a regular diff |
| T-09-18 (DoS, smoke venv install hanging) | MITIGATED -- subprocess.run timeouts (180s pip / 15s --version / 15s --dry-run); after timeout, venv force-removed via shutil.rmtree(ignore_errors=True) |
| T-09-19 (Repudiation, wrong file uploaded) | MITIGATED -- PUBLISH.md upload command targets the literal glob `dist/ultra_claude-0.1.0*` (not `dist/*`); Task 1's `rm -rf dist/` cleanup also prevents stale 0.0.1 artefacts in dist/ |
| T-09-20 (EoP, malicious typo-squat dependency) | MITIGATED -- pyproject.toml pins `click>=8.3.3 / pydantic>=2.13.3 / pyyaml>=6.0.3`; pip install resolved exactly these names + 5 transitive deps from PyPI; --no-cache-dir does not affect names; names come from pyproject.toml not user input |

## Deferred Issues

**None.** The 4 pre-existing Phase 2 ruff errors (deferred since 07-01) were CLEARED in this plan as a Rule 3 deviation (see "Deviations from Plan" below).

The two lowest-coverage modules (registry.py 36%, adapters/base.py 73%) have uncovered branches but the project-wide TOTAL exceeds the 80% gate by 5 percentage points. Further coverage improvements are deferred to post-v0.1.0 work.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Cleared 4 pre-existing Phase 2 ruff errors blocking the v0.1.0 quality gate**
- **Found during:** Task 2 Step 7 (`ruff check`)
- **Issue:** 4 errors reported -- RUF022 + UP037 in `src/ultra_claude/config.py`; I001 + F401 in `tests/test_config.py`. All 4 documented in `.planning/phases/07-gemini-codex-adapters/deferred-items.md` since 07-01 as pre-existing Phase 2 violations explicitly nominated for "a future cleanup plan (likely Phase 9 quality-bar pass) or a dedicated fixup commit."
- **Why blocking for v0.1.0:** The 09-04 must_have explicitly states: "ruff check passes with zero errors project-wide (TST-06)". Leaving the 4 errors unfixed would ship v0.1.0 with a broken project-wide quality gate. The deferred-items.md note specifically blesses Phase 9 as the cleanup destination -- this plan IS that cleanup.
- **Fix:**
  - `config.py:38` (RUF022): added `# noqa: RUF022` with rationale comment matching the convention in `stop_conditions.py:34`, `adapters/__init__.py:34`, `exceptions.py:80`, `cli.py:52`
  - `config.py:110` (UP037): removed quotes from `RoundtableConfig` return annotation (`from __future__ import annotations` is active at line 27)
  - `tests/test_config.py:12` (I001): ran `ruff check --fix` -- one-blank-line reorganization across 3 import groups
  - `tests/test_config.py:24` (F401): ran `ruff check --fix` -- removed unused `format_validation_error` import (the bonus test at line 227 calls it indirectly via `RoundtableConfig.from_yaml_string` -> `format_validation_error` -> ConfigError message)
- **Files modified:** `src/ultra_claude/config.py`, `tests/test_config.py`
- **Commit:** `e462b8f` (`fix(09-04): clear pre-existing ruff errors blocking v0.1.0 quality gate`)
- **Verification post-fix:** `ruff check` -> "All checks passed!"; `mypy` -> "Success: no issues found in 13 source files"; `pytest --cov` -> 86/86 PASS, TOTAL 85% (no regression -- the test_config.py I001+F401 fix did not change the bonus test's behaviour); `ultra-claude --version` -> `0.1.0` (no source-behaviour change)

**2. [Rule 3 - Blocking] Extended `.gitignore` with `.smoke-venv-*/` pattern**
- **Found during:** Task 2 Step 1 (smoke venv creation)
- **Issue:** The plan creates `.smoke-venv-09` (per the executor prompt's success_criteria) and `.smoke-venv-0.1.0-verify` (per the plan's automated verify script). Phase 1's `.gitignore` only covered the literal `.smoke-venv/` -- neither variant was ignored, risking accidentally committing a 100MB+ venv tree if cleanup failed.
- **Fix:** added `.smoke-venv-*/` glob pattern below `.smoke-venv/` on line 56 of `.gitignore`. Verified via `git check-ignore` that `.smoke-venv-09-test/` matches the new pattern; `git status --short` against the temp test dir produces zero output.
- **Why blocking:** without this change, the smoke-venv variants would surface in `git status` during execution and risk being staged with `git add -A` (though the plan's commit guidance says NEVER to use `-A`).
- **Files modified:** `.gitignore`
- **Commit:** `e462b8f` (folded into Task 2 commit)

### Python 3.11 f-string Limitation (incidental)

While writing the helper script `_append_publish.py`, hit a Python 3.11 f-string limitation: `f"... {expr.count(b'\\n')} ..."` raises `SyntaxError: f-string expression part cannot include a backslash`. This was previously documented in plan 03-01's deviations.

**Workaround:** extracted the count to a separate variable before the f-string:
```python
lf_count = verify.count(b"\n")
print(f"PUBLISH.md OK: {len(verify)} bytes / 0 CRLF / {lf_count} LF")
```

The deviation never reached committed code; only the AUTHORING workflow was affected. The helper `_append_publish.py` was deleted post-run.

## Authentication Gates

**None.** The user's `python -m twine upload` IS an auth gate (PyPI credentials needed) but it is OUT of this plan's scope -- the runbook is documented in PUBLISH.md and the user runs it manually after this plan completes. This is the design pattern Phase 1 used for the 0.0.1 stub upload (also user-action; never executed; PKG-05 still pending).

## What Unblocks

- **User action:** `python -m twine upload dist/ultra_claude-0.1.0*` -- this single command closes PKG-06 (v0.1.0 PyPI publish) AND PKG-01 (`pip install ultra-claude` from a fresh machine works) AND, transitively, supersedes Phase 1's PKG-05 (the never-uploaded 0.0.1 stub is no longer needed once 0.1.0 owns the name).
- **After upload + user-confirmed verification step in PUBLISH.md:** mark PKG-06, PKG-01 complete in `.planning/REQUIREMENTS.md`; tag `v0.1.0` in git; close Phase 9 fully in STATE.md / ROADMAP.md.

## Twine Upload Command (Staged for User)

```bash
# From the repo root, with .smoke-venv-09 and dist/ already produced:
python -m twine upload dist/ultra_claude-0.1.0*

# Then verify from any other shell:
python -m venv .verify-venv
source .verify-venv/Scripts/activate     # Windows
# or: source .verify-venv/bin/activate   # POSIX
pip install --no-cache-dir ultra-claude==0.1.0
ultra-claude --version                    # expect: ultra-claude, version 0.1.0
ultra-claude run --preset debate --inline "test" --dry-run  # expect: 9-turn schedule
deactivate
rm -rf .verify-venv
```

PUBLISH.md contains the full runbook including PyPI account setup, API token generation, three upload methods (interactive / env-var / `~/.pypirc`), error table, and 6-item sanity checklist.

## Self-Check: PASSED

Created files (verified to exist on disk):
- FOUND: `dist/ultra_claude-0.1.0-py3-none-any.whl` (40407 bytes)
- FOUND: `dist/ultra_claude-0.1.0.tar.gz` (33618 bytes)

Modified files (verified to exist + diff applied):
- FOUND: `.gitignore` (added `.smoke-venv-*/` line 56)
- FOUND: `src/ultra_claude/config.py` (RUF022 noqa + UP037 quote removal)
- FOUND: `tests/test_config.py` (I001 import reorg + F401 unused import removal)
- FOUND: `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md` (12923 bytes; v0.1.0 section appended)

Commits (verified to exist in git log):
- FOUND: `e462b8f` (Task 2 ruff cleanup + .gitignore)
- FOUND: `1e4d2f3` (Task 3 PUBLISH.md update)
