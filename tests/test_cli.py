"""Tests for src/ultra_claude/cli.py.

11 tests covering CLI-01..CLI-11 plus PRE-01 (bundled debate preset).
Each test maps to one or more requirements in
``.planning/phases/08-cli-surface-debate-preset/08-CONTEXT.md``
"Testing strategy".

Test strategy:
* ``click.testing.CliRunner`` invokes the CLI in-process -- no shell, no
  subprocess. Per CLAUDE.md Critical Constraint #1, this means the test
  file launches ZERO real CLIs (Claude/Gemini/Codex) and ZERO subprocess
  calls. The doctor command's internal ``subprocess.run`` is mocked via
  ``monkeypatch.setattr``.
* End-to-end pipeline test injects a ``FakeAdapter`` factory through
  ``monkeypatch.setattr(orch_module, "get_adapter", ...)`` so the
  orchestrator runs to completion writing a real transcript to
  ``tmp_path``. The orchestrator imports ``get_adapter`` from
  ``.registry`` at module top level, so patching the symbol on the
  orchestrator module replaces the binding the run() loop uses.
* Stdout/stderr discipline test relies on click 8.3+'s default behavior
  where ``result.stdout`` and ``result.stderr`` are split automatically
  (no ``mix_stderr=False`` parameter required -- it was removed in
  click 8.3 in favor of always-split semantics).

Requirements coverage: CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, CLI-06,
CLI-07, CLI-08, CLI-09, CLI-10, CLI-11, PRE-01.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

import ultra_claude.cli as cli_module
import ultra_claude.orchestrator as orch_module
from ultra_claude.cli import main

# ---------------------------------------------------------------------------
# FakeAdapter (mirrors tests/test_orchestrator.py for runtime independence)
# ---------------------------------------------------------------------------


class FakeAdapter:
    """Pure-Python Adapter for tests. Records every invoke call.

    Mirrors ``tests/test_orchestrator.py``'s FakeAdapter rather than
    importing it so this test file is independently runnable in
    isolation (``pytest tests/test_cli.py -x`` works without
    ``tests/test_orchestrator.py`` being collected).
    """

    def __init__(
        self,
        name: str,
        *,
        canned_output: str = "ok",
        raise_exc: Exception | None = None,
    ) -> None:
        self.name: str = name
        self.canned_output: str = canned_output
        self.raise_exc: Exception | None = raise_exc
        self.calls: list[tuple[str, int]] = []

    def invoke(self, prompt: str, timeout: int) -> str:
        self.calls.append((prompt, timeout))
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.canned_output


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_MINIMAL_YAML = """\
agents:
  - name: Alpha
    role: tester
    adapter: claude
    system_prompt: be helpful
  - name: Beta
    role: tester
    adapter: gemini
    system_prompt: be helpful

max_turns: 4
stop_keywords:
  - AGREED
"""


def _make_yaml(tmp_path: Path, *, body: str | None = None) -> Path:
    """Write a minimal valid ultra-claude.yaml to ``tmp_path`` and return its path."""
    text = body if body is not None else _MINIMAL_YAML
    cfg = tmp_path / "ultra-claude.yaml"
    cfg.write_text(text, encoding="utf-8", newline="\n")
    return cfg


# ---------------------------------------------------------------------------
# CLI-01: --version
# ---------------------------------------------------------------------------


def test_version_flag_prints_version_and_exits_zero() -> None:
    """CLI-01: ``ultra-claude --version`` prints __version__ and exits 0."""
    from ultra_claude import __version__

    runner = CliRunner()
    result = runner.invoke(main, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.output


# ---------------------------------------------------------------------------
# CLI-02: --help
# ---------------------------------------------------------------------------


def test_help_flag_lists_subcommands_and_exits_zero() -> None:
    """CLI-02: ``ultra-claude --help`` shows ``run`` and ``doctor``, exit 0."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "run" in result.output
    assert "doctor" in result.output
    assert "Commands" in result.output or "commands" in result.output.lower()


# ---------------------------------------------------------------------------
# CLI-06 + CLI-07: --inline + --dry-run validates without invoking adapters
# ---------------------------------------------------------------------------


