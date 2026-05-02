# Requirements: ultra-claude

**Defined:** 2026-05-02
**Core Value:** A user can run `ultra-claude run task.md` and get three CLI agents debating their problem in a transcript file — using only their existing CLI logins, no API keys.

## v1 Requirements

Requirements for initial PyPI release (`v0.1.0`). Each maps to roadmap phases.

### Packaging & Distribution

- [ ] **PKG-01**: User can `pip install ultra-claude` from PyPI and the `ultra-claude` command is on PATH
- [x] **PKG-02**: Repository ships a valid `pyproject.toml` using the `hatchling` build backend with pinned minimum versions for click, pydantic v2, and pyyaml
- [x] **PKG-03**: Repository ships an `MIT LICENSE` file at the project root
- [x] **PKG-04**: Repository ships a `.gitignore` covering Python build artifacts, virtualenvs, and editor files
- [ ] **PKG-05**: A `0.0.1` stub package is reserved on PyPI under the name `ultra-claude` before any feature work merges (squat-protection) — *Build artifacts produced and validated locally in plan 01-03 (sdist + wheel pass twine check, clean-venv install verifies `__version__ == "0.0.1"` triple alignment); operator runbook at `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md`. Closure pending user-side `python -m twine upload dist/ultra_claude-0.0.1*` with their PyPI API token; mark complete after `pip install ultra-claude==0.0.1` from PyPI returns the stub.*
- [ ] **PKG-06**: `v0.1.0` is published to PyPI manually via `python -m build` + `twine upload` (implementation half delivered in plan 09-01 commits 8ade3e6 + bc8e3d1 + 6155dc6 — `__version__ = "0.1.0"` literal in src/ultra_claude/__init__.py + empty PEP 561 py.typed marker + CHANGELOG.md [0.1.0] - 2026-05-02 section listing the v1 feature surface; release-side closure (`python -m build` -> dist/ artifacts -> user `twine upload`) lands in plan 09-04)
- [x] **PKG-07**: `__version__` is exposed from `ultra_claude.__init__` and matches the `[project] version` in `pyproject.toml` (export delivered in plan 01-01 commit 2b15b36; dynamic-version wiring delivered in plan 01-02 commit b9bf3c5 — `[tool.hatch.version] path = "src/ultra_claude/__init__.py"` resolves statically to the `__version__ = "0.0.1"` literal; runtime cross-check after `pip install` lands in plan 01-03)

### Config Schema & Loader

