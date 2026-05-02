---
gsd_state_version: 1.0
milestone: v0.1.0
milestone_name: Release
status: phase-3-complete-transcript-module-landed
last_updated: "2026-05-02T02:59:22Z"
progress:
  total_phases: 9
  completed_phases: 2
  total_plans: 6
  completed_plans: 6
  percent: 67
---

# State: ultra-claude

**Last Updated:** 2026-05-02

## Project Reference

**Core Value:** A user can run `ultra-claude run task.md` and get three CLI agents debating their problem in a transcript file — using only their existing CLI logins, no API keys.

**Current Focus:** Phase 3 COMPLETE. Plan 03-01 closed TRX-01..TRX-05 — `src/ultra_claude/transcript.py` (`TurnRecord` Pydantic model + `Transcript` class with append-as-you-go markdown + JSONL sidecar) and `tests/test_transcript.py` (8 tests, 8 PASS; full suite 16/16 PASS) landed via commits `88b6186` + `6230667`. Phase 1 autonomous portion still complete; PKG-05 still pending user `twine upload` (independent of subsequent phases). Phases 4 (Adapter Protocol & ClaudeAdapter) and 5 (Stop Conditions) are now unblocked.

## Current Position

Phase: 03-transcript-module — COMPLETE (1/1 plan, all 5 TRX requirements closed)
Next phase: 04-adapter-protocol-claudeadapter (depends on Phase 1; can begin in parallel with Phase 5)
| Field | Value |
|-------|-------|
| Phase | 3 (Transcript Module) — COMPLETE |
| Plan | 03-01 COMPLETE; Phase 4 NEXT (parallelizable with Phase 5) |
| Status | All 5 TRX requirements complete; `from ultra_claude.transcript import Transcript, TurnRecord` works; 8/8 transcript tests pass + 8/8 config tests still pass (16 total); LF-only on disk; UTF-8 round-trip with em-dash/smart-quote/emoji proven; all plan-level verification commands PASS |
| Progress | 2/9 phases complete; 6/6 plans (Phase 1: 3/3, Phase 2: 2/2, Phase 3: 1/1) |

