---
phase: 06-orchestrator-loop
plan: 02
subsystem: testing
tags: [orchestrator, fakeadapter, pytest, caplog, capsys, protocol, round-robin, stop-conditions, continue-on-error, abort-on-error, stdout-discipline]
requires:
  - phase: 06-orchestrator-loop
    provides: "src/ultra_claude/orchestrator.py and src/ultra_claude/registry.py landed in plan 06-01 with adapter_factory injection seam"
  - phase: 04-adapter-protocol-claudeadapter
    provides: "Adapter Protocol (runtime_checkable) and AdapterError + AdapterAuthError exception hierarchy"
  - phase: 03-transcript-module
    provides: "Transcript class with read_turns()/markdown_text()/__len__ read-back helpers used to inspect runs"
  - phase: 02-config-schema-yaml-loader
    provides: "AgentConfig + RoundtableConfig Pydantic models constructed via direct kwargs in test fixtures"
provides:
  - "tests/test_orchestrator.py — FakeAdapter helper (pure-Python Protocol satisfier) plus 8 test cases proving ORC-01..ORC-06 from executable assertions instead of inline `python -c` smoke checks"
  - "Locked-in test pattern: caplog for logger emission assertions, capsys for stdout discipline assertions — applies to any future test that exercises the orchestrator's stderr-logging contract"
affects:
  - "Phase 7 (Gemini + Codex Adapters): test pattern is reusable; FakeAdapter fixture pattern can be adapted for adapter conformance tests"
  - "Phase 8 (CLI Surface): the orchestrator's adapter_factory injection seam is now test-locked, so CLI integration tests can confidently rely on it"
  - "Phase 9 (v0.1.0 Release): TST-04 coverage requirement is closer — orchestrator has 8 tests now exercising every public branch"

tech-stack:
  added: []
  patterns:
    - "Pure-Python Protocol satisfiers for testing: FakeAdapter has name + invoke() but does NOT inherit Adapter — duck-typed structural conformance via runtime_checkable"
    - "adapter_factory injection seam exercised in 7/8 tests via `_make_factory(adapters: dict[str, FakeAdapter])` returning insertion-order-keyed dispenser"
    - "caplog for logger record assertions, capsys for stdout discipline — pytest's logging plugin diverts records away from sys.stderr writes, so capsys.err is empty even though the orchestrator's StreamHandler is correctly bound"
    - "AgentConfig fixtures via direct kwargs (NOT YAML loader) — tests bypass the config loader to focus on orchestrator behaviour; the literal `adapter='claude'` value never reaches the registry because adapter_factory short-circuits it"
key-files:
  created:
    - "tests/test_orchestrator.py (17306 bytes, 460 lines, LF-only, ASCII-only, UTF-8)"
  modified: []
key-decisions:
  - "Use caplog instead of capsys.err for logger emission assertions (Rule 1 deviation from plan's verification suggestion of `propagate = False`)"
  - "FakeAdapter does NOT inherit from Adapter — relies on runtime_checkable structural typing so the Protocol is verified end-to-end (the orchestrator accepts whatever the factory returns; if FakeAdapter satisfies the duck type, the orchestrator can drive a real run)"
  - "_make_factory uses dict-insertion-order to dispense adapters (mirrors how 06-01's run() calls factory once per agent in declared order); the factory parameter `_kind` is intentionally unused — the leading underscore keeps ruff happy AND signals 'we trust the orchestrator's call order, not the literal'"
  - "Test 8 deliberately resets logger handlers (commented out in final form because caplog is the assertion mechanism, not capsys.err) and uses caplog.set_level(INFO, logger='ultra_claude.orchestrator') because caplog defaults to WARNING"
  - "Stop-keyword tests use the literal `IMPOSSIBLE-MARKER` / `IMPOSSIBLE-MARKER-NEVER-SAID` placeholder so MaxTurns is the only stop signal — defends future readers from confusion if Keyword's regex semantics ever change"
patterns-established:
  - "FakeAdapter pattern: pure-Python helper with `calls: list[tuple[str, int]]` recording every invoke call, `canned_output` for happy paths, `raise_exc` for error paths — covers continue-on-error AND abort-on-error in <40 lines"
  - "caplog assertion pattern for orchestrator-emitted log records: future tests verifying `'turn N starting'` style messages should use caplog.text + caplog.records, not capsys.err"
  - "Direct AgentConfig/RoundtableConfig construction in tests via _agent() helper that hardcodes adapter='claude' since the registry is bypassed by adapter_factory"

