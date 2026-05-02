# ultra-claude

## What This Is

A Python CLI that orchestrates conversations between Claude Code, Gemini CLI, and Codex CLI by spawning them as subprocesses. The transcript becomes each next turn's prompt, so the agents "talk to each other" without knowing the others exist — they just see a growing conversation file. No API keys required; users ride their existing CLI logins.

Built for developers who already pay for Claude/Gemini/ChatGPT subscriptions and want multi-agent debate without doubling their spend on API tokens.

## Core Value

**A user can run `ultra-claude run task.md` and get three CLI agents debating their problem in a transcript file — using only their existing CLI logins, no API keys.**

If everything else fails, this single command must work end-to-end with a real transcript at the end.

## Current State

**Shipped: v0.1.0 (2026-05-02).** All 58 v1 requirements complete (autonomous-completable parts). 86/86 tests pass in clean venv with NONE of claude/gemini/codex installed; 85% line coverage on `src/ultra_claude/`. Distribution artifacts (`dist/ultra_claude-0.1.0.tar.gz` + wheel) built and twine-checked. Pending user action: `python -m twine upload dist/ultra_claude-0.1.0*` per `.planning/milestones/v0.1.0-phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md`.

## Requirements

### Validated (v0.1.0 — 2026-05-02)

- ✓ Python package `ultra-claude`, CLI binary `ultra-claude` — v0.1.0 (PyPI upload pending user)
- ✓ `Adapter` `typing.Protocol` (NOT `BaseAdapter` ABC — architecture corrected per CLAUDE.md) — v0.1.0
- ✓ `ClaudeAdapter` invoking `claude -p` via stdin — v0.1.0
- ✓ `GeminiAdapter` invoking `gemini -p` via stdin — v0.1.0
- ✓ `CodexAdapter` invoking `codex exec` via stdin (with empty-stdout defense for `openai/codex#19945`) — v0.1.0
- ✓ Pydantic v2 schema (`RoundtableConfig`, `AgentConfig`) loaded from YAML with field-pointing errors — v0.1.0
- ✓ Orchestrator function `run(config, task) -> Path` (NOT a class — corrected per CLAUDE.md) — v0.1.0
- ✓ Stop conditions: `Keyword` (anchored regex + unanimity-window), `MaxTurns`, `AnyOf` — v0.1.0
- ✓ CLI: `ultra-claude run`, `doctor`, `--version`, `--help` with all flags — v0.1.0
- ✓ Bundled preset `presets/debate.yaml` (architect + critic + implementer) — v0.1.0
- ✓ Tests run in clean venv via `pytest-subprocess` — v0.1.0 (86 tests, 85% coverage)
- ✓ README with quickstart + extending guide; CONTRIBUTING; examples/ — v0.1.0
- ✓ MIT LICENSE, `pyproject.toml` (hatchling), `.gitignore` — v0.1.0
- ✓ Build artifacts for v0.1.0 ready for manual `twine upload` — v0.1.0 (autonomous portion)

### Active

(No active requirements — v0.1.0 shipped. Run `/gsd-new-milestone` to start v0.1.1 / v0.2.0 / etc.)

#### v2 candidates (when next milestone is scoped)

#### v2 — Reach (after v1 ships)

- [ ] GitHub Actions: pytest matrix on push/PR
- [ ] GitHub Actions: auto-publish to PyPI on `v*` tag push (Trusted Publishing OIDC)
- [ ] Additional presets: `plan_review.yaml`, `debug.yaml`
- [ ] `speaker_chooses` turn order (agent picks who replies next)
- [ ] Additional stop conditions: `file_exists`, custom regex
- [ ] Real captured-transcript examples (replace synthetic ones from v0.1.0)
- [ ] Full docs site (installation, configuration, adding_new_agents)
- [ ] Promotion: r/LocalLLaMA, r/ClaudeAI, r/ChatGPTCoding, Show HN, X/Twitter
- [ ] Async adapter variant + per-token streaming output
- [ ] Mid-run resume from existing transcript

### Out of Scope

