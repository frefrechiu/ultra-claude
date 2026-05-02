# Project Research Summary

**Project:** ultra-claude
**Domain:** Multi-agent CLI orchestration via subprocess (no API keys, uses existing CLI logins)
**Researched:** 2026-05-02
**Confidence:** HIGH

## Executive Summary

ultra-claude occupies a small but defensibly distinct corner of the multi-agent space: subprocess-based orchestration of three already-installed LLM CLIs (Claude Code, Gemini CLI, Codex), with the transcript itself acting as the only inter-agent channel. The closest competitors (AutoGen, LangGraph, CrewAI) require API keys; the closest tmux-based alternatives (AWS Labs CAO, dmux, overstory) bring substantial infra. ultra-claude's wedge — "spawn three CLIs, share a markdown file, no API keys, no tmux" — is technically sound: all three target CLIs verifiably support clean one-shot invocation (`claude -p`, `gemini -p`, `codex exec`).

The recommended approach is a small Python package built on `hatchling` + `click` + `pydantic v2` + `pyyaml`, with adapters defined as a `typing.Protocol` (not ABC) so third-party adapters require no inheritance. The orchestrator is a single function operating a round-robin loop; transcripts are markdown (canonical, re-promptable) with a JSONL sidecar (parseable for future resume/analysis tooling).

The biggest risks are technical, not adoption-related: (1) a live, severity-CRITICAL bug in `codex exec` 0.124.0+ that returns exit-0 with empty stdout when no TTY is present — exactly the conditions `subprocess.run` produces; (2) Windows command-line length limits (~8 KB through cmd.exe) that argv-passed prompts hit by debate-turn 3; (3) the Windows encoding triple-trap (cp1252 default × OEM stderr × UTF-8 LLM output) that crashes on emoji and smart quotes. All three are addressable with defensive adapter design and Windows-from-day-1 CI.

## Key Findings

### Recommended Stack

Python 3.10+ with `hatchling` build backend, `click` CLI framework, `pydantic v2` config validation, `pyyaml` config loading. Verified via PyPI lookups on 2026-05-02. PyPI name `ultra-claude` is verified AVAILABLE — should be reserved as a 0.0.1 stub on day 1 before any public mention.

**Core technologies:**
- **Python ≥ 3.10** — `Literal` typing, modern type hints. (3.10 EOLs 2026-10-31; plan a 3.11 floor in late 2026.)
- **hatchling** (build backend) — modern PyPA-maintained backend. User does NOT need the full `hatch` CLI; plain `pip install -e ".[dev]"` is sufficient project management.
- **click 8.3.3** — proven CLI framework; reject Typer (overkill for 1-3 commands), reject rich-click (transitive bloat).
- **pydantic 2.13.3 + pyyaml 6.0.3** — Pydantic's official examples show `model_validate(yaml.safe_load(f))` pattern. Reject `pydantic-settings` (wrong tool — config is YAML file, not env vars). Reject `ruamel.yaml` (read-only config doesn't need comment preservation).
- **ruff ≥ 0.13** (replaces black+isort+flake8+pyupgrade in one Rust binary), **mypy ≥ 1.18** (libraries should match what their users will use for type-checking).
- **pytest ≥ 8.4 + pytest-mock + pytest-cov + pytest-subprocess** — `pytest-subprocess`'s `fp` fixture is the dominant solution for subprocess testing. Add a tiny `tests/fixtures/echo_cli.py` Python script as a fake CLI binary for orchestrator E2E tests.
- **PyPI Trusted Publishing (OIDC) via `pypa/gh-action-pypi-publish`** — the 2026 standard, no API tokens. Defer to v2 per PROJECT.md. v1 manual `python -m build` + `twine upload` is fine for v0.1.0.

See `.planning/research/STACK.md` for full version matrix and rationale.

### Expected Features

Categorized by area (Adapters, Orchestrator, Config, CLI UX, Distribution, Docs, Testing). Full detail in `.planning/research/FEATURES.md`.

