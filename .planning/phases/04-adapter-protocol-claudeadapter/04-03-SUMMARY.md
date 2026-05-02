---
phase: 04-adapter-protocol-claudeadapter
plan: 03
subsystem: tests
tags: [pytest, pytest-subprocess, ast-lint, runtime_checkable, structural-typing, tst-05, regression-tripwire]

# Dependency graph
requires:
  - phase: 04-adapter-protocol-claudeadapter
    provides: Adapter Protocol + _SubprocessAdapterMixin (04-01) and ClaudeAdapter (04-02). 04-03 verifies them with executable tests.
provides:
  - tests/test_adapters_base.py -- 7 tests covering ADP-01 (runtime_checkable Protocol structural typing) + ADP-02 partial (mixin annotations + ClaudeAdapter inheritance + populated attributes)
  - tests/test_adapter_claude.py -- 10 tests covering ADP-02..05, ADP-08 via the pytest-subprocess fp fixture (happy + empty stdout x2 + FNF + 4 auth marker variants + timeout-with-kill)
  - tests/test_subprocess_lint.py -- 3 tests implementing TST-05: ast-walks src/ultra_claude/, asserts every subprocess.run/Popen has text=True/encoding="utf-8"/errors="replace" and not shell=True. Manually verified to FAIL on a synthetic bad call.
  - The single most important regression tripwire in the codebase -- a future PR adding a non-compliant subprocess call cannot land without explicitly bypassing CI.
