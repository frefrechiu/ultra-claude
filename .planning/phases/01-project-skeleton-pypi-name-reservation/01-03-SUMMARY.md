---
phase: 01-project-skeleton-pypi-name-reservation
plan: 03
subsystem: infra
tags: [packaging, build, sdist, wheel, hatchling, pypi-stub, twine, clean-venv-smoke-test, runbook, checkpoint-human-action]

# Dependency graph
requires:
  - "01-01 (LICENSE, README.md, CHANGELOG.md, src/ultra_claude/__init__.py)"
  - "01-02 (pyproject.toml with hatchling backend + dynamic version + pinned deps)"
provides:
  - "dist/ultra_claude-0.0.1.tar.gz (sdist artifact for PyPI upload)"
  - "dist/ultra_claude-0.0.1-py3-none-any.whl (wheel artifact for PyPI upload)"
  - "Empirical proof: __version__ == importlib.metadata.version('ultra-claude') == '0.0.1' in a clean venv"
  - "PUBLISH.md operator runbook for the manual twine upload (the user-action half of PKG-05)"
  - ".gitignore amendment: .smoke-venv/ now ignored (defensive — prevents stray-venv leak on abnormal exit)"
affects: [02-deps-bootstrap, 04-subprocess-mixin, 09-release]

# Tech tracking
tech-stack:
  added:
    - "build 1.5.0 (Python build frontend; bootstrapped into the host Python at task 1, NOT into project deps — listed in [project.optional-dependencies.dev] for in-venv use later)"
    - "twine 6.2.0 (PyPI upload tool; same bootstrap pattern)"
  patterns:
    - "python -m build runs in an isolated env; it pulls hatchling>=1.29 itself, no global hatchling install needed"
    - "Clean-venv smoke test invocation pattern: .smoke-venv/Scripts/python.exe -m pip install -e \".[dev]\" — direct interpreter calls, no shell activation, Windows-friendly"
    - "Triple-alignment proof: literal __version__ in __init__.py == [project] version resolved by hatchling == importlib.metadata.version('ultra-claude') after editable install"
    - "Deferred-user-action checkpoint pattern: build/verify autonomously, document command in PUBLISH.md, stage for user to run with their credentials"

key-files:
  created:
    - "dist/ultra_claude-0.0.1.tar.gz (gitignored, NOT committed; lives only on the build host until twine upload pushes it to PyPI)"
    - "dist/ultra_claude-0.0.1-py3-none-any.whl (gitignored, NOT committed)"
    - ".planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md (committed in e96ccb6)"
  modified:
    - ".gitignore (added .smoke-venv/ entry; committed in 3e31832)"

key-decisions:
  - "build + twine bootstrapped into the HOST Python (not the project venv) for plan 01-03 only — they're declared in [project.optional-dependencies.dev] but the autonomous build runs before any project venv exists. python -m build supplies its own isolated env for hatchling, so the host install of `build` is the only pre-existing requirement."
  - "Smoke-venv created and torn down in-task; not persisted. Direct interpreter invocation (.smoke-venv/Scripts/python.exe ...) avoided the source/activate ergonomics issue across Windows shells."
  - ".smoke-venv/ added to .gitignore as a Rule 3 deviation BEFORE creating the venv. Defensive insurance — even though the test always deletes the venv at task end, an abnormal exit between create and rm would leak an untracked tree. Cheap to add, no downside."
  - "Task 4 (twine upload checkpoint) deferred to user action without blocking the plan. The autonomous-completable deliverables (build, verify, runbook) all exist; the user runs `python -m twine upload dist/ultra_claude-0.0.1*` independently using PUBLISH.md. SUMMARY records the deferral; STATE/ROADMAP advance so subsequent phases are unblocked. PKG-05 reservation reopens only when the user reports back 'uploaded'."

patterns-established:
  - "When a plan's deliverable is artifact-only (gitignored output) + a runbook (committed), the runbook's existence + the local artifacts' verifiable state IS the autonomous completion — no per-task commit is needed for the artifact-build task."
  - "When a checkpoint:human-action gates only credential-bearing operations, autonomous mode bypasses by documenting the exact command + prerequisites in a runbook .md and continuing. The phase verifier will check for the artifact + runbook + (eventually) the upload result."

requirements-completed: []
requirements-deferred-to-user-action:
  - "PKG-05 (PyPI name reservation) — Tasks 1-3 fully complete; Task 4 (twine upload) deferred to user. Reopens once user reports `pip install ultra-claude==0.0.1` from PyPI succeeds."

