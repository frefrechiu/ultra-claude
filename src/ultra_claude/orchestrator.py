"""Roundtable orchestrator -- the run(config, task) -> Path entry point.

Composes :class:`~ultra_claude.adapters.base.Adapter` (Phase 4) +
:class:`~ultra_claude.transcript.Transcript` (Phase 3) +
:class:`~ultra_claude.stop_conditions.AnyOf` /
:class:`~ultra_claude.stop_conditions.MaxTurns` /
:class:`~ultra_claude.stop_conditions.Keyword` (Phase 5) into a single
function that drives the round-robin debate end-to-end.

Phase 6 success criteria (ROADMAP / 06-CONTEXT.md):

1. ``run(config, task)`` returns a :class:`pathlib.Path` to the completed
   transcript file. With ``max_turns=6`` and 3 agents, the file contains 6
   turns in declared round-robin order. (ORC-01, ORC-02)
2. Each turn's prompt is::

       # Task
       {task}

       # Your role
       {agent.system_prompt}

       {transcript_so_far}

       # Reminder of the task
       {task}

       Respond now as {agent.name} ({agent.role}). Stay focused on the task above.

   The trailing GOAL ANCHOR mitigates problem drift (Pitfall #6, ORC-03).
3. After every ``transcript.append_turn`` the orchestrator calls
   ``composite.check(transcript)``; on True it logs the reason and returns
   the transcript path. (ORC-04)
4. ``AdapterError`` (which covers ``AdapterAuthError`` via subclass) is
   logged to stderr; a placeholder turn ``[adapter error: <exc>]`` is
   appended; the run continues UNLESS ``config.abort_on_error`` is True
   (then the exception is re-raised). (ORC-05)
5. Progress is logged via ``logging.getLogger("ultra_claude.orchestrator")``
   to a stderr ``StreamHandler``; stdout is reserved for the CLI to print
   the final transcript path. ``run()`` itself never touches stdout, so
   ``capsys.readouterr().out`` is empty after a test run. (ORC-06)

Architecture note (per CLAUDE.md): this is a function, not a class. The
v3 case for parallel speakers would justify promotion, but v1 has none.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from pathlib import Path

from .adapters import Adapter
from .config import AgentConfig, RoundtableConfig
from .exceptions import AdapterError
from .registry import get_adapter
from .stop_conditions import AnyOf, Keyword, MaxTurns
from .transcript import Transcript

__all__ = ["run"]


# ---------------------------------------------------------------------------
# Defaults (06-CONTEXT.md Deferred: AgentConfig.timeout is a v2 idea)
# ---------------------------------------------------------------------------

_DEFAULT_TRANSCRIPT_PATH: Path = Path("ultra-claude-transcript.md")
"""Where to write the transcript when the caller does not specify a path.

Lives in the cwd so ``ultra-claude run task.md`` produces a file the user
can `tail -f` immediately. The CLI in Phase 8 will pass an explicit path.
"""

_DEFAULT_TIMEOUT_SECONDS: int = 120
"""Per-adapter-invocation timeout cap.