affects: [Phase 6 (orchestrator can wire ClaudeAdapter with confidence in the contract), Phase 7 (Gemini/Codex adapters get tested under the same lint test for free), Phase 9 (CI pipeline runs all 3 test files on Windows + Linux runners)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pytest-subprocess fp fixture for behavioral tests of subprocess-launching code -- mocks both subprocess.run and subprocess.Popen, supports stdin_callable + callback for stdin assertion and TimeoutExpired simulation"
    - "monkeypatch on a class-level @staticmethod to record cleanup-helper invocations without forking real children -- proves _kill_process_tree fires on TimeoutExpired in CI on every platform"
    - "ast-walking lint tests as a regression tripwire -- cheaper than a custom ruff plugin or mypy plugin, runs in the standard pytest suite, fails fast on the first violation with file:lineno across every site"
    - "Negative-case Protocol tests (assert NOT isinstance(half_baked, Adapter)) to pin runtime_checkable's method-presence semantics -- guards against a relaxed Protocol slipping past code review"

key-files:
  created:
    - "tests/test_adapters_base.py (5043 bytes, 122 lines, LF-only, ASCII-only) -- 7 Protocol/mixin shape tests"
    - "tests/test_adapter_claude.py (9655 bytes, 253 lines, LF-only, ASCII-only) -- 10 ClaudeAdapter behavioural tests via pytest-subprocess fp fixture"
    - "tests/test_subprocess_lint.py (7853 bytes, 200 lines, LF-only, ASCII-only) -- TST-05 ast-walking lint test (3 tests)"
    - ".planning/phases/04-adapter-protocol-claudeadapter/deferred-items.md -- 4 pre-existing ruff errors in Phase 2 files logged for a future chore plan"
  modified: []

key-decisions:
  - "Used pytest-subprocess fp fixture for ClaudeAdapter tests rather than unittest.mock.patch because fp gives us argv-shape matching, stdin_callable for assertion, and callback for TimeoutExpired simulation -- all of which mock would force us to reimplement"
  - "monkeypatch on _SubprocessAdapterMixin._kill_process_tree (staticmethod) rather than monkeypatch on os.killpg / subprocess.run individually -- covers both POSIX and Windows branches with one stub and proves the cleanup path runs without us forking real children in CI"
  - "Used callback raising TimeoutExpired (not the wait= timeout argument) because pytest-subprocess _finalize_thread re-raises the thread's exception on communicate(), which is exactly the path the mixin's except block is designed to catch"
  - "The lint test parses with ast.parse and walks Call nodes (not AST visitor or libcst) -- ast-walk is the simplest tool that handles both subprocess.run / subprocess.Popen attribute access AND from-imported bare run/Popen, with no third-party deps"
  - "The lint test enumerates ALL violations and fails once with a multi-line message (instead of failing on the first), so a CI run shows every offending file:lineno at once -- a developer fixing a regression sees the complete list"
  - "FileNotFoundError test uses monkeypatch on subprocess.Popen rather than fp's pass_command + raise -- gives us a deterministic crash at exactly the OS-level Popen() call, regardless of pytest-subprocess's internal allow-unregistered behavior"
  - "Logged 4 pre-existing ruff errors (RUF022/UP037 in src/ultra_claude/config.py, I001/F401 in tests/test_config.py) in deferred-items.md instead of fixing inline -- per scope boundary rule, those errors come from Phase 2 commits e97325a + 5c272f0 and were not introduced by 04-03"

patterns-established:
  - "Lint tests as tripwires: TST-05 establishes the pattern of using a pytest-collected ast-walking test to enforce repo-wide invariants. Future invariants (e.g. 'no print() in src/'; 'every Pydantic model has ConfigDict extra=forbid') can follow the same template."
  - "Behavior-test template for the remaining two adapters (Phase 7): ClaudeAdapter's 10 tests in test_adapter_claude.py are a copy-paste template -- GeminiAdapter and CodexAdapter tests will only need to swap argv ['claude', '-p'] for ['gemini', '-p'] / ['codex', 'exec'], swap auth markers, and reuse the same five paths verbatim."

requirements-completed: [TST-05]
requirements-verified-by-tests: [ADP-01, ADP-02, ADP-03, ADP-04, ADP-05, ADP-08]

# Metrics
duration: 6min
completed: 2026-05-02
---

# Phase 4 Plan 03: Adapter Tests + TST-05 Subprocess Lint Test Summary

**Three test files (575 lines, 20 new tests) close Phase 4: pytest-subprocess fp-fixture behavioural tests for ClaudeAdapter, runtime_checkable Protocol structural-typing tests, and the TST-05 ast-walking lint tripwire that fails the build on any future subprocess.run/Popen call missing the safe-contract keywords -- the single most important regression guard in the entire codebase.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-02T03:42:27Z
- **Completed:** 2026-05-02T03:48:18Z
- **Tasks:** 3 / 3
- **Files created:** 4 (3 test files + 1 deferred-items.md)
- **Files modified:** 0

## Accomplishments

- **20 new tests added (16 prior + 20 = 36 total)**, all pass in `python -m pytest tests/ -v` in 0.30 s on Windows. Zero regression in the 16 Phase 2/3 tests.
- **`tests/test_adapters_base.py` (7 tests):** verifies `Adapter` is a `runtime_checkable` Protocol via the `_is_runtime_protocol` dunder; verifies `isinstance(ClaudeAdapter(), Adapter)` is True; verifies a duck-typed `ThirdPartyAdapter` with `name: str` and `invoke(prompt, timeout) -> str` ALSO satisfies the Protocol (proving structural subtyping works as the public extension point); verifies a class missing `invoke` does NOT satisfy (negative-case guard); verifies `_SubprocessAdapterMixin` declares `cli_name` and `auth_error_markers` annotations; verifies `ClaudeAdapter` inherits from `_SubprocessAdapterMixin`; verifies `ClaudeAdapter.cli_name == "claude"` and `auth_error_markers` is a non-empty tuple of whitespace-trimmed strings.
- **`tests/test_adapter_claude.py` (10 tests via pytest-subprocess fp fixture):** five distinct behaviour paths cover ADP-02..05 + ADP-08:
  1. **Happy path + stdin pipe (Pitfall #1 mitigation):** `stdin_callable` captures the prompt; assertion `captured["stdin"] == "the prompt"` proves the prompt flows via stdin, not argv.
  2. **Happy path + argv shape:** `fp.calls` records `["claude", "-p"]` confirming the list-form argv.
  3. **Empty stdout (Pitfall #2 / openai/codex#19945):** `returncode=0, stdout=""` raises `AdapterError` whose message contains both "claude" and "empty" or "19945".
  4. **Whitespace-only stdout:** `stdout="   \n\t\n  "` ALSO raises `AdapterError` (proving the defense matches `stdout.strip() == ""`, not just `stdout == ""`).
  5. **FileNotFoundError (ADP-08 path 1):** `monkeypatch.setattr(subprocess, "Popen", _raise_fnf)` triggers the mixin's except branch -> `AdapterAuthError` whose message contains "claude" + "login"/"install"/"path" hint.
  6. **Auth marker substring (ADP-08 path 2, 4 parametrize variants):** `"Error: not logged in"` (lowercase exact), `"ERROR: NOT LOGGED IN"` (uppercase, case-insensitive match), `"Authentication required to continue"` (alternate marker), `"please run /login first"` (marker buried in message) -- all four raise `AdapterAuthError`.
  7. **TimeoutExpired + process-tree kill (ADP-04 / Pitfall #5):** `fp.register(callback=lambda p: raise TimeoutExpired)` makes pytest-subprocess re-raise on `_finalize_thread`; `monkeypatch.setattr(Mixin, "_kill_process_tree", staticmethod(fake_kill))` records the kill invocation; the test asserts `len(kill_calls) >= 1` AND the re-raised `AdapterError` message contains "claude" and "tim" (timeout).
- **`tests/test_subprocess_lint.py` (3 tests, TST-05):** ast-walks every `.py` file under `src/ultra_claude/`, finds every `Call` node whose `func` is `subprocess.run`, `subprocess.Popen`, or bare-imported `run` / `Popen`, and asserts each call has `text=True`, `encoding="utf-8"`, `errors="replace"`, and does NOT have `shell=True`. The 3 tests are: package root sanity check; "at least one call site exists" (so the lint test cannot pass vacuously if the mixin disappears); the headline "every site has the required keywords" check that aggregates ALL failures into one multi-line `pytest.fail(...)` so CI shows every violation at once.
- **Manual paranoia check confirmed the lint test FIRES correctly:** I temporarily injected a scratch file `src/ultra_claude/_scratch.py` with `subprocess.run(["echo", "hi"])` (missing all four kwargs), ran `pytest tests/test_subprocess_lint.py -x`, and confirmed:
  - `returncode=1` (test fails)
  - Failure message lists the file:lineno
  - Failure message names each missing keyword: `text=True`, `encoding='utf-8'`, `errors='replace'`
  - I separately verified the `shell=True` branch fires by injecting `subprocess.run(["echo"], text=True, encoding="utf-8", errors="replace", shell=True)` -- confirmed the scratch file made the test fail with "shell=True is forbidden"
  - Scratch file deleted in both cases; no residue in the working tree.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create `tests/test_adapters_base.py` -- Adapter Protocol structural typing tests** -- `ab17d77` (test)
2. **Task 2: Create `tests/test_adapter_claude.py` -- ClaudeAdapter behaviour tests via pytest-subprocess fp fixture** -- `e0ea60e` (test)
3. **Task 3: Create `tests/test_subprocess_lint.py` -- TST-05 ast-walking subprocess-contract lint test** -- `e16c4f9` (test)

_Plan metadata commit will follow this SUMMARY._

## Files Created/Modified

- `tests/test_adapters_base.py` (created) -- 122 lines, 5043 bytes, LF-only, ASCII-only. 7 Protocol/mixin shape tests covering ADP-01 (runtime_checkable, structural subtyping with positive + negative cases) and ADP-02 partial (mixin annotations, inheritance, populated attributes).
- `tests/test_adapter_claude.py` (created) -- 253 lines, 9655 bytes, LF-only, ASCII-only. 10 behavioural tests via `pytest-subprocess` `fp` fixture and `monkeypatch`. The `fp` fixture's `stdin_callable` and `callback` parameters give us deterministic argv + stdin assertion + TimeoutExpired simulation; `monkeypatch.setattr(subprocess, "Popen", ...)` gives us the FileNotFoundError path; `monkeypatch.setattr(Mixin, "_kill_process_tree", staticmethod(fake_kill))` proves the cross-platform cleanup path runs.
- `tests/test_subprocess_lint.py` (created) -- 200 lines, 7853 bytes, LF-only, ASCII-only. 3 ast-walking lint tests implementing TST-05. Detects both attribute access (`subprocess.run`) and bare-imported names (`run` from `from subprocess import run`); aggregates all failures into a single multi-line `pytest.fail(...)` so CI surfaces every violation. Manually verified to fail on a synthetic bad scratch file (regression detection works).
- `.planning/phases/04-adapter-protocol-claudeadapter/deferred-items.md` (created) -- 4 pre-existing ruff errors (`RUF022` in `src/ultra_claude/config.py:38`, `UP037` at `:110`, `I001` in `tests/test_config.py:12`, `F401` at `:24`) logged for a future chore plan. Confirmed pre-existing via `git log --oneline -- <file>` -- both files come from Phase 2 commits `e97325a`/`5c272f0`, not 04-03.

## Verification

All plan-level verification commands PASS:

- `python -m pytest tests/test_adapters_base.py tests/test_adapter_claude.py tests/test_subprocess_lint.py -v` -> **20 passed**
- `python -m pytest tests/ -v` -> **36 passed** (16 Phase 2/3 + 20 new; zero regression)
- `python -m mypy --strict src/ultra_claude` -> `Success: no issues found in 7 source files`
- `python -m ruff check tests/test_adapters_base.py tests/test_adapter_claude.py tests/test_subprocess_lint.py` -> `All checks passed!`
- `python -m ruff check src/ultra_claude/adapters` -> `All checks passed!`
- LF-only check on all 3 test files -> `CRLF=0, ASCII=True` on each
- Manual paranoia check: scratch file with `subprocess.run(["echo","hi"])` (no safe kwargs) makes `pytest tests/test_subprocess_lint.py` exit 1 with file:lineno violation report -> CONFIRMED; scratch file deleted afterward
- Manual paranoia check (variant): scratch file with `shell=True` makes the test fail with the "shell=True is forbidden" branch -> CONFIRMED; scratch file deleted afterward

Total project test count: **16 -> 36** (delta +20, exceeds the plan's "+19" floor).

## Decisions Made

See `key-decisions` in the frontmatter. Highlights:

- **`pytest-subprocess` `fp` over `unittest.mock.patch`** for ClaudeAdapter tests because the `fp` fixture provides argv matching, stdin capture (via `stdin_callable`), and callback-based exception injection out of the box -- all of which `mock` would force us to reimplement by hand.
- **`monkeypatch` on `_SubprocessAdapterMixin._kill_process_tree`** rather than on the underlying `os.killpg` / `subprocess.run` (taskkill) -- one stub covers both POSIX and Windows branches and proves the cleanup path RUNS without forking real children in CI.
- **`ast.walk` over `libcst` or a custom ruff plugin** for TST-05 -- ast is in the stdlib, handles both attribute and bare-name forms, and runs in the standard pytest collection (no separate CI step).
- **Aggregate-all-failures pattern** in the lint test -- one `pytest.fail(...)` with a multi-line message lists every violation so a developer fixing a regression in CI sees the complete list, not just the first.

## Deviations from Plan

The plan executed largely as written. **One Rule 3 deviation** to make the lint test pass `ruff check`:

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ruff SIM102 on nested-if in `_is_subprocess_call`**

- **Found during:** Task 3 ruff verification.
- **Issue:** ruff `SIM102` ("Use a single `if` statement instead of nested `if` statements") flagged the literal code from the plan, which used `if isinstance(func, ast.Attribute):` containing a nested `if (...condition...): return True`. The structure is logically equivalent to a single combined `if isinstance(...) and ...: return True` but ruff considers the nested form a stylistic regression.
- **Fix:** Combined the two `if` statements into one using `and`:
  ```python
  if (
      isinstance(func, ast.Attribute)
      and isinstance(func.value, ast.Name)
      and func.value.id == "subprocess"
      and func.attr in SUBPROCESS_CALL_NAMES
  ):
      return True
  ```
- **Verification:** Ruff now passes; the 3 lint tests still pass; the manual paranoia check (scratch file) still confirms the test fires on bad input. No semantic change.
- **Files modified:** `tests/test_subprocess_lint.py` (single function body, no behavioural change).
- **Commit:** `e16c4f9` (Task 3 commit).

**2. [Rule 3 - Blocking] ruff I001 auto-fixed on `tests/test_adapters_base.py`**

- **Found during:** Task 1 ruff verification.
- **Issue:** ruff `I001` ("Import block is un-sorted or un-formatted") flagged a stylistic blank-line difference between the literal code in the plan and ruff's import organizer. Specifically, the plan's literal code had a blank line between `from ultra_claude.adapters import ...` and the next section comment (`# ---`); ruff wanted no blank line between them.
- **Fix:** Ran `python -m ruff check --fix tests/test_adapters_base.py` which removed the offending blank line. No semantic change; the imports are unchanged.
- **Verification:** Ruff now passes; all 7 tests still pass; LF-only and ASCII-only on disk preserved.
- **Files modified:** `tests/test_adapters_base.py` (single blank-line removal at file scope).
- **Commit:** `ab17d77` (Task 1 commit).

No Rule 1 (bug), Rule 2 (missing critical functionality), or Rule 4 (architectural) deviations were needed. Both deviations were cosmetic source-text adjustments to satisfy ruff without changing semantics. All other behavior in the test files matches the plan exactly.

## Out-of-Scope Discoveries Logged (not actioned in 04-03)

Per the executor scope-boundary rule, four pre-existing ruff errors in files NOT touched by this plan are logged in `.planning/phases/04-adapter-protocol-claudeadapter/deferred-items.md` rather than fixed inline:

1. `src/ultra_claude/config.py:38` -- `RUF022` `__all__` not sorted (Phase 2)
2. `src/ultra_claude/config.py:110` -- `UP037` quoted forward-reference (Phase 2)
3. `tests/test_config.py:12` -- `I001` import block un-sorted (Phase 2)
4. `tests/test_config.py:24` -- `F401` unused import `format_validation_error` (Phase 2)

All four come from Phase 2 commits `e97325a` and `5c272f0` (verified via `git log --oneline --all -- <path>`); none were introduced or modified by 04-03. A future small chore plan can address them together with the `core.autocrlf` / `.gitattributes` item already logged in `02/deferred-items.md`.

## Issues Encountered

None blocking. The two ruff deviations were cosmetic and resolved within seconds.

## Authentication Gates

None. This plan does not invoke any external CLI -- the `claude` binary is mocked via pytest-subprocess `fp` fixture for behaviour tests and via `monkeypatch.setattr(subprocess, "Popen", _raise_fnf)` for the FileNotFoundError test.

## Threat Flags

None. This plan adds test surface only (3 files under `tests/`, 1 deferred-items.md under `.planning/`). The lint test (`tests/test_subprocess_lint.py`) makes the threat surface SMALLER by enforcing the safe-subprocess contract on every future src-tree change.

## Self-Check: PASSED

Verified files exist:

- FOUND: `tests/test_adapters_base.py`
- FOUND: `tests/test_adapter_claude.py`
- FOUND: `tests/test_subprocess_lint.py`
- FOUND: `.planning/phases/04-adapter-protocol-claudeadapter/deferred-items.md`

Verified commits exist in git log:

- FOUND: `ab17d77` (Task 1: test(04-03): add Adapter Protocol structural typing tests)
- FOUND: `e0ea60e` (Task 2: test(04-03): add ClaudeAdapter behaviour tests using pytest-subprocess fp fixture)
- FOUND: `e16c4f9` (Task 3: test(04-03): add TST-05 ast-walking subprocess-contract lint test)

## Next Phase Readiness

- TST-05 closed; ADP-01..05 + ADP-08 verified by executable tests. **Phase 4 is fully closed (3/3 plans, 7/7 ADP+TST requirements).**
- Phase 5 (Stop Conditions) was always parallelizable with Phase 4 -- it is now ready to plan or execute.
- Phase 7 (Gemini/Codex adapters) inherits the entire Phase 4 contract for free. The 10-test ClaudeAdapter behaviour suite serves as a copy-paste template: GeminiAdapter and CodexAdapter tests will only need to swap argv (`["claude","-p"]` -> `["gemini","-p"]` / `["codex","exec"]`), swap auth markers, and reuse the same five paths verbatim. The TST-05 lint test will automatically cover any new subprocess.run/Popen call those adapters introduce -- they cannot regress the safety contract without explicitly bypassing CI.
- Phase 6 (orchestrator) can wire `ClaudeAdapter` (and the future Gemini/Codex adapters) with confidence that the contract is provably airtight.

---
*Phase: 04-adapter-protocol-claudeadapter*
*Completed: 2026-05-02*
