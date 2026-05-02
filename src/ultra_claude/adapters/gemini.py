"""GeminiAdapter -- subprocess adapter for the Google Gemini CLI.

Wraps the ``gemini -p`` subcommand. The prompt is piped in via stdin
(NOT ``gemini -p <huge string>`` -- see Pitfall #1: Windows ``cmd.exe``
caps argv at ~8 KB; multi-turn debate prompts blow past that). The
``-p`` flag is the non-interactive prompt mode documented at
https://github.com/google-gemini/gemini-cli (the same shape as
``claude -p`` so the mixin can be reused unchanged).

The class itself is intentionally tiny:

* ``name = "gemini"`` -- satisfies the
  :class:`~ultra_claude.adapters.base.Adapter` Protocol (used by the
  orchestrator to route turns and by Phase 8's ``ultra-claude doctor``
  for per-CLI status reporting).
* ``cli_name = "gemini"`` -- the binary the mixin actually launches.
* ``auth_error_markers`` -- substrings the mixin scans for in
  stdout/stderr; any match raises
  :class:`~ultra_claude.exceptions.AdapterAuthError` with a re-auth hint.
  Markers are KEPT DISTINCT from the Claude/Codex tuples (per Phase 7
  decision D-02) because real-world auth failure phrasing varies by CLI.
* ``invoke(prompt, timeout) -> str`` -- delegates to
  :meth:`_SubprocessAdapterMixin._run_subprocess` with
  ``argv = ["gemini", "-p"]``. Every safety property (UTF-8,
  errors=replace, mandatory timeout, process-tree kill, Pitfall #2
  empty-stdout defense, auth-marker detection) is inherited from the
  mixin. This file deliberately does NOT pull in the stdlib subprocess
  module -- the lint test in :mod:`tests.test_subprocess_lint` would
  catch any regression.

Phase 7 success criterion (ADP-06):
  ``GeminiAdapter().invoke("hi", timeout=10)`` (mocked) issues a
  ``subprocess.Popen`` call with list-form argv ``["gemini", "-p"]``,
  prompt piped via stdin, and the full safe-contract kwargs.
"""

from __future__ import annotations

from .base import _SubprocessAdapterMixin

__all__ = ["GeminiAdapter"]


class GeminiAdapter(_SubprocessAdapterMixin):
    """Adapter for Google's Gemini CLI (``gemini -p``).

    Structural conformance with :class:`~ultra_claude.adapters.base.Adapter`:
    the class declares ``name: str`` and an ``invoke(prompt, timeout) -> str``
    method, so ``isinstance(GeminiAdapter(), Adapter)`` is True.
    """

    #: Display name used by the orchestrator and CLI (Adapter Protocol field).
    name: str = "gemini"

    #: Binary name passed to ``subprocess.Popen`` and used in error messages.
    cli_name: str = "gemini"

    #: Substrings the mixin searches case-insensitively against stdout+stderr.
    #: Any match raises :class:`AdapterAuthError`. Strings come from observed
    #: ``gemini`` CLI auth-failure messages. Kept DISTINCT from Claude/Codex
    #: per Phase 7 decision D-02 -- vendor phrasing varies and shared markers
    #: would over-trigger.
    auth_error_markers: tuple[str, ...] = (
        "not logged in",
        "please run `gemini auth login`",
        "authentication required",
        "no credentials",
    )

    def invoke(self, prompt: str, timeout: int) -> str:
        """Run ``gemini -p`` with ``prompt`` piped via stdin.

        Args:
            prompt: Full prompt text (typically the running transcript +
                the current agent's system prompt + the original task).
                Sent to the child via stdin -- never inlined into argv.
            timeout: Hard ceiling in seconds. Enforced by the mixin's
                Popen + communicate loop; on overrun the entire process
                tree is killed before the exception escapes (Pitfall #5).

        Returns:
            ``stdout.strip()`` of ``gemini -p`` on the happy path.

        Raises:
            AdapterAuthError: ``gemini`` binary missing from PATH, or an
                auth marker found in stdout/stderr.
            AdapterError: ``gemini`` exited non-zero, returned empty stdout
                with exit-0 (Pitfall #2 defense applies even though Gemini
                doesn't have the codex TTY bug -- belt + braces), or hit
                the ``timeout``.
        """

        argv = ["gemini", "-p"]
        return self._run_subprocess(argv, prompt, timeout)
