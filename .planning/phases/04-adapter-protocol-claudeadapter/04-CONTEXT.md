# Phase 4: Adapter Protocol & ClaudeAdapter - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

Lock the subprocess invocation contract once, prove it on the first concrete adapter (`ClaudeAdapter`). Phases 7, 8 reuse the contract.

Scope:
- `src/ultra_claude/adapters/__init__.py` — package marker
- `src/ultra_claude/adapters/base.py` — `Adapter` `typing.Protocol` (runtime_checkable) + `_SubprocessAdapterMixin` + `AdapterError`/`AdapterAuthError` exceptions
- `src/ultra_claude/adapters/claude.py` — `ClaudeAdapter` class using the mixin
- `tests/test_adapters_base.py` — Protocol structural typing tests, mixin contract tests, isinstance check
- `tests/test_adapter_claude.py` — `ClaudeAdapter` tests using `pytest-subprocess` (mocks `claude -p` calls)
- `tests/test_subprocess_lint.py` — CI lint test (TST-05) that scans `src/ultra_claude/` for any `subprocess.run` call missing `text=True`, `encoding="utf-8"`, `errors="replace"`, or `shell=False`. This test MUST FAIL the build if any new code regresses.

Out of scope: Gemini/Codex adapters (Phase 7 — they reuse the mixin), orchestrator (Phase 6), CLI (Phase 8).

</domain>

<decisions>
## Implementation Decisions

### Locked from REQUIREMENTS.md (ADP-01..ADP-05, ADP-08, TST-05) and CLAUDE.md "Critical Constraints"

#### Adapter Protocol (ADP-01)

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Adapter(Protocol):
    name: str
    def invoke(self, prompt: str, timeout: int) -> str: ...
```

- `runtime_checkable` so `isinstance(claude_adapter, Adapter)` works for adapter discovery in CLI doctor command (Phase 8) and orchestrator wiring.
- Third-party adapters do NOT need to inherit — structural subtyping is the contract.

#### `_SubprocessAdapterMixin` (ADP-02, ADP-03, ADP-04, ADP-08)

A regular class (not a Protocol). Concrete adapters inherit from it for the safe `_run_subprocess(...)` method.

```python
class _SubprocessAdapterMixin:
    cli_name: str          # subclass sets, e.g. "claude"
    auth_error_markers: tuple[str, ...]   # subclass sets, e.g. ("not logged in", "please run")
    
    def _run_subprocess(
        self,
        argv: list[str],
        prompt: str,
        timeout: int,
    ) -> str:
        """
        Safe subprocess invocation contract — MUST be the only way concrete adapters call subprocess.
        
        Enforces:
        - text=True, encoding="utf-8", errors="replace"
        - shell=False, list-form argv
        - mandatory timeout
        - prompt piped via stdin (NEVER on argv to avoid Windows ~8KB cmd.exe limit)
        - returncode==0 AND stdout.strip()=="" raises AdapterError (Codex bug defense)
        - FileNotFoundError -> AdapterAuthError("CLI not on PATH: re-auth or install")
        - subprocess.TimeoutExpired -> kill process tree (POSIX killpg, Windows taskkill /T /F) -> AdapterError
        - Auth-error markers in stdout/stderr -> AdapterAuthError with re-auth hint
        - Returns stdout.strip()
        """
```

- **Process-tree kill (ADP-04):** On POSIX, `os.killpg(os.getpgid(proc.pid), signal.SIGKILL)`. On Windows, `subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], ...)`. Detected via `os.name == "nt"`.
- **Empty-stdout defense (ADP-03):** Check `proc.returncode == 0 and not proc.stdout.strip()`. Raise `AdapterError(f"{self.cli_name}: empty stdout despite returncode 0 (possible TTY-only output bug, see openai/codex#19945)")`.
- **Auth-error detection (ADP-08):** Match auth_error_markers (case-insensitive) against `stdout + stderr`. If matched, raise `AdapterAuthError(f"{self.cli_name}: not logged in. Run `{self.cli_name} login` and retry.")`.

#### `ClaudeAdapter` (ADP-05)

```python
class ClaudeAdapter(_SubprocessAdapterMixin):
    name = "claude"
    cli_name = "claude"
    auth_error_markers = (
        "not logged in",
        "please run `claude login`",
        "authentication required",
    )
    
    def invoke(self, prompt: str, timeout: int) -> str:
        argv = ["claude", "-p"]
        return self._run_subprocess(argv, prompt, timeout)
```

- `argv = ["claude", "-p"]` exactly — `-p` reads prompt from stdin per `claude-code` CLI conventions.
- The class IS structurally an `Adapter` (has `name: str` and `invoke(...) -> str`).

#### Exceptions (ADP-08, base for Phase 7)

In `src/ultra_claude/adapters/base.py` (or extend `src/ultra_claude/exceptions.py` from Phase 2):

```python
class AdapterError(Exception):
    """Adapter raised an error invoking its CLI subprocess."""

class AdapterAuthError(AdapterError):
    """Adapter's CLI is not authenticated. Tells the user how to re-auth."""
