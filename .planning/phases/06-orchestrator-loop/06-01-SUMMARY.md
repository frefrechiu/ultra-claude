---
phase: 06-orchestrator-loop
plan: 01
subsystem: orchestrator
tags: [orchestrator, registry, round-robin, stop-conditions, adapter, transcript, logging]
requires:
  - "src/ultra_claude/adapters/__init__.py (Phase 4 — Adapter Protocol + ClaudeAdapter)"
  - "src/ultra_claude/adapters/base.py (Phase 4 — _SubprocessAdapterMixin)"
  - "src/ultra_claude/adapters/claude.py (Phase 4 — ClaudeAdapter)"
  - "src/ultra_claude/transcript.py (Phase 3 — Transcript + TurnRecord)"
  - "src/ultra_claude/stop_conditions.py (Phase 5 — AnyOf, Keyword, MaxTurns)"
  - "src/ultra_claude/config.py (Phase 2 — RoundtableConfig + AgentConfig)"
  - "src/ultra_claude/exceptions.py (Phase 4 — AdapterError + AdapterAuthError subclass)"
provides:
  - "src/ultra_claude/registry.py — get_adapter(adapter_kind) -> Adapter dispatcher"
  - "src/ultra_claude/orchestrator.py — run(config, task) -> Path entry point"
affects:
  - "Phase 7: GeminiAdapter and CodexAdapter slot into get_adapter() without orchestrator changes"
  - "Phase 8: CLI calls run() and prints its returned Path"
tech-stack:
  added: []
  patterns:
    - "Stateless dispatcher function (not a dict): defers adapter instantiation to call time so a missing CLI does not blow up at import"
    - "Idempotent logger setup via _logger.hasHandlers(): Phase 8 CLI can install its own handler without producing double-output"
    - "GOAL ANCHOR re-injection at prompt tail: mitigates Pitfall #6 (problem drift) by exploiting LLM recency bias"
    - "Subclass-aware single-clause continue-on-error: catching AdapterError covers AdapterAuthError too because the latter is a subclass"
    - "try/except/else symmetry around adapter.invoke: append_turn lives in BOTH branches so the composite.check after the loop body runs uniformly"
    - "Adapter factory injection seam: production path uses get_adapter; tests pass adapter_factory=fake_factory"
key-files:
  created:
    - "src/ultra_claude/registry.py (2286 bytes, 56 lines, LF-only, ASCII-only, UTF-8)"
    - "src/ultra_claude/orchestrator.py (11876 bytes, 307 lines, LF-only, ASCII-only, UTF-8)"
  modified: []
decisions:
  - "Registry is a function, not a dict (defers instantiation; matches CLAUDE.md no-class-without-state rule)"
  - "NotImplementedError messages explicitly name 'Phase 7' so users running ahead of the roadmap get a clear signpost"
  - "ValueError on unknown adapter kinds: defence-in-depth even though AgentConfig.adapter is a Literal"
  - "_DEFAULT_TIMEOUT_SECONDS = 120 hardcoded; AgentConfig.timeout deferred to v2 per 06-CONTEXT.md"
  - "_DEFAULT_TRANSCRIPT_PATH = Path('ultra-claude-transcript.md') in cwd when caller passes None and config.transcript_path is None"
  - "transcript_path.parent.mkdir(parents=True, exist_ok=True) BEFORE constructing Transcript (Transcript raises OSError on missing parent per D-11)"
  - "Adapter instances built ONCE up front so NotImplementedError for gemini/codex halts before any transcript is written"
  - "logging.getLogger('ultra_claude.orchestrator') is idempotent: addHandler only when hasHandlers() is False"
  - "Logger setup uses StreamHandler(sys.stderr) with format '%(asctime)s [%(levelname)s] %(message)s'"
  - "Prompt structure (locked): # Task -> # Your role -> transcript-so-far -> # Reminder of the task + 'Respond now as ...' GOAL ANCHOR"
  - "transcript_so_far block omitted entirely when empty (turn 1) so we do not emit a stray blank section"
  - "Stop conditions wired as AnyOf([MaxTurns(config.max_turns), Keyword(config.stop_keywords)]) — STP-05 / ORC-04"
  - "composite.check(transcript) called AFTER every transcript.append_turn (in both try/except and else branches via the post-block check)"
  - "Continue-on-error: catch AdapterError (covers AdapterAuthError subclass), log via _logger.exception, append placeholder turn '[adapter error: <exc>]', continue UNLESS config.abort_on_error is True (then re-raise)"
  - "TRY401 anticipated and pre-empted: _logger.exception called WITHOUT trailing exc arg (logger.exception attaches traceback automatically)"
  - "DEBUG-level prompt-length logging only; never log prompt content (per Phase 3 D-04 secret-leakage avoidance)"
  - "Signature uses keyword-only transcript_path/adapter_factory to keep the public API self-documenting"
  - "Return type is bare Path (no RoundtableResult dataclass): 06-CONTEXT.md Claude's Discretion explicitly recommended NO for v1"