requirements-completed:
  - ORC-01
  - ORC-02
  - ORC-03
  - ORC-04
  - ORC-05
  - ORC-06

# Metrics
duration: ~5 min (2026-05-02T04:38:18Z to 2026-05-02T04:43:11Z)
completed: 2026-05-02
---

# Phase 6 Plan 02: Orchestrator Test Suite — Summary

**8-test pytest suite for `run(config, task) -> Path` covering round-robin, GOAL ANCHOR prompt assembly, transcript-so-far visibility, keyword unanimity early-stop, AdapterError continue-vs-abort, return-path correctness, and stdout/logging discipline — all using a pure-Python FakeAdapter via the adapter_factory injection seam (zero subprocess launches).**

## Performance

- **Duration:** ~5 min (2026-05-02T04:38:18Z to 2026-05-02T04:43:11Z)
- **Started:** 2026-05-02T04:38:18Z
- **Completed:** 2026-05-02T04:43:11Z
- **Tasks:** 1/1 (single Task 1 from the plan, executed atomically)
- **Files modified:** 0 (plan modifies nothing; only creates tests/test_orchestrator.py)
- **Files created:** 1 (tests/test_orchestrator.py)
- **Tests added:** 8 (all PASS first time after the test-8 caplog fix)
- **Total project test count:** 42 -> 50 (zero regression in the 42 prior tests)

## Accomplishments

- Locked ORC-01..ORC-06 with executable tests; the 06-01 implementation was previously verified only by an inline `python -c` smoke script (NOT committed). This plan replaces that ad-hoc validation with 8 committed tests that fail loud if any future change breaks the contract.
- FakeAdapter helper (40 lines including docstring) is structurally an `Adapter` Protocol satisfier — proves the runtime_checkable Protocol from Phase 4 plays correctly with the orchestrator's factory injection from 06-01.
- Verified all five end-to-end smoke scenarios from 06-01 are now committed-test-driven: round-robin in declared order, GOAL ANCHOR appears in every prompt, transcript-so-far reaches turn N+1, Keyword unanimity halts after turn 2 with max_turns=6, continue-vs-abort branches both correct.
- Established the canonical pattern for testing Python logging behaviour in this project: `caplog` for record assertions, `capsys` for stdout discipline assertions — pytest's built-in logging plugin makes the naive `capsys.err` approach unreliable.

## Task Commits