- **API-key-driven agents** — defeats the whole point; users would just use existing API SDKs. The pitch is "no API keys, use your existing CLI logins."
- **Real-time streaming output mid-turn** — adapters block on `subprocess.run` until the CLI finishes a turn. Streaming would force per-CLI special-casing and complicate the simple subprocess model.
- **Persistent agent memory between runs** — the transcript IS the memory. Each run starts fresh from the task file.
- **Hosted/SaaS version** — this is a local CLI tool. Hosting it would require API keys (out of scope) and undercut the value prop.
- **Mobile app / GUI** — terminal-only.
- **Inter-agent direct messaging** — agents communicate only via the shared transcript. The "they don't know the others exist" property is a feature, not a bug.

## Context

- **The gap this fills:** Multi-agent frameworks (LangGraph, CrewAI, AutoGen) all require API keys and burn budget per turn. Slash-command flows (Claude Code subagents, Gemini CLI subagents) are too manual for back-and-forth debate. Nobody has the simple "subprocess these three CLIs and pipe transcripts" tool.
- **Why subprocess-based works:** Claude Code, Gemini CLI, and Codex CLI all support `-p <prompt>` (or `exec <prompt>`) one-shot invocation that returns to stdout. Each call is fully authenticated by the user's existing login session.
- **Author context:** Developer (`frefrechiu` on GitHub) running active projects (x-news, others) with an existing Claude Code workflow. Familiar with `subprocess.run`, Pydantic, and PyPI. First open-source publish.
- **Demo strategy:** Don't show abstract "agents discuss API design." Record a failing test → `ultra-claude run "Fix test_auth.py"` → Claude proposes fix → Gemini finds edge case → Codex writes code → test passes. That's the GIF for the README and Show HN post.

## Constraints

- **Tech stack**: Python ≥ 3.10 — required for `Literal` typing, modern type hints, structural pattern matching if needed.
- **Dependencies**: `pydantic >= 2.0`, `pyyaml >= 6.0`, `click >= 8.0`. Keep dependency surface small for fast install.
- **Build tool**: `hatch` (modern, simpler than poetry for libraries). `pyproject.toml`-driven.
- **Distribution**: PyPI — package name `ultra-claude`, CLI binary `ultra-claude`. Verify name availability before tagging v0.1.0.
- **License**: MIT (most permissive, easiest adoption).
- **Runtime dependencies**: User must have at least one of `claude`, `gemini`, `codex` on PATH and authenticated. The tool reports a clear error if the configured adapter's CLI is missing.
- **No network calls from the package itself** — the package only spawns subprocesses. All network IO happens inside the spawned CLIs.
- **Cross-platform**: Must work on macOS, Linux, Windows. `subprocess.run` with `encoding="utf-8", errors="replace"` to handle non-UTF8 stderr on Windows.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Name: `ultra-claude` (not roundtable/consilium/triadic) | User preference; brand-aligned with Claude-centric workflow | ✓ Validated v0.1.0 |
| CLI binary: `ultra-claude` (not short alias `uc` or `ultra`) | Discoverability over brevity. Short aliases can be added in v2 if requested. | ✓ Validated v0.1.0 |
| v1 = Lean MVP, defer GH Actions + auto-publish to v2 | Ship the core value (agents debating end-to-end) first. CI/CD is leverage on top of a working tool, not a prerequisite. | ✓ Validated v0.1.0 |
| Subprocess-based, not API-key-based | The whole point. Differentiates from every existing multi-agent framework. | ✓ Validated v0.1.0 |
| Round-robin turn order in v1 (not `speaker_chooses`) | Simpler to reason about, deterministic, easier to test. `speaker_chooses` adds dispatch logic complexity. | ✓ Validated v0.1.0 |
| `subprocess.run` (blocking), not async | Each turn is a discrete LLM call. No streaming UI in v1 means no benefit from async. | ✓ Validated v0.1.0 |
| YAML + Pydantic for config | YAML is what users expect for this kind of tool; Pydantic gives free validation with good errors. | ✓ Validated v0.1.0 |
| MIT license | Permissive license maximizes adoption and PR contributions. | ✓ Validated v0.1.0 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-02 after v0.1.0 milestone complete.*
