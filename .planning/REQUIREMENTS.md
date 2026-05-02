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
- [ ] **PKG-06**: `v0.1.0` is published to PyPI manually via `python -m build` + `twine upload`
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
- [ ] **ADP-06**: `GeminiAdapter` invokes `gemini -p` with prompt via stdin and returns trimmed stdout
- [ ] **ADP-07**: `CodexAdapter` invokes `codex exec` with prompt via stdin and returns trimmed stdout
- [x] **ADP-08**: Adapter raises a clear `AdapterAuthError` with re-auth instructions when the underlying CLI is not logged in

### Stop Conditions

- [ ] **STP-01**: A `StopCondition` Strategy interface defines `check(transcript) -> bool`
- [ ] **STP-02**: `Keyword` stop condition matches an anchored multiline regex (e.g. `^## Decision\n(AGREED|SHIP IT)\s*$`), NOT naive substring match
- [ ] **STP-03**: `Keyword` requires the marker to appear in the last N turns from M distinct agents (unanimity-window) before stopping; defaults: N=2, M=2
- [ ] **STP-04**: `MaxTurns` stop condition halts the orchestrator after `config.max_turns` turns
- [ ] **STP-05**: `AnyOf` composite stops the run when any wrapped condition matches; orchestrator wires bundled conditions through `AnyOf` by default

### Orchestrator Loop

- [ ] **ORC-01**: Orchestrator is a single function `run(config, task) -> Path` that returns the transcript path on completion
- [ ] **ORC-02**: Orchestrator iterates agents in round-robin order for up to `max_turns` turns
- [ ] **ORC-03**: Each turn's prompt = task statement + full transcript so far + the current agent's system prompt + a goal-anchoring re-injection of the original task (mitigates problem drift)
- [ ] **ORC-04**: Orchestrator checks stop conditions after every turn and exits cleanly on first match
- [ ] **ORC-05**: Adapter errors mid-run are logged to stderr; the run continues unless `abort_on_error: true` is set in config (default `false`)
- [ ] **ORC-06**: Orchestrator writes structured progress to stderr via stdlib `logging` (turn N starting / completed / stopped); stdout stays clean for piping

### CLI

- [ ] **CLI-01**: `ultra-claude --version` prints `__version__` and exits 0
- [ ] **CLI-02**: `ultra-claude --help` prints click-generated help and exits 0
- [ ] **CLI-03**: `ultra-claude run <task-file>` reads the task, loads `./ultra-claude.yaml`, runs the orchestrator, and prints the transcript path on stdout
- [ ] **CLI-04**: `ultra-claude run --config <path>` overrides the default config location
- [ ] **CLI-05**: `ultra-claude run --preset <name>` loads a bundled preset (e.g. `--preset debate`) instead of a user config file
- [ ] **CLI-06**: `ultra-claude run --inline "<task>"` accepts the task as a string instead of a file path
- [ ] **CLI-07**: `ultra-claude run --dry-run` validates config + prints planned turn order without invoking any adapter
- [ ] **CLI-08**: `ultra-claude run --output <path>` overrides the transcript output path
- [ ] **CLI-09**: `ultra-claude doctor` checks for `claude`/`gemini`/`codex` on PATH, probes login state for each, and prints a per-CLI status table (PASS / FAIL / UNKNOWN)
- [ ] **CLI-10**: Exit codes follow Unix convention: `0` success, `1` runtime error, `2` config validation error
- [ ] **CLI-11**: Live progress (e.g. "Claude is thinking…") renders to stderr only when stdout is a TTY; suppressed when piped or redirected

### Presets & Examples

- [ ] **PRE-01**: A bundled `presets/debate.yaml` ships in the package with three agents (architect: claude, critic: gemini, implementer: codex) and is loadable via `--preset debate`
- [ ] **PRE-02**: An `examples/` directory in the repo contains at least one real captured transcript (e.g. fixing a failing test) with the YAML config alongside it

### Testing & CI

