---
gsd_state_version: 1.0
milestone: v0.1.0
milestone_name: Release
status: phase-4-plan-02-complete-claudeadapter-landed
last_updated: "2026-05-02T03:34:05Z"
progress:
  total_phases: 9
  completed_phases: 2
  total_plans: 8
  completed_plans: 8
  percent: 89
---

# State: ultra-claude

**Last Updated:** 2026-05-02

## Project Reference

**Core Value:** A user can run `ultra-claude run task.md` and get three CLI agents debating their problem in a transcript file — using only their existing CLI logins, no API keys.

**Current Focus:** Phase 4 plan 04-02 COMPLETE. Closed ADP-05 — `src/ultra_claude/adapters/claude.py` (95 lines, 4222 bytes, LF-only, ASCII-only) defines `class ClaudeAdapter(_SubprocessAdapterMixin)` with `name = cli_name = "claude"`, 5-element lowercase `auth_error_markers` tuple, and a one-line `invoke(prompt, timeout)` returning `self._run_subprocess(["claude", "-p"], prompt, timeout)`. Zero direct subprocess imports; `isinstance(ClaudeAdapter(), Adapter)` is True; the Phase 4 contract from 04-01 (UTF-8/replace, mandatory timeout, process-tree kill, empty-stdout defense, auth-marker detection, FileNotFoundError handling) is inherited from the mixin. `src/ultra_claude/adapters/__init__.py` updated (now 26 lines, 1263 bytes) to re-export `ClaudeAdapter`; `__all__` extended to `["Adapter", "_SubprocessAdapterMixin", "ClaudeAdapter"]` with `# noqa: RUF022` plus justifying comment for chronological-by-introduction order. Landed via commits `85e1c8f` + `40dd2ab`. All 6 plan-level verification commands PASS: imports, mypy --strict on adapters/ clean, ruff clean, pytest 16/16 PASS (zero regression), LF-only on disk on both files, no `import subprocess` in claude.py. Two Rule-3 deviations: (1) docstring rephrased to avoid literal `import subprocess` substring (verification command's source-text check would false-positive on descriptive prose), (2) `# noqa: RUF022` on `__all__` to preserve plan-mandated order. Plan 04-03 (tests + TST-05 lint) is now the last 04 plan; Phase 5 (Stop Conditions) remains parallelizable. Phase 1 autonomous portion still complete; PKG-05 still pending user `twine upload`.

## Current Position

Phase: 04-adapter-protocol-claudeadapter — Plan 04-02 COMPLETE (2/3 plans, 6/7 ADP+TST requirements closed for the phase)
Next plan: 04-03 (tests + TST-05 lint) — Wave 2, depends on 04-01 + 04-02
| Field | Value |
|-------|-------|
| Phase | 4 (Adapter Protocol & ClaudeAdapter) — IN PROGRESS (2/3 plans complete) |
| Plan | 04-02 COMPLETE; 04-03 (tests + TST-05 lint) NEXT — Wave 2 |
| Status | ADP-01..05 + ADP-08 closed; `from ultra_claude.adapters import Adapter, _SubprocessAdapterMixin, ClaudeAdapter` works; `isinstance(ClaudeAdapter(), Adapter)` is True; mypy --strict + ruff clean across all 4 files (`exceptions.py`, `adapters/__init__.py`, `adapters/base.py`, `adapters/claude.py`); 16/16 existing tests still PASS (zero regression); zero direct subprocess imports in `claude.py`; LF-only on disk on all 4 files; ASCII-only source |
| Progress | 2/9 phases complete; 8 completed plans (Phase 1: 3/3, Phase 2: 2/2, Phase 3: 1/1, Phase 4: 2/3) |

```
[########            ] Phase 4 plan 04-02 of 3 landed; 04-03 (tests + TST-05 lint) next
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases planned | 9 |
| Phases complete | 2 (Phases 2 + 3 fully closed; Phase 1 awaiting user twine upload to fully close PKG-05; Phase 4 in progress 2/3 plans) |
| Plans complete | 8 (Phase 1: 3/3, Phase 2: 2/2, Phase 3: 1/1, Phase 4: 2/3) |
| v1 requirements mapped | 58/58 |
| Requirements completed | 20 (PKG-02, PKG-03, PKG-04, PKG-07, CFG-01..05, TRX-01..05, ADP-01..05, ADP-08) |
| Requirements partial | 0 |
| Requirements deferred-to-user | 1 (PKG-05 — twine upload, runbook ready) |
| Coverage | 100% |
| Plan 01-01 duration | ~2 min (2026-05-02T01:48:41Z → 2026-05-02T01:50:25Z) |
| Plan 01-02 duration | ~1.5 min (2026-05-02T01:54:42Z → 2026-05-02T01:56:12Z) |
| Plan 01-03 duration | ~5 min (2026-05-02T02:00:57Z → 2026-05-02T02:06:15Z) — autonomous portion |
| Plan 02-01 duration | ~2 min (2026-05-02T02:28:34Z → 2026-05-02T02:30:33Z) |
| Plan 02-02 duration | ~4 min (2026-05-02T02:35:56Z → 2026-05-02T02:39:52Z) |
| Plan 03-01 duration | ~6 min (2026-05-02T02:53:30Z → 2026-05-02T02:59:22Z) — 2 tasks, 2 commits, 1 Rule 1 deviation (Python 3.11 f-string limitation) |
| Plan 04-01 duration | ~7 min (2026-05-02T03:17:46Z → 2026-05-02T03:24:44Z) — 2 tasks, 2 commits, 4 Rule 3 deviations (mypy Popen overload via per-platform branches; mypy attr-defined for POSIX-only os attrs; ruff SIM105 -> contextlib.suppress; ruff RUF022 -> noqa with justifying comment) |
| Plan 04-02 duration | ~3 min (2026-05-02T03:31:04Z → 2026-05-02T03:34:05Z) — 2 tasks, 2 commits, 2 Rule 3 deviations (docstring rephrased to avoid literal `import subprocess` substring; ruff RUF022 -> noqa with justifying comment) |

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

### Phase 4 Progress (IN PROGRESS — 2/3 plans complete)

- [x] **Plan 04-01 (extend exceptions.py + adapters/base.py):** New file `src/ultra_claude/adapters/__init__.py` (923 bytes, 21 lines, LF-only, ASCII-only) re-exports `Adapter` and `_SubprocessAdapterMixin`. New file `src/ultra_claude/adapters/base.py` (11805 bytes, 269 lines, LF-only, ASCII-only) defines `@runtime_checkable class Adapter(Protocol)` with `name: str` and `invoke(self, prompt: str, timeout: int) -> str`, plus `class _SubprocessAdapterMixin` with `cli_name: str` and `auth_error_markers: tuple[str, ...]` class-level annotations and a `_run_subprocess(argv, prompt, timeout) -> str` method that enforces the safe-subprocess contract end-to-end. The Popen call is split into per-platform `if os.name == "nt"` / `else` branches passing literal kwargs (`stdin/stdout/stderr=subprocess.PIPE`, `text=True`, `encoding="utf-8"`, `errors="replace"`, `shell=False`, plus either `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP` or `start_new_session=True`) so mypy --strict resolves the `Popen[str]` overload directly. The prompt is piped via stdin via `proc.communicate(input=prompt, timeout=timeout)` (NEVER on argv — Pitfall #1 mitigation). On `subprocess.TimeoutExpired`, `_kill_process_tree(proc)` is called BEFORE re-raising as `AdapterError`; the helper dispatches by `os.name`: Windows runs `subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], ..., text=True, encoding="utf-8", errors="replace", shell=False, capture_output=True)` (the taskkill call itself respects the safe-contract kwargs so 04-03's TST-05 lint test will not flag it), POSIX runs `os.killpg(os.getpgid(proc.pid), signal.SIGKILL)` (with `# type: ignore[attr-defined]` scoped to two POSIX-only lines because mypy on Windows cannot see those attrs). On `FileNotFoundError` from Popen the mixin raises `AdapterAuthError` ("CLI not found on PATH; run `<cli> login`"). After communicate succeeds, the mixin checks (a) auth markers via case-insensitive substring match against `stdout + "\n" + stderr` -> `AdapterAuthError`, (b) `proc.returncode == 0 and not stdout.strip()` -> `AdapterError` naming `openai/codex#19945` (Pitfall #2 defense lifted into the mixin so EVERY adapter inherits it), (c) `proc.returncode != 0` -> `AdapterError` with stdout+stderr captured. Happy path returns `stdout.strip()`. Plus `src/ultra_claude/exceptions.py` extended (3569 bytes, 80 lines, LF-only, ASCII-only) with `class AdapterError(Exception)` and `class AdapterAuthError(AdapterError)` -- subclassing keeps continue-on-error semantics uniform; the module docstring tense was updated from "Phase 4 will append" to past tense; `__all__` extended to `["ConfigError", "AdapterError", "AdapterAuthError"]` with `# noqa: RUF022` and a justifying comment about the intentional Phase-2-then-Phase-4 ordering. All 5 plan-level verification commands PASS: imports work, mypy --strict on `src/ultra_claude/exceptions.py src/ultra_claude/adapters/` clean, ruff check on the same target clean, full pytest suite 16/16 PASS (zero regression), LF-only on disk on all 3 files. Plus 6 inline integration smoke checks (FileNotFoundError, empty-stdout, auth-marker, happy-path, non-zero exit, TimeoutExpired-with-kill) all PASS. Four Rule-3 deviations -- all about making the source acceptable to project's strict tooling without changing semantics: (1) refactored Popen call to per-platform branches so mypy resolves the right overload (the original `dict[str, object]` spread caused `call-overload` -> `Any` -> `no-any-return`); (2) added `# type: ignore[attr-defined]` on POSIX-only `os.getpgid`/`os.killpg` (mypy on Windows cannot see them); (3) replaced three `try/except/pass` with `contextlib.suppress(...)` for ruff SIM105; (4) added `# noqa: RUF022` + justifying comment for `__all__` order. Atomic commits: `e4423d0` (feat: add AdapterError and AdapterAuthError exceptions) + `eceb9da` (feat: add Adapter Protocol and _SubprocessAdapterMixin). SUMMARY at `.planning/phases/04-adapter-protocol-claudeadapter/04-01-SUMMARY.md`. Requirements: ADP-01, ADP-02, ADP-03, ADP-04, ADP-08 all COMPLETE; ADP-05 remains for plan 04-02; TST-05 remains for plan 04-03.
- [x] **Plan 04-02 (ClaudeAdapter):** New file `src/ultra_claude/adapters/claude.py` (4222 bytes, 95 lines, LF-only, ASCII-only) defines `class ClaudeAdapter(_SubprocessAdapterMixin)` with three class-level attributes (`name: str = "claude"`, `cli_name: str = "claude"`, `auth_error_markers: tuple[str, ...] = ("not logged in", "please run \`claude login\`", "please run /login", "authentication required", "authentication failed")` -- all lowercase; the mixin matches case-insensitively) and a single `invoke(self, prompt: str, timeout: int) -> str` method whose body is `argv = ["claude", "-p"]; return self._run_subprocess(argv, prompt, timeout)`. Zero direct subprocess imports; the mixin owns every subprocess call. `isinstance(ClaudeAdapter(), Adapter)` is True at runtime via the runtime_checkable Protocol's structural typing (the class declares both `name: str` and `invoke(prompt, timeout) -> str`). All four Phase 4 safety properties (UTF-8/replace decoding, mandatory timeout, process-tree kill, empty-stdout defense) flow through ClaudeAdapter without it touching subprocess directly -- the proof-of-concept that GeminiAdapter and CodexAdapter (Phase 7) will follow the same template line-for-line. Plus `src/ultra_claude/adapters/__init__.py` updated (1263 bytes, 26 lines, was 923 bytes / 21 lines): added `from .claude import ClaudeAdapter`; `__all__` extended to `["Adapter", "_SubprocessAdapterMixin", "ClaudeAdapter"]` with `# noqa: RUF022` plus justifying comment for chronological-by-introduction order; module docstring updated to mention ClaudeAdapter as landed (no longer "Phase 4 deliverable -- not yet shipped"). All 6 plan-level verification commands PASS: `from ultra_claude.adapters import ClaudeAdapter, Adapter` works and `isinstance(ClaudeAdapter(), Adapter)` is True; mypy --strict on `src/ultra_claude/adapters/` -> clean (3 files); ruff check on `src/ultra_claude/adapters/` -> clean; pytest 16/16 PASS (zero regression); LF-only on disk on both files; no `import subprocess` substring in `claude.py`. Plus the Task 1 inline assertion block (5 source-introspection asserts) all PASS. Two Rule-3 deviations: (1) docstring on claude.py rephrased to avoid the literal `import subprocess` substring -- the plan's verification command checks `'import subprocess' not in src` (substring, not AST), so descriptive prose containing the literal phrase tripped the assertion; replaced with semantically equivalent wording ("This file deliberately does NOT pull in the stdlib subprocess module"); (2) ruff RUF022 on `__all__` order in `adapters/__init__.py` -- the plan acceptance criteria demand `["Adapter", "_SubprocessAdapterMixin", "ClaudeAdapter"]` in chronological-by-introduction order (matching `exceptions.py` from 04-01), so added `# noqa: RUF022` plus justifying comment. Atomic commits: `85e1c8f` (feat(04-02): add ClaudeAdapter wrapping `claude -p` via _SubprocessAdapterMixin) + `40dd2ab` (feat(04-02): re-export ClaudeAdapter from adapters package). SUMMARY at `.planning/phases/04-adapter-protocol-claudeadapter/04-02-SUMMARY.md`. Requirements: ADP-05 COMPLETE; TST-05 remains for plan 04-03.

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