# Metrics
duration: ~5min
completed: 2026-05-02
---

# Phase 1 Plan 3: Build Artifacts + Clean-Venv Smoke Test + PyPI Upload Prep Summary

**Built `dist/ultra_claude-0.0.1.tar.gz` and `dist/ultra_claude-0.0.1-py3-none-any.whl` via `python -m build`, validated both with `twine check`, empirically proved `__version__ == importlib.metadata.version('ultra-claude') == "0.0.1"` in a fresh venv with `pip install -e ".[dev]"`, and authored `PUBLISH.md` operator runbook so the user can execute the manual `twine upload` step that reserves the PyPI name. Task 4's user-action checkpoint is staged: artifacts + runbook are ready; PKG-05 closes once the user runs the upload.**

## Performance

- **Duration:** ~5 min 18 sec
- **Started:** 2026-05-02T02:00:57Z
- **Completed:** 2026-05-02T02:06:15Z
- **Tasks autonomously completed:** 3 of 4 (build, smoke test, runbook)
- **Tasks deferred to user action:** 1 of 4 (twine upload — needs user PyPI credentials)
- **Files modified:** 2 committed (`.gitignore`, `PUBLISH.md`) + 2 produced-but-gitignored (`dist/*.tar.gz`, `dist/*.whl`)

## Accomplishments

### Task 1 — Build sdist + wheel via `python -m build`

- Bootstrapped `build 1.5.0` and `twine 6.2.0` into the host Python (`python -m pip install --upgrade build twine`). They're already declared in `[project.optional-dependencies.dev]` for in-venv use, but the autonomous build needed them at the host level since the project venv doesn't exist yet at this point.
- Ran `python -m build` from repo root. Output:
  - `Creating isolated environment: venv+pip...`
  - `Installing packages in isolated environment: hatchling>=1.29`
  - `Successfully built ultra_claude-0.0.1.tar.gz and ultra_claude-0.0.1-py3-none-any.whl`
- `python -m twine check dist/*` reported `PASSED` for both files.
- Wheel namelist contains `ultra_claude/__init__.py` + `ultra_claude-0.0.1.dist-info/METADATA` (plus `WHEEL`, `licenses/LICENSE`, `RECORD`).
- Sdist top-level (after stripping the `ultra_claude-0.0.1/` prefix) contains: `CHANGELOG.md`, `src/ultra_claude/__init__.py`, `.gitignore`, `LICENSE`, `README.md`, `pyproject.toml`, `PKG-INFO`. All five required files (LICENSE, README.md, CHANGELOG.md, pyproject.toml, src/ultra_claude/__init__.py) present.
- Both filenames carry exactly `0.0.1` — proves hatchling's `[tool.hatch.version]` regex correctly read `__version__ = "0.0.1"` from `src/ultra_claude/__init__.py`.

### Task 2 — Clean-venv smoke test

- Created `.smoke-venv/` from system Python via `python -m venv .smoke-venv` — fresh interpreter, only baseline pip/setuptools.
- Upgraded pip in venv: `24.0` → `26.1`.
- Ran `.smoke-venv/Scripts/python.exe -m pip install -e ".[dev]"`. Resolved + installed (relevant pins italicized for verification):
  - Runtime: **click 8.3.3** (>=8.3.3 ✓), **pydantic 2.13.3** (>=2.13.3 ✓), **pyyaml 6.0.3** (>=6.0.3 ✓)
  - Dev: **ruff 0.15.12** (>=0.13 ✓), **mypy 1.20.2** (>=1.18 ✓), **pytest 9.0.3** (>=8.4 ✓), **pytest-mock 3.15.1** (>=3.15 ✓), **pytest-cov 7.1.0** (>=6.0 ✓), **pytest-subprocess 1.5.4** (>=1.5 ✓), **types-pyyaml 6.0.12.20260408**, **build 1.5.0** (>=1.2 ✓), **twine 6.2.0** (>=5.1 ✓)
  - Project: **ultra-claude 0.0.1** (editable install pointing at `src/ultra_claude/`)
- Verified `__version__`:
  ```text
  $ .smoke-venv/Scripts/python.exe -c "import ultra_claude; print(ultra_claude.__version__)"
  0.0.1
  ```
