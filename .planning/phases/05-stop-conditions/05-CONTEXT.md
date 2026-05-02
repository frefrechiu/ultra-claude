# Phase 5: Stop Conditions - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

Three composable stop strategies — `Keyword` (anchored regex + unanimity-window), `MaxTurns`, `AnyOf` — so the orchestrator can terminate cleanly without false-positive consensus from sycophantic agents.

Scope:
- `src/ultra_claude/stop_conditions.py` — `StopCondition` Protocol + `Keyword` + `MaxTurns` + `AnyOf` classes
- `tests/test_stop_conditions.py` — covering all 4 success criteria (anchored regex, unanimity-window, MaxTurns equality, AnyOf short-circuit)

Out of scope: orchestrator wiring (Phase 6), CLI flag plumbing (Phase 8).

</domain>

<decisions>
## Implementation Decisions

### Locked from REQUIREMENTS.md (STP-01..STP-05) and CLAUDE.md Pitfall #4

- **`StopCondition` Protocol:**
  ```python
  @runtime_checkable
  class StopCondition(Protocol):
      def check(self, transcript: Transcript) -> bool: ...
  ```
  Consumes the `Transcript` from Phase 3. Returns `True` when the orchestrator should stop.

- **`Keyword`:**
  ```python
  class Keyword:
      def __init__(self, keywords: list[str], *, n: int = 2, m: int = 2) -> None: ...
      def check(self, transcript: Transcript) -> bool: ...
  ```
  - Compiles each keyword into an anchored multiline regex: `re.compile(rf"^{re.escape(kw)}\s*$", re.MULTILINE)` — the anchor defeats Pitfall #4 ("I am NOT going to say AGREED yet" doesn't match, but a line containing exactly `AGREED` does).
  - Decision-block sentinel preferred but not required — accepts the keyword on its own line as the canonical match. Recommended user pattern: `## Decision\nAGREED`. The regex matches `^AGREED$` with optional trailing whitespace.
  - **Unanimity-window:** Look at the last `n` turns (default 2). If those turns include matches from at least `m` distinct agents (default 2), return True. Otherwise False.
  - This means a single agent saying AGREED twice in a row does NOT stop the run. Two different agents saying AGREED in the last 2 turns DOES stop.

- **`MaxTurns`:**
  ```python
  class MaxTurns:
      def __init__(self, max_turns: int) -> None: ...
      def check(self, transcript: Transcript) -> bool:
          return len(transcript) >= self.max_turns
  ```
  Returns True exactly when transcript has reached `max_turns` turns. Uses `len(transcript)` from the `Transcript.__len__` method added in Phase 3.

- **`AnyOf`:**
  ```python
  class AnyOf:
      def __init__(self, conditions: list[StopCondition]) -> None: ...
      def check(self, transcript: Transcript) -> bool:
          return any(c.check(transcript) for c in self.conditions)
  ```
  Short-circuits — uses Python's `any(...)` which evaluates lazily.

### Module structure

```
src/ultra_claude/
├── ...existing
└── stop_conditions.py    # NEW
```

### Testing strategy

Test cases (mapping to success criteria):
1. `test_stop_condition_protocol_structural` — duck-typed `class FakeStop: def check(...)` passes `isinstance(_, StopCondition)`
2. `test_keyword_anchored_regex_rejects_substring` — transcript with turn output `"I am NOT going to say AGREED yet"` → `Keyword(["AGREED"]).check(transcript)` returns False
3. `test_keyword_unanimity_two_agents_two_turns` — transcript with the last 2 turns from 2 different agents both ending in `AGREED` → returns True
4. `test_keyword_single_agent_self_stop_blocked` — transcript with the last 2 turns BOTH from "Architect" both ending in `AGREED` → returns False (n=2 turns but m=1 distinct agent)
5. `test_max_turns_equality` — `MaxTurns(12).check(transcript_with_11_turns)` is False; `MaxTurns(12).check(transcript_with_12_turns)` is True
6. `test_anyof_short_circuit` — `AnyOf([MaxTurns(3), Keyword(["AGREED"])])` returns True at turn 3 even if no AGREED keyword present

### Claude's Discretion

- Whether to expose a `Always(False)` and `Never` no-op stop condition for testing — recommend: no, not needed
- Whether to allow `Keyword` to take a precompiled regex argument — recommend: no, force list-of-strings for v1 simplicity
- Default `n=2, m=2` are STP-03 defaults; configurable via constructor

</decisions>

<code_context>
## Existing Code Insights

After Phases 1-4:
- Phase 3's `Transcript` class has `read_turns() -> list[TurnRecord]` and `__len__`
- TurnRecord fields: `turn`, `agent`, `role`, `prompt_hash`, `output`
- Test patterns: pytest, tmp_path, parametrize, transcript fixtures

This phase has no Windows-specific concerns and no subprocess calls — pure logic.

</code_context>

<specifics>
## Specific Ideas

- Pitfall #4 is THE defining concern: naive `"AGREED" in output` returns true for "I will NEVER say AGREED" — that's a sycophancy false-positive that would prematurely stop debates. The anchored regex `^AGREED\s*$` (multiline) only matches a line that IS the keyword.
- Unanimity-window prevents an agent from "voting itself off the island" — requires distinct agreement from `m` agents.

</specifics>

<deferred>
## Deferred Ideas

- ML-based "consensus detection" (semantic similarity rather than exact keyword) — out of v1 scope
- Time-based stop (`MaxWallTime`) — could be added in v2; Phase 5 is keyword/turn count only
- `AllOf` composite — not in v1 (requires multiple conditions to all match; debate scenarios don't motivate this yet)

</deferred>

---

*Phase: 05-stop-conditions*
*Context auto-generated 2026-05-02 (autonomous mode)*