Single atomic commit (per the plan's "expect 1 commit" output guidance):

1. **Task 1: Create tests/test_orchestrator.py — FakeAdapter helper + 8 test cases** — `747f003` (test)

```
test(06-02): add orchestrator test suite covering ORC-01..ORC-06
```

(Plan-metadata commit will follow as a final state-update commit alongside this SUMMARY + STATE + ROADMAP + REQUIREMENTS edits.)

## Files Created/Modified

- `tests/test_orchestrator.py` — NEW (17306 bytes, 460 lines, LF-only, ASCII-only, UTF-8). Contains:
  - Module docstring listing each test's ORC-N mapping (lines 1-21).
  - Imports (lines 22-34): `from __future__ import annotations`, `logging`, `Callable`, `Path`, `pytest`, plus 5 first-party imports (`Adapter`, `AgentConfig`, `RoundtableConfig`, `AdapterError`, `run`, `Transcript`).
  - `class FakeAdapter` (lines 41-72): Protocol satisfier with `name`, `canned_output`, `raise_exc`, `calls` fields. `invoke(prompt, timeout) -> str` records the call then returns canned or raises.
  - `_agent()` and `_make_factory()` test helpers (lines 75-105): build `AgentConfig` fixtures and a factory that dispenses FakeAdapters by dict insertion order.
  - 8 test functions (lines 108-460): one per ORC test case from 06-CONTEXT.md "Testing strategy".

No files modified. No `__init__.py` changes — tests/ is already a package per Phase 2.

## Test Mapping (Per-Test ORC Coverage)

| Test                                                  | ORC Reqs            | What It Proves                                                                                                                                                |
| ----------------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_run_3_agent_max_turns_6_writes_6_turns`          | ORC-01 + ORC-02     | 3-agent + max_turns=6 produces 6 turns in declared `[a,b,c,a,b,c]` round-robin order; each FakeAdapter invoked exactly twice; result Path equals input        |
| `test_run_includes_task_in_prompt`                    | ORC-03              | First prompt contains `# Task` header AND `# Reminder of the task` footer (GOAL ANCHOR mitigates Pitfall #6); task appears >=2 times; system_prompt is in prompt |
| `test_run_includes_transcript_so_far`                 | ORC-03              | Turn 3's prompt to alpha (round-robin a,b,a) contains BOTH turn 1's `ALPHA-FIRST-OUTPUT` AND turn 2's `BETA-FIRST-OUTPUT`                                     |
| `test_run_stops_on_keyword_unanimity`                 | ORC-04              | 3 agents all returning `"AGREED"` with default n=2/m=2 halts after turn 2 (alpha + beta in window); gamma never invoked even though max_turns=6                |
| `test_run_continues_on_adapter_error`                 | ORC-05              | beta raises AdapterError -> placeholder turn `"[adapter error: simulated CLI failure]"` appended; alpha + beta + gamma all 3 turns landed; gamma still invoked |
| `test_run_aborts_on_error_when_configured`            | ORC-05              | abort_on_error=True with same setup -> AdapterError propagates out of run(); gamma NOT invoked                                                                |
| `test_run_returns_transcript_path`                    | ORC-01              | Return value is `isinstance(Path)`, equals the input path, file exists; markdown contains 4 sentinel comments `<!-- turn:N agent: -->` for N in 1..4          |
| `test_run_logs_progress_to_stderr_only`               | ORC-06              | `capsys.readouterr().out == ""` (stdout discipline); `caplog.text` contains "starting roundtable" + "turn 1 starting" + "turn 2 starting"; >= 3 records from `ultra_claude.orchestrator` logger name |

All 8 tests use the `adapter_factory` injection seam — zero subprocess launches anywhere in this test file.

## Decisions Made

- **Use caplog (not capsys.err) for logger record assertions in test 8.** This is a Rule 1 deviation from the plan's verification note (which suggested `propagate = False` as the fix). See Deviations section below for full reasoning. The decision applies to any future test in this project that needs to verify Python logging output.
- **FakeAdapter does not inherit from Adapter.** The Phase 4 Adapter Protocol is `@runtime_checkable`, so structural typing alone is sufficient. Inheriting would mask any future regression where the orchestrator accidentally requires an Adapter subclass.
- **`_make_factory` uses dict insertion order, not lookup by agent name.** This mirrors how the orchestrator's `run()` calls `factory(agent.adapter)` once per agent in declared order, so the queue-by-insertion-order is semantically equivalent and simpler than a name-based dispatch dict (which would require the FakeAdapter dict keys to match `AgentConfig.name`, an irrelevant constraint).
- **Stop-keyword placeholders use `IMPOSSIBLE-MARKER` / `IMPOSSIBLE-MARKER-NEVER-SAID`.** Tests where MaxTurns should be the only stop signal use these placeholders rather than empty lists (which Keyword would still evaluate as no-op) so any future regression where Keyword fires on null/short patterns surfaces as a turn-count mismatch.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test 8 capsys.err assertion replaced with caplog**

- **Found during:** Task 1 (Create tests/test_orchestrator.py)
- **Issue:** First run of `pytest tests/test_orchestrator.py -x -v` failed test 8 with `AssertionError: assert 'starting roundtable' in '' (where '' = CaptureResult(out='', err='').err)`. Diagnosis: pytest's built-in `logging` plugin attaches a handler at the root logger level that captures records through the logging machinery rather than letting them reach `sys.stderr` for capsys to see. Confirmed by re-running with `pytest -p no:logging` — test passed. The plan's verification note suggested `propagate = False` after the handler reset; that fix would NOT work because the issue is not propagation, it's that pytest's logging plugin is the active stderr-bound logging consumer, not `sys.stderr` itself. Asserting against `caplog.text` is the pytest-idiomatic way to verify that a specific logger emitted specific messages and is the canonical fix for this class of issue.
- **Fix:** Added `caplog: pytest.LogCaptureFixture` parameter; added `caplog.set_level(logging.INFO, logger="ultra_claude.orchestrator")` at test entry (caplog defaults to WARNING); replaced `assert "..." in captured.err` with `assert "..." in caplog.text`; added a tightening assertion `len(orchestrator_records) >= 3` to verify records came from the right named logger. Kept `assert captured.out == ""` for the stdout discipline check (capsys IS the right tool for that — direct stdout writes are what we want to forbid).
- **Files modified:** `tests/test_orchestrator.py` (test 8 only; lines 386-460 — replaced the entire body of the function plus its parameter list and docstring; the orchestrator source is unchanged).
- **Verification:** Re-ran `pytest tests/test_orchestrator.py -x -v` -> 8/8 PASS. Re-ran full suite `pytest tests/` -> 50/50 PASS. Re-ran `ruff check tests/test_orchestrator.py` -> clean.
- **Committed in:** `747f003` (the single Task 1 commit). The fix was applied before the commit, so there's no separate Rule-1 commit — the test file as committed already uses the caplog form.

**2. [Rule 3 - Blocking] ruff I001 import-block formatting**

- **Found during:** Task 1 verification step (`ruff check tests/test_orchestrator.py`)
- **Issue:** ruff I001 ("Import block is un-sorted or un-formatted") flagged the import block — specifically, two blank lines between the imports and the first `# ----` comment block. ruff wanted exactly one.
- **Fix:** Removed one blank line between `from ultra_claude.transcript import Transcript` and `# ---------------------------------------------------------------------------` (lines 34-36 region). No semantic change.
- **Files modified:** `tests/test_orchestrator.py` (1 blank line removed).
- **Verification:** `ruff check tests/test_orchestrator.py` -> "All checks passed!". `pytest tests/test_orchestrator.py -x -v` -> still 8/8 PASS.
- **Committed in:** `747f003` (folded into the same Task 1 commit before commit).

---

**Total deviations:** 2 auto-fixed (1 Rule 1 - test correctness bug; 1 Rule 3 - blocking ruff lint).
**Impact on plan:** The Rule 1 fix superseded the plan's verification-section recommendation (`propagate = False`) with a more correct solution (`caplog` is the pytest-canonical mechanism for asserting logging records). The plan's success criteria still hold: stdout-discipline is verified via `capsys.out == ""`, logger-emission is verified via `caplog.text`. No scope creep.

## Issues Encountered

- **`core.autocrlf=true` on Windows host risks CRLF in working tree:** Mitigated by writing the file via the Write tool (which produces LF-only content). Verified the on-disk file is 0 CRLF / 460 LF, and the staged blob is also 0 CRLF / 460 LF (`git show :tests/test_orchestrator.py | python -c "..."` reports 17306 bytes / 0 CRLF / 460 LF). The Git "warning: in the working copy of '...', LF will be replaced by CRLF the next time Git touches it" message is benign — the staged blob and on-disk file are both LF.
- **Pytest logging-plugin / capsys interaction (Rule 1 deviation above):** First-run failure on test 8 was diagnosed as pytest's logging plugin diverting records before they reach the StreamHandler's bound `sys.stderr`. Resolved by switching to caplog. Logged the resolution in the deviation section so future contributors don't repeat the diagnosis.

## User Setup Required

None — no external service configuration required. This is a pure-Python test file using `tmp_path`, `capsys`, and `caplog` fixtures (all built-in to pytest 8+).

## Verification Battery (All PASS)

| Check                                                          | Command                                                                                            | Result                                                                                                                          |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 8 new tests pass                                               | `pytest tests/test_orchestrator.py -x -v`                                                          | 8/8 PASS                                                                                                                        |
| Full suite passes (zero regression)                            | `pytest tests/`                                                                                    | 50/50 PASS (8 new + 42 prior; 8 config + 8 transcript + 7 adapters_base + 10 adapter_claude + 3 subprocess_lint + 6 stop_conditions + 8 orchestrator) |
| Ruff lint clean on the new file                                | `ruff check tests/test_orchestrator.py`                                                            | "All checks passed!"                                                                                                            |
| mypy --strict still clean on src                               | `mypy --strict src/ultra_claude`                                                                   | "Success: no issues found in 10 source files" (tests/ not in mypy.files; no src changes in this plan)                            |
| TST-05 lint test still passes                                  | `pytest tests/test_subprocess_lint.py -x`                                                          | 3/3 PASS (orchestrator/registry/test file add zero subprocess calls)                                                            |
| LF-only on disk on the new file                                | `python -c "p=Path('tests/test_orchestrator.py'); assert b'\\r\\n' not in p.read_bytes()"`         | PASS — 0 CRLF / 460 LF                                                                                                          |
| ASCII-only on disk on the new file                             | `python -c "Path('tests/test_orchestrator.py').read_bytes().decode('ascii')"`                      | PASS — no UnicodeDecodeError                                                                                                    |
| Exactly 8 tests in the new file                                | `python -c "re.findall(r'^def (test_\\w+)\\(', src, re.MULTILINE)"`                                | 8 tests verified (test_run_3_agent_max_turns_6_writes_6_turns, ...includes_task..., ...includes_transcript_so_far..., ...stops_on_keyword..., ...continues_on_adapter_error..., ...aborts_on_error..., ...returns_transcript_path..., ...logs_progress_to_stderr_only) |
| Staged blob LF-only                                            | `git show :tests/test_orchestrator.py | python -c "..."`                                          | 17306 bytes / 0 CRLF / 460 LF                                                                                                   |

## File Stats

**tests/test_orchestrator.py**

- Bytes: 17306
- Lines: 460 (LF-terminated)
- Encoding: UTF-8 with ASCII-only content
- Test functions: 8 (matches success criterion)
- Helper functions: 2 (`_agent`, `_make_factory`) plus 1 helper class (`FakeAdapter`)
- Imports: stdlib (`logging`, `collections.abc.Callable`, `pathlib.Path`) + `pytest` + 5 first-party (`Adapter`, `AgentConfig`, `RoundtableConfig`, `AdapterError`, `run`, `Transcript`)
- Subprocess imports: ZERO (FakeAdapter is pure Python; `adapter_factory` injection seam bypasses the registry which would otherwise instantiate `ClaudeAdapter`)

## Phase 6 Status

- **Plan 06-02: COMPLETE** — `tests/test_orchestrator.py` landed; 8/8 tests PASS; full suite 50/50 PASS; ruff clean; mypy --strict still clean (10 source files, unchanged); LF-only + ASCII-only on disk; staged blob LF-only despite `core.autocrlf=true`.
- **Phase 6 fully closed.** 2/2 plans complete (06-01: implementation + 06-02: test suite). All 6 ORC requirements (ORC-01..ORC-06) now have executable test verification, not just implementation.
- **Phase 7 (Gemini & Codex Adapters) is unblocked.** Phase 7 reuses the Phase 4 mixin so it doesn't touch orchestrator code; the orchestrator's adapter_factory injection seam is now test-locked, so any future regression in 06-01's `run()` shape will be caught immediately by the tests in this plan.

## Next Phase Readiness

- **Phase 7 ready:** Plan-time will need to verify `gemini -p` non-interactive flag (issue #19774) and `codex exec` `--quiet`/stdin support empirically — those checks are still pending per the research-flags table in STATE.md. Otherwise Phase 7 is fully unblocked: the mixin contract is test-locked from Phase 4, the orchestrator can drive any new adapter via the registry, and the tests in this plan show the exact pattern Phase 7 should mirror.
- **Phase 1 closure (PKG-05):** Still pending user `twine upload` per `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md`. Independent of Phase 7.
- **No outstanding blockers for autonomous execution.**

## Self-Check: PASSED

- `tests/test_orchestrator.py` — FOUND (17306 bytes, 460 lines, LF-only, ASCII-only)
- Commit `747f003` — FOUND in `git log --oneline -3` (HEAD, head of current branch)
- `pytest tests/` — 50/50 PASS (zero regression)
- `pytest tests/test_orchestrator.py -x -v` — 8/8 PASS
- `mypy --strict src/ultra_claude` — clean (10 source files)
- `ruff check tests/test_orchestrator.py` — clean ("All checks passed!")
- 8 test functions enumerated by `re.findall(r'^def (test_\w+)\(', src, re.MULTILINE)`
- TST-05 lint test still passes (3/3 PASS) — free regression check confirms zero new subprocess calls
- Staged blob byte-check: `git show :tests/test_orchestrator.py | wc -c` reports 17306 bytes; CRLF count via `python -c` is 0
- ORC-01..ORC-06 mapped to tests 1+7, 2+3, 4, 5+6, 8 (per the test mapping table above)

---
*Phase: 06-orchestrator-loop*
*Completed: 2026-05-02*
