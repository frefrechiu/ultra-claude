# Feature Research

**Domain:** Multi-agent LLM orchestration via subprocess (CLI-driven, no-API-key)
**Researched:** 2026-05-02
**Confidence:** HIGH for table stakes and v1 differentiators (verified against multiple competitors and Click/PyPI conventions); MEDIUM for v2+ differentiators (some are derived from adjacent-domain patterns, not from direct CLI-based competitors).

## How This Was Categorized

This document categorizes by **functional area** first, then within each area splits into:

- **Table stakes** — must have or users leave / product feels incomplete
- **Differentiators (v1-shippable)** — competitive advantages that fit the v1 scope
- **Differentiators (v2+)** — valuable but defer until v1 ships
- **Anti-features** — explicitly NOT building, with reason

For each individual feature: complexity, fit, dependencies. The "Cross-Check Against PROJECT.md Active List" section at the bottom maps each Active requirement to its category.

---

## Area 1: Adapters (CLI Subprocess Wrappers)

The whole product hinges on these. If any of the three adapters is broken, the value prop dies.

### Table Stakes

| Feature | Why Expected | Complexity | v1/v2 | Notes |
|---------|--------------|------------|-------|-------|
| `BaseAdapter` ABC with `invoke(prompt, timeout) -> str` | Without a contract, you can't add new CLIs cleanly. Plugin authors expect Python ABCs. | LOW | v1 | Single method, plus `name` property. Use `abc.ABC`. |
| `ClaudeAdapter` (`claude -p <prompt>`) | First adapter — the brand-aligned one. Verified: Claude Code's `-p` flag does one-shot non-interactive prompt and exits. | LOW | v1 | Pass `--output-format text` (default) for clean stdout. |
| `GeminiAdapter` (`gemini -p <prompt>`) | Verified: Gemini CLI supports `-p` for one-shot non-interactive mode, outputs single response and exits. No tool authorization in this mode (good — keeps it pure). | LOW | v1 | Positional arg `gemini "<prompt>"` also works. |
| `CodexAdapter` (`codex exec <prompt>`) | Verified: `codex exec` (or `codex e`) is the scripted/CI invocation. Exits non-zero on failure. | LOW | v1 | Stdin-piping form `codex exec -` exists but isn't needed for v1. |
| Authenticated-CLI detection / clear error if missing | Constraint in PROJECT.md: "tool reports a clear error if the configured adapter's CLI is missing." Verified by `shutil.which()`. | LOW | v1 | Catch `FileNotFoundError` from `subprocess.run` and re-raise with actionable message naming the missing CLI and pointing to install docs. |
| UTF-8 encoding with `errors="replace"` | Constraint in PROJECT.md (Windows non-UTF8 stderr). Without it, the tool crashes on Windows when CLIs print emoji / non-ASCII. | LOW | v1 | One line: `subprocess.run(..., encoding="utf-8", errors="replace")`. |
| Per-turn timeout (passed through to `subprocess.run(timeout=...)`) | Without it, a hung CLI hangs the whole orchestrator forever. Standard expectation for any subprocess-driver. | LOW | v1 | Default 600s (10 min). Configurable per-agent. Catch `TimeoutExpired` and treat as a turn failure. |

### Differentiators (v1-shippable)

| Feature | Value Proposition | Complexity | v1/v2 | Notes |
|---------|-------------------|------------|-------|-------|
| Per-agent CLI args (e.g., extra flags like `--allowedTools`) | Users will want to pass `--append-system-prompt` to Claude or `--attempts 3` to Codex without forking. Differentiator: most competitors hardcode CLI invocation. | LOW | v1 | YAML field `extra_args: ["--allowedTools", "Read,Edit"]`. Append to argv. |

### Differentiators (v2+)

| Feature | Value Proposition | Complexity | v1/v2 | Dependencies |
|---------|-------------------|------------|-------|--------------|
| `OllamaAdapter` / `LlamaCppAdapter` (local LLM CLIs) | Complete the no-API-key story for users who run local models. Hoangsonww's AI-Agents-Orchestrator already supports Ollama. | LOW | v2 | None. |
| `CursorAdapter` / `CopilotAdapter` / `OpenCodeAdapter` / `AmpAdapter` | dmux supports 11 runtimes. Plugin parity helps adoption. | LOW each | v2 | One per CLI; cheap to add once `BaseAdapter` is stable. |
| Adapter retry on `subprocess.CalledProcessError` (configurable count + backoff) | Real CLIs occasionally crash, time out, or return malformed output. Without retry, one flake aborts the whole conversation. | LOW | v2 | YAML field `retries: 2`. Don't retry on `TimeoutExpired` by default (the agent is probably stuck). |
| Stdin-based prompt passing (instead of argv) | Some CLIs choke on very long prompts in argv on Windows (~32k char limit). Codex supports `codex exec -` (stdin). | LOW | v2 | Add an opt-in `prompt_via: stdin` field on `AgentConfig`. |
| Adapter health-check / dry-run subcommand | `ultra-claude doctor` runs each configured CLI with a trivial "say hi" prompt and reports status. Reduces "why isn't it working" support. | LOW | v2 | Calls each adapter with `"reply 'OK'"` and asserts non-empty stdout. |

### Anti-features

| Feature | Why Requested | Why NOT Build | Alternative |
|---------|---------------|---------------|-------------|
| Real-time per-token streaming during a turn | Users see streaming in chat UIs and assume it's standard. | `subprocess.run` is blocking. Streaming would force per-CLI special-casing (`stream-json` for Claude, NDJSON for Codex, none for Gemini). PROJECT.md Out of Scope. Defeats the "simple subprocess model" pitch. | Stream the **completed** turn output to stdout immediately when the turn finishes (write+flush). Optional `tail -f` of the transcript file gives a real-time-feeling experience. |
| API-key-based adapter (`OpenAIAdapter`, `AnthropicAdapter`) | "I already have a key, why not use it?" | PROJECT.md Out of Scope: defeats the whole pitch. If users want this, AutoGen / CrewAI / LangGraph already exist. | Document the trade clearly in README: "Use ultra-claude if you don't want API keys; use AutoGen if you do." |

---

## Area 2: Orchestrator (Conversation Loop)

### Table Stakes