**Must have (table stakes — without these the tool doesn't feel real):**
- Three working adapters: `ClaudeAdapter`, `GeminiAdapter`, `CodexAdapter`
- Round-robin turn order
- Markdown transcript appended turn-by-turn (so `tail -f transcript.md` works)
- At least two stop conditions: keyword match + `max_turns`
- Per-agent system prompts (without these, `debate.yaml` is meaningless)
- `ultra-claude run <task>` CLI with `--config`, `--output`, `--help`, `--version`, exit codes
- `pyproject.toml`, README with quickstart, MIT LICENSE
- Mocked-subprocess tests (CI runs without real CLIs installed)

**Should have (v1 differentiators — bigger onboarding wins, low cost):**
- `--preset debate` flag (load bundled preset)
- `--inline` flag (run with task as a string instead of file)
- `--dry-run` flag (validate config without invoking adapters)
- `examples/` directory with real transcripts (PyPI page credibility)
- Pre-flight auth check before the orchestrator loop starts

**Defer (v2+):**
- Speaker-chooses turn order (AutoGen-style dispatch)
- Additional stop conditions: `file_exists`, custom regex, custom Python predicate
- Plugin discovery via entry points (third-party adapters)
- JSONL transcript sidecar (parseable for resume/analysis)
- TUI live view (rich/textual)
- GitHub Actions test matrix + auto-publish on tag
- Additional presets: `plan_review.yaml`, `debug.yaml`
- `ultra-claude doctor` standalone subcommand
- Full docs site (mkdocs-material + mkdocs-click)

**Anti-features (deliberately NOT built):**
- API-key-driven adapters (defeats whole value prop)
- Hosted SaaS
- Per-token streaming during a turn (subprocess.run is blocking by design)
- Persistent agent memory across runs (transcript IS the memory)
- Inter-agent direct messaging (transcript-as-channel is a feature, not a bug)

### Architecture Approach

Small Python package, src layout. The user's proposed module split is mostly correct with three corrections.

**Major components:**
1. **`cli.py`** — click entry point; parses args, loads config, calls orchestrator. ~80 lines.
2. **`config.py`** — Pydantic schemas (`AgentConfig`, `RoundtableConfig`); YAML loader. **Folds in `Agent` data — drop the proposed separate `agent.py`** (it's just data, not behavior).
3. **`transcript.py`** — markdown read/write with append-as-you-go. JSONL sidecar deferred to v2.
4. **`stop_conditions.py`** — Strategy pattern; `StopCondition.check(transcript) -> bool`. Bundled: `Keyword`, `MaxTurns`. `AnyOf` composite for short-circuit "any match wins."
5. **`adapters/base.py`** — `Adapter` as `typing.Protocol` (NOT `abc.ABC`); third parties don't inherit. Internal `_SubprocessAdapterMixin` (regular class) absorbs duplication.
6. **`adapters/{claude,gemini,codex}.py`** — concrete adapters, each ~30 lines. Subprocess invocation via stdin pipe (NOT argv `-p`).
7. **`orchestrator.py`** — single **function** (not class for v1). Loops turns, writes transcript, checks stop conditions. Promote to class only when v3 adds parallel speakers.
8. **`presets/debate.yaml`** — bundled preset for `--preset debate`.

**Data flow:** CLI parses args → Config loader reads YAML → Orchestrator loop → Adapter invoke per turn (stdin-piped prompt) → Transcript append → StopCondition check → repeat or exit.

**Architecture corrections to PROJECT.md's proposed split:**
- ❌ Drop `agent.py` → fold `AgentConfig` into `config.py`
- ❌ `BaseAdapter` ABC → ✅ `Adapter` `typing.Protocol`
- ❌ Orchestrator class → ✅ Orchestrator function

See `.planning/research/ARCHITECTURE.md` for full diagrams and code examples.

### Critical Pitfalls

Five non-negotiable risks. Full set of 21 pitfalls in `.planning/research/PITFALLS.md`.

1. **Codex `exec` empty-stdout bug ([openai/codex#19945](https://github.com/openai/codex/issues/19945))** — `codex exec` 0.124.0+ exits with code 0 and zero output when stdio is detached from a TTY. This is exactly what `subprocess.run` produces. *Mitigation:* `_SubprocessAdapterMixin.invoke()` raises `AdapterError` on `returncode == 0 AND stdout.strip() == ""`. Defends against this AND any future similar regression in any CLI.

2. **Argument-length death on Windows (~8 KB cmd.exe limit)** — verified bug in Anthropic's own `claude-agent-sdk-python` ([#501](https://github.com/anthropics/claude-agent-sdk-python/issues/501)). By debate turn 3, the accumulated transcript exceeds the limit. *Mitigation:* `Adapter` Protocol commits to stdin-piped prompts (`subprocess.run(..., input=prompt)`) as the sole delivery path. Decide this BEFORE writing any concrete adapter — retrofitting is a full rewrite.

3. **Windows encoding triple-trap** — Python default codepage (cp1252) × OEM stderr (cp850/cp437) × UTF-8 LLM output. LLM output regularly includes em-dashes, smart quotes, emoji — valid UTF-8, often invalid in cp1252. Verified via CPython issue #105312. *Mitigation:* `encoding="utf-8", errors="replace"` is mandatory on every `subprocess.run`. Add a CI lint test that fails the build on any subprocess call missing these args. Windows CI from day one is non-negotiable.

4. **Stop-condition false positives (sycophancy / degenerate consensus)** — published research phenomenon ([CONSENSAGENT 2025](https://aclanthology.org/2025.findings-acl.1141/)). Naive `"AGREED" in output` matches "I am NOT going to say AGREED yet." *Mitigation:* anchored multiline regex (`^## Decision\nAGREED\s*$`) AND require the marker in the last N turns from M distinct agents. Both safeguards are v1.

5. **PyPI name squatting risk** — `ultra-claude` verified available 2026-05-02. *Mitigation:* upload a 0.0.1 stub on day 1 (Phase 1 first task), before the GitHub repo is publicized or the name appears in any post. Also reserve `ultraclaude` to prevent typosquatting.

## Implications for Roadmap

Based on research, suggested phase structure (fine granularity, ~9 phases):

### Phase 1: Project skeleton & PyPI name reservation
**Rationale:** Reserving the name on day 1 prevents squatting; minimal pyproject.toml + LICENSE + README stub unblock everything else.
**Delivers:** `pyproject.toml` (hatchling, click/pydantic/pyyaml), MIT LICENSE, `.gitignore`, `src/ultra_claude/__init__.py` with `__version__ = "0.0.1"`, README skeleton, **0.0.1 stub uploaded to PyPI manually**.
**Addresses:** Distribution table stakes from FEATURES.md.
**Avoids:** PyPI name squatting (Pitfall #5).

### Phase 2: Config schema + YAML loader
**Rationale:** Config is the input boundary — every later phase consumes a `RoundtableConfig`. Build it first, test it independently.
**Delivers:** `config.py` with `AgentConfig`, `RoundtableConfig`, YAML loader. Pydantic validation errors with line numbers. Tests against good and bad YAML.
**Uses:** pydantic v2, pyyaml.
**Implements:** Component 2 from ARCHITECTURE.md.

### Phase 3: Transcript module with append-as-you-go writes
**Rationale:** Transcript is the shared state every adapter and stop condition reads/writes — must exist before either can be tested.
**Delivers:** `transcript.py` with `Transcript` class supporting append, full read, and `render_prompt()` for the next turn. Markdown format. Cross-platform `newline="\n"` writes.
**Avoids:** Pitfall #3 (encoding) for the file-write side.

### Phase 4: Adapter Protocol + ClaudeAdapter
**Rationale:** First contact with subprocess. Get the contract right before writing two more adapters that would have to be rewritten.
**Delivers:** `adapters/base.py` with `Adapter` Protocol + `_SubprocessAdapterMixin`. `adapters/claude.py` with `ClaudeAdapter`. Stdin-piped prompt. Empty-stdout = error. UTF-8 + errors="replace". Mandatory timeout. Cross-platform process-tree kill on timeout.
**Addresses:** Pitfalls #1, #2, #3 — all foundational; must land in this phase.
**Research flag:** Verify `claude -p` exact argv shape and stdin-acceptance empirically at implementation time.

### Phase 5: Stop conditions (Keyword + MaxTurns + AnyOf)
**Rationale:** Orchestrator needs them to terminate; small enough to land alongside orchestrator if needed.
**Delivers:** `stop_conditions.py` with `Keyword` (anchored regex + unanimity-window), `MaxTurns`, `AnyOf` composite.
**Avoids:** Pitfall #4 (sycophancy false positives).

### Phase 6: Orchestrator loop
**Rationale:** Brings adapters + transcript + stop conditions together. End-to-end test path.
**Delivers:** `orchestrator.py` with `run(config, task) -> Path`. Round-robin. Continue-on-error with `abort_on_error: bool` knob. Stdlib logging to stderr. Mocked-subprocess E2E test using fake-CLI fixture.

### Phase 7: GeminiAdapter + CodexAdapter
**Rationale:** Once the contract is proven, additional adapters are nearly free.
**Delivers:** `adapters/gemini.py`, `adapters/codex.py`. Both reuse `_SubprocessAdapterMixin`. Codex's empty-stdout defense is automatic from the mixin.
**Addresses:** Pitfall #1 specifically validated against Codex bug.

### Phase 8: CLI + first preset (debate.yaml)
**Rationale:** First user-runnable build. Demo path complete.
**Delivers:** `cli.py` with `ultra-claude run <task>`, `--config`, `--preset debate`, `--inline`, `--dry-run`, `--output`, `--help`, `--version`. `presets/debate.yaml` (architect + critic + implementer). Pre-flight auth check.
**Implements:** Component 1 from ARCHITECTURE.md + onboarding differentiators.

### Phase 9: Tests, README, manual v0.1.0 release
**Rationale:** Wraps everything for the public release. Windows CI must pass.
**Delivers:** Full test suite (unit + E2E), Windows-row CI matrix on GitHub Actions, README quickstart with GIF placeholder, CONTRIBUTING.md ("no third-party adapters in core in v1"), `examples/` directory with one real transcript, manual `python -m build` + `twine upload` of `v0.1.0`.

### Phase Ordering Rationale

- **Skeleton first** so name + structure exist before any code; reduces refactor risk.
- **Config → Transcript → Adapter** is strict DAG: each consumes the prior. No cycles.
- **Stop conditions before orchestrator** because orchestrator imports them; tiny phase but cleanly separated for testing.
- **First adapter alone before the others** because the Protocol contract gets refined against real subprocess behavior — better to refine once than three times.
- **Cross-platform polish woven into each phase** rather than late: encoding rules go into Phase 4 (adapter mixin), transcript newlines into Phase 3.
- **Tests + release LAST** so the visible artifact (v0.1.0) lands at the moment everything works end-to-end.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (Adapter Protocol + ClaudeAdapter):** verify `claude -p` exact current argv shape and stdin acceptance empirically. The CLI may have shifted since PROJECT.md was written.
- **Phase 7 (Gemini + Codex adapters):** verify each CLI's exact non-interactive flags (Gemini's [#19774](https://github.com/google-gemini/gemini-cli/issues/19774), Codex's `--quiet` etc.).
- **Phase 9 (release):** verify PyPI Trusted Publishing setup if pulled forward from v2; verify Windows GH Actions runner config for subprocess tests.

Phases with standard patterns (skip phase-research):
- **Phase 1 (skeleton):** standard hatchling pyproject.
- **Phase 2 (config):** standard Pydantic+YAML pattern.
- **Phase 3 (transcript):** simple file IO.
- **Phase 5 (stop conditions):** Strategy pattern.
- **Phase 6 (orchestrator):** simple loop.
- **Phase 8 (CLI):** standard click patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified via PyPI 2026-05-02; PyPI name availability verified directly |
| Features | HIGH (table stakes), MEDIUM (v2 reach) | Table stakes verified against AutoGen/CrewAI/CAO/dmux; v2 list extrapolated from adjacent-domain patterns |
| Architecture | HIGH | PEP 544 (Protocol), Hatchling docs, Click docs, Pydantic v2 docs all converge; orchestrator-as-function is YAGNI applied |
| Pitfalls | HIGH | Live GitHub issues with reproducer details; CPython issue tracker; published sycophancy research |

**Overall confidence:** HIGH

### Gaps to Address

- **Exact CLI argv reality:** `claude -p`, `gemini -p`, `codex exec` documented shapes may have drifted. Validate empirically at Phase 4 + Phase 7 implementation time.
- **Auth state file paths:** referenced as `~/.claude/auth.json` etc. but unverified per platform. Confirm during pre-flight auth check implementation in Phase 8.
- **Long-run transcript truncation strategy:** at >50 turns, prompt size exceeds individual CLI context windows. v1 simply doesn't support that. v2 needs sliding-window or summarization — defer the strategy choice.
- **Windows process-tree kill via `taskkill /T`:** needs an integration test before claiming it works in different process groups.
- **Anthropic trademark on "claude" in package name:** ship with disclaimer; reach out to dev-rel proactively if traction grows. Backup names: `ultraclaude`, `ultraclaude-cli`.

## Sources

### Primary (HIGH confidence)
- PEP 544 — Protocols: structural subtyping
- Pydantic v2 official docs (Context7-verified): models, YAML examples
- Click 8.3 official docs (Pallets)
- Hatchling / Hatch (PyPA)
- Python Packaging User Guide — entry points, plugins
- CPython issue tracker — #105312 (subprocess Windows encoding), #6135, #25942 (SIGKILL behavior)
- PyPI direct API check — `ultra-claude` 404 verified 2026-05-02

### Secondary (MEDIUM-HIGH confidence)
- [openai/codex#19945](https://github.com/openai/codex/issues/19945) — Codex `exec` TTY bug (live)
- [anthropics/claude-agent-sdk-python#501](https://github.com/anthropics/claude-agent-sdk-python/issues/501) — argv length on Windows
- [google-gemini/gemini-cli#19774](https://github.com/google-gemini/gemini-cli/issues/19774) — Gemini non-interactive
- [SuperClaude_Framework#492](https://github.com/SuperClaude-Org/SuperClaude_Framework/issues/492) — Windows UnicodeDecodeError
- AWS Labs `cli-agent-orchestrator` (CAO) — closest competitor analysis
- AutoGen, CrewAI, dmux — speaker-selection pattern verification
- pytest-subprocess docs and Simon Willison TIL

### Tertiary (lower confidence, used as guidance)
- Industry maintainer survey (Linux Foundation), Star History playbook
- arxiv 2509.23055, 2502.19559 — multi-agent debate sycophancy / drift
- CONSENSAGENT (ACL 2025 findings)

---
*Research completed: 2026-05-02*
*Ready for roadmap: yes*
