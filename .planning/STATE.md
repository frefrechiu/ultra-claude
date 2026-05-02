---
gsd_state_version: 1.0
milestone: v0.1.0
milestone_name: Release
status: phase-2-plan-01-complete-config-error-class-landed
last_updated: "2026-05-02T02:30:33Z"
progress:
  total_phases: 9
  completed_phases: 0
  total_plans: 5
  completed_plans: 4
  percent: 44
---

# State: ultra-claude

**Last Updated:** 2026-05-02

## Project Reference

**Core Value:** A user can run `ultra-claude run task.md` and get three CLI agents debating their problem in a transcript file — using only their existing CLI logins, no API keys.

**Current Focus:** Phase 2 underway. Plan 02-01 COMPLETE — `ConfigError` exception class landed in `src/ultra_claude/exceptions.py` (commit `ddfca71`). Phase 1 autonomous portion still complete; PKG-05 still pending user `twine upload` (independent of Phase 2 progress). Plan 02-02 (config.py + tests) is now unblocked.

## Current Position

Phase: 02-config-schema-yaml-loader — IN PROGRESS (1/2 plans complete)
Plan: 02-01 COMPLETE; 02-02 NEXT
| Field | Value |
|-------|-------|
| Phase | 2 (Config Schema & YAML Loader) |
| Plan | 02-01 COMPLETE (ConfigError class); 02-02 NEXT (config.py + load_config + tests) |
| Status | Exception class landed; importable as `from ultra_claude.exceptions import ConfigError`; zero third-party imports; LF-only on disk; all 6 verification commands PASS |
| Progress | 0/9 phases complete; 4/5 plans (Phase 1: 3/3, Phase 2: 1/2) |