**Last action:** Executed Phase 4 plan 04-02 (ClaudeAdapter). Created `src/ultra_claude/adapters/claude.py` (4222 bytes, 95 lines, LF-only, ASCII-only) defining `class ClaudeAdapter(_SubprocessAdapterMixin)` with three class-level attributes (`name = cli_name = "claude"`; `auth_error_markers: tuple[str, ...] = ("not logged in", "please run \`claude login\`", "please run /login", "authentication required", "authentication failed")` -- all lowercase, the mixin matches case-insensitively) and a single `invoke(self, prompt: str, timeout: int) -> str` method whose body is `argv = ["claude", "-p"]; return self._run_subprocess(argv, prompt, timeout)`. Zero direct subprocess imports; the mixin from 04-01 owns every subprocess call. `isinstance(ClaudeAdapter(), Adapter)` is True at runtime. All four Phase 4 safety properties (UTF-8/replace, mandatory timeout, process-tree kill, empty-stdout defense) flow through ClaudeAdapter without it touching subprocess directly -- proof-of-concept that GeminiAdapter and CodexAdapter (Phase 7) will follow the same template line-for-line. Updated `src/ultra_claude/adapters/__init__.py` (1263 bytes, 26 lines, was 923 / 21): added `from .claude import ClaudeAdapter`; `__all__` extended to `["Adapter", "_SubprocessAdapterMixin", "ClaudeAdapter"]` with `# noqa: RUF022` plus justifying comment for chronological-by-introduction order; module docstring updated to mention ClaudeAdapter as landed. All 6 plan-level verification commands PASS: `from ultra_claude.adapters import ClaudeAdapter, Adapter` works and `isinstance(ClaudeAdapter(), Adapter)` is True; mypy --strict on `src/ultra_claude/adapters/` clean (3 files); ruff check clean; pytest 16/16 PASS (zero regression); LF-only on disk on both files; no `import subprocess` substring in `claude.py`. Plus the Task 1 inline assertion block (5 source-introspection asserts) all PASS. Two Rule-3 deviations: (1) docstring on claude.py rephrased to avoid the literal `import subprocess` substring -- the plan's verification command checks `'import subprocess' not in src` (substring, not AST), so descriptive prose containing the literal phrase tripped the assertion; replaced with semantically equivalent wording ("This file deliberately does NOT pull in the stdlib subprocess module"); (2) ruff RUF022 on `__all__` order in `adapters/__init__.py` -- the plan acceptance criteria demand `["Adapter", "_SubprocessAdapterMixin", "ClaudeAdapter"]` in chronological-by-introduction order (matching `exceptions.py` from 04-01), so added `# noqa: RUF022` plus justifying comment. Atomic commits: `85e1c8f` (feat(04-02): add ClaudeAdapter wrapping `claude -p` via _SubprocessAdapterMixin) + `40dd2ab` (feat(04-02): re-export ClaudeAdapter from adapters package). SUMMARY at `.planning/phases/04-adapter-protocol-claudeadapter/04-02-SUMMARY.md`. Plan 04-02 CLOSED; Phase 4 2/3 plans complete; ADP-05 closed.

