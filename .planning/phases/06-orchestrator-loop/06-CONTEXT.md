# Phase 6: Orchestrator Loop - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

Compose adapters + transcript + stop conditions into a single `run(config, task) -> Path` function. Drives the round-robin debate end-to-end with structured stderr logging and continue-on-error semantics.

Scope:
- `src/ultra_claude/orchestrator.py` — `run(config: RoundtableConfig, task: str, *, transcript_path: Path | None = None) -> Path`
- `src/ultra_claude/registry.py` — small helper that maps `AgentConfig.adapter` literal ("claude"/"gemini"/"codex") to an adapter instance. For Phase 6 we only have `ClaudeAdapter` so the registry returns it for `"claude"` and raises `NotImplementedError` for the others (Phase 7 will add Gemini/Codex). The registry keeps adapter wiring out of the orchestrator function body.
- `tests/test_orchestrator.py` — end-to-end tests using a fake adapter that's structurally an `Adapter` (no subprocess required); covers ORC-01..ORC-06

Out of scope: Gemini/Codex adapters (Phase 7), CLI surface (Phase 8).

</domain>

<decisions>
## Implementation Decisions

### Locked from REQUIREMENTS.md (ORC-01..ORC-06)

- **`run` signature:**
  ```python
  def run(
      config: RoundtableConfig,
      task: str,
      *,
      transcript_path: Path | None = None,
      adapter_factory: Callable[[str], Adapter] | None = None,
  ) -> Path:
      """Drive a roundtable debate to completion. Returns the transcript path."""
  ```
  - `adapter_factory` parameter lets tests inject fake adapters without monkey-patching the registry. Default value `None` falls through to the production registry.
  - Returns the transcript markdown `Path`.
  - `transcript_path` defaults to a stable path: `Path("ultra-claude-transcript.md")` in the cwd if not provided. Phase 8's CLI will pass this explicitly.

- **Round-robin loop (ORC-02):**
  - Iterate agents in declared order: `for turn_idx in range(1, max_turns + 1): agent_cfg = config.agents[(turn_idx - 1) % len(config.agents)]`
  - This means turn 1 → agents[0], turn 2 → agents[1], ..., turn N+1 → agents[0] again.