- [x] **CFG-01**: User can author a `ultra-claude.yaml` file with `agents`, `max_turns`, `stop_keywords`, and `transcript_path` fields and have it validated by Pydantic v2
- [x] **CFG-02**: Each agent in config has `name`, `role`, `adapter` (literal: `claude` | `gemini` | `codex`), and `system_prompt` fields, all required
- [x] **CFG-03**: Invalid YAML or invalid config produces a human-readable error pointing at the offending field (Pydantic's structured error output)
- [x] **CFG-04**: `turn_order` field accepts only `round_robin` in v1 (Literal type); `max_turns` defaults to 12 when omitted
- [x] **CFG-05**: `stop_keywords` defaults to `["AGREED", "DONE"]` when omitted

### Transcript

- [x] **TRX-01**: Orchestrator writes the transcript as a markdown file, appended after every turn (so `tail -f` works during a run)
- [x] **TRX-02**: Each turn is delimited by a non-markdown sentinel (e.g. `<!-- turn:N agent:Claude -->`) so re-prompting the conversation does not collide with content markdown
- [x] **TRX-03**: A JSONL sidecar at `<transcript>.jsonl` is written in parallel, one record per turn, capturing turn index, agent name, role, prompt-hash, and raw output
- [x] **TRX-04**: Transcript file uses LF newlines on all platforms (`newline="\n"`)
- [x] **TRX-05**: Transcript content is encoded as UTF-8 on disk

### Adapters (subprocess-based)

- [x] **ADP-01**: An `Adapter` `typing.Protocol` defines the `invoke(prompt: str, timeout: int) -> str` contract; third-party adapters do not need to inherit
- [x] **ADP-02**: Internal `_SubprocessAdapterMixin` enforces the safe subprocess invocation contract: stdin-piped prompt, `text=True`, `encoding="utf-8"`, `errors="replace"`, mandatory timeout, list-form argv (`shell=False`)
- [x] **ADP-03**: Any adapter that returns `returncode == 0` AND empty stdout raises `AdapterError` (defends against the live Codex `exec` TTY bug and any future similar regression)
- [x] **ADP-04**: Adapter timeout triggers cross-platform process-tree kill (handles child processes on POSIX and Windows)
- [x] **ADP-05**: `ClaudeAdapter` invokes `claude -p` with prompt via stdin and returns trimmed stdout
- [x] **ADP-06**: `GeminiAdapter` invokes `gemini -p` with prompt via stdin and returns trimmed stdout
- [x] **ADP-07**: `CodexAdapter` invokes `codex exec` with prompt via stdin and returns trimmed stdout
- [x] **ADP-08**: Adapter raises a clear `AdapterAuthError` with re-auth instructions when the underlying CLI is not logged in

### Stop Conditions

- [x] **STP-01**: A `StopCondition` Strategy interface defines `check(transcript) -> bool`
- [x] **STP-02**: `Keyword` stop condition matches an anchored multiline regex (e.g. `^## Decision\n(AGREED|SHIP IT)\s*$`), NOT naive substring match
- [x] **STP-03**: `Keyword` requires the marker to appear in the last N turns from M distinct agents (unanimity-window) before stopping; defaults: N=2, M=2
- [x] **STP-04**: `MaxTurns` stop condition halts the orchestrator after `config.max_turns` turns
- [x] **STP-05**: `AnyOf` composite stops the run when any wrapped condition matches; orchestrator wires bundled conditions through `AnyOf` by default

### Orchestrator Loop

- [x] **ORC-01**: Orchestrator is a single function `run(config, task) -> Path` that returns the transcript path on completion
- [x] **ORC-02**: Orchestrator iterates agents in round-robin order for up to `max_turns` turns
- [x] **ORC-03**: Each turn's prompt = task statement + full transcript so far + the current agent's system prompt + a goal-anchoring re-injection of the original task (mitigates problem drift)
- [x] **ORC-04**: Orchestrator checks stop conditions after every turn and exits cleanly on first match
- [x] **ORC-05**: Adapter errors mid-run are logged to stderr; the run continues unless `abort_on_error: true` is set in config (default `false`)
- [x] **ORC-06**: Orchestrator writes structured progress to stderr via stdlib `logging` (turn N starting / completed / stopped); stdout stays clean for piping

### CLI

- [x] **CLI-01
**: `ultra-claude --version` prints `__version__` and exits 0
- [x] **CLI-02
**: `ultra-claude --help` prints click-generated help and exits 0
- [x] **CLI-03
**: `ultra-claude run <task-file>` reads the task, loads `./ultra-claude.yaml`, runs the orchestrator, and prints the transcript path on stdout
- [x] **CLI-04
**: `ultra-claude run --config <path>` overrides the default config location
- [x] **CLI-05
**: `ultra-claude run --preset <name>` loads a bundled preset (e.g. `--preset debate`) instead of a user config file
- [x] **CLI-06
**: `ultra-claude run --inline "<task>"` accepts the task as a string instead of a file path
- [x] **CLI-07
**: `ultra-claude run --dry-run` validates config + prints planned turn order without invoking any adapter
- [x] **CLI-08
**: `ultra-claude run --output <path>` overrides the transcript output path
- [x] **CLI-09
**: `ultra-claude doctor` checks for `claude`/`gemini`/`codex` on PATH, probes login state for each, and prints a per-CLI status table (PASS / FAIL / UNKNOWN)
- [x] **CLI-10
**: Exit codes follow Unix convention: `0` success, `1` runtime error, `2` config validation error
- [x] **CLI-11
**: Live progress (e.g. "Claude is thinking…") renders to stderr only when stdout is a TTY; suppressed when piped or redirected

### Presets & Examples

- [x] **PRE-01
**: A bundled `presets/debate.yaml` ships in the package with three agents (architect: claude, critic: gemini, implementer: codex) and is loadable via `--preset debate`
- [x] **PRE-02
**: An `examples/` directory in the repo contains at least one real captured transcript (e.g. fixing a failing test) with the YAML config alongside it

### Testing & CI

- [ ] **TST-01**: Test suite passes via `pytest` without any of `claude`/`gemini`/`codex` installed (subprocess fully mocked)
- [ ] **TST-02**: Adapter tests use `pytest-subprocess`'s `fp` fixture to assert exact argv, stdin payload, and timeout
- [x] **TST-03**: A `tests/fixtures/echo_cli.py` fake-CLI Python script enables orchestrator E2E tests without real LLM calls
- [x] **TST-04**: Test coverage of `src/ultra_claude/` is reported by `pytest-cov`
- [x] **TST-05**: A grep-based lint test fails the build if any `subprocess.run`/`subprocess.Popen` call in the codebase is missing `encoding="utf-8"` or `errors="replace"`
- [ ] **TST-06**: `ruff check` and `mypy` (configured strict for `src/ultra_claude/`) pass with zero errors
- [ ] **TST-07**: Manual `python -m build` produces a wheel and sdist that install cleanly into a fresh virtualenv on macOS, Linux, and Windows (smoke-tested before tagging v0.1.0)

### Documentation

- [x] **DOC-01
**: `README.md` opens with a one-line pitch, a GIF placeholder block (final GIF lands as part of release), a 3-command quickstart, a "why this exists" section, a config example, and a short "extending to new CLIs" pointing at the `Adapter` Protocol
- [x] **DOC-02
**: `CONTRIBUTING.md` documents dev setup, how to add an adapter, and the v1 policy that core ships only the three bundled adapters (third-party adapters live in their own packages)

## v2 Requirements

Deferred from v1. Tracked but not in current roadmap.

### Distribution / Release Automation

- **PKG-V2-01**: GitHub Actions test matrix on push/PR (Python 3.10/3.11/3.12/3.13 × ubuntu/macos/windows)
- **PKG-V2-02**: Auto-publish to PyPI via Trusted Publishing (OIDC) on `v*` tag push
- **PKG-V2-03**: TestPyPI dry-run step in the publish workflow

### Orchestration

- **ORC-V2-01**: `speaker_chooses` turn order — agent picks who replies next (AutoGen-style dispatch)
- **ORC-V2-02**: Per-turn timeouts in addition to global timeouts
- **ORC-V2-03**: Adapter retry with exponential backoff on transient subprocess failures
- **ORC-V2-04**: Concurrent CLI invocation when turn order does not require strict sequencing

### Stop Conditions

- **STP-V2-01**: `FileExists` stop condition — halts when a watched file appears
- **STP-V2-02**: `CustomRegex` stop condition — user-supplied pattern with anchoring
- **STP-V2-03**: `Predicate` stop condition — user-supplied Python callable

### Transcript

- **TRX-V2-01**: `ultra-claude resume <transcript>` continues a saved run from the JSONL sidecar
- **TRX-V2-02**: Sliding-window or summarization strategy for transcripts that exceed individual CLI context windows

### CLI / UX

- **CLI-V2-01**: TUI live view via Rich/Textual (`--tui` flag)
- **CLI-V2-02**: Plugin discovery via entry points (`[project.entry-points."ultra_claude.adapters"]`) so third-party adapters install transparently
- **CLI-V2-03**: Adapter import-path escape hatch (`adapter: "mypkg.MyAdapter"` in YAML for one-off adapters)

### Presets & Docs

- **PRE-V2-01**: Bundled `plan_review.yaml` preset
- **PRE-V2-02**: Bundled `debug.yaml` preset
- **DOC-V2-01**: `mkdocs-material` + `mkdocs-click` docs site at `frefrechiu.github.io/ultra-claude/`

### Promotion (post-release)

- **REL-V2-01**: r/LocalLLaMA, r/ClaudeAI, r/ChatGPTCoding launch posts
- **REL-V2-02**: Show HN ("Show HN: ultra-claude — multi-agent CLI orchestrator using subscription logins")
- **REL-V2-03**: X/Twitter post with GIF tagging @AnthropicAI, @GoogleDeepMind, @OpenAIDevs
- **REL-V2-04**: PRs to `awesome-claude-code` and similar curated lists

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| API-key-driven adapters | Defeats the entire value proposition. The pitch is "no API keys, use existing CLI logins." |
| Per-token streaming during a turn | `subprocess.run` is blocking by design; streaming would require per-CLI special casing and complicates the simple subprocess model. Append-as-you-go transcript writing delivers most of the perceived UX benefit. |
| Persistent agent memory across runs | The transcript IS the memory. Each run starts fresh from the task file. |
| Hosted SaaS version | Hosting requires API keys and undercuts the value prop. |
| Mobile app / GUI | Terminal-only tool. |
| Inter-agent direct messaging (out-of-band channel) | Agents communicate only via the shared transcript. The "they don't know the others exist" property is a feature. |
| Persistent agent memory / vector store | Transcript is the only state. Anything more starts to look like the API-key-driven frameworks we're avoiding. |
| Conversation branching / forking (Forky-style) | High complexity, niche use case, not competitive-essential. Reconsider in v3+ if user demand emerges. |
| Real-time streaming UI mid-turn | Same as per-token streaming — incompatible with blocking subprocess model. |
| Async / asyncio runtime | No streaming use case in v1; blocking subprocess is simpler and easier to test. Revisit only if v2 concurrent invocation requires it. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PKG-01 | Phase 9 | Pending |
| PKG-02 | Phase 1 | Complete (plan 01-02, commit b9bf3c5) |
| PKG-03 | Phase 1 | Complete (plan 01-01, commit 562d05e) |
| PKG-04 | Phase 1 | Complete (plan 01-01, commit 562d05e) |
| PKG-05 | Phase 1 | Pending (artifacts + runbook ready in plan 01-03; awaits user `twine upload`) |
| PKG-06 | Phase 9 | Implementation half complete in plan 09-01 (commits 8ade3e6 + bc8e3d1 + 6155dc6: 0.1.0 literal + py.typed marker + CHANGELOG [0.1.0] section); release-side closure deferred to plan 09-04 (`python -m build` + user `twine upload`) |
| PKG-07 | Phase 1 | Complete (plan 01-01 export commit 2b15b36 + plan 01-02 dynamic wiring commit b9bf3c5); runtime cross-check in plan 01-03 |
| CFG-01 | Phase 2 | Complete (plan 02-02 commits e97325a + 5c272f0 — `RoundtableConfig.from_yaml_string` + `load_config` parse valid YAML into typed `RoundtableConfig`; verified by `test_valid_yaml_parses_into_typed_config`) |
| CFG-02 | Phase 2 | Complete (plan 02-02 commits e97325a + 5c272f0 — `AgentConfig` requires `name`/`role`/`adapter` Literal/`system_prompt` with `min_length=1`; verified by `test_missing_agent_field_names_offending_field_path` + `test_invalid_adapter_literal_is_rejected_with_field_path`) |
| CFG-03 | Phase 2 | Complete (plan 02-01 commit ddfca71 + plan 02-02 commits e97325a + 5c272f0 — `ConfigError` wraps `yaml.YAMLError`/`pydantic.ValidationError`/`FileNotFoundError`; `format_validation_error` produces field-path-named lines; verified by `test_malformed_yaml_produces_human_readable_error` + `test_format_validation_error_produces_field_path_per_line`) |
| CFG-04 | Phase 2 | Complete (plan 02-02 commits e97325a + 5c272f0 — `turn_order: Literal['round_robin']` default `'round_robin'`; `max_turns: int = 12, ge=2`; verified by `test_non_round_robin_turn_order_is_rejected` + `test_defaults_for_max_turns_and_stop_keywords`) |
| CFG-05 | Phase 2 | Complete (plan 02-02 commits e97325a + 5c272f0 — `stop_keywords: list[str] = default_factory=lambda: ['AGREED', 'DONE']`; verified by `test_defaults_for_max_turns_and_stop_keywords`) |
| TRX-01 | Phase 3 | Complete (plan 03-01 commits 88b6186 + 6230667 — `Transcript.append_turn` writes markdown via `mode="a"`; verified by `test_three_turn_round_trip_appends_to_markdown` asserting strictly increasing file size between calls) |
| TRX-02 | Phase 3 | Complete (plan 03-01 commits 88b6186 + 6230667 — `_render_turn_block` emits `<!-- turn:{turn} agent:{agent} -->` sentinel; verified by `test_each_turn_has_html_comment_sentinel` with anchored multiline regex) |
| TRX-03 | Phase 3 | Complete (plan 03-01 commits 88b6186 + 6230667 — JSONL sidecar at `markdown_path.with_suffix(suffix + ".jsonl")` written via `TurnRecord.model_dump_json()` per turn with turn/agent/role/prompt_hash/output fields; verified by `test_jsonl_sidecar_records_match_schema`) |
| TRX-04 | Phase 3 | Complete (plan 03-01 commits 88b6186 + 6230667 — every `open()` passes `newline="\n"`; verified by `test_lf_only_on_disk` asserting `b"\r\n" not in path.read_bytes()` for both files) |
| TRX-05 | Phase 3 | Complete (plan 03-01 commits 88b6186 + 6230667 — every `open()` passes `encoding="utf-8"`; verified by `test_utf8_round_trip` with em-dash + smart quotes + rocket emoji) |
| ADP-01 | Phase 4 | Complete (plan 04-01 commit eceb9da — `src/ultra_claude/adapters/base.py` defines `@runtime_checkable class Adapter(Protocol)` with `name: str` and `invoke(prompt, timeout) -> str`; verified by inline isinstance smoke test on a duck-typed FakeAdapter; tests in 04-03 will lock this in) |
| ADP-02 | Phase 4 | Complete (plan 04-01 commit eceb9da — `_SubprocessAdapterMixin._run_subprocess` uses `subprocess.Popen` with `text=True, encoding="utf-8", errors="replace", shell=False`, list-form argv, mandatory timeout, prompt piped via stdin via `proc.communicate(input=prompt)`; mypy --strict + ruff clean) |
| ADP-03 | Phase 4 | Complete (plan 04-01 commit eceb9da — `_run_subprocess` raises `AdapterError` when `proc.returncode == 0 and not stdout.strip()` with a message naming `openai/codex#19945`; verified by inline integration smoke test) |
| ADP-04 | Phase 4 | Complete (plan 04-01 commit eceb9da — `subprocess.TimeoutExpired` in `_run_subprocess` calls `_kill_process_tree(proc)` BEFORE re-raising as `AdapterError`; POSIX `os.killpg(os.getpgid(pid), SIGKILL)` after `start_new_session=True`; Windows `taskkill /T /F /PID` after `CREATE_NEW_PROCESS_GROUP`; the taskkill subprocess.run itself uses the full safe-contract kwargs so 04-03's TST-05 lint test will not flag it) |
| ADP-05 | Phase 4 | Complete (plan 04-02 commits 85e1c8f + 40dd2ab — `src/ultra_claude/adapters/claude.py` defines `class ClaudeAdapter(_SubprocessAdapterMixin)` with `name = cli_name = "claude"`, 5-element lowercase `auth_error_markers` tuple, and one-line `invoke(prompt, timeout)` returning `self._run_subprocess(["claude", "-p"], prompt, timeout)`; zero direct subprocess imports; `isinstance(ClaudeAdapter(), Adapter)` is True; `adapters/__init__.py` re-exports ClaudeAdapter; mypy --strict + ruff clean; pytest 16/16 PASS zero regression; mocked-subprocess runtime tests in 04-03) |
| ADP-06 | Phase 7 | Complete (plan 07-01 commit 4a09f27 + 5f067c1 — IMPLEMENTATION: `src/ultra_claude/adapters/gemini.py` defines `class GeminiAdapter(_SubprocessAdapterMixin)` with `name = cli_name = "gemini"`, 4-element lowercase `auth_error_markers` tuple kept distinct from Claude/Codex per D-02, and one-line `invoke(prompt, timeout)` returning `self._run_subprocess(["gemini", "-p"], prompt, timeout)`; zero direct subprocess imports per CLAUDE.md Critical Constraint #1; `isinstance(GeminiAdapter(), Adapter)` is True via runtime_checkable Protocol; `registry.get_adapter("gemini")` returns concrete `GeminiAdapter()`. plan 07-02 commit 4377a27 — TEST VERIFICATION: `tests/test_adapter_gemini.py` (261 lines, 11 collected) covers all six locked-decision paths: argv+stdin happy-path (Pitfall #1 mitigation via `stdin_callable` capture), list-form `["gemini", "-p"]` argv (defensively asserted via `fp.calls`), empty-stdout AdapterError (Pitfall #2 inherited mixin defense), whitespace-only stdout same defense, FileNotFoundError -> AdapterAuthError, parametrized auth-marker substring (5 cases incl. uppercase + backticks-in-marker for `please run \`gemini auth login\``) -> AdapterAuthError, TimeoutExpired -> `_kill_process_tree` recorded via monkeypatch + AdapterError. 11/11 PASS in isolation; 72/72 full suite PASS) |
| ADP-07 | Phase 7 | Complete (plan 07-01 commit 4a09f27 + 5f067c1 — IMPLEMENTATION: `src/ultra_claude/adapters/codex.py` defines `class CodexAdapter(_SubprocessAdapterMixin)` with `name = cli_name = "codex"`, 3-element lowercase `auth_error_markers` tuple kept distinct from Claude/Gemini per D-02, and one-line `invoke(prompt, timeout)` returning `self._run_subprocess(["codex", "exec"], prompt, timeout)`; module docstring contains the literal `openai/codex#19945` reference per D-03 documenting why the inherited Pitfall #2 empty-stdout defense matters specifically here; NO Codex-specific defensive code added — the Phase 4 mixin already catches the regression for every adapter; zero direct subprocess imports; `isinstance(CodexAdapter(), Adapter)` is True via runtime_checkable Protocol; `registry.get_adapter("codex")` returns concrete `CodexAdapter()`. plan 07-02 commit e538e88 — TEST VERIFICATION: `tests/test_adapter_codex.py` (333 lines, 11 collected) covers the same six paths as Gemini PLUS the **headline** `test_codex_empty_stdout_bug_regression` at line 129 explicitly documenting Pitfall #2 / openai/codex#19945 with: (a) bug source URL `https://github.com/openai/codex/issues/19945` in docstring, (b) bug shape pinned via `fp.register(["codex", "exec"], stdout="", stderr="warning: no TTY attached; using non-interactive mode", returncode=0)`, (c) defense location named (`_SubprocessAdapterMixin._run_subprocess` from Phase 4 plan 04-01), (d) explicit "what the test pins vs deliberately does NOT pin" section. The headline regression test passes WITHOUT any Codex-specific defensive code in `CodexAdapter` — the inherited Phase 4 mixin's empty-stdout defense fires directly. Two assertion anchors: (1) `"codex" in msg.lower()`, (2) `"empty" in msg.lower() or "19945" in msg`. 11/11 PASS in isolation; 72/72 full suite PASS) |
| ADP-08 | Phase 4 | Complete (plan 04-01 commit eceb9da — two paths both raise `AdapterAuthError`: (a) `FileNotFoundError` on `Popen` -> "CLI not found on PATH; run `<cli> login`", (b) case-insensitive substring match of `auth_error_markers` against `stdout + stderr` -> "not authenticated; run `<cli> login`"; `AdapterAuthError` subclasses `AdapterError` so continue-on-error catches both) |
| STP-01 | Phase 5 | Complete (plan 05-01 commits e56a779 + 9dbc164 — `src/ultra_claude/stop_conditions.py` defines `@runtime_checkable class StopCondition(Protocol)` with `check(self, transcript: Transcript) -> bool`; verified by `test_stop_condition_protocol_structural` exercising both positive (FakeStop with `check`) and negative (HalfBaked without `check`) duck-typed isinstance probes plus all 3 bundled classes) |
| STP-02 | Phase 5 | Complete (plan 05-01 commits e56a779 + 9dbc164 — `Keyword.__init__` pre-compiles `re.compile(rf"^{re.escape(kw)}\s*$", re.MULTILINE)` literally at line 105; verified by `test_keyword_anchored_regex_rejects_substring` with m=1 isolation showing `"I am NOT going to say AGREED yet."` returns False — the Pitfall #4 mitigation) |
| STP-03 | Phase 5 | Complete (plan 05-01 commits e56a779 + 9dbc164 — `Keyword.__init__(keywords, *, n=2, m=2)` exposes unanimity-window defaults; `Keyword.check` slices `turns[-self._n:]` and counts distinct `.agent` strings via `set[str]`, returns True iff `>= self._m`; verified by `test_keyword_unanimity_two_agents_two_turns` (Architect+Critic both AGREED -> True positive) and `test_keyword_single_agent_self_stop_blocked` (Architect twice -> False; voting-itself-off-the-island defense)) |
| STP-04 | Phase 5 | Complete (plan 05-01 commits e56a779 + 9dbc164 — `MaxTurns.check` returns `len(transcript) >= self._max_turns` exact-boundary equality; verified by `test_max_turns_equality` asserting both `MaxTurns(12).check(11_turn_transcript) is False` AND `MaxTurns(12).check(12_turn_transcript) is True`) |
| STP-05 | Phase 5 | Complete (plan 05-01 commits e56a779 + 9dbc164 — `AnyOf.check` returns `any(c.check(transcript) for c in self._conditions)` lazy generator expression for short-circuit evaluation; verified by `test_anyof_short_circuit` with `AnyOf([MaxTurns(3), Keyword(["AGREED"])])` on a 3-turn AGREED-free transcript -> True (MaxTurns fires first; Keyword never reached); plus loose `MaxTurns(99)` sanity case asserting AnyOf returns False when no wrapped condition fires) |
| ORC-01 | Phase 6 | Complete (plan 06-01 commits 8cfee40 + b9b80b3 — `src/ultra_claude/orchestrator.py:run(config, task, *, transcript_path=None, adapter_factory=None) -> Path` returns `transcript.markdown_path`; verified by plan 06-02 commit 747f003 — `tests/test_orchestrator.py::test_run_3_agent_max_turns_6_writes_6_turns` asserts return value equals input `transcript_path` AND `test_run_returns_transcript_path` asserts `isinstance(result, Path)` + `result.exists()` + 4 sentinel comments) |
| ORC-02 | Phase 6 | Complete (plan 06-01 commit b9b80b3 — `agent_cfg = config.agents[(turn_idx - 1) % n_agents]` round-robin loop; verified by plan 06-02 commit 747f003 — `test_run_3_agent_max_turns_6_writes_6_turns` asserts 3-agent + max_turns=6 produces declared order `[alpha, beta, gamma, alpha, beta, gamma]` AND each FakeAdapter invoked exactly twice) |
| ORC-03 | Phase 6 | Complete (plan 06-01 commit b9b80b3 — `_build_prompt` assembles `# Task` -> `# Your role` -> transcript-so-far -> GOAL ANCHOR `# Reminder of the task` + `Respond now as {name} ({role}). Stay focused on the task above.` per Pitfall #6 mitigation; verified by plan 06-02 commit 747f003 — `test_run_includes_task_in_prompt` asserts task appears >=2 times (header + footer) AND `system_prompt` is in prompt AND `Respond now as alpha` + `Stay focused on the task above` in footer; `test_run_includes_transcript_so_far` asserts turn 3's prompt contains both turn 1 and turn 2 outputs) |
| ORC-04 | Phase 6 | Complete (plan 06-01 commit b9b80b3 — `composite = AnyOf([MaxTurns(config.max_turns), Keyword(config.stop_keywords)])` probed via `composite.check(transcript)` after every `transcript.append_turn`; verified by plan 06-02 commit 747f003 — `test_run_stops_on_keyword_unanimity` asserts 3 agents all returning `"AGREED"` with default n=2/m=2 halts after turn 2 (alpha+beta in window) even though max_turns=6, and gamma never invoked) |
| ORC-05 | Phase 6 | Complete (plan 06-01 commit b9b80b3 — `try: adapter.invoke(...) except AdapterError as exc:` (subclass-aware single-clause covers AdapterAuthError too) -> `_logger.exception(...)` + placeholder `[adapter error: <exc>]` turn UNLESS `config.abort_on_error` (then bare `raise`); verified by plan 06-02 commit 747f003 — `test_run_continues_on_adapter_error` asserts beta's placeholder turn `"[adapter error: simulated CLI failure]"` appended AND gamma still invoked; `test_run_aborts_on_error_when_configured` asserts `pytest.raises(AdapterError, match="simulated abort")` AND gamma NOT invoked) |
| ORC-06 | Phase 6 | Complete (plan 06-01 commit b9b80b3 — `_logger = logging.getLogger("ultra_claude.orchestrator")` with idempotent `_ensure_default_handler()` attaching `StreamHandler(sys.stderr)` only when `_logger.hasHandlers()` is False; verified by plan 06-02 commit 747f003 — `test_run_logs_progress_to_stderr_only` asserts `capsys.readouterr().out == ""` (stdout discipline) AND `caplog.text` contains "starting roundtable" + "turn 1 starting" + "turn 2 starting" AND >= 3 records from `ultra_claude.orchestrator` logger name) |
| CLI-01 | Phase 8 | Complete (2026-05-02, plan 08-02 commit f452152 + plan 08-03 commit 4ada905; `--version` reads `__version__` from `ultra_claude/__init__.py`; test_version_flag_prints_version_and_exits_zero verifies via CliRunner) |
| CLI-02 | Phase 8 | Complete (2026-05-02, plan 08-02 commit f452152 + plan 08-03 commit 4ada905; click auto-generates `--help` listing `run` + `doctor` subcommands; test_help_flag_lists_subcommands_and_exits_zero verifies via CliRunner) |
| CLI-03 | Phase 8 | Complete (2026-05-02, plan 08-02 commit f452152 + plan 08-03 commit 4ada905; default config path `./ultra-claude.yaml` + transcript path on stdout; test_run_end_to_end_with_fake_adapters_writes_transcript verifies via FakeAdapter injection through `monkeypatch.setattr(orch_module, "get_adapter", ...)`) |
| CLI-04 | Phase 8 | Complete (2026-05-02, plan 08-02 commit f452152 + plan 08-03 commit 4ada905; `--config <path>` overrides default; test_run_with_config_path_overrides_default verifies via CliRunner) |
| CLI-05 | Phase 8 | Complete (2026-05-02, plan 08-02 commit f452152 + plan 08-03 commit 4ada905; `--preset debate` loads bundled YAML via `importlib.resources.files("ultra_claude.presets")`; test_run_with_preset_debate_loads_bundled_yaml verifies via CliRunner from any cwd without local YAML; PRE-01 verified by the same test) |
| CLI-06 | Phase 8 | Complete (2026-05-02, plan 08-02 commit f452152 + plan 08-03 commit 4ada905; `--inline TEXT` provides task as string; test_run_with_inline_task_dry_run_validates_and_exits_zero verifies via CliRunner) |
| CLI-07 | Phase 8 | Complete (2026-05-02, plan 08-02 commit f452152 + plan 08-03 commit 4ada905; `--dry-run` validates config + prints planned turn order without invoking adapters; test_run_dry_run_outputs_full_turn_order verifies all `Turn N:` lines for max_turns=4) |
| CLI-08 | Phase 8 | Complete (2026-05-02, plan 08-02 commit f452152 + plan 08-03 commit 4ada905; `--output PATH` overrides transcript output path; test_run_end_to_end_with_fake_adapters_writes_transcript verifies the transcript is written at the supplied --output path) |
| CLI-09 | Phase 8 | Complete (2026-05-02, plan 08-02 commit f452152 + plan 08-03 commit 4ada905; doctor probes claude/gemini/codex via `shutil.which` + `subprocess.run` with FULL safe-contract kwargs; test_doctor_command_prints_status_table verifies 4-column ASCII table AND that the fake_run callable's safe-contract kwargs assertions fire on every call — defense-in-depth alongside TST-05 lint) |
| CLI-10 | Phase 8 | Complete (2026-05-02, plan 08-02 commit f452152 + plan 08-03 commit 4ada905; ConfigError -> ctx.exit(2); AdapterError (incl. AdapterAuthError subclass) -> ctx.exit(1); test_config_error_exits_with_code_two verifies exit 2 path; test_adapter_error_with_abort_on_error_exits_with_code_one verifies exit 1 path via FakeAdapter raising AdapterError on every invoke + --abort-on-error flag) |
| CLI-11 | Phase 8 | Complete (2026-05-02, plan 08-02 commit f452152 + plan 08-03 commit 4ada905; TTY-aware logging via `_configure_logging` sets `ultra_claude.orchestrator` logger to INFO when BOTH stdout AND stderr are ttys, WARNING otherwise; test_stdout_only_contains_transcript_path_on_success verifies `result.stdout.strip() == str(output)` AND `str(output) not in result.stderr` using click 8.3+'s default-split semantics) |
| PRE-01 | Phase 8 | Complete (2026-05-02, plan 08-01 commits 481c8e9 + 7331fc7 — bundled `src/ultra_claude/presets/debate.yaml` reachable via `importlib.resources.files('ultra_claude.presets')`; verified by plan 08-03 commit 4ada905 — test_run_with_preset_debate_loads_bundled_yaml asserts CliRunner can run `--preset debate` from any cwd without a local YAML and the output contains all 3 agent names + all 3 adapter literals) |
| PRE-02 | Phase 9 | Complete (2026-05-02, plan 09-03 commit `2ab93b7` -- `examples/` directory populated with `README.md` (1771 bytes / 24 lines, orientation + synthetic-vs-real explanation), `debate.yaml` (1033 bytes / 30 lines, byte-identical to `src/ultra_claude/presets/debate.yaml`; T-09-12 mitigation), `transcripts/sample-debate.md` (2857 bytes / 63 lines, synthetic 3-turn debate with the TRX-02 markdown sentinel format `<!-- turn:N agent:Name -->` for turns 1/Architect, 2/Critic, 3/Implementer), `transcripts/sample-debate.md.jsonl` (3096 bytes / 3 lines, 3-record sidecar each validating against the actual `TurnRecord` Pydantic schema with 64-char lowercase-hex `prompt_hash`); all 4 files LF-only + ASCII-only on disk and in staged blobs despite `core.autocrlf=true`; `load_config('examples/debate.yaml')` succeeds returning 3 agents / max_turns=9 / stop_keywords=['AGREED', 'SHIP IT']) |
| TST-01 | Phase 9 | Pending |
| TST-02 | Phase 9 | Pending |
| TST-03 | Phase 9 | Complete (2026-05-02, plan 09-02 commit 58ec2f8 -- `tests/fixtures/echo_cli.py` fake-CLI script reading stdin and printing `echo: <prompt>` to stdout, exits 0; UTF-8 reconfigure on stdin AND stdout to defend against Windows cp1252 default; verified standalone via `python tests/fixtures/echo_cli.py < input` -> `echo: <input>`) |
| TST-04 | Phase 9 | Complete (2026-05-02, plan 09-02 commit 2575869 -- `tests/test_e2e_with_echo_cli.py` 3 test functions exercising real subprocess.Popen via `_SubprocessAdapterMixin._run_subprocess`; the `EchoAdapter` defined inside the test file inherits from `_SubprocessAdapterMixin` so the SAME production code path that ClaudeAdapter/GeminiAdapter/CodexAdapter use against vendor CLIs is exercised here against `[sys.executable, str(_ECHO_CLI_PATH)]`. Tests cover: 4-turn round-robin happy path with task-in-output verification; UTF-8 round-trip with U+201C/U+201D/U+2014/U+1F680/U+4E2D/U+6587 PASSED on Windows 11/Python 3.11.9/cp950; structural Adapter Protocol conformance via runtime_checkable. Note: the canonical TST-04 text references pytest-cov reporting; that toolchain side lands in 09-04. The orchestrator E2E test surface that the plan specifies as TST-04 closure is fully landed by this commit -- 86/86 full suite PASS) |
| TST-05 | Phase 4 | Complete (plan 04-03 commit e16c4f9 — `tests/test_subprocess_lint.py` ast-walks every .py file under `src/ultra_claude/`, detects both `subprocess.run`/`subprocess.Popen` attribute access AND bare-imported `run`/`Popen`, asserts each call has `text=True`/`encoding="utf-8"`/`errors="replace"` and does NOT have `shell=True`. Aggregates ALL violations into a single multi-line `pytest.fail(...)` listing every `file:lineno`. Manual paranoia check confirmed the lint test FIRES on synthetic bad scratch files: `subprocess.run(["echo","hi"])` -> 3 missing-keyword violations, and `subprocess.run([...], shell=True)` -> "shell=True is forbidden" violation; scratch files deleted after.) |
| TST-06 | Phase 9 | Pending |
| TST-07 | Phase 9 | Pending |
| DOC-01 | Phase 9 | Complete (2026-05-02, plan 09-03 commit `078dc7c` -- README.md replaced from 12-line stub with full v0.1.0 README (6313 bytes / 130 lines, LF-only, ASCII-only); 7 required sections in order: 1-line pitch under H1, GIF placeholder block, 3-command Quickstart (`pip install` + `doctor` + `run --preset debate --inline ...`) with per-CLI install/login table, "Why this exists" 3-bullet value prop, "Config example" embedding `presets/debate.yaml` verbatim with field-reference table, "Extending to new CLIs" with 10-line `MyAdapter(_SubprocessAdapterMixin)` example pointing at the `Adapter` Protocol, "Trademark disclaimer" naming Anthropic/Google/OpenAI; PyPI/GitHub/License/Changelog/Contributing links; staged blob LF-only despite `core.autocrlf=true`) |
| DOC-02 | Phase 9 | Complete (2026-05-02, plan 09-03 commit `180be45` -- `CONTRIBUTING.md` created (5608 bytes / 92 lines, LF-only, ASCII-only); 6+ required sections: Dev setup (clone -> venv -> `pip install -e ".[dev]"` -> pytest), Adding an adapter (minimal `_SubprocessAdapterMixin` subclass example + 5-bullet contract list: stdin pipe / encoding+errors=replace / timeout+process-tree-kill / empty-stdout defense citing openai/codex#19945 / auth-marker detection), v1 policy (core ships only claude/gemini/codex; third-party adapters live in their own packages; rationale in 3 bullets), PR checklist (pytest + mypy + ruff + REQUIREMENTS.md update + README sync + conventional-commit message style), Filing an issue (5-item bug report template), Architecture corrections from original spec (3 documented deltas), Code of Conduct; staged blob LF-only despite `core.autocrlf=true`) |

**Coverage:**
- v1 requirements: 58 total
- Mapped to phases: 58 (100%)
- Unmapped: 0

**Phase Distribution:**

| Phase | Requirements | Count |
|-------|-------------|-------|
| Phase 1 (Project Skeleton & PyPI Reservation) | PKG-02, PKG-03, PKG-04, PKG-05, PKG-07 | 5 |
| Phase 2 (Config Schema & YAML Loader) | CFG-01, CFG-02, CFG-03, CFG-04, CFG-05 | 5 |
| Phase 3 (Transcript Module) | TRX-01, TRX-02, TRX-03, TRX-04, TRX-05 | 5 |
| Phase 4 (Adapter Protocol & ClaudeAdapter) | ADP-01, ADP-02, ADP-03, ADP-04, ADP-05, ADP-08, TST-05 | 7 |
| Phase 5 (Stop Conditions) | STP-01, STP-02, STP-03, STP-04, STP-05 | 5 |
| Phase 6 (Orchestrator Loop) | ORC-01, ORC-02, ORC-03, ORC-04, ORC-05, ORC-06 | 6 |
| Phase 7 (Gemini & Codex Adapters) | ADP-06, ADP-07 | 2 |
| Phase 8 (CLI Surface & `debate` Preset) | CLI-01–CLI-11, PRE-01 | 12 |
| Phase 9 (Tests, Docs, Examples & v0.1.0 Release) | PKG-01, PKG-06, PRE-02, TST-01, TST-02, TST-03, TST-04, TST-06, TST-07, DOC-01, DOC-02 | 11 |
| **Total** | | **58** |

---
*Requirements defined: 2026-05-02*
*Last updated: 2026-05-02 after plan 07-02 autonomous completion (ADP-06 + ADP-07 now both IMPLEMENTATION + TEST verified — `tests/test_adapter_gemini.py` (261 lines / 11 collected) and `tests/test_adapter_codex.py` (333 lines / 11 collected including the headline `test_codex_empty_stdout_bug_regression` at line 129 documenting Pitfall #2 / openai/codex#19945 against the inherited Phase 4 mixin defense) landed via commits 4377a27 + e538e88; full suite 72/72 PASS — 50 prior + 22 new tests = 72; zero regression; Phase 7 fully closes; Phase 8 (CLI Surface) UNBLOCKED)*
