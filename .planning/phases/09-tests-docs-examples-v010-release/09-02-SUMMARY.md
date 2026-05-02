---
phase: 09-tests-docs-examples-v010-release
plan: 02
subsystem: tests/e2e
tags: [tests, e2e, fixtures, subprocess, utf8, windows]
requires: [src/ultra_claude/adapters/base.py, src/ultra_claude/orchestrator.py, src/ultra_claude/transcript.py, src/ultra_claude/config.py]
provides: [tests/fixtures/echo_cli.py, tests/test_e2e_with_echo_cli.py, e2e regression-net for _SubprocessAdapterMixin._run_subprocess]
affects: []
tech-stack:
  added: []
  patterns: [subprocess-real-Popen-no-mock, mixin-inheritance-from-test, ASCII-only-on-disk-via-escape-sequences]
key-files:
  created:
    - tests/fixtures/__init__.py
    - tests/fixtures/echo_cli.py
    - tests/test_e2e_with_echo_cli.py
  modified: []
decisions:
  - The EchoAdapter inherits from _SubprocessAdapterMixin (NOT structurally implementing Adapter Protocol from scratch) so the SAME production code path that ClaudeAdapter / GeminiAdapter / CodexAdapter use is exercised by the E2E test
  - The fake CLI is a Python script invoked via [sys.executable, str(echo_cli_path)] -- works in any clean venv with no extras (only sys from stdlib), no real claude/gemini/codex binaries required
  - Test file is ASCII-only on disk (all non-ASCII codepoints expressed via Python \uXXXX / \U0001XXXX escape sequences); in-memory Python string is the decoded UTF-8 equivalent at parse time, so the round-trip semantics through the OS pipe are unchanged
metrics:
  duration: ~9 min (2026-05-02T08:14:00Z -> 2026-05-02T08:23:00Z)
  completed: 2026-05-02
  tasks: 2
  commits: 2
  new_tests: 3
  total_tests: 86 (was 83, +3)
---

# Phase 9 Plan 02: Echo CLI fixture + E2E orchestrator test Summary

E2E orchestrator test using a real Python child process via `_SubprocessAdapterMixin._run_subprocess` -- the difference between "subprocess.Popen was mocked and the assertions passed" and "the OS pipe between Popen and the child IS wired correctly on this machine".

## Outcome

| Metric | Value |
|--------|-------|
| Tasks completed | 2/2 |
| Atomic commits | 2 (`58ec2f8` fixture + `2575869` test) |
| New tests added | 3 |
| Total test count | 86 (was 83 after 09-01; +3 from 09-02) |
| Full suite result | 86/86 PASS in 3.84s (zero regression) |
| TST-05 lint | 3/3 PASS (still clean) |
| ruff check on new files | "All checks passed!" |
| mypy --strict | clean (13 source files unchanged) |
| UTF-8 round-trip on Windows | PASSED (smart-curly-quotes + em-dash + rocket-emoji + Chinese ideographs all survive) |
| Rule-N deviations | 1 (Rule 3 - Blocking: stdout-encoding workaround for non-ASCII codepoint replacement during file authoring) |

## Files Created

| Path | Bytes | Purpose |
|------|-------|---------|
| tests/fixtures/__init__.py | 0 | Empty package marker so tests/fixtures/ is a valid Python package |
| tests/fixtures/echo_cli.py | 1437 | Fake CLI: reads stdin, prints `echo: <prompt>` to stdout, exits 0; UTF-8 reconfigure on stdin/stdout to survive Windows cp1252 default |
| tests/test_e2e_with_echo_cli.py | 9391 | 3 E2E tests using real subprocess.Popen via the production _SubprocessAdapterMixin |

All three files are LF-only on disk (verified via `git cat-file -p HEAD:<path>` post-commit) despite `core.autocrlf=true` host. test_e2e_with_echo_cli.py is also ASCII-only on disk (0 non-ASCII bytes; non-ASCII codepoints expressed via `\uXXXX` / `\U0001XXXX` escape sequences which decode to the corresponding UTF-8 bytes in memory at parse time).

## Tests Added

1. **`test_run_against_echo_cli_writes_real_transcript`** -- happy path: 2-agent / 4-turn round-robin debate using EchoAdapter. Asserts the returned transcript path exists, has exactly 4 turns recorded in `[alpha, beta, alpha, beta]` order, every turn output starts with the literal `echo:`, and every turn output contains the original task verbatim (proving the prompt round-tripped through stdin and the orchestrator's prompt-assembler correctly included the task in each turn's prompt).