- Verified triple alignment in one assertion:
  ```text
  triple alignment OK: __version__ == 0.0.1 == metadata.version == 0.0.1
  ```
  (i.e., `ultra_claude.__version__` literal in code == `importlib.metadata.version('ultra-claude')` resolved by hatchling at editable-install time == the string `"0.0.1"`)
- Verified runtime + key dev imports: `import click, pydantic, yaml, pytest_subprocess` all succeeded.
- Verified dev tools callable:
  - `ruff --version` → `ruff 0.15.12`
  - `mypy --version` → `mypy 1.20.2 (compiled: yes)`
  - `pytest --version` → `pytest 9.0.3`
- Tore down: `rm -rf .smoke-venv` succeeded; `test ! -d .smoke-venv` confirmed deletion; `git status --short` shows no new untracked entries from the test (only the unrelated, pre-existing `M .planning/config.json` and `?? zen_mcp_architecture.svg` remain).

### Task 3 — PUBLISH.md operator runbook

- Created `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md` (~6 KB, 156 lines, LF-only, committed in `e96ccb6`).
- Sections: Status banner (REQUIRES USER ACTION), Prerequisites (5-step), Upload command (3 options: interactive / env-var / `.pypirc`), Expected output, Verify the reservation worked, Post-upload follow-ups, What can go wrong (failure-mode table covering 403/400/InvalidDistribution/Bad credentials/README rendering), Sanity checklist (5-item).
- Required substring grep counts (Task 3 acceptance criteria):
  - `twine upload`: 3 occurrences ✓
  - `REQUIRES USER ACTION`: 1 occurrence ✓
  - `TWINE_USERNAME`: 2 occurrences ✓
  - `__token__`: 4 occurrences ✓
  - `ultra-claude==0.0.1`: 3 occurrences ✓
  - `Sanity checklist`: 1 occurrence ✓
  - `403 Forbidden`: 1 occurrence ✓

### Task 4 — twine upload checkpoint (DEFERRED TO USER)

- Per the orchestrator's instruction in this plan's invocation: the autonomous-completable artifacts (built sdist + wheel, validated, smoke-tested) and the runbook (PUBLISH.md) ARE the deliverable for autonomous mode. The user runs `python -m twine upload dist/ultra_claude-0.0.1*` separately using their PyPI API token.
- The user's report-back vocabulary ("uploaded" / "name-taken: <fallback>" / "deferred: <reason>") is preserved in PUBLISH.md and in the original plan file at `.planning/phases/01-project-skeleton-pypi-name-reservation/01-03-PLAN.md` Task 4.
- PKG-05 requirement remains incomplete in REQUIREMENTS.md tracking until the user reports "uploaded" and `pip install ultra-claude==0.0.1` from PyPI returns the stub successfully. (See "User Setup Required" section below.)

## Task Commits

Per-task atomic commits:

1. **Task 1 (build sdist + wheel + twine check):** No commit. The deliverables are gitignored artifacts in `dist/`. Successful build and twine-check passes recorded here in SUMMARY; artifacts persist on the build host until `twine upload` consumes them.
2. **Task 2 (clean-venv smoke test):** No commit. Pure verification task with no persistent file output (the `.smoke-venv/` is created and deleted in-task).
3. **Task 2 prep (defensive .gitignore amendment):** **`3e31832`** — `chore(01-03): add .smoke-venv/ to .gitignore`. Rule 3 deviation (see "Deviations" below).
4. **Task 3 (PUBLISH.md runbook):** **`e96ccb6`** — `docs(01-03): add PUBLISH.md operator runbook for manual twine upload`.
5. **Task 4 (twine upload):** Deferred to user. No commit possible from Claude.

**Plan metadata commit:** pending after this SUMMARY is written.

## Files Created/Modified

| Path | Status | Commit | Notes |
|------|--------|--------|-------|
| `dist/ultra_claude-0.0.1.tar.gz` | Created | (gitignored) | 3,406 bytes. Sdist; consumed by `twine upload`. |
| `dist/ultra_claude-0.0.1-py3-none-any.whl` | Created | (gitignored) | 2,870 bytes. Wheel; consumed by `twine upload`. |
| `.gitignore` | Modified | `3e31832` | Added `.smoke-venv/` entry under "Environments" section. |
| `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md` | Created | `e96ccb6` | Operator runbook for the manual twine upload step. |

`dist/ultra_claude-0.0.1*` are gitignored per `dist/` rule already in `.gitignore` (landed in plan 01-01). They MUST NOT be committed — they're release artifacts that PyPI hosts authoritatively.