metrics:
  duration: "~30 minutes (2026-05-02T03:58:00Z to 2026-05-02T04:27:47Z; includes baseline test run, two atomic commits, end-to-end smoke validation)"
  completed: "2026-05-02"
  tasks: "2/2"
  commits: 2
  lines_added: 363
  bytes_added: 14162
  ruff_violations_in_new_files: 0
  mypy_strict_errors: 0
  tests_before: 42
  tests_after: 42
  test_regressions: 0
---

# Phase 6 Plan 01: Adapter Registry + Orchestrator run() function — Summary

Landed `src/ultra_claude/registry.py` and `src/ultra_claude/orchestrator.py`, composing `Adapter` (Phase 4) + `Transcript` (Phase 3) + `StopCondition` family (Phase 5) into a single `run(config, task) -> Path` entry point that drives the round-robin debate end-to-end with structured stderr logging and continue-on-error semantics.

## What Was Built

**`src/ultra_claude/registry.py`** (2286 bytes, 56 lines)
- `get_adapter(adapter_kind: str) -> Adapter` — stateless dispatcher.
  - `"claude"` → returns `ClaudeAdapter()` instance.
  - `"gemini"` / `"codex"` → raises `NotImplementedError` whose message names "Phase 7 (next phase); only 'claude' is wired in Phase 6".
  - Any other string → raises `ValueError` (defence-in-depth even though `AgentConfig.adapter` is a `Literal["claude","gemini","codex"]`).
- Function-not-dict so a missing CLI on PATH does not blow up at import time. Function-not-class because it is stateless dispatch.
- `__all__ = ["get_adapter"]`. Single import: `from .adapters import Adapter, ClaudeAdapter`. Zero subprocess imports.

**`src/ultra_claude/orchestrator.py`** (11876 bytes, 307 lines)
- `run(config, task, *, transcript_path=None, adapter_factory=None) -> Path` — the only public symbol.
- Resolves `transcript_path` precedence: explicit kwarg > `config.transcript_path` > `_DEFAULT_TRANSCRIPT_PATH = Path("ultra-claude-transcript.md")`.
- Calls `transcript_path.parent.mkdir(parents=True, exist_ok=True)` before constructing `Transcript` (D-11 compliance).
- Builds per-agent adapter instances ONCE up front via the supplied `adapter_factory` (tests) or production `get_adapter` (default). NotImplementedError for unwired adapter kinds halts before any transcript is written.
- Wires `composite = AnyOf([MaxTurns(config.max_turns), Keyword(config.stop_keywords)])` and probes `composite.check(transcript)` after every `transcript.append_turn`.
- Round-robin: `agent_cfg = config.agents[(turn_idx - 1) % n_agents]`; turn 1 → agents[0], turn 2 → agents[1], turn 4 → agents[0] again (with 3 agents).
- Per-turn prompt assembly (`_build_prompt`):
  1. `# Task\n\n{task}`
  2. `# Your role\n\n{agent.system_prompt}`
  3. `transcript.markdown_text()` (omitted entirely when empty on turn 1)
  4. GOAL ANCHOR: `# Reminder of the task\n\n{task}\n\nRespond now as {agent.name} ({agent.role}). Stay focused on the task above.`
- Continue-on-error guard: `try: adapter.invoke(...) except AdapterError as exc: _logger.exception(...); if config.abort_on_error: raise; else append placeholder '[adapter error: <exc>]' turn`. Single except clause covers `AdapterAuthError` because it is a subclass of `AdapterError`.
- `_ensure_default_handler()` attaches a `StreamHandler(sys.stderr)` with `"%(asctime)s [%(levelname)s] %(message)s"` formatting ONLY when `_logger.hasHandlers()` is False. Phase 8 CLI can install its own handler without double-output.
- `_DEFAULT_TIMEOUT_SECONDS = 120` hardcoded; `AgentConfig.timeout` deferred to v2 per 06-CONTEXT.md.
- Function (not class) per CLAUDE.md "no class without state" architecture rule.

## Atomic Commits

| Hash      | Message                                          | File                                           | Lines |
| --------- | ------------------------------------------------ | ---------------------------------------------- | ----- |
| `8cfee40` | feat(06-01): add adapter registry dispatcher    | `src/ultra_claude/registry.py`                | 56    |
| `b9b80b3` | feat(06-01): add orchestrator run() function    | `src/ultra_claude/orchestrator.py`            | 307   |

## Verification

**Plan-level battery (all PASS):**

