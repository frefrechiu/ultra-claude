"""Adapter Protocol and the safe-subprocess mixin.

This module is THE choke point for every ultra-claude adapter. Concrete
adapters (``ClaudeAdapter``, ``GeminiAdapter``, ``CodexAdapter``) inherit
from :class:`_SubprocessAdapterMixin` and call its
:meth:`_SubprocessAdapterMixin._run_subprocess` method to actually launch a
CLI. They MUST NOT call :mod:`subprocess` directly -- the mixin is the only
sanctioned path, and the lint test in :mod:`tests.test_subprocess_lint`
fails the build if any new ``subprocess.run`` / ``subprocess.Popen`` call
in :mod:`src/ultra_claude` is missing the safe-contract keywords.

The contract enforced by ``_run_subprocess``:

1.  **List-form argv, ``shell=False``** -- never let the shell parse the
    command. Eliminates whole classes of injection bugs.
2.  **Prompt via stdin, never argv** -- mitigates Pitfall #1: Windows
    ``cmd.exe`` rejects argv > ~8 KB; ``CreateProcess`` caps at ~32 KB.
    Multi-turn debate prompts blow past both. ``input=prompt, text=True``
    feeds the prompt through the OS pipe instead.
3.  **``text=True, encoding="utf-8", errors="replace"``** -- mitigates
    Pitfall #3: Windows defaults to cp1252 and crashes on smart quotes /
    em-dashes / emoji that LLMs emit constantly. ``replace`` swallows the
    rare un-decodable byte rather than aborting the run mid-debate.
4.  **Mandatory ``timeout``** -- mitigates Pitfall #5. Without a timeout,
    a stalled CLI blocks forever and ``Ctrl-C`` orphans the child.
5.  **Process-tree kill on TimeoutExpired** -- POSIX ``os.killpg`` after
    ``start_new_session=True`` so SIGKILL hits every descendant; Windows
    ``taskkill /T /F /PID`` after
    ``creationflags=CREATE_NEW_PROCESS_GROUP``. Half-measures (timeout but
    no tree kill) leave runaway children burning subscription quota --
    the worst possible regression.
6.  **Empty-stdout defense** -- if ``returncode == 0`` AND
    ``stdout.strip() == ""``, raise :class:`AdapterError`. Mitigates
    Pitfall #2: the live ``codex exec`` 0.124.0+ TTY bug
    (`openai/codex#19945
    <https://github.com/openai/codex/issues/19945>`_) returns exit-0 with
    zero bytes when no controlling TTY is attached. We catch it for
    *every* adapter, not just Codex, so future regressions of the same
    shape (silent failures with successful exit codes) are caught
    automatically.
7.  **Auth-error detection** -- ``FileNotFoundError`` (CLI not on PATH) or
    a configured ``auth_error_markers`` substring (case-insensitive) in
    stdout+stderr raise :class:`AdapterAuthError` with a re-auth hint
    naming the CLI by ``cli_name``.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
from typing import Protocol, runtime_checkable

from ..exceptions import AdapterAuthError, AdapterError

__all__ = ["Adapter", "_SubprocessAdapterMixin"]


# ---------------------------------------------------------------------------
# Public Protocol (ADP-01)
# ---------------------------------------------------------------------------


@runtime_checkable
class Adapter(Protocol):
    """Structural contract for every ultra-claude adapter.

    Any class with a ``name: str`` attribute and an
    ``invoke(prompt: str, timeout: int) -> str`` method satisfies this
    Protocol -- third-party adapters do NOT need to inherit anything.
    The ``@runtime_checkable`` decorator means
    ``isinstance(some_object, Adapter)`` works at runtime, which the
    Phase 8 ``ultra-claude doctor`` subcommand relies on for adapter
    discovery / probing.
    """

    name: str

    def invoke(self, prompt: str, timeout: int) -> str: ...


# ---------------------------------------------------------------------------
# Private mixin (ADP-02, ADP-03, ADP-04, ADP-08)
# ---------------------------------------------------------------------------


class _SubprocessAdapterMixin:
    """Internal base for the three bundled adapters.

    Subclasses MUST set:

    * ``cli_name: str`` -- the binary name used in error messages
      (e.g. ``"claude"``).
    * ``auth_error_markers: tuple[str, ...]`` -- substrings searched
      case-insensitively against stdout+stderr; any match raises
      :class:`AdapterAuthError`.

    Subclasses MUST call :meth:`_run_subprocess` to actually launch their
    CLI; they MUST NOT call :mod:`subprocess` directly.
    """

    cli_name: str
    auth_error_markers: tuple[str, ...]

    def _run_subprocess(
        self,
        argv: list[str],
        prompt: str,
        timeout: int,
    ) -> str:
        """Launch ``argv`` with ``prompt`` piped via stdin, return stripped stdout.

        Args:
            argv: List-form command, e.g. ``["claude", "-p"]``. Never let
                callers inline the prompt here -- that defeats Pitfall #1.
            prompt: Full prompt text. Will be UTF-8 encoded into the
                child's stdin pipe.
            timeout: Hard ceiling in seconds. ``TimeoutExpired`` triggers
                a process-tree kill before the exception escapes.

        Returns:
            ``stdout.strip()`` of the child process on the happy path.

        Raises:
            AdapterAuthError: CLI binary missing (``FileNotFoundError``)
                or an auth marker matched in stdout/stderr.
            AdapterError: ``returncode != 0`` from the child, OR
                ``returncode == 0 and stdout.strip() == ""`` (Pitfall #2),
                OR ``TimeoutExpired`` (after process-tree kill).
        """

        # ------------------------------------------------------------------
        # Cross-platform Popen: explicit per-branch calls so mypy --strict
        # picks the right overload (a dict[str, object] spread does not).
        # POSIX uses start_new_session=True so os.killpg(pgid, SIGKILL)
        # can hit every descendant; Windows uses CREATE_NEW_PROCESS_GROUP
        # so taskkill /T /F /PID can enumerate descendants. (Pitfall #5.)
        # ------------------------------------------------------------------
        try:
            if os.name == "nt":
                proc = subprocess.Popen(
                    argv,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    shell=False,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                proc = subprocess.Popen(
                    argv,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    shell=False,
                    start_new_session=True,
                )
        except FileNotFoundError as err:
            # CLI binary not on PATH -- ADP-08 path #1.
            raise AdapterAuthError(
                f"{self.cli_name}: CLI not found on PATH. "
                f"Install it and run `{self.cli_name} login`, then retry."
            ) from err

        try:
            stdout, stderr = proc.communicate(input=prompt, timeout=timeout)
        except subprocess.TimeoutExpired as err:
            # Process-tree kill BEFORE re-raising as AdapterError, so no
            # orphaned children leak. (Pitfall #5 / ADP-04.)
            self._kill_process_tree(proc)
            # Drain whatever is left so the OS can clean up the pipes.
            with contextlib.suppress(subprocess.TimeoutExpired, OSError):
                proc.communicate(timeout=2)
            raise AdapterError(
                f"{self.cli_name}: timed out after {timeout}s; "
                f"process tree killed."
            ) from err

        # ------------------------------------------------------------------
        # Auth-error markers (ADP-08 path #2) -- case-insensitive sub-string
        # match against the union of stdout and stderr.
        # ------------------------------------------------------------------
        haystack = f"{stdout}\n{stderr}".lower()
        for marker in self.auth_error_markers:
            if marker.lower() in haystack:
                raise AdapterAuthError(
                    f"{self.cli_name}: not authenticated. "
                    f"Run `{self.cli_name} login` and retry. "
                    f"(matched marker: {marker!r})"
                )

        # ------------------------------------------------------------------
        # Empty-stdout defense (ADP-03, Pitfall #2 / openai/codex#19945)
        # ------------------------------------------------------------------
        if proc.returncode == 0 and not stdout.strip():
            raise AdapterError(
                f"{self.cli_name}: empty stdout despite returncode 0 "
                f"(possible TTY-only output regression; "
                f"see openai/codex#19945). stderr was: {stderr.strip()!r}"
            )

        # ------------------------------------------------------------------
        # Non-zero exit -- generic adapter failure
        # ------------------------------------------------------------------
        if proc.returncode != 0:
            raise AdapterError(
                f"{self.cli_name}: exited with code {proc.returncode}. "
                f"stdout: {stdout.strip()!r}. stderr: {stderr.strip()!r}"
            )

        # Happy path -- trimmed stdout (ADP-05/06/07 phrasing all say "trimmed").
        return stdout.strip()

    # ----------------------------------------------------------------------
    # Cross-platform process-tree kill helper (ADP-04 / Pitfall #5)
    # ----------------------------------------------------------------------

    @staticmethod
    def _kill_process_tree(proc: subprocess.Popen[str]) -> None:
        """Kill ``proc`` and every descendant.

        POSIX: ``os.killpg(os.getpgid(pid), SIGKILL)`` -- requires the
        ``start_new_session=True`` flag set at Popen time so the child has
        its own process group.

        Windows: ``taskkill /T /F /PID <pid>`` -- ``/T`` walks the tree,
        ``/F`` is force. Requires ``CREATE_NEW_PROCESS_GROUP`` at Popen
        time so taskkill can enumerate descendants.

        Errors during kill are swallowed -- if the child is already gone,
        that is fine; the goal is "no orphans", not "kill twice".
        """

        if os.name == "nt":
            # Windows path
            try:
                subprocess.run(
                    ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                    check=False,
                    timeout=10,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    shell=False,
                    capture_output=True,
                )
            except (OSError, subprocess.TimeoutExpired):
                # Last-ditch direct kill of the leader if taskkill itself
                # fails (e.g. taskkill not on PATH).
                with contextlib.suppress(OSError):
                    proc.kill()
        else:
            # POSIX path. The os.getpgid / os.killpg / signal.SIGKILL
            # attributes are POSIX-only; mypy on Windows cannot see them
            # so suppress attr-defined for this branch only.
            try:
                pgid = os.getpgid(proc.pid)  # type: ignore[attr-defined]
                os.killpg(pgid, signal.SIGKILL)  # type: ignore[attr-defined]
            except (ProcessLookupError, PermissionError, OSError):
                # Already dead, or we lack permission -- fall back to direct kill.
                with contextlib.suppress(OSError):
                    proc.kill()