def test_run_with_inline_task_dry_run_validates_and_exits_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI-06 + CLI-07: ``--inline ... --dry-run`` works without a real adapter."""
    cfg = _make_yaml(tmp_path)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["run", "--config", str(cfg), "--inline", "do the thing", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert "Turn 1:" in result.output
    assert "do the thing" in result.output


# ---------------------------------------------------------------------------
# CLI-05 + PRE-01: --preset debate works without a local YAML
# ---------------------------------------------------------------------------


def test_run_with_preset_debate_loads_bundled_yaml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI-05 + PRE-01: ``--preset debate`` works in any cwd."""
    monkeypatch.chdir(tmp_path)  # NO ultra-claude.yaml in cwd

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["run", "--preset", "debate", "--inline", "test task", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    # Plan 08-01 ships exactly Architect (claude), Critic (gemini), Implementer (codex):
    assert "Architect" in result.output
    assert "Critic" in result.output
    assert "Implementer" in result.output
    assert "claude" in result.output
    assert "gemini" in result.output
    assert "codex" in result.output


# ---------------------------------------------------------------------------
# CLI-04: --config <path>
# ---------------------------------------------------------------------------


def test_run_with_config_path_overrides_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI-04: ``--config <path>`` loads from the given file."""
    custom_cfg = tmp_path / "custom-config.yaml"
    custom_cfg.write_text(_MINIMAL_YAML, encoding="utf-8", newline="\n")
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["run", "--config", str(custom_cfg), "--inline", "test", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert "Turn 1:" in result.output


# ---------------------------------------------------------------------------
# CLI-07: dry-run prints turn order
# ---------------------------------------------------------------------------


def test_run_dry_run_outputs_full_turn_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI-07: dry-run prints planned turn order, never invokes adapters."""
    cfg = _make_yaml(tmp_path)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["run", "--config", str(cfg), "--inline", "test", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    # _MINIMAL_YAML has max_turns=4, 2 agents -> turn order Alpha/Beta/Alpha/Beta
    for turn_no in (1, 2, 3, 4):
        assert f"Turn {turn_no}:" in result.output


# ---------------------------------------------------------------------------
# CLI-09: doctor command
# ---------------------------------------------------------------------------


def test_doctor_command_prints_status_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI-09: doctor prints status table for all 3 CLIs and exits 0.

    Mocks ``shutil.which`` and ``subprocess.run`` so the probe never
    launches a real process. The fake_run function additionally
    asserts that the safe-contract kwargs (CLAUDE.md Critical
    Constraint #1) are present on every call -- defense-in-depth
    alongside the TST-05 lint test.
    """

    def fake_which(cmd: str) -> str | None:
        return f"/fake/bin/{cmd}" if cmd in ("claude", "gemini", "codex") else None

    class _FakeCompleted:
        def __init__(self, *, stdout: str, stderr: str, returncode: int) -> None:
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    def fake_run(*args: Any, **kwargs: Any) -> _FakeCompleted:
        # Validate the safe-contract kwargs (Critical Constraint #1).
        # If cli.py's doctor probe is ever changed to drop these, this
        # test catches it (defense-in-depth alongside TST-05 lint).
        assert kwargs.get("text") is True
        assert kwargs.get("encoding") == "utf-8"
        assert kwargs.get("errors") == "replace"
        assert kwargs.get("shell", False) is False
        assert "timeout" in kwargs
        return _FakeCompleted(stdout="claude version 1.2.3", stderr="", returncode=0)

    monkeypatch.setattr(cli_module.shutil, "which", fake_which)
    monkeypatch.setattr(cli_module.subprocess, "run", fake_run)

    runner = CliRunner()
    result = runner.invoke(main, ["doctor"])

    assert result.exit_code == 0, result.output
    assert "CLI" in result.output
    assert "On PATH" in result.output
    assert "Auth" in result.output
    assert "Notes" in result.output
    for cli_name in ("claude", "gemini", "codex"):
        assert cli_name in result.output


# ---------------------------------------------------------------------------
# CLI-10: ConfigError -> exit 2
# ---------------------------------------------------------------------------


def test_config_error_exits_with_code_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI-10: invalid YAML -> exit code 2."""
    bad_cfg = tmp_path / "bad.yaml"
    # Intentionally malformed YAML (string list entry where a mapping is required)
    bad_cfg.write_text(
        "agents:\n  - this is not a valid agent entry\nmax_turns: 4\n",
        encoding="utf-8",
        newline="\n",
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["run", "--config", str(bad_cfg), "--inline", "test", "--dry-run"],
    )

    assert result.exit_code == 2, f"expected 2, got {result.exit_code}: {result.output}"


# ---------------------------------------------------------------------------
# CLI-10: AdapterError + abort_on_error -> exit 1
# ---------------------------------------------------------------------------


def test_adapter_error_with_abort_on_error_exits_with_code_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI-10: AdapterError raised by orchestrator -> exit code 1."""
    cfg = _make_yaml(tmp_path)
    monkeypatch.chdir(tmp_path)

    # Inject a factory that returns a FakeAdapter raising on every invoke.
    from ultra_claude.exceptions import AdapterError

    def fake_factory(adapter_kind: str) -> FakeAdapter:
        return FakeAdapter(
            adapter_kind,
            raise_exc=AdapterError("simulated CLI failure"),
        )

    monkeypatch.setattr(orch_module, "get_adapter", fake_factory)

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "run",
            "--config",
            str(cfg),
            "--inline",
            "test",
            "--abort-on-error",
            "--output",
            str(tmp_path / "out.md"),
        ],
    )

    assert result.exit_code == 1, f"expected 1, got {result.exit_code}: {result.output}"


# ---------------------------------------------------------------------------
# CLI-03 + CLI-08: end-to-end with FakeAdapter via injection seam
# ---------------------------------------------------------------------------


def test_run_end_to_end_with_fake_adapters_writes_transcript(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI-03 + CLI-08: full pipeline produces a transcript file at --output path."""
    cfg = _make_yaml(tmp_path)
    monkeypatch.chdir(tmp_path)

    output = tmp_path / "transcript.md"

    # Inject FakeAdapters so no real CLI is launched.
    fakes: dict[str, FakeAdapter] = {}

    def fake_factory(adapter_kind: str) -> FakeAdapter:
        fa = fakes.get(adapter_kind)
        if fa is None:
            fa = FakeAdapter(adapter_kind, canned_output=f"AGREED from {adapter_kind}")
            fakes[adapter_kind] = fa
        return fa

    monkeypatch.setattr(orch_module, "get_adapter", fake_factory)

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "run",
            "--config",
            str(cfg),
            "--inline",
            "do the thing",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert output.exists(), f"transcript not written at {output}"
    transcript_text = output.read_text(encoding="utf-8")
    assert "Alpha" in transcript_text
    assert "Beta" in transcript_text
    # CLI-03: stdout's last meaningful line is the transcript path.
    assert str(output) in result.output


# ---------------------------------------------------------------------------
# CLI-11: stdout-clean discipline -- only the transcript path on success
# ---------------------------------------------------------------------------


def test_stdout_only_contains_transcript_path_on_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CLI-11: stdout has only the transcript path; progress goes to stderr/log.

    click 8.3+ splits ``result.stdout`` from ``result.stderr`` by
    default (no ``mix_stderr=False`` parameter required -- it was
    removed in click 8.3 in favor of always-split semantics). This
    test asserts the stdout-only contract by reading
    ``result.stdout`` directly.
    """
    cfg = _make_yaml(tmp_path)
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "transcript.md"

    def fake_factory(adapter_kind: str) -> FakeAdapter:
        return FakeAdapter(adapter_kind, canned_output=f"AGREED from {adapter_kind}")

    monkeypatch.setattr(orch_module, "get_adapter", fake_factory)

    runner = CliRunner()
    with caplog.at_level(logging.INFO, logger="ultra_claude.orchestrator"):
        result = runner.invoke(
            main,
            [
                "run",
                "--config",
                str(cfg),
                "--inline",
                "test",
                "--output",
                str(output),
            ],
        )

    assert result.exit_code == 0, result.stderr
    # Stdout MUST contain only the transcript path. Allow trailing newline.
    assert result.stdout.strip() == str(output)
    # Stderr MAY contain log progress (if stderr was a tty), but must
    # NEVER contain the transcript path -- that is a stdout-only signal.
    assert str(output) not in result.stderr
