# Phase 2: Config Schema & YAML Loader - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

Make `ultra-claude.yaml` a fully-validated input boundary. Every later phase consumes a `RoundtableConfig` instance with confidence — invalid configs are rejected at load time with helpful, field-pointing errors.

Scope:
- `src/ultra_claude/config.py` — Pydantic v2 models: `AgentConfig`, `RoundtableConfig`, plus a `load_config(path: Path) -> RoundtableConfig` function
- YAML parsing via `yaml.safe_load` (never `yaml.load`)
- Pydantic v2 `ValidationError` translated into a single human-readable error message that names the field path (e.g. `agents[0].adapter: invalid value 'clade'`)
- `tests/test_config.py` covering: happy path, missing required fields per agent, invalid `adapter` Literal, invalid `turn_order`, default values for `max_turns` and `stop_keywords`, malformed YAML (syntax errors)

Out of scope: actual orchestrator (Phase 6), adapter implementations (Phase 4 / 7), CLI parsing (Phase 8).

</domain>

<decisions>
## Implementation Decisions

### Locked from REQUIREMENTS.md / CLAUDE.md

- **Pydantic version:** v2 (>= 2.13.3). Use `pydantic.BaseModel` with `model_config = ConfigDict(extra="forbid")` to reject unknown fields — surfacing typos at validation time.
- **YAML loader:** `yaml.safe_load` ONLY. Never `yaml.load`. PyYAML >= 6.0.3.
- **`AgentConfig` required fields:** `name: str`, `role: str`, `adapter: Literal["claude", "gemini", "codex"]`, `system_prompt: str`. Use `pydantic.Field` with min_length=1 on string fields to reject empty values.
- **`RoundtableConfig` fields:**
  - `agents: list[AgentConfig]` — required, min_length=2 (a "roundtable" needs >=2 voices)
  - `task: str | None = None` — optional (CLI `--inline` or task-file overrides this)
  - `max_turns: int = 12` — default 12; validation: must be >= 2
  - `stop_keywords: list[str] = ["AGREED", "DONE"]` — default; min_length=1 if provided
  - `transcript_path: Path | None = None` — optional; default behavior decided in Phase 6
  - `turn_order: Literal["round_robin"] = "round_robin"` — only round_robin in v1
  - `abort_on_error: bool = False` — used by orchestrator (ORC-05)
- **Error formatter:** A `format_validation_error(err: pydantic.ValidationError, source_path: Path | None) -> str` helper that produces a single-line-per-error message:
  ```
  ultra-claude.yaml validation error:
    agents[0].adapter: invalid value 'clade' (expected 'claude', 'gemini', or 'codex')
    max_turns: must be >= 2 (got 1)
  ```
  No raw Python tracebacks reach the user. Catch `ValidationError` in `load_config`, format, raise `ConfigError`.
- **`ConfigError` exception class:** A new `class ConfigError(Exception)` in `src/ultra_claude/exceptions.py` (creates the file if it doesn't exist — used by later phases for `AdapterError`, etc.). Use this for all config-validation failures so the CLI can map it to exit code 2 (CLI-10).
- **YAML syntax errors:** `yaml.YAMLError` from `safe_load` is caught and re-raised as `ConfigError` with the file path and line number from the YAML error.
- **File not found:** If config path doesn't exist, raise `ConfigError("Config file not found: {path}")`. Don't silently fall back.
- **`load_config` signature:** `def load_config(path: Path | str) -> RoundtableConfig`. Accepts both Path and str for ergonomics. Reads with `encoding="utf-8"`.

### Module structure

```
src/ultra_claude/
├── __init__.py              # already exists (Phase 1)
├── config.py                # NEW — AgentConfig, RoundtableConfig, load_config
└── exceptions.py            # NEW — ConfigError (and forward-declared AdapterError + AdapterAuthError + AdapterError ancestor base class for Phase 4 to extend)
```

`exceptions.py` will be small and grow in Phase 4. Phase 2 only adds `ConfigError`.

### Testing strategy

- **Tests location:** `tests/` directory at repo root (not in `src/`)
- **Test framework:** pytest (already pinned in dev deps)
- **Coverage:** test_config.py for Phase 2; aim for the 6 cases listed above
- **Fixtures:** small inline YAML strings (no separate test data files needed for Phase 2)
- **No real CLIs:** this phase does not interact with subprocess at all; pure parsing/validation tests

### Claude's Discretion

- Exact wording of error messages (must be human-readable, name the field path; phrasing is flexible)
- Whether to add a `model_validator` for cross-field rules (e.g. `max_turns >= len(agents)`) — recommend: no, keep validation per-field for v1
- Whether to expose a `RoundtableConfig.from_yaml_string(s: str)` classmethod — recommend: yes, useful for tests + CLI `--inline`
- Whether to add `__all__` in `config.py` — recommend: yes, list the public symbols (`AgentConfig`, `RoundtableConfig`, `load_config`, `ConfigError`)

</decisions>

<code_context>
## Existing Code Insights

After Phase 1:
- `src/ultra_claude/__init__.py` exists with `__version__ = "0.0.1"`
- `pyproject.toml` declares pydantic >= 2.13.3 and pyyaml >= 6.0.3 as runtime deps
- `pyproject.toml` declares pytest >= 8.4 as dev dep
- No `tests/` directory yet — Phase 2 creates it
- No `src/ultra_claude/config.py` yet
- No `src/ultra_claude/exceptions.py` yet

The package is buildable and installable via `pip install -e ".[dev]"` after Phase 1.

</code_context>

<specifics>
## Specific Ideas

- **Example valid config** (for tests + later docs):

```yaml
agents:
  - name: Architect
    role: high-level design
    adapter: claude
    system_prompt: "You design system architecture. Prioritize simplicity and explicit data flow."
  - name: Critic
    role: skeptic
    adapter: gemini
    system_prompt: "You poke holes in proposed designs. Reference past production failures."
  - name: Implementer
    role: hands-on coder
    adapter: codex
    system_prompt: "You write the actual code. Flag any unbuildable parts of the proposed design."
max_turns: 9
stop_keywords:
  - AGREED
  - SHIP IT
```

- **Pitfall #4 from research/PITFALLS.md applies later (Phase 5 stop conditions):** the regex/unanimity logic lives in stop conditions, not in config validation. Phase 2 only stores `stop_keywords` as a list of strings.

</specifics>

<deferred>
## Deferred Ideas

- Cross-field validators (e.g. `max_turns >= len(agents)`)
- Per-agent `max_turn_words` or rate-limiting config — not in v1
- Custom YAML tags / anchors — `safe_load` rejects custom constructors, which is the safe default
- Schema export (e.g. `ultra-claude config-schema` CLI command) — could be added in Phase 8 but not required for v1

</deferred>

---

*Phase: 02-config-schema-yaml-loader*
*Context auto-generated 2026-05-02 (autonomous mode)*
