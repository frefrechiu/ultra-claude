# Requirements: ultra-claude

**Defined:** 2026-05-02
**Core Value:** A user can run `ultra-claude run task.md` and get three CLI agents debating their problem in a transcript file — using only their existing CLI logins, no API keys.

## v1 Requirements

Requirements for initial PyPI release (`v0.1.0`). Each maps to roadmap phases.

### Packaging & Distribution

- [ ] **PKG-01**: User can `pip install ultra-claude` from PyPI and the `ultra-claude` command is on PATH
- [ ] **PKG-02**: Repository ships a valid `pyproject.toml` using the `hatchling` build backend with pinned minimum versions for click, pydantic v2, and pyyaml
- [ ] **PKG-03**: Repository ships an `MIT LICENSE` file at the project root
- [ ] **PKG-04**: Repository ships a `.gitignore` covering Python build artifacts, virtualenvs, and editor files
- [ ] **PKG-05**: A `0.0.1` stub package is reserved on PyPI under the name `ultra-claude` before any feature work merges (squat-protection)
- [ ] **PKG-06**: `v0.1.0` is published to PyPI manually via `python -m build` + `twine upload`
- [ ] **PKG-07**: `__version__` is exposed from `ultra_claude.__init__` and matches the `[project] version` in `pyproject.toml`

### Config Schema & Loader

- [ ] **CFG-01**: User can author a `ultra-claude.yaml` file with `agents`, `max_turns`, `stop_keywords`, and `transcript_path` fields and have it validated by Pydantic v2
- [ ] **CFG-02**: Each agent in config has `name`, `role`, `adapter` (literal: `claude` | `gemini` | `codex`), and `system_prompt` fields, all required
- [ ] **CFG-03**: Invalid YAML or invalid config produces a human-readable error pointing at the offending field (Pydantic's structured error output)
- [ ] **CFG-04**: `turn_order` field accepts only `round_robin` in v1 (Literal type); `max_turns` defaults to 12 when omitted
- [ ] **CFG-05**: `stop_keywords` defaults to `["AGREED", "DONE"]` when omitted

### Transcript

- [ ] **TRX-01**: Orchestrator writes the transcript as a markdown file, appended after every turn (so `tail -f` works during a run)
- [ ] **TRX-02**: Each turn is delimited by a non-markdown sentinel (e.g. `<!-- turn:N agent:Claude -->`) so re-prompting the conversation does not collide with content markdown
- [ ] **TRX-03**: A JSONL sidecar at `<transcript>.jsonl` is written in parallel, one record per turn, capturing turn index, agent name, role, prompt-hash, and raw output
- [ ] **TRX-04**: Transcript file uses LF newlines on all platforms (`newline="\n"`)
- [ ] **TRX-05**: Transcript content is encoded as UTF-8 on disk

### Adapters (subprocess-based)

- [ ] **ADP-01**: An `Adapter` `typing.Protocol` defines the `invoke(prompt: str, timeout: int) -> str` contract; third-party adapters do not need to inherit
- [ ] **ADP-02**: Internal `_SubprocessAdapterMixin` enforces the safe subprocess invocation contract: stdin-piped prompt, `text=True`, `encoding="utf-8"`, `errors="replace"`, mandatory timeout, list-form argv (`shell=False`)
- [ ] **ADP-03**: Any adapter that returns `returncode == 0` AND empty stdout raises `AdapterError` (defends against the live Codex `exec` TTY bug and any future similar regression)
- [ ] **ADP-04**: Adapter timeout triggers cross-platform process-tree kill (handles child processes on POSIX and Windows)
- [ ] **ADP-05**: `ClaudeAdapter` invokes `claude -p` with prompt via stdin and returns trimmed stdout
- [ ] **ADP-06**: `GeminiAdapter` invokes `gemini -p` with prompt via stdin and returns trimmed stdout
- [ ] **ADP-07**: `CodexAdapter` invokes `codex exec` with prompt via stdin and returns trimmed stdout
- [ ] **ADP-08**: Adapter raises a clear `AdapterAuthError` with re-auth instructions when the underlying CLI is not logged in

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
| PKG-01 — PKG-07 | (assigned by roadmap) | Pending |
| CFG-01 — CFG-05 | (assigned by roadmap) | Pending |
| TRX-01 — TRX-05 | (assigned by roadmap) | Pending |
| ADP-01 — ADP-08 | (assigned by roadmap) | Pending |
| STP-01 — STP-05 | (assigned by roadmap) | Pending |
| ORC-01 — ORC-06 | (assigned by roadmap) | Pending |
| CLI-01 — CLI-11 | (assigned by roadmap) | Pending |
| PRE-01 — PRE-02 | (assigned by roadmap) | Pending |
| TST-01 — TST-07 | (assigned by roadmap) | Pending |
| DOC-01 — DOC-02 | (assigned by roadmap) | Pending |

**Coverage:**
- v1 requirements: 51 total
- Mapped to phases: 0 (roadmap pending)
- Unmapped: 51 ⚠️ (resolved by roadmapper)

---
*Requirements defined: 2026-05-02*
*Last updated: 2026-05-02 after initial definition*
