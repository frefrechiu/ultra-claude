"""Adapter registry -- maps an ``AgentConfig.adapter`` literal to an instance.

The registry is a thin dispatch function so the orchestrator never imports
concrete adapter classes directly. After Phase 7 (ADP-06 + ADP-07), all
three adapter literals (``"claude"``, ``"gemini"``, ``"codex"``) return
real instances; the ``NotImplementedError`` branch was removed when
GeminiAdapter and CodexAdapter landed.

Why a function and not a dict: the dict approach instantiates every adapter
at import time, which would fail in environments where (e.g.) only the
``claude`` CLI is on PATH. The function defers instantiation to call time.

Why a function and not a class: per CLAUDE.md "Architecture corrections",
classes are reserved for objects with state. ``get_adapter`` is stateless
dispatch, so a function is the right shape.
"""

from __future__ import annotations

from .adapters import Adapter, ClaudeAdapter, CodexAdapter, GeminiAdapter

__all__ = ["get_adapter"]


def get_adapter(adapter_kind: str) -> Adapter:
    """Return a fresh adapter instance for the given ``adapter_kind`` literal.

    Args:
        adapter_kind: One of ``"claude"``, ``"gemini"``, ``"codex"``. Other
            values raise ``ValueError`` (config validation should have caught
            this earlier, but the registry double-checks for defence in depth).

    Returns:
        A new :class:`~ultra_claude.adapters.base.Adapter` instance.

    Raises:
        ValueError: Any other string -- ``AgentConfig.adapter`` is a Literal
            so this should be unreachable in practice, but we never trust
            external input.
    """

    if adapter_kind == "claude":
        return ClaudeAdapter()
    if adapter_kind == "gemini":
        return GeminiAdapter()
    if adapter_kind == "codex":
        return CodexAdapter()
    raise ValueError(
        f"unknown adapter kind: {adapter_kind!r} "
        f"(expected one of 'claude', 'gemini', 'codex')"
    )
