"""Exceptions raised by ultra-claude.

This module is the single home for all custom exception classes used across
the package. Phase 2 landed :class:`ConfigError` (raised by
:mod:`ultra_claude.config` on invalid YAML or schema-validation failures).
Phase 4 adds :class:`AdapterError` and :class:`AdapterAuthError` for
subprocess adapters.

Keeping every custom exception in one module (rather than scattered across
``config.py`` and ``adapters/base.py``) lets the CLI layer (Phase 8) map them
to exit codes per CLI-10 without importing Pydantic or subprocess machinery::

    ConfigError       -> exit 2 (config validation error)
    AdapterAuthError  -> exit 1, plus a re-auth hint to stderr
    AdapterError      -> exit 1 (generic adapter failure)
"""

from __future__ import annotations


class ConfigError(Exception):
    """Raised when an ``ultra-claude.yaml`` config cannot be loaded or validated.

    This wraps three underlying failure modes in a single user-facing type:

    * ``yaml.YAMLError`` from ``yaml.safe_load`` (malformed YAML syntax).
    * ``pydantic.ValidationError`` from ``RoundtableConfig.model_validate``
      (schema violations: missing required fields, wrong types, bad
      Literal values, etc.).
    * ``FileNotFoundError`` when the config path does not exist.

    The ``str(err)`` representation is a single human-readable message that
    names the offending field path (e.g. ``agents[0].adapter: invalid value
    'clade'``). No Python tracebacks reach the user; the CLI maps this to
    exit code 2 (CLI-10) in Phase 8.
    """


class AdapterError(Exception):
    """Raised by a subprocess adapter when invoking its CLI fails.

    Covers every failure mode that is *not* an authentication problem:

    * ``returncode != 0`` from the child CLI (with stdout/stderr captured
      in the message so the user can see what the CLI said).
    * ``returncode == 0`` AND empty stdout -- the live ``codex exec``
      0.124.0+ TTY bug (`openai/codex#19945
      <https://github.com/openai/codex/issues/19945>`_). The mixin's
      empty-stdout defense raises this for *every* adapter, not just Codex,
      so future regressions of the same shape are caught automatically.
    * ``subprocess.TimeoutExpired`` -- the adapter has already killed the
      child process tree (POSIX ``os.killpg``, Windows ``taskkill /T /F``)
      before raising, so no orphaned children leak.

    The CLI layer (Phase 8) maps this to exit code ``1`` per CLI-10. The
    orchestrator (Phase 6) catches it per-turn and either logs+continues
    or aborts depending on ``RoundtableConfig.abort_on_error``.
    """


class AdapterAuthError(AdapterError):
    """Raised when a subprocess adapter's underlying CLI is not authenticated.

    Distinct from :class:`AdapterError` so the CLI layer can show a
    re-auth-specific message ("run ``claude login``") rather than a generic
    runtime failure. Triggered by:

    * ``FileNotFoundError`` when the CLI binary is not on PATH.
    * Known auth-error marker strings appearing in stdout or stderr (each
      adapter declares its own ``auth_error_markers`` tuple).

    Subclassing :class:`AdapterError` means a caller that catches
    ``AdapterError`` will also catch this -- the orchestrator's
    continue-on-error semantics apply uniformly. Callers that want the
    re-auth message specifically can catch ``AdapterAuthError`` first.
    """


# Order is intentional (Phase 2 base, then Phase 4 additions); not alphabetical.
__all__ = ["ConfigError", "AdapterError", "AdapterAuthError"]  # noqa: RUF022
