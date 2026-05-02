---
phase: 05-stop-conditions
plan: 01
subsystem: stop-conditions
tags: [stop-conditions, protocol, regex, unanimity, runtime-checkable, anchored-multiline, pitfall-4]

# Dependency graph
requires:
  - phase: 03-transcript-module
    provides: Transcript class (read_turns, __len__) and TurnRecord schema
provides:
  - StopCondition runtime_checkable Protocol (third parties duck-type, no inheritance)
  - Keyword class with anchored multiline regex (^kw\s*$ via re.MULTILINE) + unanimity-window (n=2 turns, m=2 distinct agents)
  - MaxTurns class with len(transcript) >= max_turns boundary check
  - AnyOf composite with lazy any(...) short-circuit composition
  - Pitfall #4 mitigation verified end-to-end via real Transcript test fixtures
affects: [phase-06-orchestrator, phase-08-cli-doctor]

# Tech tracking
tech-stack:
  added: []  # pure stdlib re + typing.Protocol; no new deps
  patterns:
    - runtime_checkable Protocol mirroring src/ultra_claude/adapters/base.py Adapter
    - chronological-by-introduction __all__ ordering with # noqa: RUF022
    - test fixtures construct real Transcript on tmp_path (no mocks) for end-to-end I/O exercise

key-files:
  created:
    - src/ultra_claude/stop_conditions.py (7142 bytes, 181 lines)
    - tests/test_stop_conditions.py (7347 bytes, 208 lines)
  modified: []

key-decisions:
  - "Protocol pattern mirrors adapters/base.py Adapter -- runtime_checkable + ellipsis-bodied check method; structural subtyping over inheritance"
  - "Anchored multiline regex re.compile(rf'^{re.escape(kw)}\\s*$', re.MULTILINE) compiled once at construction; defends Pitfall #4 sycophancy false-positive"
  - "Unanimity-window defaults n=2 turns, m=2 distinct agents; defends single-agent self-stop attack (one agent voting itself off the island)"
  - "MaxTurns uses len(transcript) (delegates to Transcript.__len__ -> JSONL sidecar count) for canonical turn-count semantics"
  - "AnyOf wraps List[StopCondition] and uses Python's lazy any(...) generator expression for short-circuit composition"
  - "Tests use real Transcript writes on tmp_path (NOT mocks) to catch regressions where Keyword reads markdown instead of JSONL"
  - "_keywords/_n/_m/_patterns are private (underscore-prefixed) to discourage external mutation; constructor is the only configuration surface"

patterns-established:
  - "Pattern 1: runtime_checkable Protocol + concrete strategies = third-party-friendly module pattern across the codebase (adapters use it; stop_conditions adopts it)"
  - "Pattern 2: pre-compile regex at construction (not per-check) -- orchestrator calls check() after every turn so this matters for hot paths"
  - "Pattern 3: 'fail-closed on degenerate input' -- empty transcript / m<=0 / n<=0 / no patterns -> return False (never accidentally fire a stop condition)"

requirements-completed: [STP-01, STP-02, STP-03, STP-04, STP-05]

# Metrics
duration: 3min
completed: 2026-05-02
---

# Phase 5 Plan 01: StopCondition Protocol + Keyword + MaxTurns + AnyOf Summary

**Composable stop strategies for the orchestrator: runtime_checkable Protocol plus anchored-multiline-regex Keyword (with unanimity-window n=2/m=2) plus MaxTurns boundary plus AnyOf lazy composite, mitigating Pitfall #4 sycophancy false-positives end-to-end.**

## Performance

- **Duration:** ~3 min 14 sec
- **Started:** 2026-05-02T04:02:14Z
- **Completed:** 2026-05-02T04:05:28Z
- **Tasks:** 2
- **Files modified:** 2 (both created)

## Accomplishments

- **STP-01 (Protocol):** `@runtime_checkable class StopCondition(Protocol)` with `check(transcript: Transcript) -> bool`; structural subtyping verified by duck-typed `FakeStop` test (positive) and `HalfBaked` test (negative -- no `check` method).
- **STP-02 (Keyword anchored regex):** `re.compile(rf"^{re.escape(kw)}\s*$", re.MULTILINE)` literal pattern present at line 105 of stop_conditions.py. The `re.escape` defends against keywords containing regex metachars; the `^...\s*$` anchor + `re.MULTILINE` rejects the Pitfall #4 sycophancy bait line `"I am NOT going to say AGREED yet"`.
- **STP-03 (Unanimity-window):** Defaults `n=2, m=2` exposed via keyword-only `__init__` parameters. Exercised in two tests: `test_keyword_unanimity_two_agents_two_turns` (Architect+Critic both AGREED -> True) and `test_keyword_single_agent_self_stop_blocked` (Architect twice -> False; voting-itself-off-the-island defense).
- **STP-04 (MaxTurns boundary):** `MaxTurns(12).check(transcript)` returns `False` at 11 turns, `True` at 12 turns -- exact-boundary equality test (not >). Uses `len(transcript)` from Transcript.__len__.
- **STP-05 (AnyOf composite):** Lazy `any(c.check(transcript) for c in self._conditions)` short-circuits on first match. Verified `AnyOf([MaxTurns(3), Keyword(["AGREED"])])` returns True at turn 3 even with no AGREED keyword present (MaxTurns fires first; Keyword never evaluated).
- **42/42 full-suite tests PASS:** 36 prior + 6 new; zero regression in the prior tests (8 config + 8 transcript + 7 adapters_base + 10 adapter_claude + 3 subprocess_lint).
- **mypy --strict clean across 8 files** (was 7 before this plan; stop_conditions.py added with all annotations explicit including `_patterns: list[re.Pattern[str]]`).
- **ruff clean** on the two new files.
- **LF-only + ASCII-only on disk** for both files.
- **TST-05 lint test still passes** (free regression check -- stop_conditions.py adds zero subprocess calls so the contract is trivially upheld).