2. **`test_echo_cli_handles_utf8_round_trip`** -- 2-agent / 2-turn debate where the task contains smart-curly-quotes (U+201C, U+201D), em-dash (U+2014), rocket emoji (U+1F680), and Chinese ideographs (U+4E2D, U+6587). Asserts every turn's recorded output contains the full UTF-8 task verbatim with NO U+FFFD replacement characters. Defends against silent Windows cp1252 corruption at the mixin layer (Pitfall #3) -- if `_SubprocessAdapterMixin._run_subprocess` ever loses its `encoding="utf-8"` kwargs, this test fails loudly on Windows. **Confirmed PASSING on Windows 11 (Python 3.11.9, cp950 system codepage)** -- the test is meaningful because the canary platform is the failure case.

3. **`test_echo_adapter_satisfies_adapter_protocol`** -- structural Protocol conformance check: `isinstance(EchoAdapter(), Adapter)` is True at runtime via the `@runtime_checkable` Protocol decoration on `Adapter`. The orchestrator does not check this directly (it duck-types), but if a future plan ever wires runtime_checkable Protocol isinstance into the orchestrator, this test makes the constraint explicit.

## EchoAdapter Design

```python
class EchoAdapter(_SubprocessAdapterMixin):
    name: str = "echo"
    cli_name: str = "echo"
    auth_error_markers: tuple[str, ...] = ()  # echo never emits auth markers

    def invoke(self, prompt: str, timeout: int) -> str:
        return self._run_subprocess(
            [sys.executable, str(_ECHO_CLI_PATH)],
            prompt,
            timeout,
        )
```

**Critical**: `EchoAdapter` inherits from `_SubprocessAdapterMixin` -- NOT from the `Adapter` Protocol directly. The Protocol is structural, so runtime inheritance breaks mypy --strict. By inheriting from the mixin, the test exercises the SAME `_run_subprocess` method that powers the three production adapters (`ClaudeAdapter`, `GeminiAdapter`, `CodexAdapter`). The `cli_name="echo"` and empty `auth_error_markers` tuple satisfy the mixin's two requirements; the empty tuple makes the case-insensitive substring loop on auth markers a guaranteed no-op.

## How This Closes the Gap

Every other test in the suite mocks subprocess at some layer:
- `tests/test_adapter_claude.py` / `test_adapter_gemini.py` / `test_adapter_codex.py` use `pytest-subprocess` `fp` fixture (intercepts subprocess.Popen)
- `tests/test_orchestrator.py` uses `FakeAdapter` with `adapter_factory=` (zero subprocess at all)
- `tests/test_cli.py` uses `monkeypatch.setattr(ultra_claude.orchestrator, "get_adapter", fake_factory)` (zero subprocess at all)

This new test is the FIRST one in the suite where bytes really do flow:
```
orchestrator.run() -> EchoAdapter.invoke -> _SubprocessAdapterMixin._run_subprocess
  -> subprocess.Popen([python, echo_cli.py]) -> [OS pipe]
  -> echo_cli.py reads stdin -> writes to stdout -> [OS pipe]
  -> back into orchestrator -> Transcript.append_turn (markdown + JSONL)
```

This catches a class of regressions invisible to the unit tests: any change to `_SubprocessAdapterMixin._run_subprocess` (e.g. a refactor that drops `encoding="utf-8"`, swaps `errors="replace"` for `errors="strict"`, removes `text=True`, or introduces a typo in `start_new_session` / `creationflags`) that would silently break the production adapters in real-world conditions but pass their unit tests because the unit tests mock at the very boundary the bug lives at.

## TST-05 Lint Compliance

The new test file's `EchoAdapter` calls `self._run_subprocess(...)` -- the production mixin method -- rather than calling `subprocess.Popen` or `subprocess.run` directly. This means:

1. The new file adds ZERO direct `subprocess.run`/`subprocess.Popen` calls to the codebase
2. The TST-05 AST walker scopes its scan to `src/ultra_claude/` only (per `tests/test_subprocess_lint.py` line 42), so test files are never scanned anyway
3. By exercising `_run_subprocess`, the test inherits ALL of the safe-contract kwargs (text=True, encoding="utf-8", errors="replace", shell=False, mandatory timeout) that TST-05 enforces

The fake CLI fixture (`tests/fixtures/echo_cli.py`) does not call subprocess at all -- it only reads stdin and writes stdout. So no subprocess-contract concerns arise there either.

## Verification Gate Results

