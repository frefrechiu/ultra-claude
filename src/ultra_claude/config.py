"""Pydantic v2 schema and YAML loader for ``ultra-claude.yaml``.

This module is the input boundary for the entire orchestrator: every later
phase consumes a :class:`RoundtableConfig` instance and trusts its shape.

The public surface is:

* :class:`AgentConfig` -- one entry in the ``agents:`` list.
* :class:`RoundtableConfig` -- the top-level config object.
* :func:`load_config` -- read a YAML file from disk and return a validated
  :class:`RoundtableConfig`, raising :class:`~ultra_claude.exceptions.ConfigError`
  on any failure.
* :func:`format_validation_error` -- convert a :class:`pydantic.ValidationError`
  into a single human-readable string that names each offending field path.

Phase 2 success criteria (from ROADMAP and ``02-CONTEXT.md``):

1. A valid ``ultra-claude.yaml`` parses into a typed ``RoundtableConfig``.
2. Each agent requires ``name``, ``role``, ``adapter`` (Literal), and
   ``system_prompt``. Omitting any produces a Pydantic error pointing at
   the offending field.
3. Defaults: ``max_turns=12``, ``stop_keywords=['AGREED', 'DONE']``,
   ``turn_order='round_robin'`` (only legal v1 value).
4. Invalid YAML syntax or invalid config types produce a single
   human-readable error message naming the field path -- no raw tracebacks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .exceptions import ConfigError

__all__ = [
    "AgentConfig",
    "RoundtableConfig",
    "load_config",
    "format_validation_error",
    "ConfigError",
]


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class AgentConfig(BaseModel):
    """One participant in the roundtable.

    All four fields are required. ``adapter`` is a Literal so any value
    other than ``"claude"``, ``"gemini"``, or ``"codex"`` is rejected at
    validation time with a message like
    ``agents[0].adapter: invalid value 'clade'``.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, description="Unique display name for this agent.")
    role: str = Field(min_length=1, description="Short description of what this agent does.")
    adapter: Literal["claude", "gemini", "codex"] = Field(
        description="Which subprocess adapter drives this agent."
    )
    system_prompt: str = Field(
        min_length=1, description="Per-agent system prompt prepended to every turn."
    )


class RoundtableConfig(BaseModel):
    """Top-level config object loaded from ``ultra-claude.yaml``.

    Defaults match Phase 2 locked decisions:
        ``max_turns=12``, ``stop_keywords=['AGREED', 'DONE']``,
        ``turn_order='round_robin'``, ``abort_on_error=False``.
    """

    model_config = ConfigDict(extra="forbid")

    agents: list[AgentConfig] = Field(
        min_length=2, description="At least two agents -- a roundtable needs >=2 voices."
    )
    task: str | None = Field(
        default=None,
        description="Optional task statement; CLI --inline or task-file overrides this.",
    )
    max_turns: int = Field(default=12, ge=2, description="Hard cap on number of turns.")
    stop_keywords: list[str] = Field(
        default_factory=lambda: ["AGREED", "DONE"],
        min_length=1,
        description="Markers that, when seen by stop conditions, end the run.",
    )
    transcript_path: Path | None = Field(
        default=None,
        description="Where to write the transcript; default behavior is decided in Phase 6.",
    )
    turn_order: Literal["round_robin"] = Field(
        default="round_robin",
        description="Only 'round_robin' is supported in v1 (CFG-04).",
    )
    abort_on_error: bool = Field(
        default=False,
        description="If True, the orchestrator stops on the first adapter failure (ORC-05).",
    )

    @classmethod
    def from_yaml_string(cls, source: str) -> "RoundtableConfig":
        """Parse a YAML string and return a validated config.

        Used by tests and by the future ``--inline`` CLI flag. Raises
        :class:`ConfigError` on malformed YAML or schema violations.
        """

        try:
            raw = yaml.safe_load(source)
        except yaml.YAMLError as err:
            raise ConfigError(_format_yaml_error(err, source_label="<string>")) from err

        if not isinstance(raw, dict):
            raise ConfigError(
                "ultra-claude config must be a YAML mapping at the top level "
                f"(got {type(raw).__name__}: {raw!r})"
            )

        try:
            return cls.model_validate(raw)
        except ValidationError as err:
            raise ConfigError(format_validation_error(err, source_path=None)) from err


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_config(path: Path | str) -> RoundtableConfig:
    """Load and validate ``ultra-claude.yaml``.

    Args:
        path: Filesystem path to the YAML file (``str`` or ``Path``).

    Returns:
        A validated :class:`RoundtableConfig`.

    Raises:
        ConfigError: If the file does not exist, contains invalid YAML, or
            violates the schema. The message names the offending field path
            (e.g. ``agents[0].adapter: invalid value 'clade'``); no raw
            Pydantic traceback reaches the caller.
    """

    config_path = Path(path)

    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as err:
        raise ConfigError(f"Could not read config file {config_path}: {err}") from err

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as err:
        raise ConfigError(_format_yaml_error(err, source_label=str(config_path))) from err

    if raw is None:
        raise ConfigError(f"Config file is empty: {config_path}")

    if not isinstance(raw, dict):
        raise ConfigError(
            f"{config_path}: top-level YAML must be a mapping "
            f"(got {type(raw).__name__})"
        )

    try:
        return RoundtableConfig.model_validate(raw)
    except ValidationError as err:
        raise ConfigError(format_validation_error(err, source_path=config_path)) from err


