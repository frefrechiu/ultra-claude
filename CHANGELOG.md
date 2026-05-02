# Changelog

All notable changes to ultra-claude are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-02

First functional release. The `0.0.1` literal in the previous heading was a never-uploaded name-reservation stub -- this `0.1.0` is the first version actually published to PyPI as a working package.

### Added

- **CLI surface** (`ultra-claude run` / `doctor` / `--version` / `--help`).
  - `run TASK_FILE` reads a task from a file and drives a multi-agent debate (CLI-03).
  - `run --inline "<task>"` accepts the task as a string (CLI-06).
  - `run --config <path>` overrides the default `./ultra-claude.yaml` (CLI-04).
  - `run --preset debate` loads the bundled 3-agent preset without a local YAML (CLI-05).
  - `run --dry-run` validates config and prints the planned turn order without invoking any adapter (CLI-07).
  - `run --output <path>` overrides the transcript output path (CLI-08).
  - `run --abort-on-error` halts on the first adapter failure instead of the default continue-on-error mode.
  - `doctor` probes `claude` / `gemini` / `codex` on PATH and prints a per-CLI status table (CLI-09).
  - Exit codes follow Unix convention: 0 on success, 1 on adapter/runtime error, 2 on config validation error (CLI-10).
  - Live progress to stderr only when stdout AND stderr are TTYs; suppressed when piped or redirected (CLI-11).
- **Config schema** (`ultra-claude.yaml`).
  - Pydantic v2 `RoundtableConfig` and `AgentConfig` with strict validation (CFG-01, CFG-02).
  - Required agent fields: `name`, `role`, `adapter` (Literal `claude`/`gemini`/`codex`), `system_prompt` (CFG-02).
  - Defaults: `max_turns=12`, `stop_keywords=["AGREED", "DONE"]`, `turn_order="round_robin"` (CFG-04, CFG-05).
  - Validation errors print one line per offending field path (e.g. `agents[0].adapter: invalid value 'clade'`); no Python tracebacks reach the user (CFG-03).
- **Transcript module**.
  - Append-as-you-go markdown writer with `<!-- turn:N agent:Name -->` HTML-comment sentinels so re-prompting does not collide with content (TRX-01, TRX-02).
  - JSONL sidecar at `<transcript>.jsonl`, one record per turn, fields `turn`/`agent`/`role`/`prompt_hash`/`output` (TRX-03).
  - LF-only newlines and UTF-8 encoding on every platform (TRX-04, TRX-05).
- **Adapter Protocol and three concrete adapters**.
  - `Adapter` `typing.Protocol` (structural subtyping; third parties do not inherit) (ADP-01).
  - `_SubprocessAdapterMixin` enforces the safe-subprocess contract: stdin-piped prompts (Pitfall #1 / Windows ~8 KB cmd.exe argv limit), `text=True` + `encoding="utf-8"` + `errors="replace"` (Pitfall #3 / cp1252 crash), mandatory timeout, list-form argv, `shell=False` (ADP-02).
  - Empty-stdout defense raises `AdapterError` when `returncode == 0` and `stdout.strip() == ""` -- catches the live `codex exec` 0.124.0+ TTY bug ([openai/codex#19945](https://github.com/openai/codex/issues/19945)) (ADP-03 / Pitfall #2).
  - Cross-platform process-tree kill on `TimeoutExpired`: POSIX `os.killpg` after `start_new_session=True`; Windows `taskkill /T /F /PID` after `CREATE_NEW_PROCESS_GROUP` (ADP-04 / Pitfall #5).
  - `AdapterAuthError` (subclass of `AdapterError`) on `FileNotFoundError` or auth-marker substring match in stdout/stderr (ADP-08).
  - `ClaudeAdapter` (`claude -p`), `GeminiAdapter` (`gemini -p`), `CodexAdapter` (`codex exec`), all sharing the mixin (ADP-05, ADP-06, ADP-07).
- **Stop conditions**.
  - `Keyword` with anchored multiline regex (`^<keyword>\s*$`) and unanimity-window default `n=2`/`m=2` so a single agent saying the marker cannot stop the run (STP-02, STP-03 / Pitfall #4).
  - `MaxTurns` (STP-04) and `AnyOf` composite with short-circuit semantics (STP-05).
- **Orchestrator loop** (`run(config, task) -> Path`).
  - Round-robin agent iteration (ORC-01, ORC-02).
  - Per-turn prompt assembly: task header + agent system prompt + transcript-so-far + GOAL ANCHOR re-injection of the task + agent-name reminder (ORC-03 / Pitfall #6).
  - Continue-on-error by default (placeholder turn `[adapter error: <exc>]` appended); `abort_on_error: true` re-raises (ORC-05).
  - Structured stderr logging via `logging.getLogger("ultra_claude.orchestrator")`; stdout reserved for the CLI to print the transcript path (ORC-06).
- **Bundled preset**: `presets/debate.yaml` -- 3-agent roundtable (Architect: claude, Critic: gemini, Implementer: codex) with `max_turns=9` and `stop_keywords=["AGREED", "SHIP IT"]` (PRE-01).
- **PEP 561 type information** via the `py.typed` marker -- downstream typed users see `ultra_claude` as fully type-checked.
- **Documentation**: full `README.md` (1-line pitch, GIF placeholder, 3-command quickstart, "why this exists", config example, "extending to new CLIs") and `CONTRIBUTING.md` (dev setup, how to add an adapter, v1 policy) (DOC-01, DOC-02).
- **Examples directory** (`examples/`): synthetic 3-turn transcript captured from the FakeAdapter test infrastructure plus the YAML config that produced it (PRE-02).
- **Test suite** runs in a clean virtualenv with NONE of `claude`/`gemini`/`codex` installed: adapter tests use `pytest-subprocess`'s `fp` fixture; orchestrator E2E tests use `tests/fixtures/echo_cli.py` as a fake CLI; `pytest-cov` reports coverage on `src/ultra_claude/` (TST-01..04).
- **CI lint tripwire** (`tests/test_subprocess_lint.py`): AST-walks `src/ultra_claude/` and fails the build if any `subprocess.run` / `subprocess.Popen` call is missing the safe-contract kwargs or sets `shell=True` (TST-05; landed in Phase 4).

### Changed

- Replaced the stub `README.md` (Phase 1 name-reservation placeholder) with the full v0.1.0 README.

### Notes

- The `0.0.1` PyPI stub release referenced by Phase 1's PKG-05 was never uploaded by the user. This `0.1.0` release supersedes it: a fresh PyPI account upload of `0.1.0` claims the `ultra-claude` distribution name AND ships the functional package in a single step. `python -m build` produces `dist/ultra_claude-0.1.0-py3-none-any.whl` and `dist/ultra_claude-0.1.0.tar.gz`; `twine upload dist/ultra_claude-0.1.0*` (user action) closes PKG-06.
- This release is manual: `python -m build` + `twine upload`. Trusted Publishing (PyPI OIDC) is deferred to v2.

## [0.0.1] - 2026-05-02

### Added
- PyPI name reservation stub. No functional code; the `0.0.1` release exists only to claim the `ultra-claude` distribution name on PyPI before any public mention (per `.planning/research/PITFALLS.md` Pitfall 14).
- Initial repository scaffolding: `LICENSE` (MIT), `.gitignore`, `README.md` stub, `pyproject.toml` (hatchling build backend), `src/ultra_claude/__init__.py` exposing `__version__`.