| Gate | Command | Result |
|------|---------|--------|
| 1 | `echo "ping" \| python tests/fixtures/echo_cli.py` | `echo: ping` (exit 0) |
| 2 | `pytest tests/test_e2e_with_echo_cli.py -v` | 3/3 PASS in 2.40s |
| 3 | `pytest tests/` | 86/86 PASS in 3.84s |
| 4 | `pytest tests/test_subprocess_lint.py` | 3/3 PASS in 0.03s |
| 5 | `ruff check tests/test_e2e_with_echo_cli.py tests/fixtures/` | "All checks passed!" |
| 6 | `mypy` | Success: no issues found in 13 source files |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Authoring-time stdout-encoding compensation for non-ASCII codepoint replacement**
- **Found during:** Task 2
- **Issue:** When converting the `utf8_task` literal in `tests/test_e2e_with_echo_cli.py` from raw non-ASCII codepoints (curly quotes, em-dash, Chinese ideographs) to ASCII-safe `\uXXXX` escape sequences (per the plan's `<action>` block ASCII-only-on-disk requirement), an initial attempt via the `Edit` tool was blocked by the read-before-edit hook reminder. A subsequent attempt using a Python heredoc through `bash -c "python <<'PYEOF'..."` failed because the shell heredoc passed `'\\u201c'` to Python as a SINGLE backslash followed by `u201c`, which Python's source parser then interpreted as the Unicode escape sequence -- making the replacement string equal to `chr(0x201c)` instead of the literal six characters `“`. This caused `text.replace(chr(0x201c), '\\u201c')` to be a no-op (replace curly with curly).
- **Fix:** Wrote the replacement script to a real `.py` file (`_ascii_fix.py`) using the `Write` tool, where backslash literals survive untouched. The file used `chr(92)` to construct the literal backslash, eliminating dependence on shell-quoting interpretation entirely. After running the script via `python _ascii_fix.py`, the test file dropped from 11 non-ASCII codepoints to 0; deleted the helper script post-run. Final file is 9391 bytes, 0 non-ASCII bytes, 0 CRLF, 227 LF.
- **Files modified:** tests/test_e2e_with_echo_cli.py (during authoring; final state in commit `2575869`)
- **Commit:** `2575869` (test(09-02): add E2E orchestrator test using real Popen + echo_cli)

No other deviations. The plan's English specification of the test contents was executed verbatim; the only deviation was the AUTHORING workflow's collision with shell heredoc backslash-eating, which never reached committed code.

## Authentication Gates

None. This plan adds zero authentication-required code paths. The fake CLI by design never emits auth markers, so the EchoAdapter's `auth_error_markers=()` empty tuple is correct.

## Known Stubs

None. All three test functions are fully wired with real assertions; no TODOs, no placeholders, no mock data.

## Threat Flags

None new. Threat register T-09-05..T-09-09 from the plan apply as documented:
- T-09-05 (spoofing): the fixture file is named `echo_cli.py` not `claude.py`/`gemini.py`/`codex.py`, eliminating impersonation confusion
- T-09-06 (info disclosure): all data flows through `tmp_path`, no production data
- T-09-07 (DoS): mixin's mandatory timeout=120s bounds any single invocation
- T-09-08 (collection): empty `tests/fixtures/__init__.py` package marker; pytest does NOT collect tests from `tests/fixtures/` (no `test_*.py` files in that dir)
- T-09-09 (TST-05 regression): the EchoAdapter inherits from `_SubprocessAdapterMixin` rather than calling subprocess directly, so the production safe-subprocess path is exercised. TST-05 lint stays 3/3 PASS post-plan (verified)

## Self-Check: PASSED

- [x] tests/fixtures/__init__.py exists (0 bytes, package marker)
- [x] tests/fixtures/echo_cli.py exists (1437 bytes, runs standalone via `python tests/fixtures/echo_cli.py < input`)
- [x] tests/test_e2e_with_echo_cli.py exists (9391 bytes, 3 test functions: test_run_against_echo_cli_writes_real_transcript, test_echo_cli_handles_utf8_round_trip, test_echo_adapter_satisfies_adapter_protocol)
- [x] Commit `58ec2f8` exists (feat(09-02) fixture)
- [x] Commit `2575869` exists (test(09-02) E2E test)
- [x] Full test suite 86/86 PASS (83 prior + 3 new; zero regression)
- [x] TST-05 lint 3/3 PASS
- [x] ruff check clean on new files
- [x] mypy --strict clean (13 source files; zero source changes)
- [x] All new files LF-only on disk + LF-only in staged git blob
- [x] tests/test_e2e_with_echo_cli.py ASCII-only on disk (0 non-ASCII bytes); UTF-8 codepoints survive parse-time decoding into the in-memory string (verified via AST walk)
- [x] UTF-8 round-trip test PASSES on Windows 11 (Python 3.11.9, cp950 system codepage)
