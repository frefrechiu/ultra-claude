---
gsd_state_version: 1.0
milestone: v0.1.0
milestone_name: Release
status: unknown
last_updated: "2026-05-02T01:50:25Z"
progress:
  total_phases: 9
  completed_phases: 0
  total_plans: 3
  completed_plans: 1
  percent: 11
---

# State: ultra-claude

**Last Updated:** 2026-05-02

## Project Reference

**Core Value:** A user can run `ultra-claude run task.md` and get three CLI agents debating their problem in a transcript file — using only their existing CLI logins, no API keys.

**Current Focus:** Phase 1 — Project Skeleton & PyPI Name Reservation (plan 01-02 next)

## Current Position

Phase: 01-project-skeleton-pypi-name-reservation — EXECUTING
Plan: 1/3 complete (next: 01-02)
| Field | Value |
|-------|-------|
| Phase | 1 (Project Skeleton & PyPI Name Reservation) |
| Plan | 01-01 COMPLETE; 01-02 next |
| Status | Repo skeleton landed (LICENSE, .gitignore, README stub, CHANGELOG, src/ultra_claude/__init__.py with __version__) |
| Progress | 0/9 phases complete; 1/3 plans in Phase 1 |

```
[#                   ] 1/9 phases (11%)
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases planned | 9 |
| Phases complete | 0 |
| Plans complete | 1 |
| v1 requirements mapped | 58/58 |
| Requirements completed | 3 (PKG-03, PKG-04, PKG-07) |
| Coverage | 100% |
| Plan 01-01 duration | ~2 min (2026-05-02T01:48:41Z → 2026-05-02T01:50:25Z) |

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

### Open Todos (Pre-Phase-1)

- [ ] Reserve PyPI name `ultra-claude` as `0.0.1` stub before any public mention (Phase 1 plan 01-03 — manual `twine upload` checkpoint)
- [ ] Verify each CLI's exact argv shape empirically at Phase 4 (Claude) and Phase 7 (Gemini, Codex) implementation time — vendor flag conventions may have drifted since research

### In-Phase-1 Progress

- [x] **Plan 01-01 (repository skeleton):** LICENSE (MIT, Freddy Chiu 2026), .gitignore, README.md stub with trademark disclaimer, CHANGELOG.md (Keep-a-Changelog), src/ultra_claude/__init__.py with `__version__ = "0.0.1"`. Commits: `562d05e`, `2b15b36`. Requirements: PKG-03, PKG-04, PKG-07.
- [ ] Plan 01-02 (pyproject.toml + tool configs)
- [ ] Plan 01-03 (build + manual PyPI upload checkpoint)

### Active Blockers

None. Roadmap is unblocked.

### Research Flags Carried Forward

| Phase | Verification Required at Plan Time |
|-------|-----------------------------------|
| Phase 4 | `claude -p` exact current argv shape and stdin-acceptance behaviour (verify empirically) |
| Phase 7 | `gemini -p` non-interactive flag (issue #19774); `codex exec` `--quiet`/stdin support |
| Phase 8 | Auth state file paths (`~/.claude/auth.json` etc.) per platform for `doctor` subcommand |
| Phase 9 | Windows GitHub Actions runner config for subprocess tests; PyPI Trusted Publishing setup if pulled forward |

## Session Continuity

**Last action:** Executed Phase 1 plan 01-01 (repository skeleton). Five files created at canonical paths, two atomic commits, all acceptance criteria pass. SUMMARY at `.planning/phases/01-project-skeleton-pypi-name-reservation/01-01-SUMMARY.md`.

**Next action:** Execute Phase 1 plan 01-02 (`pyproject.toml` configuration with hatchling backend, pinned deps, src-layout target, ruff/mypy/pytest tool tables).

**Files in scope:**

- `.planning/PROJECT.md` — core value, constraints, key decisions
- `.planning/REQUIREMENTS.md` — 58 v1 requirements mapped 100% to phases
- `.planning/ROADMAP.md` — 9-phase structure with goal-backward success criteria
- `.planning/STATE.md` — this file
- `.planning/research/{SUMMARY,STACK,ARCHITECTURE,PITFALLS,FEATURES}.md` — context for plan-time research-flagged phases

---
*State initialized: 2026-05-02 after roadmap creation*
*Plan 01-01 completed: 2026-05-02 — commits 562d05e (chore: scaffolding files) + 2b15b36 (feat: __version__ stub)*