- [ ] **TST-01**: Test suite passes via `pytest` without any of `claude`/`gemini`/`codex` installed (subprocess fully mocked)
- [ ] **TST-02**: Adapter tests use `pytest-subprocess`'s `fp` fixture to assert exact argv, stdin payload, and timeout
- [ ] **TST-03**: A `tests/fixtures/echo_cli.py` fake-CLI Python script enables orchestrator E2E tests without real LLM calls
- [ ] **TST-04**: Test coverage of `src/ultra_claude/` is reported by `pytest-cov`
- [ ] **TST-05**: A grep-based lint test fails the build if any `subprocess.run`/`subprocess.Popen` call in the codebase is missing `encoding="utf-8"` or `errors="replace"`
- [ ] **TST-06**: `ruff check` and `mypy` (configured strict for `src/ultra_claude/`) pass with zero errors
- [ ] **TST-07**: Manual `python -m build` produces a wheel and sdist that install cleanly into a fresh virtualenv on macOS, Linux, and Windows (smoke-tested before tagging v0.1.0)

### Documentation

- [ ] **DOC-01**: `README.md` opens with a one-line pitch, a GIF placeholder block (final GIF lands as part of release), a 3-command quickstart, a "why this exists" section, a config example, and a short "extending to new CLIs" pointing at the `Adapter` Protocol
- [ ] **DOC-02**: `CONTRIBUTING.md` documents dev setup, how to add an adapter, and the v1 policy that core ships only the three bundled adapters (third-party adapters live in their own packages)

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
| PKG-06 | Phase 9 | Pending |
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
| ADP-06 | Phase 7 | Pending |
| ADP-07 | Phase 7 | Pending |
| ADP-08 | Phase 4 | Complete (plan 04-01 commit eceb9da — two paths both raise `AdapterAuthError`: (a) `FileNotFoundError` on `Popen` -> "CLI not found on PATH; run `<cli> login`", (b) case-insensitive substring match of `auth_error_markers` against `stdout + stderr` -> "not authenticated; run `<cli> login`"; `AdapterAuthError` subclasses `AdapterError` so continue-on-error catches both) |
| STP-01 | Phase 5 | Pending |
| STP-02 | Phase 5 | Pending |
| STP-03 | Phase 5 | Pending |
| STP-04 | Phase 5 | Pending |
| STP-05 | Phase 5 | Pending |
| ORC-01 | Phase 6 | Pending |
| ORC-02 | Phase 6 | Pending |
| ORC-03 | Phase 6 | Pending |
| ORC-04 | Phase 6 | Pending |
| ORC-05 | Phase 6 | Pending |
| ORC-06 | Phase 6 | Pending |
| CLI-01 | Phase 8 | Pending |
| CLI-02 | Phase 8 | Pending |
| CLI-03 | Phase 8 | Pending |
| CLI-04 | Phase 8 | Pending |
| CLI-05 | Phase 8 | Pending |
| CLI-06 | Phase 8 | Pending |
| CLI-07 | Phase 8 | Pending |
| CLI-08 | Phase 8 | Pending |
| CLI-09 | Phase 8 | Pending |
| CLI-10 | Phase 8 | Pending |
| CLI-11 | Phase 8 | Pending |
| PRE-01 | Phase 8 | Pending |
| PRE-02 | Phase 9 | Pending |
| TST-01 | Phase 9 | Pending |
| TST-02 | Phase 9 | Pending |
| TST-03 | Phase 9 | Pending |
| TST-04 | Phase 9 | Pending |
| TST-05 | Phase 4 | Pending |
| TST-06 | Phase 9 | Pending |
| TST-07 | Phase 9 | Pending |
| DOC-01 | Phase 9 | Pending |
| DOC-02 | Phase 9 | Pending |

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
*Last updated: 2026-05-02 after plan 03-01 autonomous completion (TRX-01, TRX-02, TRX-03, TRX-04, TRX-05 all COMPLETE — `src/ultra_claude/transcript.py` (TurnRecord + Transcript with append-as-you-go markdown + JSONL sidecar) + 8-test pytest suite landed via commits 88b6186 + 6230667; full suite 16/16 PASS; Phase 3 closes)*
