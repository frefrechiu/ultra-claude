# Roadmap: ultra-claude

**Created:** 2026-05-02
**Granularity:** fine (9 phases)
**Parallelization:** enabled
**Coverage:** 58/58 v1 requirements mapped
**Core Value:** A user can run `ultra-claude run task.md` and get three CLI agents debating their problem in a transcript file — using only their existing CLI logins, no API keys.

## Phases

- [ ] **Phase 1: Project Skeleton & PyPI Name Reservation** - Reserve `ultra-claude` on PyPI as a `0.0.1` stub, ship `pyproject.toml`/LICENSE/.gitignore/`__version__` exposure
- [x] **Phase 2: Config Schema & YAML Loader** - Pydantic v2 models for `RoundtableConfig`/`AgentConfig` with helpful validation errors
- [x] **Phase 3: Transcript Module** - Append-as-you-go markdown writer with sentinel turn delimiters and JSONL sidecar
- [x] **Phase 4: Adapter Protocol & ClaudeAdapter** - `Adapter` `typing.Protocol` + `_SubprocessAdapterMixin` + first concrete adapter; locks the subprocess invocation contract
- [x] **Phase 5: Stop Conditions** - `Keyword` (anchored regex + unanimity-window), `MaxTurns`, `AnyOf` composite
- [x] **Phase 6: Orchestrator Loop** - `run(config, task) -> Path` with round-robin turns, transcript-as-context, structured stderr logging
- [x] **Phase 7: Gemini & Codex Adapters** - Two more adapters reusing the proven mixin; validates the empty-stdout defense against the live Codex bug
- [ ] **Phase 8: CLI Surface & `debate` Preset** - `ultra-claude run`/`doctor`/`--version`/`--help` with all flags + bundled `presets/debate.yaml`
- [ ] **Phase 9: Tests, Docs, Examples & v0.1.0 Release** - Full test suite (mocked subprocess), README quickstart, examples directory, manual PyPI publish of `v0.1.0`

## Phase Details

