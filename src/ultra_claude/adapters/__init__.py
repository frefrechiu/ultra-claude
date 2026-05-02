"""Subprocess-based adapters for Claude / Gemini / Codex CLIs.

The public surface is:

* :class:`~ultra_claude.adapters.base.Adapter` -- a ``typing.Protocol``
  that defines the ``invoke(prompt, timeout) -> str`` contract. Third-party
  adapters do NOT need to inherit anything; structural typing is the rule.
* :class:`~ultra_claude.adapters.base._SubprocessAdapterMixin` -- the
  internal mixin that enforces the safe subprocess invocation contract for
  the three adapters bundled with ultra-claude. Marked private (leading
  underscore) because we explicitly do NOT promise API stability for
  third-party adapters; they should implement the Protocol directly.
* :class:`~ultra_claude.adapters.claude.ClaudeAdapter` -- first concrete
  adapter, wraps ``claude -p`` (Phase 4).
* :class:`~ultra_claude.adapters.gemini.GeminiAdapter` -- second concrete
  adapter, wraps ``gemini -p`` (Phase 7, ADP-06).
* :class:`~ultra_claude.adapters.codex.CodexAdapter` -- third concrete
  adapter, wraps ``codex exec`` (Phase 7, ADP-07). The empty-stdout
  defense in the mixin catches openai/codex#19945 for free -- see the
  CodexAdapter module docstring for the live-bug context.
"""

from __future__ import annotations

from .base import Adapter, _SubprocessAdapterMixin
from .claude import ClaudeAdapter
from .codex import CodexAdapter
from .gemini import GeminiAdapter

# Order is intentional (base Protocol + mixin first, then concrete adapters
# in roadmap-introduction order: Claude landed in Phase 4, then
# Gemini + Codex landed together in Phase 7. Alphabetical reordering would
# obscure the architectural narrative).
__all__ = [  # noqa: RUF022
    "Adapter",
    "_SubprocessAdapterMixin",
    "ClaudeAdapter",
    "GeminiAdapter",
    "CodexAdapter",
]
