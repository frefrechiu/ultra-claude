# ultra-claude

Python CLI that orchestrates Claude Code, Gemini CLI, and Codex CLI as subprocesses. The transcript file is the only inter-agent channel — agents "talk" by reading what the previous agents wrote, with no API keys involved.

## Core Value

A user can run `ultra-claude run task.md` and get three CLI agents debating their problem in a transcript file — using only their existing CLI logins, no API keys.

## GSD Workflow

This project uses the GSD (Get Shit Done) workflow. Planning artifacts live in `.planning/`.

| File | Purpose |
|------|---------|
| `.planning/PROJECT.md` | Project context, core value, constraints, key decisions |
| `.planning/REQUIREMENTS.md` | 58 v1 requirements (PKG/CFG/TRX/ADP/STP/ORC/CLI/PRE/TST/DOC) mapped to phases |
| `.planning/ROADMAP.md` | 9-phase fine-grained roadmap with success criteria |
| `.planning/STATE.md` | Current position, key decisions locked in by roadmap, open todos |
| `.planning/research/` | Stack/Features/Architecture/Pitfalls/Summary — context for plan time |
| `.planning/config.json` | Workflow settings (yolo, fine, parallel, quality model profile) |

### Commands

- **Plan a phase:** `/gsd-plan-phase <N>` — decomposes a phase into executable plans with verification
- **Discuss a phase first:** `/gsd-discuss-phase <N>` — clarifies approach before planning
- **Execute:** `/gsd-execute-phase <N>` — wave-based parallel execution
- **Progress:** `/gsd-progress` — see where you are
- **Next:** `/gsd-next` — auto-advance to the next logical step

### Active Workflow Settings

- **Mode:** yolo (auto-approve, just execute)
- **Granularity:** fine (9 phases, focused scope each)
- **Parallelization:** enabled (Phase 2‖3, Phase 4‖5, Phase 6‖7 are concurrency-safe)
- **Research before each phase:** yes
- **Plan check:** yes
- **Verifier after each phase:** yes
- **Model profile:** quality (researcher/roadmapper on opus)

## Critical Constraints (from research, must hold across all phases)

1. **Subprocess invocation contract** — every `subprocess.run`/`subprocess.Popen` call MUST set `text=True`, `encoding="utf-8"`, `errors="replace"`, list-form argv, `shell=False`, and a mandatory `timeout`. Prompts MUST be piped via stdin (never via `-p <huge>` argv) — Windows cmd.exe rejects argv > ~8 KB. CI lint test (TST-05, lands in Phase 4) blocks regressions.

2. **Empty-stdout = hard error** — when a subprocess returns `returncode == 0` AND `stdout.strip() == ""`, raise `AdapterError`. This defends against the live `codex exec` 0.124.0+ TTY bug ([openai/codex#19945](https://github.com/openai/codex/issues/19945)) and any future regression of the same shape. Lives in `_SubprocessAdapterMixin` so all three adapters inherit it.

3. **Process-tree kill on timeout** — POSIX `os.killpg` and Windows `taskkill /T /F`. Half-measures leak orphaned children burning subscription quota.

4. **Stop-condition anchored regex + unanimity-window** — naive substring `"AGREED" in output` matches "I am NOT going to say AGREED yet". Use anchored multiline regex (`^## Decision\nAGREED\s*$`) AND require the marker in the last N=2 turns from M=2 distinct agents.

5. **PyPI name reserved before public mention** — `ultra-claude` was verified available 2026-05-02. The first concrete deliverable in Phase 1 is uploading a `0.0.1` stub to PyPI to prevent squatting.

6. **Cross-platform CI from day one** — Windows is in scope. Encoding bugs surface only when ASCII-only test data is used. Test against UTF-8 LLM output (em-dashes, smart quotes, emoji) on Windows runners.

## Architecture corrections to PROJECT.md's original spec

- ❌ Drop `agent.py` → ✅ Fold `AgentConfig` into `config.py` (it's just data)
- ❌ `BaseAdapter` ABC → ✅ `Adapter` `typing.Protocol` (third parties don't subclass)
- ❌ Orchestrator class → ✅ Orchestrator function (promote to class only when v3 adds parallel speakers)

## Tech stack (verified 2026-05-02)

- Python ≥ 3.10 (3.10 EOLs 2026-10-31; bump floor in late 2026)
- `hatchling` build backend (NOT the full `hatch` CLI — plain `pip install -e ".[dev]"` is sufficient)
- `click ≥ 8.3.3`, `pydantic ≥ 2.13.3`, `pyyaml ≥ 6.0.3`
- `ruff ≥ 0.13` (one tool replaces black+isort+flake8+pyupgrade)
- `mypy ≥ 1.18` (configured strict for `src/ultra_claude/`)
- `pytest ≥ 8.4` + `pytest-mock` + `pytest-cov` + `pytest-subprocess`
- v1 release: manual `python -m build` + `twine upload`. Trusted Publishing (OIDC) deferred to v2.

## Out of scope (v1 and v2)

- API-key-driven adapters (defeats the value prop)
- Per-token streaming during a turn (subprocess.run is blocking by design)
- Persistent agent memory across runs (transcript IS the memory)
- Hosted SaaS, mobile/GUI, conversation branching, async runtime

## Next step

Run `/gsd-plan-phase 1` to decompose Phase 1 (Project Skeleton & PyPI Name Reservation) into executable plans.

---
*Generated 2026-05-02 after `/gsd-new-project`. Update via `/gsd-docs-update` after milestone transitions.*
