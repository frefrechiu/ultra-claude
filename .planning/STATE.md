---
gsd_state_version: 1.0
milestone: v0.1.0
milestone_name: Release
status: phase-1-autonomous-complete-pending-user-twine-upload
last_updated: "2026-05-02T02:06:15Z"
progress:
  total_phases: 9
  completed_phases: 0
  total_plans: 3
  completed_plans: 3
  percent: 33
---

# State: ultra-claude

**Last Updated:** 2026-05-02

## Project Reference

**Core Value:** A user can run `ultra-claude run task.md` and get three CLI agents debating their problem in a transcript file — using only their existing CLI logins, no API keys.

**Current Focus:** Phase 1 autonomously COMPLETE — pending user `twine upload` per `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md` (closes PKG-05). Phase 2 (Config Schema & YAML Loader) is unblocked from a foundation standpoint.

## Current Position

Phase: 01-project-skeleton-pypi-name-reservation — AUTONOMOUS EXECUTION COMPLETE; PKG-05 deferred to user
Plan: 3/3 complete autonomously
| Field | Value |
|-------|-------|
| Phase | 1 (Project Skeleton & PyPI Name Reservation) |
| Plan | 01-01 COMPLETE; 01-02 COMPLETE; 01-03 COMPLETE (autonomous portion) |
| Status | Buildable + verified-installable project: dist artifacts produced, clean-venv smoke test passed (__version__ triple alignment proven at 0.0.1), PUBLISH.md runbook ready for user-side twine upload |
| Progress | 0/9 phases complete; 3/3 plans in Phase 1 (PKG-05 user-action gates phase closure) |

