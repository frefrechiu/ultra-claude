---
gsd_state_version: 1.0
milestone: v0.1.0
milestone_name: Release
status: phase-2-complete-config-schema-and-yaml-loader-landed
last_updated: "2026-05-02T02:39:52Z"
progress:
  total_phases: 9
  completed_phases: 1
  total_plans: 5
  completed_plans: 5
  percent: 56
---

# State: ultra-claude

**Last Updated:** 2026-05-02

## Project Reference

**Core Value:** A user can run `ultra-claude run task.md` and get three CLI agents debating their problem in a transcript file — using only their existing CLI logins, no API keys.

**Current Focus:** Phase 2 COMPLETE. Plan 02-02 closed CFG-01..CFG-05 — `src/ultra_claude/config.py` (schema + `load_config` + `format_validation_error`) + `tests/__init__.py` + `tests/test_config.py` (8 tests, 8 PASS) landed via commits `e97325a` + `5c272f0`. Phase 1 autonomous portion still complete; PKG-05 still pending user `twine upload` (independent of Phase 2 progress). Phase 3 (Transcript Module) is now unblocked.

## Current Position

Phase: 02-config-schema-yaml-loader — COMPLETE (2/2 plans, all 5 CFG requirements closed)
Next phase: 03-transcript-module (depends on Phase 2; can begin)
| Field | Value |
|-------|-------|
| Phase | 2 (Config Schema & YAML Loader) — COMPLETE |
| Plan | 02-01 + 02-02 both COMPLETE; Phase 3 NEXT |
| Status | All 5 CFG requirements complete; `from ultra_claude.config import RoundtableConfig, AgentConfig, load_config, format_validation_error, ConfigError` works; 8/8 tests pass; LF-only on disk; all 9 plan-level verification commands PASS |
| Progress | 1/9 phases complete; 5/5 plans (Phase 1: 3/3, Phase 2: 2/2) |

