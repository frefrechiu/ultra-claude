# Phase 8: CLI Surface & `debate` Preset - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

Ship the user-runnable `ultra-claude` binary with the full v1 flag surface (`run`, `doctor`, `--version`, `--help`) plus a bundled `debate` preset so the README quickstart works in a clean directory.

Scope:
- `src/ultra_claude/cli.py` — click-based command group with `run` and `doctor` subcommands
- `src/ultra_claude/presets/debate.yaml` — bundled preset config (architect/critic/implementer trio)
- `src/ultra_claude/__init__.py` — also expose `from ultra_claude.cli import main` for `python -m ultra_claude`
- `pyproject.toml` — add `[project.scripts] ultra-claude = "ultra_claude.cli:main"` entry point and `[tool.hatch.build] include = ["src/ultra_claude/presets/*.yaml"]` so the YAML ships in the wheel
- `tests/test_cli.py` — CLI tests using click's `CliRunner` (no real CLIs required)

Out of scope: real `pip install` smoke (Phase 9), README/docs (Phase 9), v0.1.0 release (Phase 9).

</domain>

<decisions>
## Implementation Decisions

### Locked from REQUIREMENTS.md (CLI-01..CLI-11, PRE-01) and CLAUDE.md

- **CLI framework:** click (already pinned to >= 8.3.3 in pyproject.toml)
- **Entry point:** `ultra-claude = "ultra_claude.cli:main"` — `main` is the click group function
- **Subcommands:** `run` and `doctor`
- **Group-level options:** `--version` (uses click's built-in version_option reading `__version__` from `ultra_claude`)

#### `run` command flags (CLI-03..CLI-08)
```
ultra-claude run [TASK_FILE]
  --config PATH         override default ./ultra-claude.yaml
  --preset NAME         load bundled preset (e.g. "debate")
  --inline TEXT         provide task as string instead of file
  --dry-run             validate config + print planned turn order, no adapter calls
  --output PATH         override transcript output path
  --abort-on-error      abort on first adapter error (overrides config)
```

Argument ordering rules:
- TASK_FILE positional is optional (default lookup: `./task.md` if neither it nor `--inline` is provided — actually require ONE of: TASK_FILE, --inline, or --dry-run; otherwise error)
- `--config` and `--preset` are mutually exclusive (click's mutually_exclusive_options or manual validation)

#### `doctor` command (CLI-09)
- Checks `claude`, `gemini`, `codex` on PATH (uses `shutil.which`)
- Probes login state for each by attempting to invoke with a tiny prompt and capturing stdout/stderr
- Prints a status table: `CLI | On PATH | Auth | Notes`
- Exit code 0 even if some CLIs fail — doctor reports state, doesn't fail the run

#### Exit codes (CLI-10)
- 0: success
- 1: runtime/adapter error (raised AdapterError or AdapterAuthError out of run())
- 2: config validation error (ConfigError)

Implementation: catch ConfigError → exit 2; catch AdapterError → exit 1; success → exit 0. Click's default behavior for unhandled exceptions is exit 1, which we override.

#### TTY-aware progress (CLI-11)
- "live progress" hooks: turn N starting / completed messages stay in `ultra_claude.orchestrator` logger (already done in Phase 6)
- The CLI sets up the logger to emit to stderr ONLY when `sys.stdout.isatty()` AND when stderr is a tty too — when piped/redirected, suppress the progress
- Implementation: `if sys.stdout.isatty(): logging.getLogger("ultra_claude.orchestrator").setLevel(logging.INFO); else: logging.WARNING`

#### Preset loading (PRE-01)
- `--preset debate` → load `src/ultra_claude/presets/debate.yaml` from package data
- Use `importlib.resources` to locate the file (works in both editable installs and packaged wheels)
- Phase 9 will add hatchling include rule to ship the YAML files; Phase 8 must update `pyproject.toml` for that too:
  ```toml
  [tool.hatch.build.targets.wheel]
  packages = ["src/ultra_claude"]
  
  [tool.hatch.build.targets.wheel.shared-data]
  # No shared-data needed — presets/ is inside the package
  ```
  Just confirm presets/*.yaml is in the package source tree under `src/ultra_claude/presets/`. Hatchling auto-includes everything under packages by default.

#### `presets/debate.yaml` content
```yaml
agents:
  - name: Architect
    role: high-level design
    adapter: claude
    system_prompt: |
      You design system architecture. Prioritize simplicity, explicit data flow, 
      and minimal dependencies. Push back on over-engineering. Lead with constraints.

  - name: Critic
    role: skeptic
    adapter: gemini
    system_prompt: |
      You poke holes in proposed designs. Reference past production failures.
      Challenge assumptions. Ask "what happens when X fails?" Be ruthless but constructive.

  - name: Implementer
    role: hands-on coder
    adapter: codex
    system_prompt: |
      You write the actual code. Flag any unbuildable parts of the proposed design.
      Estimate effort. Push back on vague requirements with specific clarifying questions.

max_turns: 9
stop_keywords:
  - AGREED
  - SHIP IT
```

### Module structure (after this phase)

```
src/ultra_claude/
├── __init__.py
├── cli.py                # NEW
├── config.py
├── exceptions.py
├── orchestrator.py
├── registry.py
├── stop_conditions.py
├── transcript.py
├── adapters/...
└── presets/
    └── debate.yaml       # NEW
```

### Testing strategy

`tests/test_cli.py`:
1. `test_version_flag` — `ultra-claude --version` prints version, exit 0
2. `test_help_flag` — `--help` prints help with subcommands `run` and `doctor`, exit 0
3. `test_run_with_inline_task` — `ultra-claude run --inline "test" --dry-run` validates config and exits 0
4. `test_run_with_preset` — `ultra-claude run --preset debate --inline "test" --dry-run` works without local YAML
5. `test_run_with_config_path` — `ultra-claude run --config <tmp_yaml> --inline "test" --dry-run` works
6. `test_run_dry_run_outputs_turn_order` — dry-run mode prints planned turn order to stdout
7. `test_doctor_command` — doctor probes all 3 CLIs and prints status table; exit 0 (even if all fail)
8. `test_config_error_exits_2` — invalid YAML → exit code 2
9. `test_adapter_error_exits_1` — fake adapter raises AdapterError + abort_on_error=True → exit 1
10. `test_run_with_real_orchestrator_via_adapter_factory` — uses fake adapters injected via test fixture; full pipeline works end-to-end producing a transcript
11. `test_stdout_only_contains_transcript_path_on_success` — pipe stdout, assert it contains only the path (no progress noise)

Use `click.testing.CliRunner` for invocation. Mock adapters via `adapter_factory` parameter exposed in the orchestrator (Phase 6).

### Claude's Discretion

- Whether the doctor command runs full one-token probes or just `--version` style probes — recommend: `--version` style (or analogous health-check) — fast and cheap
- Whether to add a `--verbose` flag for DEBUG logging — recommend: yes, simple to add
- Help text wording — Claude's discretion
- Whether to colorize output — recommend: NO for v1 (keep stdout clean for piping)

</decisions>

<code_context>
## Existing Code Insights

After Phases 1-7:
- `run(config, task) -> Path` exists with `adapter_factory` injection seam
- `load_config` raises `ConfigError`; orchestrator raises `AdapterError`
- Logger `ultra_claude.orchestrator` is set up by Phase 6
- `pyproject.toml` does NOT yet have `[project.scripts]` (Phase 1's stub release intentionally omitted it; Phase 8 adds it)
- 72/72 tests pass

After Phase 8 the package will be a real CLI tool installable via `pip install -e ".[dev]"` and runnable as `ultra-claude --help`.

</code_context>

<specifics>
## Specific Ideas

- The preset file SHIPS in the wheel — Phase 9's smoke test (`pip install ultra_claude-0.1.0-py3-none-any.whl` + `ultra-claude run --preset debate --dry-run`) MUST work without a separate file download.
- `pyproject.toml` change in this phase: add `[project.scripts] ultra-claude = "ultra_claude.cli:main"` and verify hatchling builds a wheel that includes the entry point AND the presets/ directory.

</specifics>

<deferred>
## Deferred Ideas

- `ultra-claude config-schema` to print the JSON schema — could be useful for IDE integration but not blocking v0.1.0
- `ultra-claude history` to list transcripts in cwd — out of v1 scope
- Shell completion (click supports it) — out of v1 scope
- Plugin system for third-party adapters via entry points — v2

</deferred>

---

*Phase: 08-cli-surface-debate-preset*
*Context auto-generated 2026-05-02 (autonomous mode)*
