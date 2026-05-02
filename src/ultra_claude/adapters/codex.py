"""CodexAdapter -- subprocess adapter for the OpenAI Codex CLI.

Wraps the ``codex exec`` subcommand. The prompt is piped in via stdin
(NOT ``codex exec <huge string>`` -- see Pitfall #1: Windows ``cmd.exe``
caps argv at ~8 KB; multi-turn debate prompts blow past that).

LIVE BUG NOTE -- openai/codex#19945:
    As of ``codex exec`` 0.124.0+, the CLI emits zero bytes to stdout
    when no controlling TTY is attached AND exits with returncode 0.
    See https://github.com/openai/codex/issues/19945. We do NOT need
    Codex-specific defensive code here -- the empty-stdout defense in
    :meth:`_SubprocessAdapterMixin._run_subprocess` (added in Phase 4
    BEFORE this adapter existed, exactly so the regression would land
    pre-broken) catches this case for every adapter. The test
    ``test_codex_empty_stdout_bug_regression`` in
    ``tests/test_adapter_codex.py`` documents that the inherited
    defense fires correctly for the Codex bug shape -- proving the
    mixin contract holds end-to-end. If the upstream fix lands and the
    bug shape changes, that test is the canary.

The class itself is intentionally tiny:

* ``name = "codex"`` -- satisfies the
  :class:`~ultra_claude.adapters.base.Adapter` Protocol (used by the
  orchestrator to route turns and by Phase 8's ``ultra-claude doctor``
  for per-CLI status reporting).
* ``cli_name = "codex"`` -- the binary the mixin actually launches.
* ``auth_error_markers`` -- substrings the mixin scans for in
  stdout/stderr; any match raises
  :class:`~ultra_claude.exceptions.AdapterAuthError` with a re-auth hint.
  Markers are KEPT DISTINCT from the Claude/Gemini tuples (per Phase 7
  decision D-02).
* ``invoke(prompt, timeout) -> str`` -- delegates to
  :meth:`_SubprocessAdapterMixin._run_subprocess` with
  ``argv = ["codex", "exec"]``. Every safety property is inherited from
  the mixin. This file deliberately does NOT pull in the stdlib
  subprocess module.

Phase 7 success criterion (ADP-07):
  ``CodexAdapter().invoke("hi", timeout=10)`` (mocked) issues a
  ``subprocess.Popen`` call with list-form argv ``["codex", "exec"]``,
  prompt piped via stdin, and the full safe-contract kwargs.
"""

from __future__ import annotations

from .base import _SubprocessAdapterMixin

__all__ = ["CodexAdapter"]


class CodexAdapter(_SubprocessAdapterMixin):
    """Adapter for OpenAI's Codex CLI (``codex exec``).

    Structural conformance with :class:`~ultra_claude.adapters.base.Adapter`:
    the class declares ``name: str`` and an ``invoke(prompt, timeout) -> str``
    method, so ``isinstance(CodexAdapter(), Adapter)`` is True.

    The empty-stdout defense from the mixin is what makes this adapter
    safe in the presence of openai/codex#19945 -- see the module docstring.
    """

    #: Display name used by the orchestrator and CLI (Adapter Protocol field).
    name: str = "codex"

    #: Binary name passed to ``subprocess.Popen`` and used in error messages.
    cli_name: str = "codex"

    #: Substrings the mixin searches case-insensitively against stdout+stderr.
    #: Any match raises :class:`AdapterAuthError`. Kept DISTINCT from
    #: Claude/Gemini per Phase 7 decision D-02 -- vendor phrasing varies.
    auth_error_markers: tuple[str, ...] = (
        "not logged in",
        "please run `codex login`",
        "authentication required",
    )

    def invoke(self, prompt: str, timeout: int) -> str:
        """Run ``codex exec`` with ``prompt`` piped via stdin.

        Args:
            prompt: Full prompt text. Sent to the child via stdin --
                never inlined into argv.
            timeout: Hard ceiling in seconds. Enforced by the mixin's
                Popen + communicate loop; on overrun the entire process
                tree is killed before the exception escapes.

        Returns:
            ``stdout.strip()`` of ``codex exec`` on the happy path.

        Raises:
            AdapterAuthError: ``codex`` binary missing from PATH, or an
                auth marker found in stdout/stderr.
            AdapterError: ``codex`` exited non-zero, returned empty stdout
                with exit-0 (the openai/codex#19945 TTY bug -- caught by
                the inherited mixin defense), or hit the ``timeout``.
        """

        argv = ["codex", "exec"]
        return self._run_subprocess(argv, prompt, timeout)