```

Decision: put them in `src/ultra_claude/exceptions.py` (extend the file Phase 2 created) — keeps all custom exceptions in one place. Update `__all__` in `exceptions.py`.

#### Subprocess Lint Test (TST-05)

`tests/test_subprocess_lint.py` walks `src/ultra_claude/`, parses each `.py` file with `ast`, finds every `subprocess.run` call, asserts:
- `text=True` is in keywords
- `encoding="utf-8"` is in keywords
- `errors="replace"` is in keywords
- No `shell=True` (must be absent or explicit `shell=False`)

This test MUST run on every CI invocation. It catches future regressions where someone adds a `subprocess.run` call missing these guards.

#### Module structure (after this phase)

```
src/ultra_claude/
├── __init__.py
├── config.py
├── exceptions.py          # extended: ConfigError, AdapterError, AdapterAuthError
├── transcript.py
└── adapters/
    ├── __init__.py        # NEW — exports Adapter, _SubprocessAdapterMixin, ClaudeAdapter
    ├── base.py            # NEW — Adapter Protocol, _SubprocessAdapterMixin
    └── claude.py          # NEW — ClaudeAdapter
```

#### Testing strategy

- **`tests/test_adapters_base.py`:**
  - `isinstance(ClaudeAdapter(), Adapter)` is True (runtime_checkable Protocol)
  - A duck-typed object with `name: str` and `invoke(prompt, timeout) -> str` also passes the isinstance check
  - `_SubprocessAdapterMixin._run_subprocess` enforces UTF-8/replace/text/shell=False (assert via mock kwargs)

- **`tests/test_adapter_claude.py`:** uses `pytest-subprocess`'s `fp` fixture
  - Happy path: `fp.register(["claude", "-p"], stdout="hello world\n")` → `ClaudeAdapter().invoke("hi", timeout=10)` returns `"hello world"`
  - argv assertion: register a callback that asserts `argv == ["claude", "-p"]` and `stdin == b"hi"`
  - Empty stdout: `fp.register(["claude", "-p"], stdout="")` → raises `AdapterError`
  - FileNotFoundError: `fp.register(["claude", "-p"], callback=lambda **k: ...)` raises FileNotFoundError → adapter raises `AdapterAuthError`
  - Auth marker: `fp.register(["claude", "-p"], stdout="Error: not logged in")` → raises `AdapterAuthError`
  - Timeout: simulate `subprocess.TimeoutExpired` → process-tree kill called, `AdapterError` raised

- **`tests/test_subprocess_lint.py`:** ast-walks `src/ultra_claude/` and asserts every `subprocess.run` call has the required guards.

### Claude's Discretion

- Whether `_run_subprocess` returns trimmed stdout (`stdout.strip()`) or raw — recommend: trimmed (matches ADP-05/06/07 phrasing)
- Whether to include start_new_session=True / creationflags=CREATE_NEW_PROCESS_GROUP automatically (needed for clean process-tree kill) — recommend: yes, set in `_run_subprocess`
- Module name: `adapters/base.py` vs `adapters/_base.py` — recommend: `base.py` (no underscore — Python convention reserves underscore for "private" but this file holds the public Protocol)

</decisions>

<code_context>
## Existing Code Insights

After Phases 1-3:
- Pydantic v2 + ConfigError pattern established in config.py + exceptions.py
- LF/UTF-8 file IO discipline established in transcript.py
- Test patterns: pytest, tmp_path, parametrize, raw-bytes assertions, anchored regex matches

The Phase 4 module surface is the largest single phase so far — but every component has a tight contract (one constraint per requirement). The CI lint test (test_subprocess_lint.py) is a meta-test that protects against future regression and is the most novel piece.

</code_context>

<specifics>
## Specific Ideas

- **Pitfall #1 from research/PITFALLS.md is THE central concern of this phase:** Windows cmd.exe rejects argv > ~8KB. This is why prompts MUST be piped via stdin, never on argv (`-p <huge>`). The mixin enforces this by making prompt-via-stdin the only API.
- **Pitfall #2 is the empty-stdout defense:** the live `codex exec` 0.124.0+ TTY bug returns returncode=0 with empty stdout. `_SubprocessAdapterMixin` catches this for ALL adapters, not just Codex. ClaudeAdapter inherits the defense for free.
- **TST-05 lives in this phase, not Phase 9:** the lint test is a tripwire that fails fast on any future PR adding a non-compliant `subprocess.run`. Phase 4 is where it makes sense — the contract is freshly minted.

</specifics>

<deferred>
## Deferred Ideas

- Async invoke variant (`async def ainvoke(...)` returning `Awaitable[str]`) — not in v1, blocked on per-token streaming which is out of scope per CLAUDE.md
- Configurable retry/backoff inside the mixin — orchestrator (Phase 6) handles continue-on-error; mixin is one-shot
- Telemetry/metrics hooks inside `_run_subprocess` — Phase 9 may add stderr logging hooks; v1 just raises typed exceptions

</deferred>

---

*Phase: 04-adapter-protocol-claudeadapter*
*Context auto-generated 2026-05-02 (autonomous mode)*