```
[####                ] 4/9 plans (44%) — Phase 2 plan 01 of 02 done
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases planned | 9 |
| Phases complete | 0 (Phase 1 awaiting user twine upload to fully close PKG-05; Phase 2 in progress) |
| Plans complete | 4 (Phase 1: 3/3, Phase 2: 1/2) |
| v1 requirements mapped | 58/58 |
| Requirements completed | 4 (PKG-02, PKG-03, PKG-04, PKG-07) |
| Requirements partial | 1 (CFG-03 — `ConfigError` class landed in 02-01; full delivery in 02-02) |
| Requirements deferred-to-user | 1 (PKG-05 — twine upload, runbook ready) |
| Coverage | 100% |
| Plan 01-01 duration | ~2 min (2026-05-02T01:48:41Z → 2026-05-02T01:50:25Z) |
| Plan 01-02 duration | ~1.5 min (2026-05-02T01:54:42Z → 2026-05-02T01:56:12Z) |
| Plan 01-03 duration | ~5 min (2026-05-02T02:00:57Z → 2026-05-02T02:06:15Z) — autonomous portion |
| Plan 02-01 duration | ~2 min (2026-05-02T02:28:34Z → 2026-05-02T02:30:33Z) |

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

### In-Phase-2 Progress

- [x] **Plan 02-01 (`ConfigError` exception class):** New file `src/ultra_claude/exceptions.py` (1387 bytes, 34 lines, LF-only, ASCII-only). Defines `class ConfigError(Exception)` with a docstring documenting the three failure modes it wraps (`yaml.YAMLError`, `pydantic.ValidationError`, `FileNotFoundError`). Module docstring foreshadows Phase 4 `AdapterError`/`AdapterAuthError` additions. `__all__ = ["ConfigError"]` declared. Zero third-party imports — verified via `dir(module)` scan returning no `pydantic`/`yaml` symbols (clean-OK). `from __future__ import annotations` present defensively. All 6 plan-level verification commands PASS (parse, import, behavior, __all__, LF-only, no third-party leakage). Commit: `ddfca71`. Requirements: CFG-03 partial (foundation; full delivery in 02-02 via `format_validation_error` + `load_config`).
- [ ] **Plan 02-02 (`config.py` + tests):** NEXT. Will land `AgentConfig`, `RoundtableConfig`, `load_config(path) -> RoundtableConfig`, and `format_validation_error(err, source_path) -> str` with `tests/test_config.py` covering 6 cases per CONTEXT.md. Closes CFG-01..CFG-05.

### Out-of-Scope Discoveries Logged (not actioned in 02-01)

- **`core.autocrlf=true` on Windows host risks CRLF on checkout.** Working-tree and git index are LF-only after this commit, but a future clone/checkout on Windows could materialise CRLF, breaking the cross-platform discipline (CLAUDE.md constraint #6). Recommended fix is a repo-root `.gitattributes` forcing LF. Logged at `.planning/phases/02-config-schema-yaml-loader/deferred-items.md`. Project-wide concern, not specific to plan 02-01 — should be addressed via a small chore plan.

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

**Last action:** Executed Phase 2 plan 02-01 (`ConfigError` exception class). Created `src/ultra_claude/exceptions.py` (1387 bytes, 34 lines, LF-only, ASCII-only) with `class ConfigError(Exception)`, module docstring foreshadowing Phase 4 `AdapterError`/`AdapterAuthError` additions, `__all__ = ["ConfigError"]`, and `from __future__ import annotations`. Zero third-party imports — verified `dir(module)` contains no `pydantic`/`yaml` symbols (clean-OK). All 6 plan-level verification commands pass post-commit (parse-OK, import-OK, behavior-OK, all-OK, LF-OK, clean-OK). Atomic commit: `ddfca71` (`feat(02-01): add ConfigError exception class`). SUMMARY at `.planning/phases/02-config-schema-yaml-loader/02-01-SUMMARY.md`. Out-of-scope discovery (autocrlf risk on Windows checkout) logged to `.planning/phases/02-config-schema-yaml-loader/deferred-items.md`.

**Next action:** Execute Phase 2 plan 02-02 (`config.py` + tests). Will import `ConfigError` from this plan's `exceptions.py` (key-link verified — `from .exceptions import ConfigError` from `config.py`). Plan 02-02 lands `AgentConfig`, `RoundtableConfig`, `load_config(path) -> RoundtableConfig`, `format_validation_error(err, source_path) -> str`, plus `tests/test_config.py` covering the 6 cases listed in CONTEXT.md (CFG-01..CFG-05). After 02-02, Phase 2 closes; Phase 3 (Transcript Module) is ready to begin.

**Files in scope:**

- `.planning/PROJECT.md` — core value, constraints, key decisions
- `.planning/REQUIREMENTS.md` — 58 v1 requirements mapped 100% to phases (4 complete, 1 partial via 02-01, 1 deferred-to-user)
- `.planning/ROADMAP.md` — 9-phase structure with goal-backward success criteria
- `.planning/STATE.md` — this file
- `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md` — operator runbook for the deferred user action (PKG-05)
- `.planning/phases/02-config-schema-yaml-loader/02-01-PLAN.md` — completed plan
- `.planning/phases/02-config-schema-yaml-loader/02-01-SUMMARY.md` — completion summary for 02-01
- `.planning/phases/02-config-schema-yaml-loader/02-02-PLAN.md` — next plan (config.py + tests)
- `.planning/phases/02-config-schema-yaml-loader/02-CONTEXT.md` — phase context (decisions, code insights, specifics)
- `.planning/phases/02-config-schema-yaml-loader/deferred-items.md` — out-of-scope discoveries (autocrlf on Windows)
- `src/ultra_claude/exceptions.py` — newly landed in this plan, consumed by 02-02
- `.planning/research/{SUMMARY,STACK,ARCHITECTURE,PITFALLS,FEATURES}.md` — context for plan-time research-flagged phases

---
*State initialized: 2026-05-02 after roadmap creation*
*Plan 01-01 completed: 2026-05-02 — commits 562d05e (chore: scaffolding files) + 2b15b36 (feat: __version__ stub)*
*Plan 01-02 completed: 2026-05-02 — commit b9bf3c5 (feat: pyproject.toml with hatchling backend, pinned deps, tool config)*
*Plan 01-03 completed: 2026-05-02 — commits 3e31832 (chore: .gitignore .smoke-venv defensive add) + e96ccb6 (docs: PUBLISH.md runbook); dist/ artifacts produced and smoke-tested locally; PKG-05 deferred to user action*
*Plan 02-01 completed: 2026-05-02 — commit ddfca71 (feat: add ConfigError exception class); CFG-03 partial (foundation; full delivery in 02-02)*