## Task Commits

Each task was committed atomically:

1. **Task 1: Create src/ultra_claude/stop_conditions.py** - `e56a779` (feat)
2. **Task 2: Create tests/test_stop_conditions.py** - `9dbc164` (test)

## Files Created/Modified

- `src/ultra_claude/stop_conditions.py` (NEW; 7142 bytes, 181 lines, LF-only, ASCII-only) -- `StopCondition` Protocol + `Keyword` + `MaxTurns` + `AnyOf` classes. Pure logic; zero subprocess; zero file IO of its own. Imports `Transcript` from `.transcript` (read-side only -- `transcript.read_turns()` for Keyword's window inspection; `len(transcript)` for MaxTurns).
- `tests/test_stop_conditions.py` (NEW; 7347 bytes, 208 lines, LF-only, ASCII-only) -- 6 test functions, all PASS. Helpers `_make_transcript(tmp_path)` and `_append(transcript, *, turn, agent, output, ...)` keep each test focused on its assertion. All tests use real Transcript instances on `tmp_path` (NOT mocks) so the unanimity-window logic is exercised against actual JSONL sidecar reads.

## Requirement Trace

| Requirement | Test                                              | Acceptance                                             |
|-------------|---------------------------------------------------|--------------------------------------------------------|
| STP-01      | test_stop_condition_protocol_structural           | runtime_checkable + duck-typed isinstance positive + negative |
| STP-02      | test_keyword_anchored_regex_rejects_substring     | "I am NOT going to say AGREED yet" with m=1 -> False (Pitfall #4 mitigation) |
| STP-03 (+)  | test_keyword_unanimity_two_agents_two_turns       | Architect+Critic both AGREED in last 2 turns -> True (defaults n=2,m=2) |
| STP-03 (-)  | test_keyword_single_agent_self_stop_blocked       | Architect twice -> False (voting-itself-off defense)   |
| STP-04      | test_max_turns_equality                           | 11 turns -> False; 12 turns -> True (boundary)         |
| STP-05      | test_anyof_short_circuit                          | MaxTurns(3) fires at turn 3 with no AGREED -> True; loose MaxTurns(99) -> False (sanity) |

## Decisions Made

None deviating from the plan. The plan's locked decisions (regex pattern, unanimity-window defaults, Protocol shape, lazy `any(...)`) were followed exactly. The two `# noqa: RUF022` annotations anticipated by the plan were applied:

1. `__all__` in `src/ultra_claude/stop_conditions.py` is in chronological-by-introduction order (`StopCondition`, `Keyword`, `MaxTurns`, `AnyOf`) to match the existing `adapters/__init__.py` and `exceptions.py` conventions. Alphabetizing would split the Protocol from its concrete strategies.

## Deviations from Plan

None - plan executed exactly as written.

The plan anticipated five potential Rule 3 deviations (RUF022 noqa annotation; ARG001 on unused tmp_path; HalfBaked empty body; ruff lint cleanups; mypy strict cosmetics). Of these:

- **RUF022 anticipated and applied:** Added `# noqa: RUF022` plus justifying comment to `__all__` in stop_conditions.py. This is documented in the plan as the expected outcome -- not a deviation.
- **ARG001 (unused tmp_path):** Did NOT trigger. The first test (`test_stop_condition_protocol_structural`) declares `tmp_path: Path` for fixture-consistency but ruff did not flag it; left as-is.
- **HalfBaked empty body:** `class HalfBaked: pass` was accepted by mypy --strict without complaint; left as-is with a comment explaining the test intent.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Phase 6 (Orchestrator) is unblocked.** The orchestrator can now wire stop conditions through `AnyOf([MaxTurns(config.max_turns), Keyword(config.stop_keywords)])`, calling `composite.check(transcript)` after every turn.
- **CFG-04 default `max_turns=12`** lines up with the MaxTurns boundary test (12 returns True, 11 returns False) so the orchestrator's loop will terminate at exactly the configured cap.
- **CFG-05 default `stop_keywords=["AGREED", "DONE"]`** flows directly into `Keyword(stop_keywords)` -- two literal-string keywords, both anchored multiline.
- **No new external dependencies.** stop_conditions.py is pure stdlib (`re` + `typing.Protocol`), so Phase 6 inherits no new install burden.
- **Phase 1 closure (PKG-05)** still pending user `twine upload` -- unrelated to this plan.

## Self-Check: PASSED

Files verified to exist:
- FOUND: src/ultra_claude/stop_conditions.py
- FOUND: tests/test_stop_conditions.py

Commits verified to exist:
- FOUND: e56a779 (feat(05-01): add StopCondition Protocol + Keyword + MaxTurns + AnyOf)
- FOUND: 9dbc164 (test(05-01): add stop_conditions test suite covering STP-01..STP-05 + Pitfall #4)

End-of-phase verification gates:
- pytest tests/ -> 42 passed (was 36; +6 new)
- mypy --strict src/ultra_claude -> Success: no issues found in 8 source files
- ruff check src/ultra_claude/stop_conditions.py tests/test_stop_conditions.py -> All checks passed!
- runtime_checkable Protocol smoke test -> Protocol OK
- LF + ASCII clean -> both files

---
*Phase: 05-stop-conditions*
*Completed: 2026-05-02*