**Next action:** Plan 04-03 (tests + TST-05 lint test) is the last 04 plan and is now unblocked. It creates `tests/test_adapters_base.py` (Protocol structural typing tests using a duck-typed FakeAdapter), `tests/test_adapter_claude.py` (5 paths via `pytest-subprocess` `fp` fixture: argv+stdin happy path, empty stdout, FileNotFoundError, auth marker, TimeoutExpired+process-tree-kill), and `tests/test_subprocess_lint.py` (TST-05: `ast`-walks `src/ultra_claude/` and fails the build on any `subprocess.run`/`subprocess.Popen` missing `text=True`/`encoding="utf-8"`/`errors="replace"` or with `shell=True`). After 04-03 lands, Phase 4 fully closes (ADP-01..05, ADP-08, TST-05 all complete). Phase 5 (Stop Conditions) remains parallelizable. Run `/gsd-execute-phase 4` to continue, or `/gsd-plan-phase 5` to decompose Phase 5.

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
- `src/ultra_claude/exceptions.py` — landed in plan 02-01; extended in plan 04-01 with `AdapterError` + `AdapterAuthError`
- `src/ultra_claude/config.py` — landed in plan 02-02
- `src/ultra_claude/transcript.py` — landed in plan 03-01, consumed by Phase 5+ (Transcript + TurnRecord) and Phase 6 (orchestrator's append-as-you-go writer)
- `src/ultra_claude/adapters/__init__.py` — landed in plan 04-01, updated in 04-02 to re-export `ClaudeAdapter`; will gain `GeminiAdapter`/`CodexAdapter` in Phase 7
- `src/ultra_claude/adapters/base.py` — landed in plan 04-01; the choke point for every ultra-claude adapter (Adapter Protocol + safe-subprocess mixin); consumed by 04-02 (ClaudeAdapter — landed), 04-03 (tests + TST-05 lint), Phase 7 (Gemini/Codex adapters)
- `src/ultra_claude/adapters/claude.py` — newly landed in plan 04-02; first concrete adapter, wraps `claude -p` via the mixin; consumed by 04-03 tests and Phase 6 orchestrator
- `.planning/phases/04-adapter-protocol-claudeadapter/04-CONTEXT.md` — phase 4 context (decisions, code insights, specifics)
- `.planning/phases/04-adapter-protocol-claudeadapter/04-01-PLAN.md` — completed plan
- `.planning/phases/04-adapter-protocol-claudeadapter/04-01-SUMMARY.md` — completion summary for 04-01
- `.planning/phases/04-adapter-protocol-claudeadapter/04-02-PLAN.md` — completed plan (this plan)
- `.planning/phases/04-adapter-protocol-claudeadapter/04-02-SUMMARY.md` — completion summary for 04-02 (this plan)
- `.planning/phases/04-adapter-protocol-claudeadapter/04-03-PLAN.md` — pending plan (tests + TST-05 lint)
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
*Plan 04-01 completed: 2026-05-02 — commits e4423d0 (feat: add AdapterError and AdapterAuthError exceptions) + eceb9da (feat: add Adapter Protocol and _SubprocessAdapterMixin); ADP-01..04, ADP-08 all COMPLETE; mypy --strict + ruff clean across all 3 files; 16/16 existing tests still PASS (zero regression); 6 inline integration smoke checks PASS; Phase 4 1/3 plans complete*
*Plan 04-02 completed: 2026-05-02 — commits 85e1c8f (feat(04-02): add ClaudeAdapter wrapping `claude -p` via _SubprocessAdapterMixin) + 40dd2ab (feat(04-02): re-export ClaudeAdapter from adapters package); ADP-05 COMPLETE; mypy --strict + ruff clean across all 4 files (exceptions.py, adapters/__init__.py, adapters/base.py, adapters/claude.py); 16/16 existing tests still PASS (zero regression); zero direct subprocess imports in claude.py; Phase 4 2/3 plans complete*
