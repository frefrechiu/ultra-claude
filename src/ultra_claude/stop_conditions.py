"""Composable stop strategies for the ultra-claude orchestrator.

Three concrete strategies plus a runtime-checkable Protocol so third-party
strategies do not need to inherit anything:

* :class:`Keyword` -- anchored multiline regex match plus an
  *unanimity-window* (default ``n=2`` last turns, ``m=2`` distinct agents).
  Mitigates Pitfall #4 (sycophancy false-positive): naive
  ``"AGREED" in output`` returns true for ``"I am NOT going to say AGREED"``.
  An anchored ``^AGREED\\s*$`` (multiline) matches only a *line* that IS the
  keyword; the unanimity-window prevents an agent from voting itself off
  the island.
* :class:`MaxTurns` -- halts when ``len(transcript) >= max_turns``. Backs
  CFG-04 ``max_turns`` default of 12 and ROADMAP success criterion 4.
* :class:`AnyOf` -- composite that short-circuits on the first wrapped
  condition that matches. The orchestrator wires ``Keyword(stop_keywords)``
  and ``MaxTurns(max_turns)`` through ``AnyOf`` by default (STP-05).

The :class:`StopCondition` Protocol is :func:`~typing.runtime_checkable`
so ``isinstance(obj, StopCondition)`` works; this matches the shape of
:class:`ultra_claude.adapters.base.Adapter` and lets the Phase 6
orchestrator probe wired conditions without forcing inheritance.

Requirements coverage: STP-01, STP-02, STP-03, STP-04, STP-05.
"""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from .transcript import Transcript

__all__ = [  # noqa: RUF022 -- chronological-by-introduction (Protocol first, then strategies in introduction order) to match adapters/__init__.py and exceptions.py conventions
    "StopCondition",
    "Keyword",
    "MaxTurns",
    "AnyOf",
]


# ---------------------------------------------------------------------------
# Public Protocol (STP-01)
# ---------------------------------------------------------------------------


@runtime_checkable
class StopCondition(Protocol):
    """Structural contract for a stop strategy.

    Any object with a ``check(transcript: Transcript) -> bool`` method
    satisfies this Protocol; third-party strategies do NOT need to inherit.
    The :func:`~typing.runtime_checkable` decorator makes
    ``isinstance(obj, StopCondition)`` work at runtime, mirroring the
    pattern used by :class:`ultra_claude.adapters.base.Adapter`.
    """

    def check(self, transcript: Transcript) -> bool: ...


# ---------------------------------------------------------------------------
# Keyword stop condition (STP-02, STP-03 -- the Pitfall #4 mitigation)
# ---------------------------------------------------------------------------


class Keyword:
    """Stop when a configured keyword appears as a *whole line* of agent
    output, in the last ``n`` turns, from at least ``m`` distinct agents.

    Each keyword is pre-compiled to ``re.compile(rf"^{re.escape(kw)}\\s*$",
    re.MULTILINE)``:

    * ``re.escape`` lets keywords contain regex metacharacters (``.``, ``*``,
      etc.) without surprising users.
    * ``^...\\s*$`` with ``re.MULTILINE`` matches a line whose content IS
      the keyword (allowing trailing whitespace). Critically, this REJECTS
      ``"I am NOT going to say AGREED yet"`` -- the marker has prose on
      either side, so it is not a line on its own.
    * The recommended user pattern is a decision-block sentinel like
      ``## Decision\\nAGREED`` (the ``AGREED`` line on its own); however,
      ``Keyword`` only requires the keyword line itself to be present.

    The *unanimity-window* (``n``, ``m``) is the second half of the
    Pitfall #4 mitigation. With defaults ``n=2, m=2`` a single agent saying
    AGREED twice in a row returns False (1 distinct agent < m=2), but two
    different agents both ending their last turn with AGREED returns True.

    Args:
        keywords: List of literal strings to match. At least one keyword
            should be supplied; an empty list will never fire.
        n: Number of trailing turns to inspect. Defaults to 2 (STP-03).
        m: Minimum number of distinct agents whose matching turns must
            appear in those last ``n`` turns. Defaults to 2 (STP-03).
    """

    def __init__(
        self,
        keywords: list[str],
        *,
        n: int = 2,
        m: int = 2,
    ) -> None:
        self._keywords: list[str] = list(keywords)
        self._n: int = n
        self._m: int = m
        # Pre-compile once at construction; orchestrator will call check()
        # after every turn so this matters for hot paths.
        self._patterns: list[re.Pattern[str]] = [
            re.compile(rf"^{re.escape(kw)}\s*$", re.MULTILINE)
            for kw in self._keywords
        ]

    def check(self, transcript: Transcript) -> bool:
        # Empty transcripts can never satisfy a unanimity-window of m>=1.
        turns = transcript.read_turns()
        if not turns or self._m <= 0 or self._n <= 0 or not self._patterns:
            return False

        window = turns[-self._n :]
        matching_agents: set[str] = set()
        for record in window:
            for pattern in self._patterns:
                if pattern.search(record.output):
                    matching_agents.add(record.agent)
                    break  # one matching keyword is enough for this turn

        return len(matching_agents) >= self._m


# ---------------------------------------------------------------------------
# MaxTurns stop condition (STP-04)
# ---------------------------------------------------------------------------


class MaxTurns:
    """Stop when the transcript has reached ``max_turns`` records.

    Uses ``len(transcript)`` from :class:`Transcript.__len__`, which counts
    JSONL sidecar records (the canonical turn count). Returns True at the
    exact boundary: ``MaxTurns(12).check(transcript_with_12_turns)`` is True.

    Args:
        max_turns: Inclusive upper bound. Typically wired from
            :attr:`RoundtableConfig.max_turns` (default 12).
    """

    def __init__(self, max_turns: int) -> None:
        self._max_turns: int = max_turns

    def check(self, transcript: Transcript) -> bool:
        return len(transcript) >= self._max_turns


# ---------------------------------------------------------------------------
# AnyOf composite (STP-05)
# ---------------------------------------------------------------------------


class AnyOf:
    """Composite stop condition that fires when ANY wrapped condition fires.

    Uses Python's lazy :func:`any` with a generator expression so wrapped
    conditions are only evaluated up to the first match (short-circuit).

    The orchestrator wires the bundled conditions through ``AnyOf`` by
    default per STP-05::

        stop = AnyOf([
            MaxTurns(config.max_turns),
            Keyword(config.stop_keywords),
        ])

    Args:
        conditions: List of objects satisfying :class:`StopCondition`.
    """

    def __init__(self, conditions: list[StopCondition]) -> None:
        self._conditions: list[StopCondition] = list(conditions)

    def check(self, transcript: Transcript) -> bool:
        return any(c.check(transcript) for c in self._conditions)
