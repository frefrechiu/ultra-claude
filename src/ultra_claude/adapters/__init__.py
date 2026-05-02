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
* ``GeminiAdapter`` and ``CodexAdapter`` will land in Phase 7, reusing
  :class:`_SubprocessAdapterMixin` unchanged.
"""

from __future__ import annotations

from .base import Adapter, _SubprocessAdapterMixin
from .claude import ClaudeAdapter

# Order is intentional (base Protocol + mixin first, then concrete adapters);
# matches the chronological-by-introduction convention used in exceptions.py.
__all__ = ["Adapter", "_SubprocessAdapterMixin", "ClaudeAdapter"]  # noqa: RUF022