- **Per-turn prompt (ORC-03):**
  - Construct a prompt string for the adapter that contains, in order:
    1. The original task statement (verbatim, in a `# Task` heading)
    2. The current agent's `system_prompt` (in a `# Your role` heading)
    3. The full transcript so far (the markdown content from `Transcript.markdown_path.read_text()`)
    4. A "GOAL ANCHOR" re-injection of the task at the END of the prompt: `# Reminder of the task\n{task}\n\nRespond now as {agent.name} ({agent.role}). Stay focused on the task above.`
  - This mitigates problem drift (Pitfall #6).

- **Stop-condition wiring (ORC-04):**
  - At orchestrator entry, build `composite = AnyOf([MaxTurns(config.max_turns), Keyword(config.stop_keywords)])`.
  - After EVERY `transcript.append_turn(...)` call, check `composite.check(transcript)`. On True, log "stopped on {reason}" to stderr and return.
  - The composite short-circuits, so we don't compute Keyword on every turn unnecessarily.

- **Continue-on-error (ORC-05):**
  - If an adapter raises `AdapterError` (or any subclass like `AdapterAuthError`), the orchestrator:
    - Logs the error to stderr via `logging.exception("agent %s failed: %s", agent.name, exc)`
    - Appends a "placeholder" turn to the transcript with the error message: `agent=<agent.name>, role=<agent.role>, output="[adapter error: {exc}]"`
    - Continues to the next agent UNLESS `config.abort_on_error` is True (then re-raises)
  - This means a missing/unauthenticated CLI doesn't kill the whole debate — the user sees a placeholder turn and the debate proceeds.

- **Logging (ORC-06):**
  - Use `logging.getLogger("ultra_claude.orchestrator")` — a named logger so users can configure it.
  - Set up a default `StreamHandler` writing to `sys.stderr` with a simple format (`"%(asctime)s [%(levelname)s] %(message)s"`) IFF the logger has no handlers yet (avoids double-config when CLI sets it up).
  - Log: "starting roundtable: %d agents, max_turns=%d", "turn %d starting (agent=%s)", "turn %d completed (%d chars output)", "stopped on <reason>".
  - **stdout discipline:** the only thing the orchestrator writes to stdout is the final transcript Path (in CLI; in `run()` it's just the return value — Phase 8's CLI prints it). Progress goes to stderr only. This is testable: capture stderr/stdout separately in tests.

- **Adapter registry (`registry.py`):**
  ```python
  from ultra_claude.adapters import ClaudeAdapter

  def get_adapter(adapter_kind: str) -> Adapter:
      if adapter_kind == "claude":
          return ClaudeAdapter()
      if adapter_kind in ("gemini", "codex"):
          raise NotImplementedError(f"{adapter_kind} adapter ships in Phase 7 (next phase)")
      raise ValueError(f"unknown adapter kind: {adapter_kind!r}")
  ```
  Phase 7 will extend this to add Gemini and Codex.

### Module structure (after this phase)

```
src/ultra_claude/
├── __init__.py
├── config.py
├── exceptions.py
├── transcript.py
├── stop_conditions.py
├── orchestrator.py        # NEW
├── registry.py            # NEW
└── adapters/
    ├── __init__.py
    ├── base.py
    └── claude.py
```

### Testing strategy

`tests/test_orchestrator.py`:
- **`FakeAdapter` helper** — structurally an `Adapter`. Has `name: str`, `invoke(prompt, timeout) -> str`. Records every call. Optionally raises configured exceptions to test continue-on-error.
- Test cases:
  1. `test_run_3_agent_max_turns_6_writes_6_turns` — verify round-robin order and turn count
  2. `test_run_includes_task_in_prompt` — capture the prompt sent to FakeAdapter; assert it contains the task in both the header AND the goal-anchor footer
  3. `test_run_includes_transcript_so_far` — by turn 3, FakeAdapter sees turns 1 and 2 in the prompt
  4. `test_run_stops_on_keyword_unanimity` — three FakeAdapters each return "AGREED" on a single line; orchestrator stops after 2 distinct agents say it
  5. `test_run_continues_on_adapter_error` — one FakeAdapter raises AdapterError; placeholder turn appended; debate continues
  6. `test_run_aborts_on_error_when_configured` — same setup but `config.abort_on_error=True` → `run` re-raises
  7. `test_run_returns_transcript_path` — return value is a Path that exists and contains the right number of turn markers
  8. `test_run_logs_progress_to_stderr_only` — capsys.readouterr() shows progress messages on stderr but stdout is empty (run() itself returns a Path; CLI is what prints to stdout)

### Claude's Discretion

- Whether to log the prompt-hash for each turn (aids debugging but adds verbose logs at INFO level) — recommend: yes, log at DEBUG level; INFO is the default and stays terse
- Whether to expose a `RoundtableResult` dataclass with `transcript_path`, `turns_completed`, `stopped_by` (e.g. "max_turns" or "keyword") — recommend: NO for v1; just return Path. Phase 8 CLI exit codes are determined from raised exceptions, not result data.

</decisions>

<code_context>
## Existing Code Insights

After Phases 1-5:
- `RoundtableConfig` with `agents`, `max_turns`, `stop_keywords`, `abort_on_error` (Phase 2)
- `Transcript.append_turn` with `prompt_hash` field (Phase 3)
- `ClaudeAdapter` and `_SubprocessAdapterMixin` (Phase 4)
- `Keyword`, `MaxTurns`, `AnyOf` stop conditions (Phase 5)

The orchestrator is glue — its job is to NOT add new abstractions, just wire up what exists.

</code_context>

<specifics>
## Specific Ideas

- `run()` is a function, not a class (per CLAUDE.md "Architecture corrections" — Orchestrator class deferred to v3 if parallel speakers ever land).
- Pitfall #6 (problem drift) → goal-anchor re-injection at prompt tail.
- ORC-05's continue-on-error must include the AdapterAuthError case — a missing CLI shouldn't kill a 3-agent debate where 2 agents are still healthy.

</specifics>

<deferred>
## Deferred Ideas

- Parallel/concurrent agent speaking (multiple agents respond per turn) — v3
- Per-agent timeout overrides (current: single global timeout per agent invocation, defaults to 120s) — could expose `AgentConfig.timeout` field in v2
- Per-turn streaming output to user — out of scope per CLAUDE.md (subprocess.run is blocking)
- Mid-run resume from existing transcript — Phase 6 only handles fresh runs; resume is v2

</deferred>

---

*Phase: 06-orchestrator-loop*
*Context auto-generated 2026-05-02 (autonomous mode)*