| Check                                                          | Result                                                              |
| -------------------------------------------------------------- | ------------------------------------------------------------------- |
| Registry shape (`get_adapter('claude') -> ClaudeAdapter`)      | PASS                                                                |
| Registry NotImplementedError naming Phase 7 (gemini, codex)    | PASS                                                                |
| Registry ValueError on `'bogus'`                               | PASS                                                                |
| Orchestrator import + signature `(config, task, *, tp, af)`    | PASS                                                                |
| `mypy --strict src/ultra_claude`                               | clean — 10 source files (was 8 in Phase 5; now 10 with registry+orchestrator) |
| `ruff check src/ultra_claude/registry.py orchestrator.py`     | clean — both files                                                  |
| `pytest tests/`                                                | 42/42 PASS (zero regression vs Phase 5)                             |
| `pytest tests/test_subprocess_lint.py` (TST-05)                | 3/3 PASS (no subprocess discipline regression)                      |
| LF-only on disk for both new files                             | PASS — registry: 0 CRLF / 56 LF; orchestrator: 0 CRLF / 307 LF      |
| ASCII-only on disk for both new files                          | PASS                                                                |
| Staged blob byte-check (registry, orchestrator)                | PASS — both staged with LF (despite `core.autocrlf=true` host)      |

**End-to-end smoke validation (5/5 PASS):**

| Smoke # | Scenario                                                                                  | Result                                                       |
| ------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| 1       | 3 fake agents, max_turns=6, no AGREED                                                     | 6 turns in declared round-robin order `[A1, A2, A3, A1, A2, A3]`; first prompt contains `# Task\n\nSmoke task` AND `# Reminder of the task\n\nSmoke task` AND `Respond now as A1 (r1). Stay focused on the task above.`; turn-4 prompt contains all three earlier outputs (`out from A1`, `out from A2`, `out from A3`) — PASS |
| 2       | continue-on-error: BoomAdapter raises AdapterAuthError, GoodAdapter returns "ok"          | All 4 turns landed in transcript; placeholder `[adapter error: not logged in]` appears for Boomer's turns; run reached max_turns — PASS |
| 3       | abort_on_error=True with same Boom/Good agents                                            | AdapterAuthError propagated out of `run()` (subclass-aware single-clause catch + bare `raise`) — PASS |
| 4       | Both fake agents output `"I'm done.\nAGREED\n"`, max_turns=10                             | Stopped at turn 2 (Keyword unanimity-window n=2/m=2 satisfied) — PASS |
| 5       | Default transcript_path resolution (no kwarg, no config.transcript_path)                  | Resolved to `Path("ultra-claude-transcript.md")` in cwd — PASS |

Smoke verification was a one-shot inline script (NOT a committed test); the tests/test_orchestrator.py file lands in plan 06-02 per the phase decomposition.

## Deviations from Plan

### None — plan executed exactly as written

Two anticipated/documented adjustments, both pre-empted in the plan's Task 2 notes (so neither counts as a deviation in the Rule-N sense):

1. **TRY401 pre-empted** (anticipated by Task 2 notes line "Anticipated ruff rule that may need attention: TRY401"). I dropped the trailing `(%s)` and `exc` argument from the `_logger.exception(...)` format string. The call now reads `_logger.exception("turn %d: agent %s failed", turn_idx, agent_cfg.name)` — `logger.exception` attaches the traceback automatically, so the explicit `exc` arg would be redundant. ruff did not flag the file at all because I wrote the conformant version up front.

2. **`core.autocrlf=true` Windows compensation** (anticipated by Task 1 notes). The host has `git config --get core.autocrlf` set to `true`. To prevent Git's working-tree filter from materialising CRLF after writing, I wrote both files via `Path.write_bytes(content.encode("utf-8"))` (registry.py) or via the Write tool which defaults to LF on this host (orchestrator.py — verified post-write). Both staged blobs and both on-disk files are LF-only / 0 CRLF. The Git "warning: in the working copy of '...', LF will be replaced by CRLF the next time Git touches it" message is a benign autocrlf check-out warning (the index blob is LF — confirmed via `git show :path | <byte counter>`); the warning itself is not a violation.

### Out-of-scope discoveries (NOT actioned)

Running `python -m ruff check src/ultra_claude` (whole-package) surfaces 2 pre-existing errors in `src/ultra_claude/config.py` (commit `e97325a` from Phase 2):

1. `config.py:38` RUF022 — `__all__` not sorted (chronological-by-introduction order intended, same as `exceptions.py` and `adapters/__init__.py` already use; needs `# noqa: RUF022` + justifying comment).
2. `config.py:110` UP037 — quoted forward-reference `-> "RoundtableConfig"` in `from_yaml_string` should be unquoted given `from __future__ import annotations`.