### Phase 1: Project Skeleton & PyPI Name Reservation
**Goal**: Reserve the PyPI name `ultra-claude` as a stub release and ship the bare repository scaffolding so every later phase has a working `pip install -e .` foundation.
**Depends on**: Nothing (first phase, must run before any feature work)
**Parallelizable with**: Nothing — all later phases depend on this
**Requirements**: PKG-02, PKG-03, PKG-04, PKG-05, PKG-07
**Success Criteria** (what must be TRUE):
  1. `pip install ultra-claude==0.0.1` from PyPI succeeds and resolves to a stub package owned by the project author (squat protection in place per Pitfall #5)
  2. The repository at HEAD contains `pyproject.toml` (hatchling backend, click/pydantic v2/pyyaml dependencies pinned), `LICENSE` (MIT) at root, and a `.gitignore` covering Python build artifacts and editor files
  3. `python -c "import ultra_claude; print(ultra_claude.__version__)"` prints `0.0.1` and the printed string equals the `[project] version` value in `pyproject.toml`
  4. `pip install -e ".[dev]"` in a clean virtualenv succeeds without errors
**Plans:** 3 plans
- [x] 01-01-PLAN.md — Repository skeleton (LICENSE, .gitignore, README, CHANGELOG, src/ultra_claude/__init__.py with __version__)
- [x] 01-02-PLAN.md — pyproject.toml with hatchling backend, pinned runtime/dev deps, dynamic version, src layout, ruff/mypy/pytest tool config
- [x] 01-03-PLAN.md — Build sdist+wheel, clean-venv smoke test, PUBLISH.md runbook + manual `twine upload` checkpoint (autonomous portion COMPLETE; PKG-05 user-action twine upload pending — runbook at `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md`)
**UI hint**: no

### Phase 2: Config Schema & YAML Loader
**Goal**: Make `ultra-claude.yaml` a fully-validated input boundary so every later phase can consume a `RoundtableConfig` instance with confidence.
**Depends on**: Phase 1
**Parallelizable with**: Phase 3 (no shared module surface between config schema and transcript writer)
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-04, CFG-05
**Success Criteria** (what must be TRUE):
  1. A user writing a valid `ultra-claude.yaml` (with `agents`, `max_turns`, `stop_keywords`, `transcript_path`) gets back a typed `RoundtableConfig` object via the loader
  2. Each `agent` entry requires `name`, `role`, `adapter` (Literal `claude`/`gemini`/`codex`), and `system_prompt` — omitting any of these produces a Pydantic error pointing at the offending field
  3. Omitting `max_turns` defaults to `12`; omitting `stop_keywords` defaults to `["AGREED", "DONE"]`; setting `turn_order` to anything other than `round_robin` is rejected at validation time
  4. Invalid YAML syntax or invalid config types produce a single human-readable error message that names the field path (e.g. `agents[0].adapter: invalid value 'clade'`), not a Python stack trace
**Plans:** 2 plans
- [x] 02-01-PLAN.md — Add `src/ultra_claude/exceptions.py` with `ConfigError` (exception class shared with future Phase 4 adapters; supports CFG-03) — COMPLETE 2026-05-02 (commit ddfca71); CFG-03 partial
- [x] 02-02-PLAN.md — Add `src/ultra_claude/config.py` (`AgentConfig`, `RoundtableConfig`, `load_config`, `format_validation_error`) plus `tests/test_config.py` covering all 6 CONTEXT.md cases (CFG-01..CFG-05) — COMPLETE 2026-05-02 (commits e97325a + 5c272f0); 8/8 tests pass; CFG-01..CFG-05 all complete
**UI hint**: no

### Phase 3: Transcript Module
**Goal**: Provide a single source of truth for conversation state — append-as-you-go markdown plus a parseable JSONL sidecar — so adapters and stop conditions can read/write turns without owning file IO.
**Depends on**: Phase 2 (uses `AgentConfig` for metadata)
**Parallelizable with**: Phase 2 (loosely — JSONL records reference `AgentConfig` shape but only depend on its fields)
**Requirements**: TRX-01, TRX-02, TRX-03, TRX-04, TRX-05
**Success Criteria** (what must be TRUE):
  1. Running a 3-turn synthetic test produces a markdown file that is appended (not rewritten) after each turn — `tail -f` on the file streams content as turns arrive
  2. Each turn in the markdown file is delimited by a non-markdown HTML-comment sentinel (e.g. `<!-- turn:N agent:Claude -->`) that survives re-prompting without being parsed as content
  3. Reading the `<transcript>.jsonl` sidecar back yields one JSON object per turn with `turn`, `agent`, `role`, `prompt_hash`, and `output` fields — the sidecar is written atomically alongside the markdown
  4. On Windows, `Path.read_bytes(transcript)` contains zero `\r\n` sequences (LF-only) and decodes cleanly as UTF-8
**Plans:** 1 plan
- [x] 03-01-PLAN.md — Add `src/ultra_claude/transcript.py` (`TurnRecord` Pydantic model + `Transcript` class with `append_turn`/`read_turns`/`markdown_path`/`jsonl_path`/`__len__`, SHA-256 prompt hashing, LF-only writes, UTF-8 encoding, idempotent re-open) plus `tests/test_transcript.py` (8 tests covering all 5 TRX requirements + 3 locked decisions) — COMPLETE 2026-05-02 (commits 88b6186 + 6230667); 8/8 transcript tests pass + 16/16 full suite PASS; TRX-01..TRX-05 all complete
**UI hint**: no

### Phase 4: Adapter Protocol & ClaudeAdapter
**Goal**: Lock in the subprocess invocation contract once — stdin-piped prompts, mandatory timeout, UTF-8/replace, empty-stdout defense, cross-platform process-tree kill — and prove it on the first concrete adapter so the remaining two are nearly free.
**Depends on**: Phase 1 (needs the package skeleton); independent of Phases 2-3
**Parallelizable with**: Phase 5 (stop conditions consume `Transcript` only, not adapters)
**Requirements**: ADP-01, ADP-02, ADP-03, ADP-04, ADP-05, ADP-08, TST-05
**Success Criteria** (what must be TRUE):
  1. A class implementing `name: str` and `invoke(prompt: str, timeout: int) -> str` is recognised as an `Adapter` without inheriting anything (Protocol structural subtyping); `runtime_checkable` `isinstance` works
  2. `ClaudeAdapter().invoke("hi", timeout=10)` (mocked via `pytest-subprocess`) issues a `subprocess.run` call with list-form argv, `text=True`, `encoding="utf-8"`, `errors="replace"`, mandatory `timeout`, `shell=False`, and a stdin-piped prompt (no prompt-on-argv)
  3. When the mocked subprocess returns `returncode=0` AND empty stdout, the adapter raises `AdapterError` (defends against the live `codex exec` TTY bug per Pitfall #1, even though this phase is `ClaudeAdapter`)
  4. When the underlying CLI is missing (`FileNotFoundError`) or returns a known auth-error string, the adapter raises `AdapterAuthError` with re-auth instructions naming the CLI
  5. When `subprocess.TimeoutExpired` fires, the adapter kills the entire process tree on both POSIX (`os.killpg`) and Windows (`taskkill /T /F`); a CI lint test fails the build if any `subprocess.run` call in the codebase is missing `encoding="utf-8"` or `errors="replace"`
**Plans:** 3 plans
- [x] 04-01-PLAN.md — Extend `src/ultra_claude/exceptions.py` with `AdapterError`/`AdapterAuthError`; create `src/ultra_claude/adapters/__init__.py` + `src/ultra_claude/adapters/base.py` (`Adapter` `typing.Protocol` + `_SubprocessAdapterMixin` with safe `_run_subprocess`: stdin pipe, UTF-8/replace, mandatory timeout, empty-stdout defense, cross-platform process-tree kill via `os.killpg`/`taskkill /T /F`) — COMPLETE 2026-05-02 (commits e4423d0 + eceb9da); ADP-01..04, ADP-08 all complete; mypy --strict + ruff clean; 16/16 existing tests still PASS
- [x] 04-02-PLAN.md — Create `src/ultra_claude/adapters/claude.py` (`ClaudeAdapter(_SubprocessAdapterMixin)` with `name="claude"`, `cli_name="claude"`, `auth_error_markers`, and one-line `invoke` delegating to `_run_subprocess(["claude", "-p"], prompt, timeout)`); update `adapters/__init__.py` to re-export — COMPLETE 2026-05-02 (commits 85e1c8f + 40dd2ab); ADP-05 closed; mypy --strict + ruff clean; 16/16 tests still PASS (zero regression); zero direct subprocess imports in claude.py (Phase 4 contract proven on first concrete adapter)
- [x] 04-03-PLAN.md — Create `tests/test_adapters_base.py` (Protocol structural typing), `tests/test_adapter_claude.py` (5 paths via `pytest-subprocess` `fp` fixture: argv+stdin happy, empty stdout, FileNotFoundError, auth marker, TimeoutExpired+process-tree-kill), `tests/test_subprocess_lint.py` (TST-05: `ast`-walks `src/ultra_claude/` and fails the build on any `subprocess.run`/`subprocess.Popen` missing `text=True`/`encoding="utf-8"`/`errors="replace"` or with `shell=True`) — COMPLETE 2026-05-02 (commits ab17d77 + e0ea60e + e16c4f9); 20 new tests (7 base + 10 claude + 3 lint); 36/36 full suite PASS (zero regression); ADP-01..05, ADP-08, TST-05 all verified by executable tests; manual paranoia check confirmed lint test FIRES on synthetic bad subprocess call
**UI hint**: no

### Phase 5: Stop Conditions
**Goal**: Provide three composable stop strategies (`Keyword`, `MaxTurns`, `AnyOf`) so the orchestrator can terminate cleanly without false-positive consensus from sycophantic agents.
**Depends on**: Phase 3 (`StopCondition.check(transcript)` consumes a `Transcript`)
**Parallelizable with**: Phase 4 (different module surface)
**Requirements**: STP-01, STP-02, STP-03, STP-04, STP-05
**Success Criteria** (what must be TRUE):
  1. A `StopCondition` Strategy interface defines `check(transcript) -> bool`; concrete classes implement it without coupling to each other
  2. `Keyword(["AGREED"])` applied to a transcript where one agent says "I am NOT going to say AGREED yet" returns `False` — the match is anchored multiline (e.g. `^## Decision\nAGREED\s*$`), not naive substring (mitigates Pitfall #4)
  3. `Keyword` with default `N=2, M=2` returns `True` only when the marker appears in the last 2 turns from 2 distinct agents — single-agent self-stopping is impossible
  4. `MaxTurns(12)` returns `True` exactly when the transcript reaches 12 turns; `AnyOf([MaxTurns(12), Keyword(["AGREED"])])` short-circuits on the first match
**Plans:** 1 plan
- [x] 05-01-PLAN.md — Add `src/ultra_claude/stop_conditions.py` (`StopCondition` Protocol + `Keyword` (anchored `re.MULTILINE` regex with unanimity-window n=2/m=2) + `MaxTurns` + `AnyOf`) plus `tests/test_stop_conditions.py` (6 tests covering STP-01..STP-05 + Pitfall #4) — COMPLETE 2026-05-02 (commits e56a779 + 9dbc164); STP-01..STP-05 all complete; 6/6 new tests pass; 42/42 full suite PASS (zero regression)
**UI hint**: no

### Phase 6: Orchestrator Loop
**Goal**: Compose adapters + transcript + stop conditions into a single `run(config, task) -> Path` function that drives the round-robin debate end-to-end with structured stderr logging and continue-on-error semantics.
**Depends on**: Phase 4 (Adapter), Phase 3 (Transcript), Phase 5 (StopCondition)
**Parallelizable with**: Phase 7 (Gemini/Codex adapters reuse the mixin from Phase 4 and don't touch orchestrator code)
**Requirements**: ORC-01, ORC-02, ORC-03, ORC-04, ORC-05, ORC-06
**Success Criteria** (what must be TRUE):
  1. `run(config, task)` returns a `Path` to the completed transcript file; given a 3-agent config with `max_turns=6`, the orchestrator iterates agents in declared round-robin order for 6 turns and writes a transcript that contains all 6 turns in order
  2. Each turn's prompt to the adapter contains: the original task statement, the full transcript so far, the current agent's `system_prompt`, AND a goal-anchoring re-injection of the original task (mitigates problem drift, Pitfall #6)
  3. The orchestrator checks all wired stop conditions after every turn and exits cleanly on the first match (returns the transcript path with status logged to stderr)
  4. When an adapter raises an error mid-run, the error is logged to stderr via `logging` and a placeholder turn is appended; the run continues unless `abort_on_error: true` is set in config (default `false`)
  5. With stdout piped to a file, the file contains only the final transcript path; all progress messages ("turn N starting", "turn N completed", "stopped on Keyword") appear on stderr only — stdout-stderr discipline holds (Twelve-Factor logs)
**Plans:** 2 plans
- [x] 06-01-PLAN.md — Adapter registry dispatcher + orchestrator run() function (registry.py + orchestrator.py) — COMPLETE 2026-05-02 (commits 8cfee40 + b9b80b3); ORC-01..ORC-06 satisfied at IMPLEMENTATION level; 363 lines added (registry.py 56 / orchestrator.py 307); 5/5 end-to-end smoke checks PASS via inline `python -c`; 42/42 full suite PASS (zero regression — orchestrator/registry only ADD code); mypy --strict on src/ultra_claude clean (10 modules; was 8); ruff clean on the 2 new files; LF-only + ASCII-only on disk; zero Rule-N deviations during execution
- [x] 06-02-PLAN.md — Orchestrator test suite with FakeAdapter helper (8 tests covering ORC-01..ORC-06) — COMPLETE 2026-05-02 (commit 747f003); 8 new tests cover round-robin/GOAL ANCHOR/transcript-so-far/keyword unanimity/continue-on-error/abort-on-error/return-path/stdout+caplog discipline; 50/50 full suite PASS (42 prior + 8 new; zero regression); 460 lines added; LF-only + ASCII-only on disk; staged blob LF-only despite `core.autocrlf=true`; mypy --strict on src still clean (10 source files); ruff clean; 2 Rule-N deviations (Rule 1: caplog instead of capsys.err for logger assertions because pytest's logging plugin diverts records — supersedes plan's `propagate=False` suggestion; Rule 3: ruff I001 1-blank-line fix in import block); ORC-01..ORC-06 all COMPLETE; Phase 6 fully CLOSED; Phase 7 unblocked
**UI hint**: no

### Phase 7: Gemini & Codex Adapters
**Goal**: Add the remaining two concrete adapters by reusing `_SubprocessAdapterMixin`, proving the contract works for all three vendors and that the empty-stdout defense correctly catches the known `codex exec` bug.
**Depends on**: Phase 4 (Adapter Protocol + Mixin)
**Parallelizable with**: Phase 6 (independent module surface — adapters/ vs orchestrator.py)
**Requirements**: ADP-06, ADP-07
**Success Criteria** (what must be TRUE):
  1. `GeminiAdapter().invoke("hi", timeout=10)` (mocked) issues `subprocess.run` with argv starting `["gemini", "-p"]` and prompt piped via stdin (no prompt-on-argv to avoid Windows ~8KB cmd.exe limit, Pitfall #1)
  2. `CodexAdapter().invoke("hi", timeout=10)` (mocked) issues `subprocess.run` with argv starting `["codex", "exec"]` and prompt piped via stdin
  3. When the mocked Codex CLI returns the live-bug pattern (`returncode=0`, `stdout=""`), `CodexAdapter` raises `AdapterError` with a clear message naming `codex` — the empty-stdout defense from Phase 4's mixin catches the regression automatically (Pitfall #2)
  4. Both adapters return trimmed stdout on the happy path and raise `AdapterAuthError` on the same auth-error patterns as `ClaudeAdapter`
**Plans:** 2 plans
- [x] 07-01-PLAN.md — Create gemini.py + codex.py concrete adapters reusing _SubprocessAdapterMixin; wire both through adapters/__init__.py and registry.py (replace NotImplementedError branch with concrete instances). 2 tasks, autonomous, Wave 1. — COMPLETE 2026-05-02 (commits 4a09f27 + 5f067c1); ADP-06, ADP-07 implementation-level COMPLETE; 50/50 full suite PASS (zero regression — new adapters not yet test-covered, that lands in 07-02); mypy --strict on src/ultra_claude clean (12 source files = 10 prior + gemini.py + codex.py); ruff clean on the 4 modified/new files; LF-only + ASCII-only on disk; codex.py module docstring references openai/codex#19945 per D-03; 1 Rule-N deviation (Rule 3: # noqa: RUF022 placement on multi-line __all__ moved from closing bracket to opening bracket per ruff 0.15.8 RUF022+RUF100 dual-fire)
- [x] 07-02-PLAN.md — Mirror tests/test_adapter_claude.py onto tests/test_adapter_gemini.py and tests/test_adapter_codex.py via pytest-subprocess fp fixture (zero real CLIs); test_adapter_codex.py adds the headline test_codex_empty_stdout_bug_regression that documents Pitfall #2 / openai/codex#19945. 2 tasks, autonomous, Wave 2 (depends on 07-01) — COMPLETE 2026-05-02 (commits 4377a27 + e538e88); ADP-06 + ADP-07 now both IMPLEMENTATION + TEST verified; 22 new tests across 2 new files (test_adapter_gemini.py 261 lines / 11 collected + test_adapter_codex.py 333 lines / 11 collected including the headline test_codex_empty_stdout_bug_regression at line 129); 72/72 full suite PASS (50 prior + 22 new); ruff clean; TST-05 lint still 3/3 PASS; LF-only + ASCII-only on disk; staged blobs LF-only despite `core.autocrlf=true`; `openai/codex#19945` literal present 3 times in codex test file; zero Rule-N deviations (plan executed verbatim); zero source changes (test-only plan); zero deletions; Phase 7 fully CLOSED (2/2 plans, 2/2 ADP requirements complete); Phase 8 (CLI Surface) UNBLOCKED
**UI hint**: no

### Phase 8: CLI Surface & `debate` Preset
**Goal**: Ship the user-runnable `ultra-claude` binary with the full v1 flag surface (`run`, `doctor`, `--version`, `--help`) plus a bundled `debate` preset so the README quickstart works in a clean directory.
**Depends on**: Phase 6 (orchestrator), Phase 7 (all three adapters)
**Parallelizable with**: Nothing (consumes everything before it)
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, CLI-06, CLI-07, CLI-08, CLI-09, CLI-10, CLI-11, PRE-01
**Success Criteria** (what must be TRUE):
  1. `ultra-claude --version` prints the package `__version__` and exits `0`; `ultra-claude --help` prints click-generated help including subcommands `run` and `doctor` and exits `0`
  2. `ultra-claude run task.md` (with `./ultra-claude.yaml` present) loads config, runs the orchestrator, and prints the resulting transcript path on stdout; supports `--config <path>`, `--preset debate`, `--inline "<task>"`, `--dry-run`, `--output <path>`
  3. `ultra-claude run --preset debate` works in any directory (no local YAML required) and uses the bundled `presets/debate.yaml` containing three agents (architect: claude, critic: gemini, implementer: codex)
  4. `ultra-claude doctor` runs without invoking the orchestrator: it checks `claude`/`gemini`/`codex` on PATH, probes login state for each, and prints a per-CLI status table with `PASS`/`FAIL`/`UNKNOWN` columns
  5. Exit codes match Unix convention: `0` on success, `1` on runtime/adapter error, `2` on config validation error; live progress (e.g. "Claude is thinking…") renders to stderr only when stdout is a TTY and is suppressed when piped or redirected
**Plans**: TBD
**UI hint**: no

### Phase 9: Tests, Docs, Examples & v0.1.0 Release
**Goal**: Lock in the v1 quality bar (tests passing without real CLIs installed, type checks clean, README + CONTRIBUTING + examples/) and manually publish `v0.1.0` to PyPI as a real (not stub) release.
**Depends on**: Phase 8 (everything must be runnable end-to-end before we can capture an example transcript or write the quickstart)
**Parallelizable with**: Nothing (final phase)
**Requirements**: PKG-01, PKG-06, PRE-02, TST-01, TST-02, TST-03, TST-04, TST-06, TST-07, DOC-01, DOC-02
**Success Criteria** (what must be TRUE):
  1. `pytest` runs green in a clean virtualenv with NONE of `claude`/`gemini`/`codex` installed — adapter tests use `pytest-subprocess`'s `fp` fixture asserting exact argv, stdin payload, and timeout; orchestrator E2E tests use `tests/fixtures/echo_cli.py` as a fake CLI; `pytest-cov` reports coverage for `src/ultra_claude/`
  2. `ruff check` and `mypy --strict` (configured for `src/ultra_claude/`) pass with zero errors
  3. `python -m build` produces a wheel and sdist that install cleanly into a fresh virtualenv on macOS, Linux, AND Windows (smoke-tested before tagging)
  4. After the manual `python -m build` + `twine upload` of `0.1.0`, `pip install ultra-claude` on a fresh machine pulls the real release; the `ultra-claude` command is on PATH and `ultra-claude --version` prints `0.1.0`
  5. The repository at the v0.1.0 tag contains: `README.md` (one-line pitch, GIF placeholder block, 3-command quickstart, "why this exists" section, config example, "extending to new CLIs" pointer at the `Adapter` Protocol), `CONTRIBUTING.md` (dev setup, how to add an adapter, v1 policy that core ships only the three bundled adapters), and `examples/` directory containing at least one real captured transcript with its YAML config alongside it
**Plans**: TBD
**UI hint**: no

## Parallelization Summary

The following phase pairs can run concurrently (no shared module surface, no DAG dependency):

| Pair | Why Safe |
|------|----------|
| Phase 2 (Config) ‖ Phase 3 (Transcript) | Both depend only on Phase 1; Phase 3 references `AgentConfig` shape but does not import it during writes |
| Phase 4 (Adapter+ClaudeAdapter) ‖ Phase 5 (Stop conditions) | Stop conditions consume `Transcript` only; adapters consume nothing from stop_conditions module |
| Phase 6 (Orchestrator) ‖ Phase 7 (Gemini+Codex adapters) | Orchestrator imports adapters via the registry; concrete Gemini/Codex adapter files don't touch orchestrator.py |

Phases 1, 8, and 9 are strict serialization points — they cannot run in parallel with anything.

## Cross-Platform Concerns by Phase

| Phase | Windows-Specific Concern Owned Here |
|-------|-------------------------------------|
| Phase 3 (Transcript) | LF newlines on disk (`newline="\n"`); UTF-8 encoding for transcript writes |
| Phase 4 (Adapter+ClaudeAdapter) | `encoding="utf-8", errors="replace"` on every `subprocess.run`; cross-platform process-tree kill (POSIX `os.killpg`, Windows `taskkill /T /F`); stdin-piped prompts to avoid ~8KB cmd.exe argv limit; CI lint test (TST-05) blocking regressions |
| Phase 7 (Gemini+Codex) | Same encoding/argv discipline as Phase 4; specific Codex empty-stdout defense (Pitfall #2) |
| Phase 8 (CLI) | TTY detection for live progress (`sys.stdout.isatty()`) so piping works on Windows; clean exit codes from PowerShell and cmd.exe |
| Phase 9 (Release) | Manual smoke test: `python -m build` + install on Windows runner before tagging v0.1.0 |

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Skeleton & PyPI Name Reservation | 3/3 | Autonomous portion complete; PKG-05 awaits user `twine upload` per PUBLISH.md | - (closes when user reports "uploaded") |
| 2. Config Schema & YAML Loader | 2/2 | COMPLETE — Plan 02-01 (commit ddfca71, `ConfigError` class) + Plan 02-02 (commits e97325a + 5c272f0, schema + loader + 8-test pytest suite); CFG-01..CFG-05 all complete | 2026-05-02 |
| 3. Transcript Module | 1/1 | COMPLETE — Plan 03-01 (commits 88b6186 + 6230667, transcript module + 8-test pytest suite); TRX-01..TRX-05 all complete; 16/16 full suite PASS | 2026-05-02 |
| 4. Adapter Protocol & ClaudeAdapter | 3/3 | COMPLETE — Plan 04-01 (commits e4423d0 + eceb9da, exceptions + Adapter Protocol + `_SubprocessAdapterMixin`) + Plan 04-02 (commits 85e1c8f + 40dd2ab, `ClaudeAdapter`) + Plan 04-03 (commits ab17d77 + e0ea60e + e16c4f9, 20 new tests + TST-05 lint tripwire); ADP-01..05, ADP-08, TST-05 all complete; 36/36 full suite PASS; mypy --strict + ruff clean on src/ultra_claude/adapters and the 3 new test files | 2026-05-02 |
| 5. Stop Conditions | 1/1 | COMPLETE — Plan 05-01 (commits e56a779 + 9dbc164, `stop_conditions.py` + 6-test pytest suite); STP-01..STP-05 all complete; 42/42 full suite PASS; mypy --strict on src/ultra_claude clean (8 files; was 7); ruff clean on both new files | 2026-05-02 |
| 6. Orchestrator Loop | 2/2 | COMPLETE — Plan 06-01 (commits 8cfee40 + b9b80b3, registry.py + orchestrator.py implementation) + Plan 06-02 (commit 747f003, 8-test FakeAdapter suite); ORC-01..ORC-06 all complete; 50/50 full suite PASS; mypy --strict on src/ultra_claude clean (10 modules); ruff clean on all new files; LF-only + ASCII-only on disk | 2026-05-02 |
| 7. Gemini & Codex Adapters | 2/2 | COMPLETE — Plan 07-01 (commits 4a09f27 + 5f067c1, gemini.py + codex.py + adapters/__init__.py + registry.py wiring) + Plan 07-02 (commits 4377a27 + e538e88, test_adapter_gemini.py + test_adapter_codex.py incl. headline test_codex_empty_stdout_bug_regression); ADP-06, ADP-07 both IMPLEMENTATION + TEST verified; 72/72 full suite PASS (50 prior + 22 new tests = 72; zero regression); mypy --strict on src/ultra_claude clean (12 modules); ruff clean on all 4 source + 2 new test files; LF-only + ASCII-only on disk; `openai/codex#19945` literal present in codex.py module docstring AND 3 times in test_adapter_codex.py per D-03; 1 Rule-N deviation across the phase (Rule 3 in 07-01: noqa: RUF022 placement on multi-line __all__; zero deviations in 07-02) | 2026-05-02 |
| 8. CLI Surface & `debate` Preset | 0/0 | Not started | - |
| 9. Tests, Docs, Examples & v0.1.0 Release | 0/0 | Not started | - |

## Coverage Validation

All 58 v1 requirements mapped to exactly one phase. No orphans, no duplicates.

| Category | Count | Distribution |
|----------|-------|--------------|
| PKG (Packaging) | 7 | Phase 1: PKG-02/03/04/05/07; Phase 9: PKG-01/06 |
| CFG (Config) | 5 | Phase 2: all |
| TRX (Transcript) | 5 | Phase 3: all |
| ADP (Adapters) | 8 | Phase 4: ADP-01/02/03/04/05/08; Phase 7: ADP-06/07 |
| STP (Stop conditions) | 5 | Phase 5: all |
| ORC (Orchestrator) | 6 | Phase 6: all |
| CLI (CLI surface) | 11 | Phase 8: all |
| PRE (Presets) | 2 | Phase 8: PRE-01; Phase 9: PRE-02 |
| TST (Testing) | 7 | Phase 4: TST-05; Phase 9: TST-01/02/03/04/06/07 |
| DOC (Documentation) | 2 | Phase 9: all |
| **Total** | **58** | **9 phases, 100% coverage** |

---
*Roadmap created: 2026-05-02 from PROJECT.md + REQUIREMENTS.md + research/*
*Last updated: 2026-05-02 after plan 07-02 autonomous completion (Phase 7 COMPLETE — 2/2 plans; tests/test_adapter_gemini.py + tests/test_adapter_codex.py landed via commits 4377a27 + e538e88; the headline test_codex_empty_stdout_bug_regression in codex test file at line 129 documents Pitfall #2 / openai/codex#19945 against the inherited Phase 4 mixin defense; ADP-06 + ADP-07 now both IMPLEMENTATION + TEST verified; 72/72 full suite PASS — 50 prior + 22 new tests = 72; zero regression; zero Rule-N deviations in 07-02 — plan executed verbatim; zero source changes — test-only plan; Phase 8 (CLI Surface) UNBLOCKED)*
*Plan 01-01 completed: 2026-05-02 (commits 562d05e, 2b15b36)*
*Plan 01-02 completed: 2026-05-02 (commit b9bf3c5)*
*Plan 01-03 completed (autonomous portion): 2026-05-02 (commits 3e31832, e96ccb6); user-action twine upload pending per PUBLISH.md*
*Phase 2 planned: 2026-05-02 (02-01-PLAN.md, 02-02-PLAN.md committed; ready for execution)*
*Plan 02-01 completed: 2026-05-02 (commit ddfca71 — feat: add ConfigError exception class); CFG-03 partial (foundation; full delivery in 02-02)*
*Plan 02-02 completed: 2026-05-02 (commits e97325a — feat: add config schema and YAML loader + 5c272f0 — test: add config validation test suite); CFG-01..CFG-05 all complete; Phase 2 fully closed*
*Plan 03-01 completed: 2026-05-02 (commits 88b6186 — feat: add transcript module with TurnRecord + Transcript classes + 6230667 — test: add transcript test suite covering TRX-01..TRX-05); TRX-01..TRX-05 all complete; Phase 3 fully closed*
*Plan 04-01 completed: 2026-05-02 (commits e4423d0 + eceb9da); ADP-01..04, ADP-08 all complete*
*Plan 04-02 completed: 2026-05-02 (commits 85e1c8f + 40dd2ab); ADP-05 complete*
*Plan 04-03 completed: 2026-05-02 (commits ab17d77 + e0ea60e + e16c4f9); TST-05 complete; Phase 4 fully closed (3/3 plans, 7/7 ADP+TST requirements)*
*Plan 05-01 completed: 2026-05-02 (commits e56a779 — feat(05-01): add StopCondition Protocol + Keyword + MaxTurns + AnyOf + 9dbc164 — test(05-01): add stop_conditions test suite covering STP-01..STP-05 + Pitfall #4); STP-01..STP-05 all complete; 42/42 full suite PASS (zero regression); Phase 5 fully closed*
*Plan 06-01 completed: 2026-05-02 (commits 8cfee40 + b9b80b3); ORC-01..ORC-06 satisfied at IMPLEMENTATION level; 363 lines added (registry.py + orchestrator.py); 5/5 end-to-end smoke checks PASS via inline `python -c`; 42/42 full suite PASS (zero regression); Phase 6 progress: 1/2 plans*
*Plan 06-02 completed: 2026-05-02 (commit 747f003 — test(06-02): add orchestrator test suite covering ORC-01..ORC-06); 8-test FakeAdapter suite covering round-robin/GOAL ANCHOR/transcript-so-far/keyword unanimity/continue-on-error/abort-on-error/return-path/stdout+caplog discipline; 460 lines added; 50/50 full suite PASS (42 prior + 8 new; zero regression); 2 Rule-N deviations (Rule 1: caplog instead of capsys.err; Rule 3: ruff I001 import-block formatting); ORC-01..ORC-06 all COMPLETE; Phase 6 fully CLOSED (2/2 plans, 6/6 ORC requirements); Phase 7 unblocked*
*Plan 07-01 completed: 2026-05-02 (commits 4a09f27 — feat(07-01): add GeminiAdapter and CodexAdapter + 5f067c1 — feat(07-01): wire Gemini/Codex into adapters package and registry); ADP-06, ADP-07 implementation-level COMPLETE; 222 lines added across 4 files (2 new: gemini.py 94 lines + codex.py 100 lines mirroring claude.py with vendor-specific deltas only; 2 modified: adapters/__init__.py 5-entry __all__ + registry.py concrete instantiation replacing NotImplementedError branch); 50/50 full suite PASS (zero regression — new adapters not yet test-covered, that lands in 07-02); mypy --strict on src/ultra_claude clean (12 source files = 10 prior + gemini.py + codex.py); ruff clean on the 4 modified/new files; LF-only + ASCII-only on disk; codex.py module docstring references openai/codex#19945 per D-03; 1 Rule-N deviation (Rule 3: # noqa: RUF022 placement on multi-line __all__ moved from closing bracket to opening bracket per ruff 0.15.8 RUF022+RUF100 dual-fire); 4 pre-existing ruff errors (Phase 2 config.py + tests/test_config.py) confirmed pre-existing via git stash round-trip and logged as out-of-scope at .planning/phases/07-gemini-codex-adapters/deferred-items.md; Phase 7 progress: 1/2 plans; 07-02 NEXT*
*Plan 07-02 completed: 2026-05-02 (commits 4377a27 — test(07-02): add GeminiAdapter test suite covering ADP-06 + e538e88 — test(07-02): add CodexAdapter test suite covering ADP-07 and openai/codex#19945 regression); ADP-06 + ADP-07 now both IMPLEMENTATION + TEST verified; 22 new tests across 2 new files (tests/test_adapter_gemini.py 261 lines / 10132 bytes / 6 functions / 11 collected with 5-entry auth-marker parametrize + tests/test_adapter_codex.py 333 lines / 13478 bytes / 7 functions / 11 collected with 4-entry auth-marker parametrize INCLUDING the headline test_codex_empty_stdout_bug_regression at line 129 documenting Pitfall #2 / openai/codex#19945 against the inherited Phase 4 mixin defense); 72/72 full suite PASS (50 prior + 22 new = 72; zero regression); ruff clean on both new test files; TST-05 lint test still 3/3 PASS (no new subprocess violations because new test files use pytest-subprocess `fp` fixture + `monkeypatch.setattr(subprocess, "Popen", ...)` only — zero direct subprocess imports); LF-only + ASCII-only on disk on both new files; staged blobs LF-only despite `core.autocrlf=true` (gemini blob 0 CRLF / 261 LF; codex blob 0 CRLF / 333 LF); `def test_codex_empty_stdout_bug_regression` present at tests/test_adapter_codex.py:129; `openai/codex#19945` literal present 3 times in codex test file (module docstring + comment block + regression-test docstring URL https://github.com/openai/codex/issues/19945); both files independently runnable in isolation; `from __future__ import annotations` in both; zero Rule-N deviations during execution — plan executed verbatim; zero source changes — test-only plan; zero deletions across both task commits; Phase 7 fully CLOSED (2/2 plans, 2/2 ADP requirements both IMPLEMENTATION + TEST verified); Phase 8 (CLI Surface) UNBLOCKED*
