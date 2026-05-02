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
* Concrete adapter classes (``ClaudeAdapter`` in plan 04-02; ``GeminiAdapter``
  and ``CodexAdapter`` in Phase 7).
"""

from __future__ import annotations

from .base import Adapter, _SubprocessAdapterMixin

__all__ = ["Adapter", "_SubprocessAdapterMixin"]
