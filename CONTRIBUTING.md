# Contributing to ultra-claude

Thanks for considering a contribution. ultra-claude is a small focused project; the goal is to keep it small and focused.

## Dev setup

```bash
git clone https://github.com/frefrechiu/ultra-claude.git
cd ultra-claude
python -m venv .venv
source .venv/Scripts/activate     # Windows
# or: source .venv/bin/activate   # POSIX
pip install -e ".[dev]"
pytest
```

You should see all tests pass on the first try. If they don't, that's a bug -- file an issue with `pytest -v` output and your platform.

## Adding an adapter

Per the v1 policy below, ultra-claude's core ships only the three bundled adapters (claude / gemini / codex). Third-party adapters live in their own packages. The structural `Adapter` Protocol (`typing.Protocol`, `runtime_checkable`) means your adapter does NOT need to inherit from anything in this repo to be loadable -- but inheriting from `_SubprocessAdapterMixin` gives you the safe-subprocess contract for free.

Minimal third-party adapter:

```python
# my_ultra_claude_adapter/myadapter.py
from ultra_claude.adapters.base import _SubprocessAdapterMixin

class MyAdapter(_SubprocessAdapterMixin):
    name = "mycli"
    cli_name = "mycli"
    auth_error_markers = ("please run `mycli login`", "not authenticated")

    def invoke(self, prompt: str, timeout: int) -> str:
        return self._run_subprocess(["mycli", "--prompt-stdin"], prompt, timeout)
```

What `_SubprocessAdapterMixin` does for you:

- Pipes the prompt via stdin (defends against the Windows ~8 KB cmd.exe argv limit).
- Sets `text=True`, `encoding="utf-8"`, `errors="replace"` (defends against Windows cp1252 crash on smart quotes / em-dashes / emoji that LLMs emit constantly).
- Enforces a mandatory timeout and does a cross-platform process-tree kill on `TimeoutExpired` (POSIX `os.killpg`, Windows `taskkill /T /F`).
- Raises `AdapterError` when `returncode == 0` AND `stdout.strip() == ""` (catches the live `codex exec` 0.124.0+ TTY bug per [openai/codex#19945](https://github.com/openai/codex/issues/19945)).
- Raises `AdapterAuthError` (subclass of `AdapterError`) on `FileNotFoundError` (CLI not on PATH) or any auth-marker substring match in stdout/stderr.

You MUST set `cli_name` (used in error messages) and `auth_error_markers` (a tuple of lowercase substrings checked case-insensitively against stdout+stderr). You MUST NOT call `subprocess.run` / `subprocess.Popen` directly -- the mixin's `_run_subprocess` is the only sanctioned path. The lint test in `tests/test_subprocess_lint.py` (TST-05) AST-walks `src/ultra_claude/` and fails the build if it sees a bare subprocess call missing the safe-contract kwargs.

## v1 policy: core ships only three adapters

The core ultra-claude package will only ever ship adapters for `claude`, `gemini`, and `codex`. Reasons:

1. Those three are the official LLM CLIs from the three vendors that matter for v1's value proposition (use existing subscriptions, no API keys).
2. Each new bundled adapter is a maintenance burden -- vendor CLIs change, auth flows change, output formats change. The narrower the surface, the longer the package lives without rot.
3. The structural Adapter Protocol means you do NOT need to merge into core to ship an adapter. `pip install ultra-claude my-cool-adapter` and a one-line YAML reference is the eventual v2 plug-in story (deferred to v2 per `.planning/REQUIREMENTS.md`).

If you want a fourth adapter, publish it as `ultra-claude-<vendor>` on PyPI and we will link to it from this README. PRs adding adapters to core will be politely declined.

## PR checklist

Before opening a PR:

- [ ] `pytest` passes (in a clean venv with NONE of `claude`/`gemini`/`codex` actually installed -- the test suite mocks them all)
- [ ] `mypy` passes with zero errors (configured strict for `src/ultra_claude/`)
- [ ] `ruff check` passes with zero errors (project-wide)
- [ ] Tests added for new behaviour (TDD-friendly: write the failing test first)
- [ ] If user-visible (new CLI flag, new config field, new error message), the README's relevant section is updated
- [ ] If a new requirement, add it to `.planning/REQUIREMENTS.md` with a category prefix (PKG / CFG / TRX / ADP / STP / ORC / CLI / PRE / TST / DOC) and a phase mapping
- [ ] Commit messages follow conventional-commits style (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`)

## Filing an issue

Use the GitHub issue tracker: <https://github.com/frefrechiu/ultra-claude/issues>.

When filing a bug, please include:

1. Output of `ultra-claude --version`.
2. Output of `ultra-claude doctor` (so we can see which CLIs are on PATH and authenticated on your machine).
3. Your `ultra-claude.yaml` (with any secrets / system prompts redacted).
4. The first ~30 lines of the failing transcript or adapter error message.
5. Your platform: `python -c "import platform; print(platform.platform())"`.

## Architecture corrections from the original spec

(Deltas from the early `.planning/PROJECT.md` design doc, baked in during Phases 2-8. These are documented for future maintainers reading old notes; you do not need to act on them.)

- `agent.py` was DROPPED. `AgentConfig` lives in `config.py` -- it's just data, no behaviour.
- `BaseAdapter` ABC was DROPPED in favour of `Adapter` `typing.Protocol` -- third parties do not need to subclass to qualify.
- The orchestrator is a function, not a class. Promotion to a class is reserved for a hypothetical v3 with parallel speakers.

## Code of Conduct

Be kind. We are all here to ship a small piece of software that does one thing well. Disagreements are welcome; harassment is not.
