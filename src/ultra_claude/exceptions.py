"""Exceptions raised by ultra-claude.

This module is the single home for all custom exception classes used across
the package. Phase 2 lands ``ConfigError`` (raised by ``ultra_claude.config``
on invalid YAML or schema-validation failures). Phase 4 will append
``AdapterError`` and ``AdapterAuthError`` for subprocess adapters.

Keeping the exception types in their own module (rather than inside
``config.py`` or ``adapters/base.py``) lets the CLI layer map them to exit
codes (per CLI-10) without importing Pydantic or subprocess machinery.
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


__all__ = ["ConfigError"]
