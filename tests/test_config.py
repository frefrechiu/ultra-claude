"""Tests for ultra_claude.config.

Covers the 6 cases enumerated in ``.planning/phases/02-config-schema-yaml-loader/02-CONTEXT.md``
plus one wire-format check for ``format_validation_error``.

Tests use inline YAML strings via ``RoundtableConfig.from_yaml_string`` for the
in-memory cases, and ``tmp_path`` + ``load_config`` for the file-IO cases.

Requirements coverage: CFG-01, CFG-02, CFG-03, CFG-04, CFG-05.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from ultra_claude.config import (
    AgentConfig,
    ConfigError,
    RoundtableConfig,
    format_validation_error,
    load_config,
)


# ---------------------------------------------------------------------------
# Test fixtures (inline YAML strings)
# ---------------------------------------------------------------------------


VALID_YAML = """\
agents:
  - name: Architect
    role: high-level design
    adapter: claude
    system_prompt: "You design system architecture."
  - name: Critic
    role: skeptic
    adapter: gemini
    system_prompt: "You poke holes in proposed designs."
  - name: Implementer
    role: hands-on coder
    adapter: codex
    system_prompt: "You write the actual code."
max_turns: 9
stop_keywords:
  - AGREED
  - SHIP IT
"""


# ---------------------------------------------------------------------------
# Case 1 -- happy path (CFG-01)
# ---------------------------------------------------------------------------


def test_valid_yaml_parses_into_typed_config() -> None:
    """A valid ultra-claude.yaml gets back a typed RoundtableConfig (CFG-01)."""
    cfg = RoundtableConfig.from_yaml_string(VALID_YAML)

    assert isinstance(cfg, RoundtableConfig)
    assert len(cfg.agents) == 3
    assert all(isinstance(a, AgentConfig) for a in cfg.agents)
    assert cfg.agents[0].name == "Architect"
    assert cfg.agents[0].adapter == "claude"
    assert cfg.agents[1].adapter == "gemini"
    assert cfg.agents[2].adapter == "codex"
    assert cfg.max_turns == 9
    assert cfg.stop_keywords == ["AGREED", "SHIP IT"]
    assert cfg.turn_order == "round_robin"
    assert cfg.abort_on_error is False
    assert cfg.transcript_path is None


# ---------------------------------------------------------------------------
# Case 2 -- missing required agent field (CFG-02)
# ---------------------------------------------------------------------------


def test_missing_agent_field_names_offending_field_path() -> None:
    """Omitting any of {name, role, adapter, system_prompt} surfaces the field path (CFG-02)."""
    bad_yaml = """\
agents:
  - name: A
    role: r
    system_prompt: p
  - name: B
    role: r
    adapter: gemini
    system_prompt: p
"""
    with pytest.raises(ConfigError) as excinfo:
        RoundtableConfig.from_yaml_string(bad_yaml)

    msg = str(excinfo.value)
    assert "agents[0].adapter" in msg
    assert "required field is missing" in msg
    # No raw Python traceback or class repr leaks to the user.
    assert "Traceback" not in msg
    assert "pydantic_core" not in msg


# ---------------------------------------------------------------------------
# Case 3 -- invalid adapter Literal (CFG-02)
# ---------------------------------------------------------------------------


def test_invalid_adapter_literal_is_rejected_with_field_path() -> None:
    """adapter must be one of the three CLI literals (CFG-02)."""
    bad_yaml = """\
agents:
  - name: A
    role: r
    adapter: clade
    system_prompt: p
  - name: B
    role: r
    adapter: gemini
    system_prompt: p
"""
    with pytest.raises(ConfigError) as excinfo:
        RoundtableConfig.from_yaml_string(bad_yaml)

    msg = str(excinfo.value)
    assert "agents[0].adapter" in msg
    assert "'clade'" in msg
    # The expected-values hint should mention all three valid adapters.
    assert "claude" in msg
    assert "gemini" in msg
    assert "codex" in msg


# ---------------------------------------------------------------------------
# Case 4 -- invalid turn_order (CFG-04)
# ---------------------------------------------------------------------------


def test_non_round_robin_turn_order_is_rejected() -> None:
    """turn_order accepts only 'round_robin' in v1 (CFG-04)."""
    bad_yaml = """\
