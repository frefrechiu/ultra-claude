"""ClaudeAdapter -- subprocess adapter for the Claude Code CLI.

Wraps the ``claude -p`` subcommand. The prompt is piped in via stdin
(NOT ``claude -p <huge string>`` -- see Pitfall #1: Windows ``cmd.exe``
caps argv at ~8 KB, and ``CreateProcess`` caps at ~32 KB; multi-turn debate
prompts blow past both limits).

The class itself is intentionally tiny:

* ``name = "claude"`` -- satisfies the :class:`~ultra_claude.adapters.base.Adapter`
  Protocol (used by the orchestrator to route turns and by Phase 8's
  ``ultra-claude doctor`` for per-CLI status reporting).
* ``cli_name = "claude"`` -- the binary the mixin actually launches.
* ``auth_error_markers`` -- substrings the mixin scans for in stdout/stderr;
  any match raises :class:`~ultra_claude.exceptions.AdapterAuthError` with
  a re-auth hint.
* ``invoke(prompt, timeout) -> str`` -- delegates to
  :meth:`_SubprocessAdapterMixin._run_subprocess` with
  ``argv = ["claude", "-p"]``. The mixin handles encoding, timeout,
  process-tree kill, empty-stdout defense, and auth-marker detection.

Every safety property (UTF-8, errors=replace, mandatory timeout,
process-tree kill, Pitfall #2 empty-stdout defense) is inherited from
the mixin. This file deliberately does NOT pull in the stdlib subprocess
module -- if a future maintainer is tempted to add such a direct dependency,
the lint test in :mod:`tests.test_subprocess_lint` (landing in 04-03) will
catch any regression. The design intent is "concrete adapters never touch
the subprocess module directly".

Phase 4 success criteria (ADP-05):
  ``ClaudeAdapter().invoke("hi", timeout=10)`` (mocked) issues a
  ``subprocess.Popen`` call with list-form argv ``["claude", "-p"]``,
  ``text=True, encoding="utf-8", errors="replace"``, mandatory ``timeout``,
  ``shell=False``, and a stdin-piped prompt. All of those properties are
  enforced by the mixin in :mod:`ultra_claude.adapters.base`.
"""

from __future__ import annotations

from .base import _SubprocessAdapterMixin

__all__ = ["ClaudeAdapter"]


class ClaudeAdapter(_SubprocessAdapterMixin):
    """Adapter for Anthropic's Claude Code CLI (``claude -p``).

    Structural conformance with :class:`~ultra_claude.adapters.base.Adapter`:
    the class declares ``name: str`` and an ``invoke(prompt, timeout) -> str``
    method, so ``isinstance(ClaudeAdapter(), Adapter)`` is True.
    """

    #: Display name used by the orchestrator and CLI (Adapter Protocol field).
    name: str = "claude"

    #: Binary name passed to ``subprocess.Popen`` and used in error messages.
    cli_name: str = "claude"

    #: Substrings the mixin searches case-insensitively against stdout+stderr.
    #: Any match raises :class:`AdapterAuthError`. Strings come from observed
    #: ``claude`` CLI auth-failure messages and the public Claude Code error
    #: docs (https://code.claude.com/docs/en/errors).
    auth_error_markers: tuple[str, ...] = (
        "not logged in",
        "please run `claude login`",
        "please run /login",
        "authentication required",
        "authentication failed",
    )

    def invoke(self, prompt: str, timeout: int) -> str:
        """Run ``claude -p`` with ``prompt`` piped via stdin.

        Args:
            prompt: Full prompt text (typically the running transcript +
                the current agent's system prompt + the original task).
                Sent to the child via stdin -- never inlined into argv.
            timeout: Hard ceiling in seconds. Enforced by the mixin's
                Popen + communicate loop; on overrun the entire process
                tree is killed before the exception escapes (Pitfall #5).

        Returns:
            ``stdout.strip()`` of ``claude -p`` on the happy path.

        Raises:
            AdapterAuthError: ``claude`` binary missing from PATH, or an
                auth marker found in stdout/stderr.
            AdapterError: ``claude`` exited non-zero, returned empty stdout
                with exit-0 (Pitfall #2 defense applies even though Claude
                doesn't have the codex TTY bug -- belt + braces), or hit
                the ``timeout``.
        """

        argv = ["claude", "-p"]
        return self._run_subprocess(argv, prompt, timeout)
