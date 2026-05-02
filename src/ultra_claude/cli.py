"""Click-based CLI for ultra-claude.

This module is the user-facing entry point declared in
``pyproject.toml [project.scripts]`` (see plan 08-01). It exposes a single
click group ``main`` with two subcommands -- ``run`` and ``doctor`` --
plus a top-level ``--version`` flag.

Phase 8 success criteria (CLI-01..CLI-11, see ROADMAP and 08-CONTEXT.md):

1. ``ultra-claude --version`` prints ``__version__`` and exits 0 (CLI-01).
2. ``ultra-claude --help`` prints click-generated help with subcommands
   ``run`` and ``doctor`` and exits 0 (CLI-02).
3. ``ultra-claude run TASK_FILE`` (with ``./ultra-claude.yaml`` present)
   loads config, runs the orchestrator, and prints the transcript path on
   stdout. Supports ``--config``, ``--preset``, ``--inline``, ``--dry-run``,
   ``--output`` (CLI-03..CLI-08).
4. ``ultra-claude doctor`` probes claude/gemini/codex on PATH and login
   state, prints a per-CLI status table, exits 0 (CLI-09).
5. Exit codes: 0 success, 1 runtime/adapter error, 2 config validation
   error (CLI-10).
6. Live progress to stderr only when stdout is a TTY (CLI-11).

Architecture decisions (locked in 08-CONTEXT.md):
* Click framework (already pinned >=8.3.3 in pyproject.toml).
* Single ``main`` click group; subcommands are siblings.
* No colorized output for v1 -- keep stdout clean for piping.
* No ``--verbose`` flag in v1 (deferred).
* Doctor probes use a fast ``--version`` style health check, not a real
  prompt -- doctor reports state, doctor doesn't pay subscription tokens.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

import click

from . import __version__
from .config import RoundtableConfig, load_config
from .exceptions import AdapterError, ConfigError
from .orchestrator import run as orchestrate

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = ["main", "run", "doctor"]  # noqa: RUF022


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG_PATH = Path("ultra-claude.yaml")
"""Where ``ultra-claude run`` looks for config when ``--config`` is omitted."""

_PRESET_PACKAGE = "ultra_claude.presets"
"""Importlib resource path for bundled preset YAML files (plan 08-01)."""

_DOCTOR_PROBE_TIMEOUT_SECONDS = 5
"""Per-CLI doctor probe budget. Short -- the probe is ``--version``-style."""

_PROBE_CLIS: tuple[str, ...] = ("claude", "gemini", "codex")
"""The three CLIs the doctor command checks."""


# ---------------------------------------------------------------------------
# Logging setup (CLI-11: TTY-aware progress)
# ---------------------------------------------------------------------------


def _configure_logging() -> None:
    """Wire ``ultra_claude.orchestrator`` log records to stderr -- when interactive.

    Per CLI-11, live progress should reach the user only when running
    interactively. When stdout (or stderr) is piped/redirected, raise the
    floor to WARNING so the orchestrator's per-turn INFO records are
    suppressed.

    The orchestrator (Phase 6) already attaches a default ``StreamHandler``
    to ``ultra_claude.orchestrator`` if one isn't installed (idempotent
    ``hasHandlers`` check). This function tunes the LEVEL only.
    """
    logger = logging.getLogger("ultra_claude.orchestrator")
    if sys.stdout.isatty() and sys.stderr.isatty():
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Preset loading (CLI-05 / PRE-01)
# ---------------------------------------------------------------------------


def _load_preset(name: str) -> RoundtableConfig:
    """Load a bundled preset by name (e.g. ``"debate"``).

    Uses ``importlib.resources`` so the preset works in editable installs,
    wheels, and zipapps alike. Raises :class:`ConfigError` (with a CLI-10
    exit-code-2-friendly message) when the preset is unknown.
    """
    try:
        resource = files(_PRESET_PACKAGE).joinpath(f"{name}.yaml")
        if not resource.is_file():
            raise ConfigError(
                f"unknown preset {name!r} (no presets/{name}.yaml in package data)"
            )
        text = resource.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise ConfigError(f"unknown preset {name!r}: {err}") from err
    except ModuleNotFoundError as err:
        raise ConfigError(
            f"preset package {_PRESET_PACKAGE!r} not installed"
        ) from err
    return RoundtableConfig.from_yaml_string(text)


# ---------------------------------------------------------------------------
# Task source resolution (CLI-03 / CLI-06)
# ---------------------------------------------------------------------------


def _resolve_task(task_file: Path | None, inline: str | None) -> str:
    """Pick the task string from the CLI's three input modes.

    Exactly one of ``task_file`` or ``inline`` must be set; the caller has
    already validated that. Reads the file as UTF-8 and returns the trimmed
    contents, or returns the inline string as-is.
    """
    if inline is not None:
        return inline
    if task_file is not None:
        try:
            return task_file.read_text(encoding="utf-8")
        except OSError as err:
            raise click.UsageError(f"could not read task file {task_file}: {err}") from err
    raise click.UsageError("internal error: neither task_file nor inline supplied")


# ---------------------------------------------------------------------------
# Dry-run output (CLI-07)
# ---------------------------------------------------------------------------


def _print_dry_run_plan(config: RoundtableConfig, task: str) -> None:
    """Print the planned turn order to stdout. Never invokes an adapter.

    Format::

        Planned roundtable (max_turns=N, stop_keywords=[...]):
          Turn 1: <Agent> (<adapter>) - <role>
          Turn 2: <Agent> (<adapter>) - <role>
          ...
        Task: <first 80 chars>...

    The output is plain text (no colors, no progress markers) so it pipes
    cleanly into a file. Uses ``click.echo`` so output is captured by
    click's ``CliRunner`` in tests.
    """
    n_agents = len(config.agents)
    click.echo(
        f"Planned roundtable (max_turns={config.max_turns}, "
        f"stop_keywords={config.stop_keywords}):"
    )
    for turn_idx in range(1, config.max_turns + 1):
        agent = config.agents[(turn_idx - 1) % n_agents]
        click.echo(
            f"  Turn {turn_idx}: {agent.name} ({agent.adapter}) - {agent.role}"
        )
    snippet = task.strip().splitlines()[0] if task.strip() else "<empty>"
    if len(snippet) > 80:
        snippet = snippet[:77] + "..."
    click.echo(f"Task: {snippet}")


# ---------------------------------------------------------------------------
# Doctor probe (CLI-09)
# ---------------------------------------------------------------------------


def _probe_cli(cli_name: str) -> tuple[str, str, str]:
    """Probe a single CLI. Returns ``(on_path, auth, notes)`` strings.

    Strategy:
        1. ``shutil.which`` for PATH check -- fast, no subprocess.
        2. If on PATH, run ``<cli> --version`` (5s timeout) as a cheap
           health probe. Success -> AUTH=PASS. Failure with non-zero exit
           or known auth-error markers -> AUTH=FAIL. Anything else
           (timeout, oddball error) -> AUTH=UNKNOWN.

    Per CLAUDE.md Critical Constraint #1 the ``subprocess.run`` call MUST
    set ``text=True``, ``encoding="utf-8"``, ``errors="replace"``, list-form
    argv, ``shell=False``, mandatory ``timeout``. The TST-05 lint will
    fire if any of those is missing.

    This function does NOT pay tokens to the underlying LLM -- ``--version``
    is a local-only operation on all three CLIs.
    """
    path = shutil.which(cli_name)
    if path is None:
        return ("FAIL", "UNKNOWN", "not on PATH")

    try:
        result = subprocess.run(
            [cli_name, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=_DOCTOR_PROBE_TIMEOUT_SECONDS,
            check=False,
            input="",
        )
    except subprocess.TimeoutExpired:
        return ("PASS", "UNKNOWN", f"--version timed out after {_DOCTOR_PROBE_TIMEOUT_SECONDS}s")
    except OSError as err:
        return ("PASS", "UNKNOWN", f"OSError: {err}")

    if result.returncode == 0 and result.stdout.strip():
        version_line = result.stdout.strip().splitlines()[0]
        return ("PASS", "PASS", f"version: {version_line}"[:60])
    if result.returncode == 0:
        # rc=0 with empty stdout matches the codex empty-stdout bug shape;
        # report it but don't fail the run -- doctor is a status report.
        return ("PASS", "UNKNOWN", "empty --version output")
    combined = (result.stdout + result.stderr).lower()
    if any(
        marker in combined
        for marker in ("not authenticated", "please log in", "login required", "auth")
    ):
        return ("PASS", "FAIL", f"auth marker in output (rc={result.returncode})")
    return ("PASS", "UNKNOWN", f"--version exited rc={result.returncode}")


def _format_doctor_table(rows: Iterable[tuple[str, str, str, str]]) -> str:
    """Render the doctor command's status table as a single string.

    Columns: CLI | On PATH | Auth | Notes. Plain text, no Unicode box
    drawing -- ASCII-only per CLAUDE.md Critical Constraint #6.
    """
    headers = ("CLI", "On PATH", "Auth", "Notes")
    rows_list = list(rows)
    cols = list(zip(headers, *rows_list, strict=False))
    widths = [max(len(str(cell)) for cell in col) for col in cols]
    lines: list[str] = []
    sep = "  "
    lines.append(sep.join(h.ljust(w) for h, w in zip(headers, widths, strict=False)))
    lines.append(sep.join("-" * w for w in widths))
    for row in rows_list:
        lines.append(sep.join(str(c).ljust(w) for c, w in zip(row, widths, strict=False)))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Click commands
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(version=__version__, prog_name="ultra-claude")
def main() -> None:
    """ultra-claude: orchestrate Claude Code, Gemini CLI, and Codex CLI in a multi-agent debate."""


@main.command("run")
@click.argument("task_file", type=click.Path(exists=True, path_type=Path), required=False)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to ultra-claude.yaml (default: ./ultra-claude.yaml).",
)
@click.option(
    "--preset",
    "preset_name",
    type=str,
    default=None,
    help="Load a bundled preset (e.g. --preset debate) instead of a config file.",
)
@click.option(
    "--inline",
    "inline_task",
    type=str,
    default=None,
    help="Task as a string instead of a file path.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Validate config + print planned turn order without invoking adapters.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Override the transcript output path.",
)
@click.option(
    "--abort-on-error",
    is_flag=True,
    default=False,
    help="Abort on the first adapter error (overrides config.abort_on_error).",
)
@click.pass_context
def run(
    ctx: click.Context,
    task_file: Path | None,
    config_path: Path | None,
    preset_name: str | None,
    inline_task: str | None,
    dry_run: bool,
    output_path: Path | None,
    abort_on_error: bool,
) -> None:
    """Run a roundtable debate. Prints the transcript path on success."""
    _configure_logging()

    # --config and --preset are mutually exclusive (08-CONTEXT.md decision).
    if config_path is not None and preset_name is not None:
        raise click.UsageError("--config and --preset are mutually exclusive")

    # Must supply at least one task source: TASK_FILE, --inline, or be dry-run
    # with config-supplied task. The dry-run-without-task path is allowed only
    # if config.task is non-None (validated after config loads, below).
    if task_file is not None and inline_task is not None:
        raise click.UsageError("supply either TASK_FILE or --inline, not both")

    # ------------------------------------------------------------------
    # Load config (CLI-03, CLI-04, CLI-05). ConfigError -> exit 2 (CLI-10).
    # ------------------------------------------------------------------
    try:
        if preset_name is not None:
            config = _load_preset(preset_name)
        else:
            cfg_path = config_path if config_path is not None else _DEFAULT_CONFIG_PATH
            config = load_config(cfg_path)
    except ConfigError as err:
        click.echo(str(err), err=True)
        ctx.exit(2)
        return  # mypy needs this; ctx.exit raises SystemExit

    # ------------------------------------------------------------------
    # Resolve task. Order: --inline > TASK_FILE > config.task (last).
    # ------------------------------------------------------------------
    if inline_task is None and task_file is None:
        if config.task is None:
            raise click.UsageError(
                "no task supplied: pass TASK_FILE, --inline, or set 'task:' in config"
            )
        task = config.task
    else:
        task = _resolve_task(task_file, inline_task)

    # ------------------------------------------------------------------
    # --abort-on-error overrides the config setting when set on CLI.
    # ------------------------------------------------------------------
    if abort_on_error:
        config = config.model_copy(update={"abort_on_error": True})

    # ------------------------------------------------------------------
    # CLI-07: dry-run validates + prints turn plan + exits 0. No adapters.
    # ------------------------------------------------------------------
    if dry_run:
        _print_dry_run_plan(config, task)
        ctx.exit(0)
        return

    # ------------------------------------------------------------------
    # Real run. AdapterError (and AdapterAuthError subclass) -> exit 1.
    # The orchestrator already handles per-turn errors internally; only
    # `abort_on_error: true` causes one to escape to here.
    # ------------------------------------------------------------------
    try:
        transcript_path = orchestrate(
            config,
            task,
            transcript_path=output_path,
        )
    except AdapterError as err:
        click.echo(f"adapter error: {err}", err=True)
        ctx.exit(1)
        return

    # CLI-03: success -> print transcript path on stdout, exit 0.
    click.echo(str(transcript_path))


@main.command("doctor")
def doctor() -> None:
    """Probe claude/gemini/codex on PATH and login state. Exits 0 even if some fail."""
    rows: list[tuple[str, str, str, str]] = []
    for cli_name in _PROBE_CLIS:
        on_path, auth, notes = _probe_cli(cli_name)
        rows.append((cli_name, on_path, auth, notes))
    click.echo(_format_doctor_table(rows))