agents:
  - name: A
    role: r
    adapter: claude
    system_prompt: p
  - name: B
    role: r
    adapter: gemini
    system_prompt: p
turn_order: speaker_chooses
"""
    with pytest.raises(ConfigError) as excinfo:
        RoundtableConfig.from_yaml_string(bad_yaml)

    msg = str(excinfo.value)
    assert "turn_order" in msg
    assert "'speaker_chooses'" in msg
    assert "round_robin" in msg


# ---------------------------------------------------------------------------
# Case 5 -- defaults (CFG-04, CFG-05)
# ---------------------------------------------------------------------------


def test_defaults_for_max_turns_and_stop_keywords() -> None:
    """Omitting optional fields yields the locked defaults (CFG-04, CFG-05)."""
    minimal_yaml = """\
agents:
  - name: A
    role: r
    adapter: claude
    system_prompt: p
  - name: B
    role: r
    adapter: gemini
    system_prompt: p
"""
    cfg = RoundtableConfig.from_yaml_string(minimal_yaml)

    assert cfg.max_turns == 12  # CFG-04
    assert cfg.stop_keywords == ["AGREED", "DONE"]  # CFG-05
    assert cfg.turn_order == "round_robin"  # CFG-04
    assert cfg.abort_on_error is False
    assert cfg.task is None
    assert cfg.transcript_path is None


# ---------------------------------------------------------------------------
# Case 6 -- malformed YAML syntax (CFG-03)
# ---------------------------------------------------------------------------


def test_malformed_yaml_produces_human_readable_error(tmp_path: Path) -> None:
    """Invalid YAML syntax yields ConfigError naming the file/line, not a yaml.YAMLError (CFG-03)."""
    cfg_path = tmp_path / "broken.yaml"
    cfg_path.write_text(
        "agents:\n"
        "  - name: A\n"
        "    role: r\n"
        "    adapter: claude\n"
        "    system_prompt: p\n"
        "  - this: is: not: valid: yaml: at: all\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as excinfo:
        load_config(cfg_path)

    msg = str(excinfo.value)
    assert "YAML parse error" in msg
    # The file path should appear in the message so the user can find it.
    assert str(cfg_path) in msg
    # The underlying YAMLError type name must NOT leak to the user.
    assert not isinstance(excinfo.value, yaml.YAMLError)
    assert not isinstance(excinfo.value, ValidationError)


# ---------------------------------------------------------------------------
# Bonus -- wire format of format_validation_error matches CONTEXT.md example (CFG-03)
# ---------------------------------------------------------------------------


def test_format_validation_error_produces_field_path_per_line() -> None:
    """The formatter output matches the shape locked in 02-CONTEXT.md (CFG-03)."""
    bad_yaml = """\
agents:
  - name: A
    role: r
    adapter: clade
    system_prompt: p
  - name: B
    role: r
    adapter: gemini
    system_prompt: p
max_turns: 1
"""
    with pytest.raises(ConfigError) as excinfo:
        RoundtableConfig.from_yaml_string(bad_yaml)

    msg = str(excinfo.value)
    lines = msg.splitlines()

    # Header line names the source.
    assert lines[0].endswith("validation error:")
    # Each subsequent line is indented with two spaces and contains a colon
    # separating the field path from its message.
    detail_lines = [ln for ln in lines[1:] if ln.strip()]
    assert detail_lines, "expected at least one detail line"
    for line in detail_lines:
        assert line.startswith("  "), f"detail line not indented: {line!r}"
        # Strip the leading indent before searching for the path<->msg colon
        # (the indent itself starts with whitespace, not a colon).
        assert ":" in line.lstrip(), f"detail line missing path/msg separator: {line!r}"

    # The two specific failures must surface.
    joined = "\n".join(detail_lines)
    assert "agents[0].adapter" in joined
    assert "max_turns" in joined


# ---------------------------------------------------------------------------
# Extra coverage -- file-not-found path in load_config
# ---------------------------------------------------------------------------


def test_missing_config_file_raises_config_error(tmp_path: Path) -> None:
    """A missing path produces ConfigError, not FileNotFoundError."""
    nonexistent = tmp_path / "does_not_exist.yaml"
    with pytest.raises(ConfigError) as excinfo:
        load_config(nonexistent)
    assert "not found" in str(excinfo.value).lower()
    assert str(nonexistent) in str(excinfo.value)