## Build Backend + Dynamic Version Wiring (End-to-End Proof)

Plan 01-01 placed `__version__ = "0.0.1"` in `src/ultra_claude/__init__.py`. Plan 01-02 wired `[tool.hatch.version] path = "src/ultra_claude/__init__.py"` and `dynamic = ["version"]` in `pyproject.toml`. Plan 01-03 (this plan) verified the chain operates end-to-end:

```text
src/ultra_claude/__init__.py:    __version__ = "0.0.1"   <-- single source of truth
                |
                v  hatchling [tool.hatch.version] regex
                |
pyproject.toml:                  dynamic = ["version"]   <-- pyproject says "ask hatchling"
                |
                v  python -m build
                |
dist filenames:                  ultra_claude-0.0.1.tar.gz
                                 ultra_claude-0.0.1-py3-none-any.whl
                |
                v  pip install -e ".[dev]"
                |
importlib.metadata.version('ultra-claude'): '0.0.1'      <-- editable-install reads metadata
                |
                v  import ultra_claude; ultra_claude.__version__
                |
runtime literal:                 '0.0.1'                  <-- back to the source

Triple equality verified empirically:
ultra_claude.__version__ == importlib.metadata.version('ultra-claude') == "0.0.1"
```

This proves ROADMAP.md success criterion 3 ("`__version__` prints `0.0.1`, equals `[project] version`") and success criterion 4 ("`pip install -e \".[dev]\"` succeeds in a clean virtualenv") simultaneously.

## Decisions Made

All decisions were pre-locked in `01-CONTEXT.md`, `CLAUDE.md`, and the plan's `<action>` blocks. The only judgment calls during execution:

1. **Bootstrap `build` and `twine` into the host Python before the smoke-venv exists.** The plan's Step 1 explicitly anticipates this. The host Python now carries `build 1.5.0` and `twine 6.2.0` outside any project venv. This is the documented bootstrap path and is not a deviation.
2. **Add `.smoke-venv/` to `.gitignore` defensively.** Documented as Rule 3 deviation below.
3. **Treat Task 4 as deferred-to-user rather than abort-and-checkpoint.** Per the orchestrator's instruction in the plan invocation. Documented above and in the section below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking risk] Added `.smoke-venv/` to `.gitignore`**