```
[###                 ] 3/9 plans (33%) — Phase 1 autonomous portion done
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases planned | 9 |
| Phases complete | 0 (Phase 1 awaiting user twine upload to fully close PKG-05) |
| Plans complete | 3 |
| v1 requirements mapped | 58/58 |
| Requirements completed | 4 (PKG-02, PKG-03, PKG-04, PKG-07) |
| Requirements deferred-to-user | 1 (PKG-05 — twine upload, runbook ready) |
| Coverage | 100% |
| Plan 01-01 duration | ~2 min (2026-05-02T01:48:41Z → 2026-05-02T01:50:25Z) |
| Plan 01-02 duration | ~1.5 min (2026-05-02T01:54:42Z → 2026-05-02T01:56:12Z) |
| Plan 01-03 duration | ~5 min (2026-05-02T02:00:57Z → 2026-05-02T02:06:15Z) — autonomous portion |

## Accumulated Context

### Key Decisions Locked in by Roadmap

1. **PyPI name `ultra-claude` reserved as `0.0.1` stub in Phase 1** — squat protection per Pitfall #5; verified available 2026-05-02.
2. **Adapter contract is a `typing.Protocol`, not an ABC** — third parties don't subclass; internal `_SubprocessAdapterMixin` absorbs duplication across the three bundled adapters.
3. **Subprocess invocation contract locked in Phase 4** — stdin-piped prompt (NOT `-p <prompt>` argv), `text=True`, `encoding="utf-8"`, `errors="replace"`, mandatory timeout, list-form argv, `shell=False`. Mitigates Pitfalls #1, #2, #3 simultaneously.
4. **Empty-stdout defense built into the mixin from Phase 4** — `returncode == 0` AND empty stdout raises `AdapterError`, defending against the active `codex exec` 0.124.0+ TTY bug (Pitfall #2) before `CodexAdapter` is even written.
5. **Cross-platform process-tree kill in Phase 4** — POSIX `os.killpg` + Windows `taskkill /T /F`; half-measures (timeout but no tree kill) leave orphaned children burning subscription quota.
6. **Stop-condition keyword matching uses anchored multiline regex + unanimity-window (N=2, M=2)** — naive substring matching causes false-positive consensus (sycophancy, Pitfall #4); anchored regex `^## Decision\nAGREED\s*$` requires structural agreement.
7. **Orchestrator is a single function, not a class** — promote to class only when v3 adds parallel speakers; YAGNI applied.
8. **Transcript is dual-format**: canonical markdown (re-promptable) + JSONL sidecar (parseable for v2 resume). Markdown uses non-markdown HTML-comment sentinels for turn delimiters to avoid markdown-in-markdown corruption (Pitfall #8).
9. **Continue-on-error by default** — adapter failures are logged + recorded as placeholder turns; run continues unless `abort_on_error: true` is set. A timed-out Codex shouldn't kill a 30-minute roundtable.
10. **`pip install` from PyPI is the v0.1.0 success criterion** — manual `python -m build` + `twine upload` for v1; auto-publish via Trusted Publishing deferred to v2.

### Open Todos (Phase-1 closure)

- [ ] **User action**: Run `python -m twine upload dist/ultra_claude-0.0.1*` per `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md` to close PKG-05. Artifacts and runbook are ready on the build host.
- [ ] After user reports "uploaded": run `pip install ultra-claude==0.0.1` from a fresh shell to confirm PyPI returns the stub; then mark PKG-05 complete in REQUIREMENTS.md.
- [ ] Verify each CLI's exact argv shape empirically at Phase 4 (Claude) and Phase 7 (Gemini, Codex) implementation time — vendor flag conventions may have drifted since research

### In-Phase-1 Progress

- [x] **Plan 01-01 (repository skeleton):** LICENSE (MIT, Freddy Chiu 2026), .gitignore, README.md stub with trademark disclaimer, CHANGELOG.md (Keep-a-Changelog), src/ultra_claude/__init__.py with `__version__ = "0.0.1"`. Commits: `562d05e`, `2b15b36`. Requirements: PKG-03, PKG-04, PKG-07.
- [x] **Plan 01-02 (pyproject.toml + tool configs):** PEP 621 metadata + hatchling >= 1.29 backend, dynamic version via `[tool.hatch.version] path = "src/ultra_claude/__init__.py"`, runtime deps pinned (click >= 8.3.3, pydantic >= 2.13.3, pyyaml >= 6.0.3), dev deps pinned (ruff >= 0.13, mypy >= 1.18, pytest >= 8.4 + auxiliaries), `[tool.hatch.build.targets.wheel] packages = ["src/ultra_claude"]` for src layout, ruff/mypy/pytest tool tables. NO `[project.scripts]` (CLI deferred to Phase 8). Commit: `b9bf3c5`. Requirements: PKG-02, PKG-07 (fully complete).
- [x] **Plan 01-03 (build + smoke test + PUBLISH.md):** Built `dist/ultra_claude-0.0.1.tar.gz` and `dist/ultra_claude-0.0.1-py3-none-any.whl` via `python -m build`; both pass `twine check`. Clean-venv smoke test verified `__version__ == importlib.metadata.version('ultra-claude') == "0.0.1"` (triple alignment) with `pip install -e ".[dev]"` succeeding in `.smoke-venv` (resolved click 8.3.3, pydantic 2.13.3, pyyaml 6.0.3, ruff 0.15.12, mypy 1.20.2, pytest 9.0.3, all dev tools callable). PUBLISH.md operator runbook authored (`e96ccb6`); `.smoke-venv/` added to .gitignore as defensive Rule 3 deviation (`3e31832`). Task 4 (twine upload) deferred to user action per orchestrator instruction. Commits: `3e31832`, `e96ccb6`. Requirements: PKG-05 staged-but-pending-user-action.

### Active Blockers

None for autonomous execution. Phase 1 final closure (PKG-05) gates on a one-step user action: running `twine upload`. Subsequent phases (2+) proceed independently of PyPI publish state — they consume the local pyproject.toml + src/ultra_claude/, both of which are committed.

### Research Flags Carried Forward

| Phase | Verification Required at Plan Time |
|-------|-----------------------------------|
| Phase 4 | `claude -p` exact current argv shape and stdin-acceptance behaviour (verify empirically) |
| Phase 7 | `gemini -p` non-interactive flag (issue #19774); `codex exec` `--quiet`/stdin support |
| Phase 8 | Auth state file paths (`~/.claude/auth.json` etc.) per platform for `doctor` subcommand |
| Phase 9 | Windows GitHub Actions runner config for subprocess tests; PyPI Trusted Publishing setup if pulled forward |

## Session Continuity

**Last action:** Executed Phase 1 plan 01-03 (build + smoke test + PUBLISH.md). `python -m build` produced `dist/ultra_claude-0.0.1.tar.gz` and `dist/ultra_claude-0.0.1-py3-none-any.whl`; both passed `twine check`. Clean-venv smoke test created/destroyed `.smoke-venv` and proved `__version__ == importlib.metadata.version('ultra-claude') == "0.0.1"` triple alignment after `pip install -e ".[dev]"`. PUBLISH.md operator runbook authored at `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md`. Two atomic commits: `3e31832` (defensive `.gitignore` add of `.smoke-venv/`, Rule 3 deviation) and `e96ccb6` (PUBLISH.md). Task 4 (twine upload) deferred to user per orchestrator instruction. SUMMARY at `.planning/phases/01-project-skeleton-pypi-name-reservation/01-03-SUMMARY.md`.

**Next action:** USER runs `python -m twine upload dist/ultra_claude-0.0.1*` per PUBLISH.md to close PKG-05. After upload + `pip install ultra-claude==0.0.1` smoke check from a fresh shell, mark PKG-05 complete in REQUIREMENTS.md and Phase 1 fully closes. Then proceed to Phase 2 planning via `/gsd-plan-phase 2` (Config Schema & YAML Loader) — Phase 2 does not depend on the PyPI upload, only on the local skeleton + pyproject.toml which are committed.

**Files in scope:**

- `.planning/PROJECT.md` — core value, constraints, key decisions
- `.planning/REQUIREMENTS.md` — 58 v1 requirements mapped 100% to phases (4 complete, 1 deferred-to-user)
- `.planning/ROADMAP.md` — 9-phase structure with goal-backward success criteria
- `.planning/STATE.md` — this file
- `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md` — operator runbook for the deferred user action
- `.planning/research/{SUMMARY,STACK,ARCHITECTURE,PITFALLS,FEATURES}.md` — context for plan-time research-flagged phases

---
*State initialized: 2026-05-02 after roadmap creation*
*Plan 01-01 completed: 2026-05-02 — commits 562d05e (chore: scaffolding files) + 2b15b36 (feat: __version__ stub)*
*Plan 01-02 completed: 2026-05-02 — commit b9bf3c5 (feat: pyproject.toml with hatchling backend, pinned deps, tool config)*
*Plan 01-03 completed: 2026-05-02 — commits 3e31832 (chore: .gitignore .smoke-venv defensive add) + e96ccb6 (docs: PUBLISH.md runbook); dist/ artifacts produced and smoke-tested locally; PKG-05 deferred to user action*