```
[#####               ] 5/9 plans (56%) — Phase 2 complete; Phase 3 next
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases planned | 9 |
| Phases complete | 1 (Phase 2 fully closed; Phase 1 awaiting user twine upload to fully close PKG-05) |
| Plans complete | 5 (Phase 1: 3/3, Phase 2: 2/2) |
| v1 requirements mapped | 58/58 |
| Requirements completed | 9 (PKG-02, PKG-03, PKG-04, PKG-07, CFG-01, CFG-02, CFG-03, CFG-04, CFG-05) |
| Requirements partial | 0 |
| Requirements deferred-to-user | 1 (PKG-05 — twine upload, runbook ready) |
| Coverage | 100% |
| Plan 01-01 duration | ~2 min (2026-05-02T01:48:41Z → 2026-05-02T01:50:25Z) |
| Plan 01-02 duration | ~1.5 min (2026-05-02T01:54:42Z → 2026-05-02T01:56:12Z) |
| Plan 01-03 duration | ~5 min (2026-05-02T02:00:57Z → 2026-05-02T02:06:15Z) — autonomous portion |
| Plan 02-01 duration | ~2 min (2026-05-02T02:28:34Z → 2026-05-02T02:30:33Z) |
| Plan 02-02 duration | ~4 min (2026-05-02T02:35:56Z → 2026-05-02T02:39:52Z) |

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

### Phase 2 Progress (COMPLETE)

- [x] **Plan 02-01 (`ConfigError` exception class):** New file `src/ultra_claude/exceptions.py` (1387 bytes, 34 lines, LF-only, ASCII-only). Defines `class ConfigError(Exception)` with a docstring documenting the three failure modes it wraps (`yaml.YAMLError`, `pydantic.ValidationError`, `FileNotFoundError`). Module docstring foreshadows Phase 4 `AdapterError`/`AdapterAuthError` additions. `__all__ = ["ConfigError"]` declared. Zero third-party imports. Commit: `ddfca71`. Requirements: CFG-03 partial (foundation completed by 02-02).
- [x] **Plan 02-02 (`config.py` + tests):** New file `src/ultra_claude/config.py` (9714 bytes, 267 lines, LF-only, ASCII-only) defining `AgentConfig` (Literal['claude','gemini','codex'] adapter, all required, min_length=1), `RoundtableConfig` (agents min_length=2, max_turns default 12 ge=2, stop_keywords default ['AGREED','DONE'], turn_order Literal['round_robin'], abort_on_error False, transcript_path optional, task optional), `load_config(path) -> RoundtableConfig`, `RoundtableConfig.from_yaml_string` classmethod, `format_validation_error(err, source_path) -> str` with specialised `literal_error`/`missing` wording, `_format_loc` ('agents', 0, 'adapter') -> 'agents[0].adapter', `_format_yaml_error` 1-indexed line/column. Both `BaseModel`s use `ConfigDict(extra='forbid')`. `__all__` exports 5 public symbols. Plus `tests/__init__.py` (0 bytes, package marker) and `tests/test_config.py` (8763 bytes, 276 lines, 8 test functions). All 8 tests pass; all 9 plan-level verification commands PASS. One Rule 3 deviation: ran `pip install -e ".[dev]"` (acknowledged in plan note) to make `ultra_claude` importable for pytest collection — no working-tree changes. Commits: `e97325a` (feat: add config schema and YAML loader), `5c272f0` (test: add config validation test suite). Requirements: CFG-01..CFG-05 all COMPLETE.

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

**Last action:** Executed Phase 2 plan 02-02 (config schema + YAML loader + tests). Created `src/ultra_claude/config.py` (9714 bytes, 267 lines, LF-only, ASCII-only) with `AgentConfig`, `RoundtableConfig`, `load_config(path) -> RoundtableConfig`, `RoundtableConfig.from_yaml_string` classmethod, `format_validation_error(err, source_path) -> str` with specialised `literal_error`/`missing` wording, `_format_loc` and `_format_yaml_error` helpers, `__all__` exporting 5 public symbols. Both Pydantic models use `ConfigDict(extra='forbid')`. Created `tests/__init__.py` (0 bytes, package marker) and `tests/test_config.py` (8763 bytes, 276 lines, 8 test functions covering CFG-01..CFG-05 plus wire-format check and file-not-found path). `python -m pytest tests/test_config.py -v` shows 8/8 PASSED in 0.11s. All 9 plan-level verification commands PASS (full suite, CFG references, public API, ConfigError identity, defaults, turn_order rejection, error isolation, LF-only, parse). Verified ConfigError-from-config and ConfigError-from-exceptions are the SAME class object (no shadowing). Verified ValidationError + yaml.YAMLError never leak to the caller (3-layer assertion). Atomic commits: `e97325a` (feat: add config schema and YAML loader) + `5c272f0` (test: add config validation test suite). One Rule 3 deviation: ran `pip install -e ".[dev]" --quiet` to make `ultra_claude` importable for pytest collection (plan acknowledged this in note; no working-tree changes). SUMMARY at `.planning/phases/02-config-schema-yaml-loader/02-02-SUMMARY.md`. Phase 2 fully CLOSED.

**Next action:** Phase 3 (Transcript Module) is unblocked and ready to begin. Phase 3 will land `src/ultra_claude/transcript.py` with the append-as-you-go markdown writer using non-markdown HTML-comment sentinels (per Pitfall #8 to avoid markdown-in-markdown corruption) plus a JSONL sidecar. Phase 3 imports `AgentConfig` from `ultra_claude.config` (now available). Phase 3 covers TRX-01..TRX-05. Run `/gsd-plan-phase 3` (or `/gsd-discuss-phase 3` to clarify approach first) to decompose Phase 3 into executable plans.

**Files in scope:**

- `.planning/PROJECT.md` — core value, constraints, key decisions
- `.planning/REQUIREMENTS.md` — 58 v1 requirements mapped 100% to phases (9 complete, 1 deferred-to-user)
- `.planning/ROADMAP.md` — 9-phase structure with goal-backward success criteria
- `.planning/STATE.md` — this file
- `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md` — operator runbook for the deferred user action (PKG-05)
- `.planning/phases/02-config-schema-yaml-loader/02-01-PLAN.md` — completed plan
- `.planning/phases/02-config-schema-yaml-loader/02-01-SUMMARY.md` — completion summary for 02-01
- `.planning/phases/02-config-schema-yaml-loader/02-02-PLAN.md` — completed plan
- `.planning/phases/02-config-schema-yaml-loader/02-02-SUMMARY.md` — completion summary for 02-02 (this plan)
- `.planning/phases/02-config-schema-yaml-loader/02-CONTEXT.md` — phase context (decisions, code insights, specifics)
- `.planning/phases/02-config-schema-yaml-loader/deferred-items.md` — out-of-scope discoveries (autocrlf on Windows)
- `src/ultra_claude/exceptions.py` — landed in plan 02-01, consumed by 02-02
- `src/ultra_claude/config.py` — newly landed in plan 02-02, consumed by Phase 3+ (RoundtableConfig + AgentConfig)
- `tests/__init__.py` and `tests/test_config.py` — newly landed in plan 02-02 (8 tests, all PASS)
- `.planning/research/{SUMMARY,STACK,ARCHITECTURE,PITFALLS,FEATURES}.md` — context for plan-time research-flagged phases

---
*State initialized: 2026-05-02 after roadmap creation*
*Plan 01-01 completed: 2026-05-02 — commits 562d05e (chore: scaffolding files) + 2b15b36 (feat: __version__ stub)*
*Plan 01-02 completed: 2026-05-02 — commit b9bf3c5 (feat: pyproject.toml with hatchling backend, pinned deps, tool config)*
*Plan 01-03 completed: 2026-05-02 — commits 3e31832 (chore: .gitignore .smoke-venv defensive add) + e96ccb6 (docs: PUBLISH.md runbook); dist/ artifacts produced and smoke-tested locally; PKG-05 deferred to user action*
*Plan 02-01 completed: 2026-05-02 — commit ddfca71 (feat: add ConfigError exception class); CFG-03 partial (foundation; full delivery in 02-02)*
*Plan 02-02 completed: 2026-05-02 — commits e97325a (feat: add config schema and YAML loader) + 5c272f0 (test: add config validation test suite); CFG-01..CFG-05 all COMPLETE; 8/8 tests PASS; Phase 2 fully CLOSED*