| Feature | Why Expected | Complexity | v1/v2 | Notes |
|---------|--------------|------------|-------|-------|
| Round-robin turn order | The simplest, most predictable pattern. Every multi-agent framework supports this (AutoGen has it as a built-in option, CrewAI's "sequential" process). | LOW | v1 | List of agent names; loop modulo length. |
| Transcript-as-context (each turn sees full prior transcript) | This is the core mechanism. Without it, agents have no memory of the conversation. | LOW | v1 | Concatenate all prior turns + task into the next prompt. |
| Markdown transcript output | Human-readable; renders on GitHub; the conventional format. Verified: claude-code-log, claude-JSONL-browser, claude-conversation-extractor all convert TO markdown. Users expect this. | LOW | v1 | One H2 per turn with agent name + turn number, prose body. |
| `max_turns` stop condition | Verified: AutoGen, CrewAI, LangGraph (as `recursion_limit`) all have this. Required to prevent infinite loops draining quota / time. | LOW | v1 | Hard cap. Default 20. Configurable. |
| Keyword stop condition (e.g., `AGREED`, `SHIP IT`) | Verified: AutoGen documents "explicit DONE tokens" as a standard termination rule. Users want explicit consensus signals. | LOW | v1 | Substring match (case-insensitive) against latest turn. List of triggers in YAML. |
| Task-file ingestion | `ultra-claude run task.md` is in PROJECT.md core value. The whole UX. | LOW | v1 | Read file, use as initial prompt. Plain text or markdown. |
| Transcript saved to disk (file path or stdout) | Users need the artifact afterward. Defaults: `transcript_<timestamp>.md` in cwd. | LOW | v1 | Atomic write (temp file + rename) so partial transcripts aren't corrupted on Ctrl-C. |

### Differentiators (v1-shippable)

| Feature | Value Proposition | Complexity | v1/v2 | Dependencies |
|---------|-------------------|------------|-------|--------------|
| Append-as-you-go transcript writing (not just at end) | Users can `tail -f transcript.md` and watch the conversation unfold in real time without needing streaming inside a turn. Beats waiting for end-of-run. | LOW | v1 | Open file in append mode; flush after each turn. **Significantly improves UX without violating the "no streaming" Out of Scope rule.** |
| Per-agent system prompts | Each agent has a role (architect, critic, implementer). Without per-agent prompts, agents are fungible — no point having three. **Without this, the bundled "debate" preset is meaningless.** | LOW | v1 | YAML field `system_prompt: "..."` per agent. Prepended to each invocation. For Claude, route via `--append-system-prompt`. For others, prepend inline to the prompt. |

### Differentiators (v2+)

| Feature | Value Proposition | Complexity | v1/v2 | Dependencies |
|---------|-------------------|------------|-------|--------------|
| `speaker_chooses` turn order (last agent picks next) | Verified: AutoGen's "auto" speaker selection. Allows agents to escalate to a specialist mid-debate. **Already in v2 list in PROJECT.md.** | MED | v2 | Round-robin (v1). Need a parser to extract `@agent_name` mentions from turn output (or a dedicated last-line convention like `NEXT: gemini`). |
| `manual` turn order (user picks next agent each turn) | Verified: AutoGen has "manual" mode. Useful for debugging presets and curating high-stakes conversations. | LOW | v2 | Same dispatcher as `speaker_chooses`. Reads from stdin instead of parsing output. |
| `random` turn order | Verified: AutoGen has "random" mode. Useful as a brainstorming pattern (no fixed order). | LOW | v2 | Trivial. |
| `file_exists` stop condition | **Already in v2 list in PROJECT.md.** Stop when an agent creates a target file (e.g., `solution.py`). Useful for "build the thing" workflows. | LOW | v2 | Check `Path(target).exists()` after each turn. |
| `regex` stop condition | **Already in v2 list in PROJECT.md.** Generalization of keyword. E.g., stop when transcript matches `^DONE: .*` or contains a code-block with shebang. | LOW | v2 | `re.search(pattern, latest_turn)`. |
| `custom Python predicate` stop condition | Power users want full programmatic control. E.g., stop when test suite passes. **Pattern: import-string in YAML pointing to a Python callable.** | MED | v2 | Resolve dotted path via `importlib`. Predicate signature: `def stop(transcript: list[Turn]) -> bool`. Document a security note: arbitrary import means arbitrary code execution; load only from local project dirs by default. |
| Resume from existing transcript | Crash recovery + iterative work. Load a transcript, append new turns. Verified: Claude Code itself supports `--continue` / session IDs. Forky / ContextBranch provide this for chats. | MED | v2 | Parse transcript file to reconstruct prior turns; pass to orchestrator as initial context. JSONL transcript format makes this trivial; markdown format requires a parser. **Dependency: JSONL transcript format (below).** |
| JSONL transcript format (machine-readable, structured) | Enables programmatic consumption (other tools, dashboards, evals) and clean resume. Verified: Claude Code uses JSONL natively; `claude-code-log` exists to convert. | LOW | v2 | One JSON object per turn per line: `{turn, agent, prompt, output, started_at, ended_at, duration_s, exit_code}`. Add `--format jsonl` flag. **Recommend: write BOTH markdown and JSONL by default in v2** — markdown for humans, JSONL for tools. |
| JSON transcript format (single-document, structured) | Some users / tools prefer one JSON file over JSONL. Easier to load with `json.load()`. | LOW | v2 | Trivial once JSONL exists. |
| Branching/forking conversations (checkpoint at turn N, fork into A and B) | Verified: Forky, ContextBranch, LibreChat, Warp all support this for single-agent chats. **For multi-agent debate, this is novel and very powerful** — re-run the same task with different agent rosters from a checkpoint. **Recommend deferring to v3** — adds CLI surface (`ultra-claude fork`, `ultra-claude switch`), state management, and isn't essential for the "first PyPI release" narrative. | HIGH | v3 (out of scope for v1 and v2 per current PROJECT.md) | JSONL transcript format, resume capability. |
| Concurrent agent invocation when order doesn't matter | E.g., turn 1 is "all three agents independently propose a solution", then turn 2 is "merge". Speedup ~3x on multi-agent independent turns. Verified: Python's `asyncio.create_subprocess_exec` + `asyncio.gather` makes this clean. | MED | v2 | Adds an async path alongside the sync subprocess path. YAML field `parallel: true` on a turn-spec, or a new turn-order `parallel_then_summarize`. **Note: PROJECT.md key decision says "subprocess.run (blocking), not async" for v1 — respect this; only adopt async if/when this feature ships.** |
| TUI live view (rich/textual multi-pane) | Verified: dmux uses tmux for this; overstory has `ov dashboard`. Three colored panes showing each agent's stream-of-completed-turns is a strong demo. **But:** PROJECT.md says streaming is Out of Scope, and a TUI mostly shines if you have streaming. Without per-token streaming, a TUI is just "colored stdout with panes" — nice but not a 10x improvement over plain markdown stdout. | MED | v2 (optional) | rich/textual (new dependency). Can be opt-in via `--tui` flag so default install stays lean. |
| Per-turn timeouts vs global timeout | A "fast" agent could have a tight timeout, a "slow" reasoning agent could have a long one. Already covered as adapter-level; documented here for clarity. | LOW | v1 | Resolved via per-agent `timeout` field. Global `timeout` covers the whole run. |
| Reactor mode (external trigger spawns a turn) | Webhooks / file-watcher / CI-event triggers a new run or a new turn in an existing conversation. Verified pattern: langchain-runner, Hermes Agent, Langflow webhook component. **Adds an HTTP server, deviates from "local CLI tool" simplicity. Defer.** | HIGH | v3+ | All v1/v2 features. Adds `aiohttp` or similar. |

### Anti-features

| Feature | Why Requested | Why NOT Build | Alternative |
|---------|---------------|---------------|-------------|
| Persistent agent memory across runs | Users imagine agents "remembering" past conversations. Sounds productive. | PROJECT.md Out of Scope: "the transcript IS the memory." Adds state management, contradicts the stateless-subprocess model, complicates testing, and creates schema-versioning headaches. | Document: "to continue a conversation, point `ultra-claude run` at an existing transcript file as your task" (i.e., the v2 resume feature is the alternative — same tool, different angle). |
| Inter-agent direct messaging | Sounds collaborative. Other frameworks (CrewAI's task-output passing, AutoGen's direct messaging) have it. | PROJECT.md Out of Scope: "the 'they don't know the others exist' property is a feature, not a bug." Direct messaging would force agents to know about each other, breaking the abstraction. | The shared transcript IS the message bus. Each agent reads everyone else's "messages" automatically. |
| Hosted SaaS / web dashboard | Other CLI orchestrators (overstory's `ov serve`, AI-Agents-Orchestrator's Vue dashboard, dmux web UI) have one. | PROJECT.md Out of Scope. Hosting requires API keys (see anti-feature above) and undercuts the local-CLI value prop. | If a user wants a web UI, they can pipe `tail -f transcript.md` into a static-site generator or use any markdown-watcher. |
| Mobile app / GUI | "Run it on my phone." | PROJECT.md Out of Scope: terminal-only. | None. |

---

## Area 3: Configuration (YAML + Pydantic)

### Table Stakes

| Feature | Why Expected | Complexity | v1/v2 | Notes |
|---------|--------------|------------|-------|-------|
| `RoundtableConfig` Pydantic model (top-level) | Every modern Python tool with config uses Pydantic. Free validation + clear errors. **Already in PROJECT.md Active list.** | LOW | v1 | Fields: `agents: list[AgentConfig]`, `turn_order: Literal["round_robin"]` (v1), `stop: StopConfig`, `transcript: TranscriptConfig`, `task: TaskConfig` (or task is CLI arg). |
| `AgentConfig` Pydantic model (per-agent) | Models the per-agent setup. **Already in PROJECT.md Active list.** | LOW | v1 | Fields: `name: str`, `adapter: Literal["claude", "gemini", "codex"]`, `system_prompt: str \| None`, `extra_args: list[str]`, `timeout: int = 600`. |
| YAML loader with helpful errors | Pydantic v2 raises `ValidationError` with field locations and messages. Wrap and pretty-print so the user sees: "config error at agents[0].adapter: 'clade' is not one of ['claude', 'gemini', 'codex']" — not a stack trace. | LOW | v1 | `yaml.safe_load` then `RoundtableConfig.model_validate(data)`. Catch `ValidationError`, format human-readably, exit 2 (CLI usage error). |
| Config file discovery (default `ultra-claude.yaml` in cwd) | **In PROJECT.md Active list:** "reads `ultra-claude.yaml`". Standard convention (cf. `pytest.ini`, `pyproject.toml`). | LOW | v1 | `--config` flag overrides; otherwise look in cwd. |
| Bundled preset: `debate.yaml` (architect + critic + implementer) | **In PROJECT.md Active list.** Without one out-of-the-box preset, users have to write YAML before they get any value. | LOW | v1 | Ship inside the package (`ultra_claude/presets/debate.yaml`). Loadable via `--preset debate` shortcut. |

### Differentiators (v1-shippable)

| Feature | Value Proposition | Complexity | v1/v2 | Dependencies |
|---------|-------------------|------------|-------|--------------|
| `--preset <name>` flag (uses bundled preset, no local YAML required) | Lowest-friction onboarding. `ultra-claude run task.md --preset debate` works in any directory without setup. **Supports the README quickstart.** | LOW | v1 | Look up preset in `ultra_claude/presets/<name>.yaml`. List presets via `ultra-claude presets`. |
| `${CLAUDE_BIN}` / env-var interpolation in YAML | Users with non-PATH installs (e.g. nvm-managed CLIs) want to point at custom binary paths. | LOW | v1 | Pydantic field validator that runs `os.path.expandvars` on string fields. |

### Differentiators (v2+)

| Feature | Value Proposition | Complexity | v1/v2 | Dependencies |
|---------|-------------------|------------|-------|--------------|
| Additional presets: `plan_review.yaml`, `debug.yaml` | **Already in PROJECT.md v2 list.** Domain-specific presets show off the tool's range. | LOW each | v2 | None. |
| Schema export (`ultra-claude schema > ultra-claude.schema.json`) | IDE autocomplete in YAML files. Pydantic generates JSON schema for free. | LOW | v2 | `RoundtableConfig.model_json_schema()`. Document VSCode YAML extension setup. |
| Config inheritance / `extends:` | Compose presets ("start from `debate`, but use my custom system prompts"). | MED | v2 | Merge logic with deep-merge semantics. Tests for override precedence. |
| Per-project `pyproject.toml` config table | `[tool.ultra-claude]` in `pyproject.toml` for projects that already have one. | LOW | v2 | Read `pyproject.toml` if present and `[tool.ultra-claude]` table exists. |

### Anti-features

| Feature | Why Requested | Why NOT Build | Alternative |
|---------|---------------|---------------|-------------|
| TOML config (in addition to YAML) | "Why not both?" | Doubles the schema surface and tests. YAML is the convention for this kind of tool (CrewAI, AWS CAO, dmux all use markdown+YAML or YAML). | Stick with YAML. Document why ("most multi-agent tools converge on YAML"). |
| JSON config (in addition to YAML) | "JSON is universal." | Same reason. YAML is a superset of JSON anyway — users can write JSON in a YAML file if they really want. | None needed. |
| Plugin system for adapters via entry-points | "I want to ship `MyCoolAdapter` as a separate package." | Premature. v1 has 3 adapters; the plugin authority becomes load-bearing only when there are 10+. Adds discovery complexity, version-coupling. | Document: "to add a new adapter, subclass `BaseAdapter`, drop it in your project, reference it by import-string in YAML." Inspired by `custom Python predicate` pattern. |

---

## Area 4: CLI UX (`ultra-claude` Command)

### Table Stakes

| Feature | Why Expected | Complexity | v1/v2 | Notes |
|---------|--------------|------------|-------|-------|
| `ultra-claude run <task-file>` (primary command) | **In PROJECT.md Active list.** This IS the product. | LOW | v1 | Click subcommand. Required positional `task_file`. Optional `--config`, `--preset`, `--output`. |
| `ultra-claude --help` and per-subcommand `--help` | Click gives this for free. Users universally expect it. | LOW | v1 | Auto-generated. Customize the top-level docstring (`@click.group()`'s docstring becomes the help). |
| `ultra-claude --version` | Verified: standard Click pattern (`@click.version_option`). Users running `pip install` then `<tool> --version` to verify is a near-universal first-step ritual. | LOW | v1 | One line: `@click.version_option(__version__)`. Read from `importlib.metadata.version("ultra-claude")`. |
| Sane exit codes (0 success, 1 runtime error, 2 usage error) | Verified: Click conventions. Required for piping in CI / shell composition. Currently in scripting standards: 0 = success, 1 = error, 2 = misuse / config invalid. | LOW | v1 | Click does most of this; explicitly raise `click.UsageError` for config validation failures (auto-exit 2). Re-raise unhandled adapter errors as exit 1. |
| Clear error message on missing CLI | Constraint in PROJECT.md. Without this, users get cryptic `FileNotFoundError`. | LOW | v1 | Catch missing-binary at adapter-instantiation time. Print: "ultra-claude: 'claude' CLI not found on PATH. Install it: https://docs.anthropic.com/claude/docs/claude-code-cli" |

### Differentiators (v1-shippable)

| Feature | Value Proposition | Complexity | v1/v2 | Dependencies |
|---------|-------------------|------------|-------|--------------|
| Inline task (`ultra-claude run "Fix the auth bug" --inline`) | Skip writing a file for quick tasks. Lowers friction for the demo GIF. | LOW | v1 | If `--inline` flag, treat positional arg as the task string itself. |
| Live progress / status line ("Turn 3/20: gemini thinking…") | Without it, users stare at a frozen terminal during long Claude turns and assume the tool is broken. **Crucial UX without violating "no per-token streaming."** | LOW | v1 | Print status line to stderr (so transcript on stdout stays clean). Use `\r` to overwrite. |
| `ultra-claude presets` (list bundled presets) | Discoverability. Without it, users have to read source. | LOW | v1 | List YAML files in `ultra_claude/presets/`. Print name + description. |
| `--dry-run` (validate config + check CLIs without running) | Saves expensive turns when debugging YAML. Industry-standard for any complex CLI tool. | LOW | v1 | Validate config, run `shutil.which()` on each adapter, print plan, exit 0. |

### Differentiators (v2+)

| Feature | Value Proposition | Complexity | v1/v2 | Dependencies |
|---------|-------------------|------------|-------|--------------|
| `ultra-claude doctor` | Health-check all configured CLIs (login status, version, smoke test). | LOW | v2 | See "Adapter health-check" above. |
| `ultra-claude resume <transcript>` | Resume from a saved transcript. **Already covered as a v2 feature; the CLI surface is added here.** | MED | v2 | Resume capability + JSONL transcript. |
| `ultra-claude init` (scaffold `ultra-claude.yaml` interactively) | Guided onboarding. Click prompt-based. Could ship in v1 if friction-reduction is a priority. | LOW | v2 | Click prompts; write YAML. |
| Shell completion (`ultra-claude completion bash/zsh/fish`) | Standard for any CLI tool that grows. Click 8.x has built-in completion infra. | LOW | v2 | One-liner per shell. Include install instructions in docs. |
| `--quiet` / `--verbose` / `-v` flags | Standard. Pre-empts user confusion about output noise. | LOW | v2 | Click's `count` flag for `-v`. Wire into a logger. |
| TUI mode (`ultra-claude run --tui`) | See Orchestrator section. Opt-in only. | MED | v2 | rich/textual. |
| Color output / no-color (`--no-color` + `NO_COLOR` env) | Standard. Already supported by Click + rich. | LOW | v2 | Detect `NO_COLOR` env per the no-color.org spec. |

### Anti-features

| Feature | Why Requested | Why NOT Build | Alternative |
|---------|---------------|---------------|-------------|
| Interactive REPL (`ultra-claude shell`) | AI-Agents-Orchestrator and AWS CAO have one. | The product is "spawn a debate, get a transcript." A REPL adds state, makes scripting harder, and competes with the natural REPL each underlying CLI already has. | None. Use the underlying CLI directly for interactive work. |
| Short alias (`uc` / `ultra`) | "I'll type this 100 times." | **PROJECT.md Key Decision: discoverability over brevity.** Can revisit in v2 if requested. | Document the trade. Users can `alias uc=ultra-claude` themselves. |

---

## Area 5: Distribution (PyPI Package)

### Table Stakes

| Feature | Why Expected | Complexity | v1/v2 | Notes |
|---------|--------------|------------|-------|-------|
| Published to PyPI as `ultra-claude` | **In PROJECT.md Active list and Constraints.** Without PyPI presence, the tool is invisible. | LOW | v1 | `hatch publish`. Verify name availability on PyPI before tagging v0.1.0. **Risk: Anthropic might object to "claude" in the name.** Have a backup name ready (e.g., `ultraclaude`, `ultraclaude-cli`). |
| `pyproject.toml` (hatch backend) | **In PROJECT.md Active list.** Modern standard; Real Python and pyOpenSci both recommend hatchling. | LOW | v1 | `[build-system]` requires `hatchling`, build-backend `hatchling.build`. |
| MIT LICENSE | **In PROJECT.md Active list.** Most permissive, easiest adoption. | LOW | v1 | LICENSE file at repo root. PEP 639 SPDX expression in pyproject.toml: `license = "MIT"`, `license-files = ["LICENSE"]`. |
| README on PyPI (rendered from README.md) | **In PROJECT.md Active list.** First impression for anyone visiting the PyPI page. Users decide install/no-install in ~5 seconds. | LOW | v1 | `readme = "README.md"` in pyproject.toml. Use `hatch-fancy-pypi-readme` if README contains relative GitHub-only links. |
| One-line pitch + GIF placeholder + quickstart in README | **In PROJECT.md Active list.** Quickstart is the conversion lever. Demo GIF is the wow lever. | LOW | v1 | GIF placeholder ("![Demo](demo.gif) — *recording in progress*"). Real GIF can land in v0.1.1. |
| `.gitignore` | **In PROJECT.md Active list.** Standard. | LOW | v1 | Use Python.gitignore from github/gitignore. Add `*.transcript.md`. |
| Semver versioning | Universal Python expectation. PyPI sorts by semver. | LOW | v1 | Start at `0.1.0`. Bump per change. Use `__version__ = "0.1.0"` in package + read in CLI. |
| Cross-platform (macOS, Linux, Windows) | **PROJECT.md Constraint.** A Windows-broken tool on PyPI gets one-star reviews fast. | LOW | v1 | UTF-8 errors handling (covered above). Test on Windows (manual or via GH Actions in v2). |

### Differentiators (v1-shippable)

| Feature | Value Proposition | Complexity | v1/v2 | Dependencies |
|---------|-------------------|------------|-------|--------------|
| Small dependency surface (`pydantic`, `pyyaml`, `click` only) | **PROJECT.md Constraint:** "Keep dependency surface small for fast install." Differentiates from CrewAI/LangGraph (heavy deps). | LOW | v1 | Discipline; don't add transitive heavyweights. |
| Python ≥ 3.10 declared | **PROJECT.md Constraint:** Required for `Literal` typing, modern type hints. | LOW | v1 | `requires-python = ">=3.10"` in pyproject. |

### Differentiators (v2+)

| Feature | Value Proposition | Complexity | v1/v2 | Dependencies |
|---------|-------------------|------------|-------|--------------|
| GitHub Actions: pytest matrix (3.10, 3.11, 3.12, 3.13) on push/PR | **PROJECT.md v2 list.** Catches platform-specific breakage before users do. | LOW | v2 | Standard GH Actions Python workflow. |
| GitHub Actions: auto-publish to PyPI on `v*` tag | **PROJECT.md v2 list.** PyPI Trusted Publishing (OIDC, no API tokens). Fastest path from "merged" to "released." | LOW | v2 | Configure trusted publisher on PyPI. Tag-triggered workflow. |
| Distribute as both wheel (`*.whl`) and sdist (`*.tar.gz`) | Standard. wheels = fast install, sdist = source-build fallback. | LOW | v1 | `hatch build` produces both by default. |
| `pipx install ultra-claude` instructions in README | CLI tools should be installed in isolation. pipx is the canonical way. | LOW | v1 | Document in quickstart. |
| Homebrew formula | Mac users expect `brew install ultra-claude`. Adds discoverability beyond PyPI. | MED | v3 | After v1 traction. Maintained by hand or via homebrew-bump. |

### Anti-features

| Feature | Why Requested | Why NOT Build | Alternative |
|---------|---------------|---------------|-------------|
| Conda package | "Some users prefer conda." | Long tail. Maintainer burden disproportionate to user count for a CLI tool. | Conda-forge community can package if there's demand. |
| Docker image | "Containerized environments." | Each user's `claude`/`gemini`/`codex` logins are host-specific (login session in `~/.claude`, etc.). A container would have to bind-mount auth dirs — complex, fragile, and undermines "ride your existing CLI logins." | Document the pattern if a community PR shows up; don't ship official image. |

---

## Area 6: Documentation

### Table Stakes

| Feature | Why Expected | Complexity | v1/v2 | Notes |
|---------|--------------|------------|-------|-------|
| README quickstart (install, run example, first transcript) | **PROJECT.md Active list.** The 60-second "did it work?" moment. | LOW | v1 | 3-step: `pipx install ultra-claude` → `ultra-claude run task.md --preset debate` → "open transcript.md". |
| README "extending to new CLIs" section | **PROJECT.md Active list.** Demonstrates the BaseAdapter pattern. | LOW | v1 | 30-line example: subclass `BaseAdapter`, register via YAML import-string. |
| README one-line pitch | **PROJECT.md Active list.** Above-the-fold; the elevator pitch. | LOW | v1 | "Get Claude, Gemini, and Codex to debate your problem in your terminal — using your existing CLI logins, no API keys." |

### Differentiators (v1-shippable)

| Feature | Value Proposition | Complexity | v1/v2 | Dependencies |
|---------|-------------------|------------|-------|--------------|
| Demo GIF (failing test → debate → fix) | **PROJECT.md Demo Strategy.** GIFs convert 3-5x better than text on dev tools. | MED (recording) | v1 (placeholder ok at launch) | asciinema → agg → gif. |
| Real transcript artifacts in `examples/` directory | **PROJECT.md v2 list — but recommend pulling forward.** Lets users see actual output without running, lowering install-friction for tire-kickers. | LOW | v1 | One transcript per bundled preset. Real output, redacted as needed. |
| FAQ section ("why no API keys?", "how does this differ from AutoGen?") | Pre-empts the same questions you'll get on Show HN / Reddit. | LOW | v1 | Inline in README under `## FAQ`. |

### Differentiators (v2+)

| Feature | Value Proposition | Complexity | v1/v2 | Dependencies |
|---------|-------------------|------------|-------|--------------|
| Full docs site (mkdocs / docusaurus) | **PROJECT.md v2 list.** Past a certain README size, a docs site beats one mega-README. | MED | v2 | mkdocs-material is the Python convention. GH Pages hosting. |
| Adding-new-agents tutorial (longform) | Encourages contributions and enables the long tail of CLI integrations. | LOW | v2 | Walks through subclassing `BaseAdapter`. |
| Configuration reference (auto-generated from Pydantic schema) | Single source of truth for YAML keys; never goes stale. | LOW | v2 | `pydantic2docs` or hand-rolled from `model_json_schema()`. |
| Examples gallery (`x_news_debug.md`, `api_design.md`) | **PROJECT.md v2 list.** Real-world transcripts validate the value. | LOW | v2 | Capture during dogfooding. |

### Anti-features

| Feature | Why Requested | Why NOT Build | Alternative |
|---------|---------------|---------------|-------------|
| Video tutorials | "Some people prefer video." | Maintenance burden (re-record on UI changes). GIF + text is sufficient for a CLI tool. | Community can make videos. |

---

## Area 7: Testing

### Table Stakes

| Feature | Why Expected | Complexity | v1/v2 | Notes |
|---------|--------------|------------|-------|-------|
| Tests with `subprocess.run` mocked | **PROJECT.md Active list:** "tests with `subprocess.run` mocked so CI runs without real CLIs installed." Required so contributors don't need Anthropic+OpenAI+Google logins to run tests. | LOW | v1 | `pytest` + `unittest.mock.patch("subprocess.run")`. Mock returns canned `CompletedProcess` objects. |
| Pydantic validation tests (good config + bad config error messages) | Without these, the YAML→Pydantic→error-format pipeline silently regresses. | LOW | v1 | `pytest.raises(ValidationError)` then assert `.errors()` has the expected `loc`/`type`. |
| Adapter tests (each adapter calls subprocess with right argv) | The whole product is "the right argv." Skip this and you ship broken adapters. | LOW | v1 | Mock + assert call_args. |
| Orchestrator loop test (round-robin produces correct turn sequence) | Core logic. | LOW | v1 | Mock adapters return canned strings; assert transcript order. |
| Stop condition tests (max_turns, keyword) | Without these, users hit infinite loops. | LOW | v1 | Mock orchestrator with controlled inputs. |

### Differentiators (v1-shippable)

| Feature | Value Proposition | Complexity | v1/v2 | Dependencies |
|---------|-------------------|------------|-------|--------------|
| Cross-platform tests (Linux, macOS, Windows) | **PROJECT.md Constraint:** "Must work on macOS, Linux, Windows." | LOW (in v2 with GH Actions) / MED (manual in v1) | v1 manual / v2 CI matrix | GH Actions matrix in v2. |
| Coverage report (≥90% line) | Confidence baseline. Public PRs review easier when coverage stays green. | LOW | v1 | `pytest --cov=ultra_claude`. |

### Differentiators (v2+)

| Feature | Value Proposition | Complexity | v1/v2 | Dependencies |
|---------|-------------------|------------|-------|--------------|
| Integration tests with real CLIs (opt-in, marked `@pytest.mark.integration`) | Mocks lie. At least one nightly run against real CLIs catches real-world breakage. | MED | v2 | GH Actions secret-stored login state. |
| Property-based tests (Hypothesis) for config schema | Catches edge-case YAML inputs the test author didn't think of. | MED | v2 | `hypothesis-pydantic-strategies`. |

### Anti-features

| Feature | Why Requested | Why NOT Build | Alternative |
|---------|---------------|---------------|-------------|
| 100% line coverage target | Sounds rigorous. | Often pads with low-value tests. ~90% with manual mutation review beats 100% by metric-gaming. | Aim for 90%+ with judgement. |

---

## Feature Dependencies

```
┌───────────────────────────────────────────────────────────────┐
│ TABLE STAKES (v1) — all flat, no internal deps to break       │
└───────────────────────────────────────────────────────────────┘
   BaseAdapter ABC
       └──> ClaudeAdapter, GeminiAdapter, CodexAdapter (siblings)

   Pydantic config schema (RoundtableConfig, AgentConfig)
       └──> YAML loader
              └──> CLI entrypoint (`ultra-claude run`)
                     └──> Orchestrator loop
                            └──> Markdown transcript writer

   `debate.yaml` preset
       └── depends on: AgentConfig schema being stable

┌───────────────────────────────────────────────────────────────┐
│ V1 DIFFERENTIATORS — mostly flat too                          │
└───────────────────────────────────────────────────────────────┘
   Per-agent system prompts ──> required by `debate.yaml` to be useful
   Append-as-you-go transcript writing ──> standalone
   --preset flag ──> depends on bundled preset
   --dry-run ──> depends on adapter health-check or shutil.which

┌───────────────────────────────────────────────────────────────┐
│ V2 — many features chain through JSONL transcript             │
└───────────────────────────────────────────────────────────────┘
   JSONL transcript format
       └──> Resume capability (`ultra-claude resume`)
              └──> [v3] Branching/forking
       └──> Programmatic stop predicates (cleaner with structured data)

   `speaker_chooses` turn order
       └──> Requires output-parsing convention (e.g., `NEXT: <agent>` last line)

   Concurrent agent invocation
       └──> Requires asyncio adapter path (parallel to v1's sync path)

   TUI mode
       └──> Depends on rich/textual; opt-in via flag to keep core install lean

   GH Actions auto-publish to PyPI
       └──> Depends on PyPI Trusted Publishing (no token mgmt)
       └──> Depends on first manual v0.1.0 publish (registers the package)

┌───────────────────────────────────────────────────────────────┐
│ V3+ (deferred / aspirational)                                 │
└───────────────────────────────────────────────────────────────┘
   Branching/forking ──> JSONL + resume + state mgmt
   Reactor mode ──> HTTP server, deviates from "local CLI" simplicity
   Homebrew formula ──> after PyPI traction
```

### Dependency Notes

- **Per-agent system prompts ⇒ `debate.yaml` preset:** Without per-agent system prompts, the bundled preset can't differentiate architect/critic/implementer roles. **The preset feature is empty without it.** Both stay in v1.
- **JSONL transcript ⇒ Resume capability ⇒ Branching/forking:** Resume is much cleaner with structured turns; branching is essentially "resume from arbitrary checkpoint with substitutions." All three should land in this order, **JSONL first**.
- **`speaker_chooses` requires output-parsing convention:** Either a sentinel last line (`NEXT: gemini`) or in-prose mention parsing (`@gemini, can you...`). Pick one and document it. **Sentinel-last-line is more reliable** but requires per-agent system-prompt instruction.
- **Concurrent invocation conflicts with `subprocess.run` (sync) decision in PROJECT.md:** v1 explicitly chose sync; concurrent invocation requires asyncio. **Don't fold async in until v2 actually needs it** (the feature itself is the trigger). Adapters can be ported to async then; the sync `BaseAdapter` interface can keep working via `asyncio.to_thread`.
- **GH Actions auto-publish requires manual v0.1.0 first:** PyPI Trusted Publishing needs a project to exist before binding to it. **PROJECT.md sequence is correct: manual v0.1.0 in v1, automation in v2.**

---

## MVP Definition

### Launch With (v1) — the "Lean MVP" per PROJECT.md

**Adapters (Area 1):**
- [ ] `BaseAdapter` ABC
- [ ] `ClaudeAdapter`, `GeminiAdapter`, `CodexAdapter`
- [ ] Missing-CLI clear error
- [ ] UTF-8 with `errors="replace"` (Windows)
- [ ] Per-turn timeout via `subprocess.run(timeout=...)`
- [ ] Per-agent CLI extra-args field (small differentiator, near-zero cost)

**Orchestrator (Area 2):**
- [ ] Round-robin turn order
- [ ] Transcript-as-context
- [ ] Markdown transcript writer (append-as-you-go)
- [ ] `max_turns` stop condition
- [ ] Keyword stop condition (e.g., `AGREED`, `SHIP IT`)
- [ ] Per-agent system prompts

**Config (Area 3):**
- [ ] Pydantic `RoundtableConfig` + `AgentConfig`
- [ ] YAML loader with humanized errors
- [ ] Default `ultra-claude.yaml` discovery (cwd)
- [ ] `--config` flag
- [ ] Bundled `debate.yaml` preset
- [ ] `--preset <name>` flag
- [ ] Env-var interpolation (`${VAR}`)

**CLI UX (Area 4):**
- [ ] `ultra-claude run <task-file>` — primary command
- [ ] `--help` and `--version`
- [ ] Sane exit codes (0 / 1 / 2)
- [ ] Live status line on stderr
- [ ] `ultra-claude presets` (list bundled presets)
- [ ] `--inline` for one-shot tasks
- [ ] `--dry-run`

**Distribution (Area 5):**
- [ ] PyPI publish (`ultra-claude`)
- [ ] `pyproject.toml` (hatch)
- [ ] MIT LICENSE
- [ ] README (pitch + GIF placeholder + quickstart + extending)
- [ ] `.gitignore`
- [ ] Python ≥ 3.10
- [ ] Small deps only (`pydantic`, `pyyaml`, `click`)
- [ ] Wheel + sdist
- [ ] `pipx` install instructions

**Docs (Area 6):**
- [ ] README quickstart
- [ ] README "extending to new CLIs"
- [ ] One-line pitch
- [ ] FAQ
- [ ] Examples directory with at least one real transcript

**Testing (Area 7):**
- [ ] Mocked-subprocess tests
- [ ] Pydantic validation tests
- [ ] Adapter argv tests
- [ ] Orchestrator loop tests
- [ ] Stop condition tests
- [ ] Coverage ≥ 90%

### Add After Validation (v1.x — point releases)

Trigger: bug reports, install-friction reports, the obvious gaps you hit while making the demo GIF.

- [ ] Adapter retry on subprocess failure (cheap; ship after first user reports a flaky CLI)
- [ ] `ultra-claude doctor` (cheap; ship after first "why isn't it working" issue)
- [ ] Real demo GIF (replace placeholder)
- [ ] Additional bundled presets (`plan_review`, `debug`) — quick wins

### Future Consideration (v2+) — already planned in PROJECT.md

Trigger: v1 has traction (PyPI downloads, GitHub stars, issue activity).

- [ ] GH Actions: pytest matrix
- [ ] GH Actions: auto-publish on tag
- [ ] `speaker_chooses` turn order
- [ ] `manual` and `random` turn orders (cheap to add alongside)
- [ ] `file_exists` and `regex` stop conditions
- [ ] Custom Python predicate stop condition
- [ ] JSONL transcript format
- [ ] Resume from existing transcript
- [ ] Concurrent agent invocation (async path)
- [ ] Additional adapters (Cursor, Copilot, OpenCode, Amp, Ollama, llama.cpp)
- [ ] Schema export
- [ ] Shell completion
- [ ] `--quiet` / `--verbose`
- [ ] Full docs site (mkdocs)
- [ ] TUI live view (opt-in via `--tui`)
- [ ] Examples gallery

### Defer to v3+ / Out of Scope

- [ ] Branching/forking conversations — high complexity, niche, defer until JSONL+resume bedding in
- [ ] Reactor mode (webhook-triggered) — adds HTTP server, complicates "local CLI" pitch
- [ ] Homebrew formula — after PyPI traction
- [ ] Plugin system via entry-points — premature; import-string pattern suffices
- [ ] **Anti-features (never build):** API-key adapters, hosted SaaS, real-time per-token streaming, persistent inter-run memory, inter-agent direct messaging, mobile/GUI, REPL, short alias

---

## Feature Prioritization Matrix

(Top-line summary; full per-feature complexity is in the area tables above.)

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Three working adapters | HIGH | LOW | **P1 (v1)** |
| Round-robin orchestrator + markdown transcript | HIGH | LOW | **P1 (v1)** |
| `max_turns` + keyword stop conditions | HIGH | LOW | **P1 (v1)** |
| Per-agent system prompts | HIGH | LOW | **P1 (v1)** — required for `debate.yaml` to mean anything |
| Append-as-you-go transcript | HIGH | LOW | **P1 (v1)** — best-bang-for-buck UX win without violating no-streaming |
| `debate.yaml` preset + `--preset` flag | HIGH | LOW | **P1 (v1)** — biggest onboarding lever |
| Live status line on stderr | MED | LOW | **P1 (v1)** — prevents "is it frozen?" |
| Mocked-subprocess tests | HIGH | LOW | **P1 (v1)** |
| README quickstart + GIF | HIGH | MED | **P1 (v1)** |
| PyPI publish | HIGH | LOW | **P1 (v1)** |
| Cross-platform UTF-8 | MED (Windows users only) | LOW | **P1 (v1)** |
| `--dry-run` | MED | LOW | **P1 (v1)** |
| `--inline` task | MED | LOW | **P1 (v1)** |
| Adapter retries | MED | LOW | **P2 (v1.x)** |
| `ultra-claude doctor` | MED | LOW | **P2 (v1.x)** |
| Additional presets | MED | LOW | **P2 (v2)** |
| GH Actions CI/CD | HIGH (maintainer value) | LOW | **P2 (v2)** |
| `speaker_chooses` | HIGH | MED | **P2 (v2)** |
| `file_exists` / `regex` / `predicate` stops | MED | LOW–MED | **P2 (v2)** |
| JSONL transcript | MED (programmatic users) | LOW | **P2 (v2)** |
| Resume capability | MED | MED | **P2 (v2)** |
| Concurrent invocation | MED | MED | **P2 (v2)** |
| TUI mode | MED | MED | **P3 (v2 opt-in)** |
| Branching/forking | HIGH (power users) | HIGH | **P3 (v3)** |
| Reactor mode | LOW (niche) | HIGH | **P3 (v3+)** |

---

## Competitor Feature Analysis

| Feature | AutoGen / AG2 | CrewAI | LangGraph | dmux | overstory | AWS CAO | AI-Agents-Orch. (hoangsonww) | **ultra-claude** |
|---------|---------------|--------|-----------|------|-----------|---------|------------------------------|------------------|
| **Authentication model** | API keys | API keys (any provider) | API keys | Rides CLI logins (tmux) | Rides CLI logins (some) | Rides CLI logins | Rides CLI logins | **Rides CLI logins (subprocess)** |
| **Process model** | In-process | In-process | In-process | tmux panes + git worktrees | git worktrees + headless / tmux | tmux sessions | Subprocess + REPL | **subprocess.run, blocking, no tmux** |
| **Turn order** | round-robin / auto / random / manual / custom fn | sequential / hierarchical / consensual | graph-defined | n/a (parallel agents) | coordinator-dispatched | handoff / assign / send | fixed chain / agentic team | **round-robin (v1), `speaker_chooses` (v2)** |
| **Stop conditions** | max rounds + DONE token + custom | task complete | recursion_limit + interrupt | merge-ready + watchdog | merge_ready / check-complete / stop | n/a (per agent) | max-turns + PM gate | **max_turns + keyword (v1); + file_exists/regex/predicate (v2)** |
| **Transcript format** | structured (in-process) | structured (in-process) | structured (in-process) | tmux scrollback | NDJSON + runtime-specific | n/a (per session) | JSON / Markdown / HTML | **Markdown (v1), JSONL+JSON (v2)** |
| **Resume from transcript** | session IDs | n/a | checkpointer | n/a | --recover | n/a | history within graph | **v2** |
| **Branching/forking** | n/a | n/a | thread branches | per-worktree | per-worktree | n/a | n/a | **v3 (deferred)** |
| **Concurrent agents** | yes (event-driven) | yes (parallel) | yes (parallel branches) | yes (multi-pane) | yes (worktrees) | yes (assign pattern) | n/a | **v2** |
| **TUI mode** | n/a | n/a | n/a | tmux (native) | `ov dashboard` | tmux (native) | REPL shell | **v2 opt-in (rich/textual)** |
| **Web dashboard** | n/a | yes | yes (LangSmith) | n/a | `ov serve` | yes (HTTP server) | Vue/Nuxt | **NO (anti-feature)** |
| **Bundled presets** | n/a (write code) | n/a | n/a | n/a | n/a | profile templates | 7 workflows | **`debate.yaml` (v1), more (v2)** |
| **Plugin model** | code-level | code-level | code-level | runtime adapters (11) | runtime adapters (11) | profile markdown | 9 specialized agents | **subclass `BaseAdapter`, import-string in YAML** |
| **Config language** | Python code | YAML / Python | Python code | YAML | TOML / YAML | Markdown+YAML frontmatter | YAML | **YAML + Pydantic** |
| **Install complexity** | `pip install pyautogen` (heavy deps) | `pip install crewai` (very heavy) | `pip install langgraph` (heavy) | npm + tmux + git + each CLI | npm + git worktrees + each CLI | tmux + each CLI | npm + each CLI | **`pipx install ultra-claude` + ≥1 of `claude`/`gemini`/`codex`** |
| **First-run experience** | write Python | write Python or YAML | write Python | configure each agent | configure each agent | write Markdown profile | configure REPL | **`ultra-claude run task.md --preset debate`** |

**ultra-claude's narrow but strong wedge:**
1. **Subprocess-only model** (uniquely simple — most "CLI orchestrators" actually use tmux + git worktrees)
2. **No API keys** (uniquely true vs AutoGen/CrewAI/LangGraph)
3. **PyPI installable** (uniquely Python+pip vs npm-heavy ecosystem of overstory/dmux)
4. **YAML-first** with bundled preset (uniquely zero-Python-code first run vs AutoGen/LangGraph)
5. **Minimal abstraction** — three adapters, one loop, one transcript file (vs the conceptual heaviness of AI-Agents-Orchestrator's 9 agents + 22 skills + MCP server + Vue dashboard)

**Risks vs competitors:**
- AWS CAO (`cli-agent-orchestrator`) is the closest direct competitor, with AWS marketing weight. **Differentiate on simplicity and Python ecosystem.** AWS CAO uses tmux + Markdown profiles + an HTTP server. ultra-claude uses subprocess + YAML + a flat library. Smaller surface = easier to grok = more contributions.
- dmux has the same "subprocess each CLI" idea but is tmux-centric and parallel-execution-focused. **ultra-claude's wedge: serial debate vs parallel work.**
- Aider's architect/editor mode is a 2-agent special case. ultra-claude generalizes to N agents with arbitrary roles.

---

## Cross-Check Against PROJECT.md Active List

Mapping each requirement in PROJECT.md to its category here.

### v1 Active list (from PROJECT.md) — all categorized

| PROJECT.md Active item | This doc's category | Status |
|------------------------|---------------------|--------|
| Python package `ultra-claude` published to PyPI | Area 5: Distribution → table stakes | ✓ covered |
| `BaseAdapter` ABC | Area 1: Adapters → table stakes | ✓ covered |
| `ClaudeAdapter` (`claude -p <prompt>`) | Area 1 → table stakes | ✓ covered (verified `-p` works for one-shot) |
| `GeminiAdapter` (`gemini -p <prompt>`) | Area 1 → table stakes | ✓ covered (verified `-p` works) |
| `CodexAdapter` (`codex exec <prompt>`) | Area 1 → table stakes | ✓ covered (verified `codex exec` works) |
| Pydantic `RoundtableConfig`, `AgentConfig` | Area 3: Configuration → table stakes | ✓ covered |
| Orchestrator: round-robin + transcript-as-context + markdown | Area 2: Orchestrator → table stakes | ✓ covered |
| Stop conditions: keyword + max_turns | Area 2 → table stakes | ✓ covered |
| CLI: `ultra-claude run <task-file>` | Area 4: CLI UX → table stakes | ✓ covered |
| Bundled preset: `debate.yaml` | Area 3 → table stakes | ✓ covered |
| Mocked-subprocess tests | Area 7: Testing → table stakes | ✓ covered |
| README (pitch / GIF / quickstart / extending) | Area 6: Documentation → table stakes | ✓ covered |
| MIT LICENSE, pyproject.toml (hatch), .gitignore | Area 5 → table stakes | ✓ covered |
| First public release v0.1.0 to PyPI | Area 5 → table stakes | ✓ covered |

### v2 Active list (from PROJECT.md) — all categorized

| PROJECT.md v2 item | This doc's category | Status |
|--------------------|---------------------|--------|
| GH Actions: pytest matrix | Area 5 → v2 | ✓ covered |
| GH Actions: auto-publish on tag | Area 5 → v2 | ✓ covered |
| Additional presets `plan_review`, `debug` | Area 3 → v2 | ✓ covered |
| `speaker_chooses` turn order | Area 2 → v2 | ✓ covered |
| Stop conditions: `file_exists`, regex | Area 2 → v2 | ✓ covered |
| Examples directory with real transcripts | Area 6 → v2 (recommend pulling forward to v1) | ✓ covered, with v1-pull-forward recommendation |
| Full docs site | Area 6 → v2 | ✓ covered |
| Promotion (Reddit, Show HN, X) | n/a — marketing, not feature | not in this doc's scope |

### Out of Scope list (from PROJECT.md) — all confirmed as anti-features

| PROJECT.md OoS item | This doc's anti-feature reasoning | Aligned? |
|---------------------|-----------------------------------|----------|
| API-key-driven agents | Area 1 anti-feature with same reasoning | ✓ aligned |
| Real-time streaming output mid-turn | Area 1 anti-feature with same reasoning + alternative | ✓ aligned |
| Persistent agent memory between runs | Area 2 anti-feature with same reasoning + alternative (point at saved transcript) | ✓ aligned |
| Hosted/SaaS version | Area 2 anti-feature with same reasoning | ✓ aligned |
| Mobile app / GUI | Area 2 anti-feature with same reasoning | ✓ aligned |
| Inter-agent direct messaging | Area 2 anti-feature with same reasoning + alternative (transcript IS the bus) | ✓ aligned |

### Gaps and Surplus — explicit flagging

**Gaps in PROJECT.md Active list (features this research recommends adding to v1 that aren't in PROJECT.md):**

1. **Per-agent system prompts** — without this, the bundled `debate.yaml` preset cannot differentiate architect / critic / implementer roles. The preset would have all three agents doing the same thing. **Strongly recommend pulling into v1.** Cost: LOW (one optional field on `AgentConfig`, prepended to prompt).
2. **Append-as-you-go transcript writing** — biggest UX win without per-token streaming. Instead of waiting until the run ends, users can `tail -f transcript.md` and watch the debate. Cost: LOW (open file in append mode, flush each turn).
3. **Live status line on stderr** ("Turn 3/20: gemini thinking…") — prevents "is it frozen?" confusion during long Claude turns. Cost: LOW.
4. **`--preset <name>` shortcut flag** — onboarding friction killer. `ultra-claude run task.md --preset debate` Just Works in any directory without a local YAML file. Cost: LOW.
5. **`--dry-run` flag** — validate config + check CLIs without burning a turn. Cost: LOW. Saves users from expensive failures.
6. **`--inline "task string"` flag** — skip writing a task file for one-shots. Critical for the demo GIF and for casual usage. Cost: LOW.
7. **`ultra-claude --version`** — implicit standard, but worth listing explicitly. Click gives this for free. Cost: NIL.
8. **Per-agent CLI extra-args** (`extra_args: ["--allowedTools", "Read,Edit"]`) — lets users customize Claude/Codex without forking. Cost: LOW. Strong differentiator vs hardcoded competitors.
9. **Env-var interpolation in YAML** (`${CLAUDE_BIN}`) — for users with non-PATH installs (nvm, rbenv, etc.). Cost: LOW.
10. **Per-turn timeout** — implicit but worth being explicit. Without it, a hung CLI hangs the whole run. **Risk: catastrophic UX failure if missed.** Cost: NIL (one kwarg to `subprocess.run`).
11. **UTF-8 + `errors="replace"`** — already a constraint but not a feature line-item; should be explicit. Cost: NIL.
12. **One real example transcript in `examples/`** — pulled forward from v2. Lets tire-kickers see output without installing. Cost: LOW (just paste a real run).

**Surplus / things in PROJECT.md that this research found don't need extra work:**

- `.gitignore` — fully a 1-line standard file. No analysis needed.
- MIT LICENSE — fully a 1-file standard. No analysis needed.
- "Promotion: r/LocalLLaMA, r/ClaudeAI…" — out of scope for feature research; this is marketing strategy.

**Things on the v2 Active list that this research recommends pulling forward to v1:**

- `examples/` directory with at least one real transcript — recommend v1.

**Things this research recommends explicitly deferring beyond v2 (PROJECT.md doesn't list them, but I want to flag the choice):**

- Branching/forking conversations → v3.
- Reactor mode (webhook-triggered) → v3+.
- Homebrew formula → v3+ (after PyPI traction).

---

## Confidence Notes

- **HIGH confidence** for all v1 features: every CLI invocation pattern was verified against official docs (Claude Code `-p`, Gemini `-p`, Codex `exec`); Click conventions verified against Click 8.3 docs; PyPI/hatch conventions verified against pyOpenSci and packaging.python.org.
- **HIGH confidence** for v2 features that mirror PROJECT.md's v2 list (`speaker_chooses`, `file_exists`/regex stops, GH Actions, additional presets) — these are direct user-stated targets.
- **MEDIUM confidence** for the "differentiator (v1-shippable)" features I'm recommending adding to PROJECT.md (per-agent system prompts, append-as-you-go transcript, live status line, --preset, --dry-run, --inline, extra_args, env-var interp). Reasoning is solid but these are recommendations, not user-stated requirements.
- **MEDIUM confidence** for branching/forking and reactor mode being v3 (deferred). Could be v2 if user wants to compete head-on with overstory / Forky on power-user features. **Flag this for the requirements step.**
- **LOW confidence** about the exact ordering of v2 features beyond what's in PROJECT.md. Real ordering should be reactive to v1 feedback.

---

## Sources

**Direct competitors (CLI-orchestrator class):**
- [awslabs/cli-agent-orchestrator (CAO)](https://github.com/awslabs/cli-agent-orchestrator) — closest direct competitor, tmux-based
- [Introducing CLI Agent Orchestrator (AWS Open Source Blog)](https://aws.amazon.com/blogs/opensource/introducing-cli-agent-orchestrator-transforming-developer-cli-tools-into-a-multi-agent-powerhouse/)
- [jayminwest/overstory](https://github.com/jayminwest/overstory) — 11-runtime adapter system, git worktrees
- [hoangsonww/AI-Agents-Orchestrator](https://github.com/hoangsonww/AI-Agents-Orchestrator) — fixed chains + Agentic Team runtime
- [standardagents/dmux](https://github.com/standardagents/dmux) — tmux-based parallel multiplexer
- [dmux: The Dev Agent Multiplexer for Parallel AI](https://blog.brightcoding.dev/2026/03/21/dmux-the-revolutionary-dev-agent-multiplexer-for-parallel-ai)
- [andyrewlee/awesome-agent-orchestrators](https://github.com/andyrewlee/awesome-agent-orchestrators) — landscape index

**Adjacent multi-agent frameworks (API-key-based):**
- [microsoft/autogen](https://github.com/microsoft/autogen)
- [Multi-agent Conversation Framework | AutoGen 0.2](https://microsoft.github.io/autogen/0.2/docs/Use-Cases/agent_chat/)
- [Group Chat with Customized Speaker Selection](https://microsoft.github.io/autogen/0.2/docs/topics/groupchat/customized_speaker_selection/)
- [crewAIInc/crewAI](https://github.com/crewaiinc/crewai)
- [CrewAI Documentation](https://docs.crewai.com/)
- [Best Multi-Agent Frameworks in 2026](https://gurusup.com/blog/best-multi-agent-frameworks-2026)
- [LangGraph: GRAPH_RECURSION_LIMIT](https://docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT)
- [LangGraph Interrupts](https://blog.langchain.com/making-it-easier-to-build-human-in-the-loop-agents-with-interrupt/)
- [Aider Chat modes (architect)](https://aider.chat/docs/usage/modes.html)
- [Aider Architect/Editor approach](https://aider.chat/2024/09/26/architect.html)

**Underlying CLIs (verifying invocation contracts):**
- [Claude Code Headless Mode (`claude -p`)](https://code.claude.com/docs/en/headless)
- [Codex CLI Features](https://developers.openai.com/codex/cli/features)
- [Codex CLI Non-interactive mode (`codex exec`)](https://developers.openai.com/codex/noninteractive)
- [Gemini CLI cheatsheet (`gemini -p`)](https://geminicli.com/docs/cli/cli-reference/)
- [Gemini CLI Tips & Tricks (Addy Osmani)](https://addyo.substack.com/p/gemini-cli-tips-and-tricks)

**Conventions (Python, Click, Pydantic, PyPI):**
- [Click Documentation 8.3](https://click.palletsprojects.com/)
- [Click Exception Handling and Exit Codes](https://click.palletsprojects.com/en/stable/exceptions/)
- [How to Validate YAML Configs with Pydantic](https://www.sarahglasmacher.com/how-to-validate-config-yaml-pydantic/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/api/pydantic_settings/)
- [pyproject.toml writing guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [pyOpenSci Python Packaging Guide](https://www.pyopensci.org/python-package-guide/tutorials/pyproject-toml.html)
- [hatchling on PyPI](https://pypi.org/project/hatchling/)

**Adjacent features (transcript formats, branching, TUI):**
- [claude-code-log (JSONL→HTML/Markdown)](https://github.com/daaain/claude-code-log)
- [claude-JSONL-browser](https://github.com/withLinda/claude-JSONL-browser)
- [Forky: git-style LLM chats](https://github.com/ishandhanani/forky)
- [Context Branching for LLM Conversations (arxiv)](https://arxiv.org/abs/2512.13914)
- [Warp Conversation forking](https://docs.warp.dev/agent-platform/warp-agents/interacting-with-agents/conversation-forking)
- [Textualize Rich Live Display](https://rich.readthedocs.io/en/latest/live.html)
- [Python Textual: Build Beautiful TUIs](https://realpython.com/python-textual/)
- [Python asyncio subprocesses (parallel CLI invocation)](https://docs.python.org/3/library/asyncio-subprocess.html)

**Reactor / event-driven patterns:**
- [Trigger flows with webhooks (Langflow)](https://docs.langflow.org/webhook)
- [Trigger-Action Workflows with LLMs](https://latitude-blog.ghost.io/blog/trigger-action-workflows-with-llms/)

---
*Feature research for: Multi-agent LLM orchestration via subprocess (CLI-driven, no-API-key)*
*Researched: 2026-05-02*