# ---------------------------------------------------------------------------
# Error formatting
# ---------------------------------------------------------------------------


def format_validation_error(
    err: ValidationError, source_path: Path | None
) -> str:
    """Convert a Pydantic v2 ``ValidationError`` into a single user-facing string.

    The output is one header line followed by one indented line per
    field-level error::

        ultra-claude.yaml validation error:
          agents[0].adapter: invalid value 'clade' (expected 'claude', 'gemini', or 'codex')
          max_turns: must be >= 2 (got 1)

    No Python tracebacks reach the user.
    """

    header_source = str(source_path) if source_path is not None else "ultra-claude.yaml"
    lines: list[str] = [f"{header_source} validation error:"]

    for issue in err.errors():
        loc = _format_loc(issue.get("loc", ()))
        msg = issue.get("msg", "invalid value")
        err_type = issue.get("type", "")
        input_value = issue.get("input")

        # Specialise the message for the most common error categories so the
        # output looks closer to the example in 02-CONTEXT.md
        # (`agents[0].adapter: invalid value 'clade' (expected ...)`)
        # rather than Pydantic's raw "Input should be 'claude' or ..." phrasing.
        if err_type == "literal_error":
            expected = issue.get("ctx", {}).get("expected", "")
            line = (
                f"  {loc}: invalid value {input_value!r} "
                f"(expected {expected})"
                if expected
                else f"  {loc}: invalid value {input_value!r} ({msg})"
            )
        elif err_type == "missing":
            line = f"  {loc}: required field is missing"
        elif err_type.startswith("string_") and err_type.endswith("_length"):
            line = f"  {loc}: {msg.lower()}"
        else:
            # Fallback: show Pydantic's own message verbatim, plus the input
            # for debugging when it is small enough to be useful.
            line = f"  {loc}: {msg}"
            if input_value is not None and not isinstance(input_value, (dict, list)):
                line = f"{line} (got {input_value!r})"

        lines.append(line)

    return "\n".join(lines)


def _format_loc(loc: tuple[str | int, ...] | list[str | int]) -> str:
    """Render a Pydantic ``loc`` tuple as ``agents[0].adapter`` style."""

    parts: list[str] = []
    for item in loc:
        if isinstance(item, int):
            if parts:
                parts[-1] = f"{parts[-1]}[{item}]"
            else:
                parts.append(f"[{item}]")
        else:
            parts.append(str(item))
    return ".".join(parts) if parts else "<root>"


def _format_yaml_error(err: yaml.YAMLError, source_label: str) -> str:
    """Render a ``yaml.YAMLError`` as a single line with file + line/column."""

    if isinstance(err, yaml.MarkedYAMLError) and err.problem_mark is not None:
        mark = err.problem_mark
        problem = err.problem or "YAML parse error"
        return (
            f"{source_label}:{mark.line + 1}:{mark.column + 1}: "
            f"YAML parse error: {problem}"
        )
    return f"{source_label}: YAML parse error: {err}"