Hardcoded for v1 because ``AgentConfig`` does not expose a per-agent
``timeout`` field (06-CONTEXT.md Deferred lists this as a v2 idea).
The mixin's ``_run_subprocess`` enforces this via ``communicate(timeout=)``
and falls back to a process-tree kill if the CLI hangs (Pitfall #5).
"""


# ---------------------------------------------------------------------------
# Logger setup -- idempotent so Phase 8's CLI can install its own handler
# without producing double-output.
# ---------------------------------------------------------------------------

_logger = logging.getLogger("ultra_claude.orchestrator")


def _ensure_default_handler() -> None:
    """Attach a stderr StreamHandler to ``_logger`` IFF it has none.

    The CLI layer (Phase 8) is allowed to set up its own handlers before
    calling ``run()``. If we always added a handler we would emit each line
    twice. The ``hasHandlers`` check (which walks up the logger hierarchy)
    is the standard idiom for "set up logging only if nothing else has".
    """

    if _logger.hasHandlers():
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Prompt assembly (ORC-03 / Pitfall #6 -- goal-anchor re-injection)
# ---------------------------------------------------------------------------


def _build_prompt(
    *, task: str, agent: AgentConfig, transcript_so_far: str
) -> str:
    """Assemble one turn's prompt per the 06-CONTEXT.md locked order.

    Order (locked):
        1. ``# Task`` heading + verbatim ``task``
        2. ``# Your role`` heading + ``agent.system_prompt``
        3. The full transcript-so-far markdown (``""`` on turn 1)
        4. GOAL ANCHOR footer: ``# Reminder of the task`` + ``task`` again,
           then ``Respond now as {name} ({role}). Stay focused on the task
           above.``

    The GOAL ANCHOR at the END is the Pitfall #6 mitigation: LLMs anchor
    on the most recent context, so re-stating the task last fights drift
    far more effectively than only stating it at the top.
    """

    # transcript_so_far may be "" on turn 1 (the file was just created and
    # has no content yet, OR doesn't exist at all). We still emit a blank
    # line between sections so the resulting prompt is human-readable.
    sections: list[str] = [
        f"# Task\n\n{task}",
        f"# Your role\n\n{agent.system_prompt}",
    ]
    if transcript_so_far.strip():
        sections.append(transcript_so_far.rstrip())
    sections.append(
        f"# Reminder of the task\n\n{task}\n\n"
        f"Respond now as {agent.name} ({agent.role}). "
        f"Stay focused on the task above."
    )
    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Public entry point (ORC-01)
# ---------------------------------------------------------------------------


def run(
    config: RoundtableConfig,
    task: str,
    *,
    transcript_path: Path | None = None,
    adapter_factory: Callable[[str], Adapter] | None = None,
) -> Path:
    """Drive a roundtable debate to completion. Returns the transcript path.

    Args:
        config: Validated :class:`RoundtableConfig` (typically from
            :func:`~ultra_claude.config.load_config`).
        task: The task statement (a string; the caller is responsible for
            reading it from a file if needed).
        transcript_path: Optional override for where to write the transcript.
            Defaults to ``./ultra-claude-transcript.md``. Parent directory
            is auto-created.
        adapter_factory: Optional injection seam for tests. When supplied,
            replaces the production :func:`~ultra_claude.registry.get_adapter`.
            Production code should leave this as ``None``.

    Returns:
        :class:`pathlib.Path` to the completed transcript markdown file.

    Raises:
        AdapterError: Only when ``config.abort_on_error`` is True AND an
            adapter raised. Otherwise adapter failures become placeholder
            turns and the run continues.
    """

    _ensure_default_handler()

    # ------------------------------------------------------------------
    # Resolve transcript path and ensure its parent directory exists.
    # Transcript.__init__ raises OSError if parent is missing (D-11).
    # ------------------------------------------------------------------
    if transcript_path is None:
        transcript_path = (
            config.transcript_path
            if config.transcript_path is not None
            else _DEFAULT_TRANSCRIPT_PATH
        )
    transcript_path = Path(transcript_path)
    transcript_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Build per-agent adapter instances ONCE up front. If a factory was
    # supplied (tests), use it; otherwise fall through to the registry.
    # Failing here (e.g. NotImplementedError for gemini/codex in Phase 6)
    # halts the run BEFORE any transcript is written -- the caller sees
    # a clean error, not a partially-debated transcript.
    # ------------------------------------------------------------------
    factory: Callable[[str], Adapter] = (
        adapter_factory if adapter_factory is not None else get_adapter
    )
    adapters: list[Adapter] = [factory(agent.adapter) for agent in config.agents]

    # ------------------------------------------------------------------
    # Compose stop conditions (STP-05 / ORC-04). AnyOf short-circuits.
    # ------------------------------------------------------------------
    composite = AnyOf(
        [
            MaxTurns(config.max_turns),
            Keyword(config.stop_keywords),
        ]
    )

    # ------------------------------------------------------------------
    # Open the transcript and start the loop. The header_task argument
    # is what the markdown file's "# Transcript: <task>" heading shows.
    # ------------------------------------------------------------------
    transcript = Transcript(transcript_path, header_task=task)

    _logger.info(
        "starting roundtable: %d agents, max_turns=%d, transcript=%s",
        len(config.agents),
        config.max_turns,
        transcript_path,
    )

    n_agents = len(config.agents)
    for turn_idx in range(1, config.max_turns + 1):
        agent_cfg = config.agents[(turn_idx - 1) % n_agents]
        adapter = adapters[(turn_idx - 1) % n_agents]

        prompt = _build_prompt(
            task=task,
            agent=agent_cfg,
            transcript_so_far=transcript.markdown_text(),
        )

        _logger.info("turn %d starting (agent=%s)", turn_idx, agent_cfg.name)
        _logger.debug(
            "turn %d prompt has %d chars (agent=%s, role=%s)",
            turn_idx,
            len(prompt),
            agent_cfg.name,
            agent_cfg.role,
        )

        # ----------------------------------------------------------------
        # Continue-on-error guard (ORC-05). AdapterAuthError is a subclass
        # of AdapterError, so a single except clause covers both.
        # ----------------------------------------------------------------
        try:
            output = adapter.invoke(prompt, _DEFAULT_TIMEOUT_SECONDS)
        except AdapterError as exc:
            _logger.exception(
                "turn %d: agent %s failed",
                turn_idx,
                agent_cfg.name,
            )
            if config.abort_on_error:
                raise
            output = f"[adapter error: {exc}]"
            transcript.append_turn(
                turn=turn_idx,
                agent=agent_cfg.name,
                role=agent_cfg.role,
                prompt=prompt,
                output=output,
            )
        else:
            transcript.append_turn(
                turn=turn_idx,
                agent=agent_cfg.name,
                role=agent_cfg.role,
                prompt=prompt,
                output=output,
            )
            _logger.info(
                "turn %d completed (agent=%s, %d chars output)",
                turn_idx,
                agent_cfg.name,
                len(output),
            )

        # ----------------------------------------------------------------
        # Stop-condition probe AFTER every turn (ORC-04). The composite
        # short-circuits, so MaxTurns fires cheaply on every call and
        # Keyword only runs when MaxTurns hasn't fired yet.
        # ----------------------------------------------------------------
        if composite.check(transcript):
            _logger.info(
                "stopped after turn %d (composite stop condition matched)",
                turn_idx,
            )
            break

    return transcript.markdown_path