- **Found during:** Task 2 prep
- **Issue:** `.smoke-venv` is NOT matched by any existing `.gitignore` rule (the existing `.venv` and `venv/` entries don't pattern-match it). The plan's intent is "always delete after the test", but an abnormal exit (interrupted task, kernel oops, hard reboot) between `python -m venv .smoke-venv` and `rm -rf .smoke-venv` would leave a thousands-of-files untracked tree polluting `git status` and risking accidental staging.
- **Fix:** Added `.smoke-venv/` line to `.gitignore` under the "Environments" section, between `.venv` and `env/`.
- **Files modified:** `.gitignore`
- **Commit:** `3e31832`

This is the canonical Rule 3 case: a small defensive change required to safely complete the current task without leaking state. No user permission needed.

### User-Action Deferral (NOT a deviation — orchestrator instruction)

**Task 4 (twine upload checkpoint) deferred to the user without blocking the plan.**

- **Why:** PyPI uploads require a credential (the user's API token starting with `pypi-...`) that Claude does not have access to. The plan originally specifies `type="checkpoint:human-action"` which would normally STOP execution and return a `## CHECKPOINT REACHED` message. The orchestrator's instruction in this plan's invocation explicitly redirects: "Do NOT abort execution. The build artifacts existing + documented upload command IS the deliverable for autonomous mode. Return `## EXECUTION COMPLETE` (not CHECKPOINT REACHED) since the autonomous-completable parts are done."
- **What's complete:** Tasks 1, 2, 3 — the artifacts exist on disk, the smoke test passed, PUBLISH.md is committed. Everything Claude can do has been done.
- **What's pending the user:** The user reads `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md`, generates a PyPI API token, and runs one of three documented `twine upload` variants. Expected user time: ~5 minutes including the account/2FA setup if not yet done.
- **How PKG-05 closes:** Once the user runs the upload and `pip install ultra-claude==0.0.1` from PyPI returns the stub successfully, PKG-05 is satisfied. The next phase's verifier (or a manual check) will confirm. Until then, PKG-05 stays in `requirements-deferred-to-user-action`.

This is documented up front in the plan's frontmatter (`autonomous: false`, `user_setup` block) so it's not a surprise — it's the expected path for credential-bearing checkpoints in yolo/autonomous mode.

## Authentication Gates

None encountered. The PyPI token requirement is documented in the plan up front and handled via the deferred-user-action pattern above, NOT as a runtime auth-gate stop. No `Not authenticated` / `401` / `403` errors hit during autonomous execution because no upload was attempted.

## Issues Encountered

**Git autocrlf warnings (informational only).** Same as plans 01-01 and 01-02 — Git emitted `LF will be replaced by CRLF the next time Git touches it` on `git add` for both `.gitignore` (commit `3e31832`) and `PUBLISH.md` (commit `e96ccb6`). The on-disk files are LF-only at the byte level (verified by the `Write` tool's deterministic newline behavior); Git stores LF in the index/repo. This is the user's `core.autocrlf` setting on Windows converting on checkout and does not affect repository content. No action needed.

## User Setup Required

**Single deferred action:** Run `python -m twine upload dist/ultra_claude-0.0.1*` per `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md`.

Prerequisites the user fulfills (all documented in PUBLISH.md):

1. PyPI account at <https://pypi.org/account/register/> if not already registered.
2. 2FA enabled at <https://pypi.org/manage/account/two-factor/>.
3. API token generated at <https://pypi.org/manage/account/token/> (scope: "Entire account" for the first upload of a new project).
4. Run `python -m twine upload dist/ultra_claude-0.0.1*` from the repo root, supplying `__token__` as username and the `pypi-...` token as password (or use env vars / `.pypirc`).
5. Verify by running `pip install ultra-claude==0.0.1` from a fresh shell — should print `0.0.1` after `python -c "import ultra_claude; print(ultra_claude.__version__)"`.

Once the user reports "uploaded" (or runs the verify step successfully), PKG-05 is satisfied and Phase 1's ROADMAP success criterion 1 closes.

## Self-Check: PASSED

Verified after writing SUMMARY.md:

- `dist/ultra_claude-0.0.1.tar.gz` exists ✓ (FOUND on disk; gitignored, NOT committed — correct)
- `dist/ultra_claude-0.0.1-py3-none-any.whl` exists ✓ (FOUND on disk; gitignored, NOT committed — correct)
- `python -m twine check dist/*` reports `PASSED` for both ✓ (re-run before SUMMARY)
- `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md` exists ✓ (FOUND on disk, present in commit `e96ccb6`)
- `.gitignore` contains `.smoke-venv/` line ✓ (FOUND, present in commit `3e31832`)
- `.smoke-venv/` does NOT exist on disk ✓ (deleted at Task 2 end)
- Commit `3e31832` exists in git log ✓ (`git log --oneline | grep 3e31832` returns 1 match)
- Commit `e96ccb6` exists in git log ✓ (`git log --oneline | grep e96ccb6` returns 1 match)
- `git status --short` shows no plan-related untracked entries ✓ (only the unrelated `M .planning/config.json` and `?? zen_mcp_architecture.svg` remain — pre-existing)

## Next Phase Readiness

**Phase 1 is autonomously complete.** All four ROADMAP success criteria (PyPI install resolves to author-owned stub, pyproject + LICENSE + .gitignore at HEAD, `__version__ == "0.0.1"`, `pip install -e ".[dev]"` succeeds in clean venv) are either satisfied (criteria 2, 3, 4) or staged-for-user-action (criterion 1, gated on PUBLISH.md execution).

**Phase 2 (deps-bootstrap) is unblocked** by everything in this plan. The smoke test in Task 2 IS the proof that Phase 2 will inherit a working `pip install -e ".[dev]"` foundation.

**Phase 1 verifier should**:
1. Confirm `dist/ultra_claude-0.0.1*` artifacts exist on the build host (this plan's deliverable).
2. Confirm `PUBLISH.md` exists and contains the `twine upload` command.
3. Confirm `.smoke-venv/` is NOT present in the working tree.
4. Optionally re-run a clean-venv smoke install to re-confirm the `__version__` triple alignment.
5. Check whether the user has reported "uploaded" — if yes, run `pip install ultra-claude==0.0.1` from a fresh shell as the PKG-05 final closure check; if no, mark PKG-05 as "deferred to user action" and continue.

---
*Phase: 01-project-skeleton-pypi-name-reservation*
*Completed (autonomous portion): 2026-05-02*
*Pending user action: `twine upload dist/ultra_claude-0.0.1*` per PUBLISH.md*
