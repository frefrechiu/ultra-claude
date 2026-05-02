# Phase 7: Gemini & Codex Adapters - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

Add the remaining two concrete adapters by reusing `_SubprocessAdapterMixin`. Validates the contract works for all three vendors AND that the empty-stdout defense correctly catches the known `codex exec` 0.124.0+ TTY bug.

Scope:
- `src/ultra_claude/adapters/gemini.py` — `GeminiAdapter`
- `src/ultra_claude/adapters/codex.py` — `CodexAdapter`
- Update `src/ultra_claude/adapters/__init__.py` to export both
- Update `src/ultra_claude/registry.py` so `get_adapter("gemini")` and `get_adapter("codex")` return real adapters (not raise NotImplementedError)
- `tests/test_adapter_gemini.py` — same shape as `test_adapter_claude.py`
- `tests/test_adapter_codex.py` — same shape PLUS the live-bug regression test (returncode=0 + stdout="" → AdapterError)

Out of scope: CLI surface (Phase 8), release prep (Phase 9).

</domain>

<decisions>
## Implementation Decisions

### Locked from REQUIREMENTS.md (ADP-06, ADP-07) and CLAUDE.md Pitfall #2

#### `GeminiAdapter` (ADP-06)

```python
class GeminiAdapter(_SubprocessAdapterMixin):
    name = "gemini"
    cli_name = "gemini"
    auth_error_markers = (
        "not logged in",
        "please run `gemini auth login`",
        "authentication required",
        "no credentials",
    )
    
    def invoke(self, prompt: str, timeout: int) -> str:
        return self._run_subprocess(["gemini", "-p"], prompt, timeout)
```

argv: `["gemini", "-p"]`, prompt via stdin.

#### `CodexAdapter` (ADP-07)

```python
class CodexAdapter(_SubprocessAdapterMixin):
    name = "codex"
    cli_name = "codex"
    auth_error_markers = (
        "not logged in",
        "please run `codex login`",
        "authentication required",
    )
    
    def invoke(self, prompt: str, timeout: int) -> str:
        return self._run_subprocess(["codex", "exec"], prompt, timeout)
```

argv: `["codex", "exec"]`, prompt via stdin.

#### Registry update

```python
def get_adapter(adapter_kind: str) -> Adapter:
    from ultra_claude.adapters import ClaudeAdapter, GeminiAdapter, CodexAdapter
    if adapter_kind == "claude":
        return ClaudeAdapter()
    if adapter_kind == "gemini":
        return GeminiAdapter()
    if adapter_kind == "codex":
        return CodexAdapter()
    raise ValueError(f"unknown adapter kind: {adapter_kind!r}")
```

#### `__init__.py` update

```python
from ultra_claude.adapters.base import Adapter, _SubprocessAdapterMixin
from ultra_claude.adapters.claude import ClaudeAdapter
from ultra_claude.adapters.codex import CodexAdapter
from ultra_claude.adapters.gemini import GeminiAdapter

__all__ = [
    "Adapter",
    "_SubprocessAdapterMixin",
    "ClaudeAdapter",
    "GeminiAdapter",
    "CodexAdapter",
]
```

### Testing strategy

- `tests/test_adapter_gemini.py` — same 5-6 cases as `test_adapter_claude.py`: argv assertion, stdin payload, empty-stdout, FileNotFoundError, auth marker, TimeoutExpired+kill
- `tests/test_adapter_codex.py` — same cases PLUS one named `test_codex_empty_stdout_bug_regression` that documents Pitfall #2 and asserts the inherited mixin defense catches it
- Both use `pytest-subprocess` `fp` fixture — NO real CLIs needed

### Claude's Discretion

- Whether the auth_error_markers tuples should be identical across adapters — recommend: KEEP DISTINCT, the actual error strings vary by CLI vendor
- Whether to add a Phase 7-specific `_DECEMBER_2025_CODEX_BUG_DOCUMENTED_AT` constant string referencing openai/codex#19945 — recommend: yes, as a comment at the top of `codex.py`. Documents WHY the inherited defense matters here.

</decisions>

<code_context>
## Existing Code Insights

After Phases 1-6:
- `_SubprocessAdapterMixin` is proven on ClaudeAdapter (Phase 4)
- `pytest-subprocess` test pattern established in `tests/test_adapter_claude.py`
- Registry dispatcher pattern in place; just needs to swap NotImplementedError for real returns
- 50/50 tests pass, mypy clean, ruff clean across the package

This phase is essentially copy-paste-modify on the proven ClaudeAdapter pattern. Three concrete subclasses, all inheriting the same safety guarantees from the mixin.

</code_context>

<specifics>
## Specific Ideas

- Pitfall #2 (live `codex exec` 0.124.0+ TTY bug): the empty-stdout defense in `_SubprocessAdapterMixin._run_subprocess` already catches this. CodexAdapter just inherits — that's the proof. The test `test_codex_empty_stdout_bug_regression` documents the bug + asserts our defense works.
- All three adapters MUST satisfy `isinstance(_, Adapter)` via runtime_checkable Protocol — already proven for ClaudeAdapter, will hold for the new two by structural typing.

</specifics>

<deferred>
## Deferred Ideas

- Per-adapter custom retry logic — deferred; v1 is one-shot per turn
- Adapter-specific config flags (e.g. `temperature`, `model`) — out of scope; users configure via vendor-side login state
- Async adapter variants — v2 minimum

</deferred>

---

*Phase: 07-gemini-codex-adapters*
*Context auto-generated 2026-05-02 (autonomous mode)*