```
[######              ] 6/9 plans (67%) — Phase 3 complete; Phase 4 (and parallel Phase 5) next
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases planned | 9 |
| Phases complete | 2 (Phases 2 + 3 fully closed; Phase 1 awaiting user twine upload to fully close PKG-05) |
| Plans complete | 6 (Phase 1: 3/3, Phase 2: 2/2, Phase 3: 1/1) |
| v1 requirements mapped | 58/58 |
| Requirements completed | 14 (PKG-02, PKG-03, PKG-04, PKG-07, CFG-01..05, TRX-01..05) |
| Requirements partial | 0 |
| Requirements deferred-to-user | 1 (PKG-05 — twine upload, runbook ready) |
| Coverage | 100% |
| Plan 01-01 duration | ~2 min (2026-05-02T01:48:41Z → 2026-05-02T01:50:25Z) |
| Plan 01-02 duration | ~1.5 min (2026-05-02T01:54:42Z → 2026-05-02T01:56:12Z) |
| Plan 01-03 duration | ~5 min (2026-05-02T02:00:57Z → 2026-05-02T02:06:15Z) — autonomous portion |
| Plan 02-01 duration | ~2 min (2026-05-02T02:28:34Z → 2026-05-02T02:30:33Z) |
| Plan 02-02 duration | ~4 min (2026-05-02T02:35:56Z → 2026-05-02T02:39:52Z) |
| Plan 03-01 duration | ~6 min (2026-05-02T02:53:30Z → 2026-05-02T02:59:22Z) — 2 tasks, 2 commits, 1 Rule 1 deviation (Python 3.11 f-string limitation) |

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

### Phase 3 Progress (COMPLETE)

- [x] **Plan 03-01 (`transcript.py` + tests):** New file `src/ultra_claude/transcript.py` (11708 bytes, 295 lines, LF-only, UTF-8) defining `TurnRecord(BaseModel)` (Pydantic v2; `turn` ge=1, `agent`/`role` min_length=1, `prompt_hash` exactly 64 hex chars, `output` str; ConfigDict extra=forbid) and `Transcript` class with `__init__(markdown_path, *, header_task=None, started_at=None)`, `markdown_path`/`jsonl_path` read-only `@property` (jsonl path = markdown path with `.jsonl` appended via `with_suffix(suffix + ".jsonl")` — literal append, not replace), `append_turn(turn, agent, role, prompt, output)` (writes BOTH markdown block + JSONL line; SHA-256 hex prompt_hash on UTF-8-encoded prompt; both opens use `mode="a", encoding="utf-8", newline="\n"`; header rendered on first write only when stat().st_size==0), `read_turns()` (returns `[]` if sidecar missing, else parses each line via `TurnRecord.model_validate_json`), `__len__`, `markdown_text()`/`jsonl_text()` read-back helpers. Sentinel format: `<!-- turn:N agent:Name -->` (Pitfall #8 mitigation; locked for Phase 5 stop conditions). `__init__` raises `OSError` when parent directory missing (D-11 — no auto-mkdir); does NOT erase existing markdown (D-10 — idempotent re-open). Plus `tests/test_transcript.py` (12880 bytes, 337 lines, 8 tests, all PASS): `test_three_turn_round_trip_appends_to_markdown` (TRX-01), `test_each_turn_has_html_comment_sentinel` (TRX-02), `test_jsonl_sidecar_records_match_schema` (TRX-03), `test_lf_only_on_disk` (TRX-04), `test_utf8_round_trip` (TRX-05 — em-dash + smart quotes + rocket emoji), `test_read_turns_returns_empty_list_when_sidecar_missing` (D-08), `test_init_raises_oserror_when_parent_missing` (D-11), `test_idempotent_creation_does_not_erase_existing_markdown` (D-10). Full suite: 16/16 PASS (8 Phase 2 + 8 Phase 3 — zero regression). Two deviations: Rule 1 (Python 3.11 `SyntaxError: f-string expression part cannot include a backslash` in `test_lf_only_on_disk` — fixed by lifting CRLF byte literal counts into locals before f-string interpolation; behavior identical) + Rule 3 (ruff lint cleanups: I001 extra blank line removed, B905 added `strict=True` to `zip()`, RUF001 x3 noqa on intentional smart-quote test fixtures). Commits: `88b6186` (feat: add transcript module with TurnRecord + Transcript classes), `6230667` (test: add transcript test suite covering TRX-01..TRX-05). SUMMARY at `.planning/phases/03-transcript-module/03-01-SUMMARY.md`. Requirements: TRX-01..TRX-05 all COMPLETE.

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

**Last action:** Executed Phase 3 plan 03-01 (transcript module + 8-test pytest suite). Created `src/ultra_claude/transcript.py` (11708 bytes, 295 lines, LF-only, UTF-8) with `TurnRecord(BaseModel)` (Pydantic v2; turn ge=1, agent/role min_length=1, prompt_hash exactly 64 hex chars, output str; ConfigDict extra=forbid) and `Transcript` class with `__init__(markdown_path, *, header_task=None, started_at=None)`, read-only `markdown_path`/`jsonl_path` properties (jsonl_path uses literal-append `.jsonl`, not suffix-replace), `append_turn(turn, agent, role, prompt, output)` that writes BOTH the markdown block AND the JSONL line per call (every `open()` uses `mode="a", encoding="utf-8", newline="\n"`; SHA-256 hex prompt_hash on UTF-8-encoded prompt; header rendered on first write only when stat().st_size==0), `read_turns()` returning `[]` if sidecar missing else `list[TurnRecord]`, `__len__`, plus `markdown_text()`/`jsonl_text()` read-back helpers. Sentinel format `<!-- turn:N agent:Name -->` locked (Pitfall #8 mitigation). `__init__` raises OSError on missing parent (D-11 — no auto-mkdir) and does not erase existing markdown (D-10 — idempotent re-open). Plus `tests/test_transcript.py` (12880 bytes, 337 lines, 8 tests covering TRX-01..TRX-05 + D-08/D-10/D-11). All 8 transcript tests PASS; full suite shows 16/16 PASS (no Phase 2 regression). All plan-level verification commands PASS: import check, pytest tests/, LF-only check on both files, mypy --strict on transcript.py, ruff on both files, sentinel-format grep. Two deviations: **Rule 1** — Python 3.11 `SyntaxError: f-string expression part cannot include a backslash` in `test_lf_only_on_disk`; fixed by lifting CRLF byte-literal counts into locals (`md_crlf_count`/`jsonl_crlf_count`) before interpolating into f-string assert messages; functionally identical, arguably cleaner; PEP 701 lifts this restriction in 3.12 but project floor is 3.10/3.11. **Rule 3** — ruff lint cleanups before commit: I001 (removed extra blank line after imports), B905 (added `strict=True` to `zip(records, payload)` for fail-loud on length mismatch), RUF001 x3 (noqa on intentional smart-quote test fixtures — the smart quotes ARE the test payload). Atomic commits: `88b6186` (feat: add transcript module with TurnRecord + Transcript classes) + `6230667` (test: add transcript test suite covering TRX-01..TRX-05). SUMMARY at `.planning/phases/03-transcript-module/03-01-SUMMARY.md`. Phase 3 fully CLOSED.

**Next action:** Phases 4 (Adapter Protocol & ClaudeAdapter) and 5 (Stop Conditions) are now unblocked. They are parallelizable per ROADMAP — Phase 4 owns the subprocess invocation contract (locks `text=True, encoding="utf-8", errors="replace"`, mandatory timeout, list-form argv, `shell=False`, stdin-piped prompts, empty-stdout defense, cross-platform process-tree kill) and the first concrete `ClaudeAdapter`; Phase 5 owns three composable stop strategies (`Keyword` with anchored multiline regex + N=2/M=2 unanimity-window, `MaxTurns`, `AnyOf`). Phase 5 consumes `Transcript.read_turns()` and the `<!-- turn:N agent:Name -->` sentinel format both delivered by this plan. Run `/gsd-plan-phase 4` (or `/gsd-plan-phase 5`, or both with `/gsd-discuss-phase` first) to decompose them into executable plans.

**Files in scope:**

- `.planning/PROJECT.md` — core value, constraints, key decisions
- `.planning/REQUIREMENTS.md` — 58 v1 requirements mapped 100% to phases (14 complete, 1 deferred-to-user)
- `.planning/ROADMAP.md` — 9-phase structure with goal-backward success criteria
- `.planning/STATE.md` — this file
- `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md` — operator runbook for the deferred user action (PKG-05)
- `.planning/phases/02-config-schema-yaml-loader/02-01-PLAN.md` — completed plan
- `.planning/phases/02-config-schema-yaml-loader/02-01-SUMMARY.md` — completion summary for 02-01
- `.planning/phases/02-config-schema-yaml-loader/02-02-PLAN.md` — completed plan
- `.planning/phases/02-config-schema-yaml-loader/02-02-SUMMARY.md` — completion summary for 02-02
- `.planning/phases/02-config-schema-yaml-loader/02-CONTEXT.md` — phase 2 context
- `.planning/phases/02-config-schema-yaml-loader/deferred-items.md` — out-of-scope discoveries (autocrlf on Windows)
- `.planning/phases/03-transcript-module/03-CONTEXT.md` — phase 3 context (decisions, code insights, specifics)
- `.planning/phases/03-transcript-module/03-01-PLAN.md` — completed plan (this plan)
- `.planning/phases/03-transcript-module/03-01-SUMMARY.md` — completion summary for 03-01 (this plan)
- `src/ultra_claude/exceptions.py` — landed in plan 02-01
- `src/ultra_claude/config.py` — landed in plan 02-02
- `src/ultra_claude/transcript.py` — newly landed in plan 03-01, consumed by Phase 5+ (Transcript + TurnRecord) and Phase 6 (orchestrator's append-as-you-go writer)
- `tests/__init__.py` — package marker (Phase 2)
- `tests/test_config.py` — landed in plan 02-02 (8 tests, all PASS)
- `tests/test_transcript.py` — newly landed in plan 03-01 (8 tests, all PASS)
- `.planning/research/{SUMMARY,STACK,ARCHITECTURE,PITFALLS,FEATURES}.md` — context for plan-time research-flagged phases

---
*State initialized: 2026-05-02 after roadmap creation*
*Plan 01-01 completed: 2026-05-02 — commits 562d05e (chore: scaffolding files) + 2b15b36 (feat: __version__ stub)*
*Plan 01-02 completed: 2026-05-02 — commit b9bf3c5 (feat: pyproject.toml with hatchling backend, pinned deps, tool config)*
*Plan 01-03 completed: 2026-05-02 — commits 3e31832 (chore: .gitignore .smoke-venv defensive add) + e96ccb6 (docs: PUBLISH.md runbook); dist/ artifacts produced and smoke-tested locally; PKG-05 deferred to user action*
*Plan 02-01 completed: 2026-05-02 — commit ddfca71 (feat: add ConfigError exception class); CFG-03 partial (foundation; full delivery in 02-02)*
*Plan 02-02 completed: 2026-05-02 — commits e97325a (feat: add config schema and YAML loader) + 5c272f0 (test: add config validation test suite); CFG-01..CFG-05 all COMPLETE; 8/8 tests PASS; Phase 2 fully CLOSED*
*Plan 03-01 completed: 2026-05-02 — commits 88b6186 (feat: add transcript module with TurnRecord + Transcript classes) + 6230667 (test: add transcript test suite covering TRX-01..TRX-05); TRX-01..TRX-05 all COMPLETE; 8/8 transcript tests PASS + 16/16 full suite PASS; Phase 3 fully CLOSED*