These were already logged at `.planning/phases/04-adapter-protocol-claudeadapter/deferred-items.md` during plan 04-03. Per the executor scope boundary rule (only auto-fix issues directly caused by the current task's changes), they remain deferred. The plan's done criterion explicitly required only "ruff check clean on the two new files" — both pass — and `mypy --strict src/ultra_claude` clean — also passes.

## Authentication Gates

None encountered. Plan was fully autonomous from start to finish; no auth, no external services, no checkpoints.

## Requirements Coverage (ORC-01..ORC-06)

All six ORC requirements satisfied at the IMPLEMENTATION level. Executable test verification lands in 06-02 (test_orchestrator.py with FakeAdapter):

| Req      | Decision in 06-CONTEXT.md                                                                   | Implementation Evidence                                                                                                                            |
| -------- | ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| ORC-01   | `run(config, task) -> Path` exists                                                          | `orchestrator.py:155-292` — public entry with full signature; smoke 1 verified return value equals `transcript.markdown_path`                     |
| ORC-02   | Round-robin index via `(turn_idx - 1) % len(agents)`                                        | `orchestrator.py:262-263` — `agent_cfg = config.agents[(turn_idx - 1) % n_agents]`; smoke 1 verified order `[A1, A2, A3, A1, A2, A3]`             |
| ORC-03   | Per-turn prompt = Task header + role + transcript-so-far + GOAL ANCHOR                      | `orchestrator.py:_build_prompt` (lines 121-149); smoke 1 verified all four sections + verbatim task in BOTH header AND footer                     |
| ORC-04   | `composite.check(transcript)` after every `append_turn`                                     | `orchestrator.py:316-322` — post-block check inside the for-loop; smoke 4 verified Keyword unanimity-window stops at turn 2                       |
| ORC-05   | Adapter failures → log + placeholder turn + continue (unless `abort_on_error`)              | `orchestrator.py:271-298` — try/except/else with subclass-aware AdapterError catch; smoke 2 verified continue, smoke 3 verified abort propagation |
| ORC-06   | Logger `'ultra_claude.orchestrator'` to stderr StreamHandler; idempotent if already set     | `orchestrator.py:_ensure_default_handler` (lines 87-104); smoke output went to stderr only (capsys-style separation enforced by `StreamHandler(sys.stderr)`) |

## File Stats

**registry.py**
- Bytes: 2286
- Lines: 56 (LF-terminated)
- Encoding: UTF-8 with ASCII-only content
- Imports: `from .adapters import Adapter, ClaudeAdapter`
- `__all__`: `["get_adapter"]`

**orchestrator.py**
- Bytes: 11876
- Lines: 307 (LF-terminated)
- Encoding: UTF-8 with ASCII-only content
- Imports: `logging`, `sys`, `collections.abc.Callable`, `pathlib.Path`, plus 6 first-party modules (`adapters`, `config`, `exceptions`, `registry`, `stop_conditions`, `transcript`)
- `__all__`: `["run"]`
- Public symbols: `run`
- Private symbols: `_logger`, `_DEFAULT_TRANSCRIPT_PATH`, `_DEFAULT_TIMEOUT_SECONDS`, `_ensure_default_handler`, `_build_prompt`

## Phase 6 Status

- **Plan 06-01: COMPLETE** — implementation landed; all 8 success-criteria checkboxes pass; both atomic commits pushed.
- **Plan 06-02 (next):** Adds `tests/test_orchestrator.py` with `FakeAdapter` helper covering all 8 test cases listed in 06-CONTEXT.md (round-robin, task-in-prompt, transcript-so-far, keyword-unanimity-stop, continue-on-error, abort-on-error, returned-path, stdout-discipline). After 06-02 lands, Phase 6 fully closes and Phase 7 (Gemini + Codex adapters) is unblocked.

## Self-Check: PASSED

- `src/ultra_claude/registry.py` — FOUND (2286 bytes, 56 lines, LF-only, ASCII-only)
- `src/ultra_claude/orchestrator.py` — FOUND (11876 bytes, 307 lines, LF-only, ASCII-only)
- Commit `8cfee40` — FOUND in `git log --all`
- Commit `b9b80b3` — FOUND in `git log --all`
- `pytest tests/` — 42/42 PASS (zero regression)
- `mypy --strict src/ultra_claude` — clean (10 modules)
- `ruff check src/ultra_claude/registry.py src/ultra_claude/orchestrator.py` — clean
- `from ultra_claude.registry import get_adapter` — succeeds; `get_adapter('claude')` returns `ClaudeAdapter()` instance satisfying `isinstance(_, Adapter)`
- `from ultra_claude.orchestrator import run` — succeeds; signature `(config, task, *, transcript_path=None, adapter_factory=None) -> Path` confirmed via `inspect.signature`
- 5 end-to-end smoke checks — ALL PASS (round-robin, GOAL ANCHOR, continue-on-error, abort-on-error, default path)
