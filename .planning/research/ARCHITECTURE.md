# Architecture Research

**Domain:** Python CLI orchestrator that spawns LLM CLIs (Claude Code, Gemini CLI, Codex CLI) as subprocesses, threading a shared transcript through their `-p`/`exec` invocations.
**Researched:** 2026-05-02
**Confidence:** HIGH for component boundaries, adapter pattern, and Windows subprocess concerns (Context7 + official docs verified). MEDIUM for transcript format choice and stop-condition composition (single-source / pattern-extrapolation reasoning).

---

## Standard Architecture

### System Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                         User-Facing Layer                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  cli.py  (click group: `ultra-claude run <task-file>`)       │  │
│  │      args -> Config -> Orchestrator.run() -> exit code       │  │
│  └──────────────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────────────┤
│                          Orchestration Layer                       │
│  ┌──────────────────────┐    ┌────────────────────────────────┐    │
│  │  config.py           │    │  orchestrator.py               │    │
│  │  RoundtableConfig    │───▶│  run(config, task) -> Path     │    │
│  │  AgentConfig         │    │  for turn in turns:            │    │
│  │  StopConfig          │    │    pick_speaker()              │    │
│  │  (Pydantic v2)       │    │    adapter.invoke(prompt)      │    │
│  │  YAML loader         │    │    transcript.append(turn)     │    │
│  └──────────────────────┘    │    if stop.check(transcript):  │    │
│                              │      break                     │    │
│                              └────┬─────────┬─────────┬───────┘    │
├───────────────────────────────────┼─────────┼─────────┼────────────┤
│                          Pluggable Layer                           │
│         ┌─────────────────────────┘         │         └────────┐   │
│         ▼                                   ▼                  ▼   │
│  ┌─────────────┐                ┌──────────────────┐    ┌────────┐ │
│  │ adapters/   │                │ transcript.py    │    │ stop_  │ │
│  │  base.py    │                │ Transcript       │    │ cond.. │ │
│  │  claude.py  │                │   .append(turn)  │    │ Strat- │ │
│  │  gemini.py  │                │   .render() str  │    │ egies  │ │
│  │  codex.py   │                │   .write(path)   │    │ +      │ │
│  │  (Protocol) │                │  (md + JSONL)    │    │ AnyOf  │ │
│  └──────┬──────┘                └──────────────────┘    └────────┘ │
│         │ subprocess.run(["claude","-p", prompt],                  │
│         │   capture_output=True, text=True,                        │
│         │   encoding="utf-8", errors="replace",                    │
│         │   timeout=N, shell=False)                                │
├─────────┼──────────────────────────────────────────────────────────┤
│         ▼                       External CLI Processes             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                    │
│  │  claude    │  │  gemini    │  │  codex     │                    │
│  │  (subproc) │  │  (subproc) │  │  (subproc) │                    │
│  └────────────┘  └────────────┘  └────────────┘                    │
│   (each authenticated by user's existing CLI login session)        │
└────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility (single sentence) | Why this boundary |
|-----------|----------------------------------|-------------------|
| `cli.py` | Parse argv via Click, locate `ultra-claude.yaml`, dispatch to orchestrator, set process exit code. | Click's group/subcommand model + `[project.scripts]` entry point keeps CLI logic separable from logic. Aligns with [Click's official "packaging entry points" guide](https://click.palletsprojects.com/en/stable/entry-points/). |
| `config.py` | Define Pydantic v2 schema (`RoundtableConfig`, `AgentConfig`, `StopConfig`); load from YAML; emit user-friendly errors. | Pydantic gives free validation with localized error messages — a `model_validate(yaml.safe_load(f))` one-liner replaces hand-rolled checks ([Pydantic docs](https://docs.pydantic.dev/latest/concepts/models/)). |
| `orchestrator.py` | Drive the round-robin loop: pick speaker, render prompt from transcript, call adapter, append turn, check stop condition. | The "loop" *is* the value prop — keep it small (~80 lines), no class needed (see "Single function vs class" below). |
| `transcript.py` | Own the canonical conversation state: append `Turn` records, render to markdown, persist to disk, optional re-load. | Single source of truth for the run's state. Decouples "how a turn looks on disk" from orchestrator semantics. |
| `adapters/base.py` | Define the `Adapter` Protocol: `name: str`, `invoke(prompt: str, *, timeout: float) -> str`. | `typing.Protocol` (not ABC) — third parties can drop in any class with that shape, no inheritance required. See [PEP 544](https://peps.python.org/pep-0544/). |
| `adapters/{claude,gemini,codex}.py` | One file per CLI: shell out via `subprocess.run`, normalize errors, return text. ~30-50 lines each. | Per-file split is justified because each CLI has different argv conventions (`-p` vs `exec`), error shapes, and possibly future env-var quirks. |
| `stop_conditions.py` | Strategy classes (`Keyword`, `MaxTurns`, `FileExists`) + `AnyOf` composite, all implementing `StopCondition.check(transcript) -> bool`. | Strategy pattern with composable `AnyOf` is the textbook fit for "any of these terminates the run." |
| `presets/*.yaml` | Bundled package data: `debate.yaml` etc. shipped via Hatch's `force-include` or `package-data`. | Discoverable preset library is the demo path; ships as data, not code. |

### Push-Back on the Proposed Module Split

The user's proposal had **`agent.py` as a separate module**. Recommend **dropping it** for v1:

> An `Agent` is just a name + role-prompt + adapter handle. That's a 5-field Pydantic model living naturally in `config.py` as `AgentConfig`. A separate `agent.py` adds an import hop without behavior. If `Agent` accumulates real behavior in v2 (per-agent state, retry policy, tool gating), promote it then. **YAGNI for v1.**

Otherwise the split is sound. Concretely, the recommended layout is:

```
src/ultra_claude/
├── __init__.py          # __version__ only
├── cli.py               # click group + `run` subcommand
├── config.py            # Pydantic models + YAML loader (incl. AgentConfig)
├── orchestrator.py      # the loop, ~80 lines
├── transcript.py        # Turn dataclass + Transcript class
├── stop_conditions.py   # Strategy + AnyOf composite
├── adapters/
│   ├── __init__.py      # registry: name -> Adapter callable; entry-point loader
│   ├── base.py          # Protocol definition
│   ├── claude.py
│   ├── gemini.py
│   └── codex.py
├── presets/
│   ├── debate.yaml
│   └── (added in v2: plan_review.yaml, debug.yaml)
└── py.typed             # PEP 561 marker so consumers see your types
tests/
├── conftest.py          # pytest-subprocess `fp` fixture wiring + tmp_path helpers
├── test_cli.py
├── test_config.py
├── test_orchestrator.py
├── test_transcript.py
├── test_stop_conditions.py
├── test_adapters/
│   ├── test_claude.py
│   ├── test_gemini.py
│   └── test_codex.py
└── fixtures/
    ├── echo_cli.py      # the fake CLI binary — see Testing section
    └── debate.yaml
```

Project root files: `pyproject.toml`, `README.md`, `LICENSE`, `.gitignore`, `.github/workflows/test.yml`.

Source: [Click packaging entry points](https://click.palletsprojects.com/en/stable/entry-points/), [Hatch build configuration with src layout](https://hatch.pypa.io/latest/config/build/), [pyOpenSci packaging guide](https://www.pyopensci.org/python-package-guide/tutorials/get-to-know-hatch.html).

---

## Architectural Patterns

### Pattern 1: Adapter as `typing.Protocol` (not `abc.ABC`)

**What:** The contract is a structural type. Anyone can satisfy it by writing a class with `name` and `invoke()` — no `class MyAdapter(BaseAdapter):` required.

**When to use:** At system boundaries (plugins, adapters, third-party integrations) where you want maximum flexibility and the contract is small (1-2 methods). PEP 544 author's own guidance ([PEP 544](https://peps.python.org/pep-0544/)) and the consensus in the [Real Python Protocols guide](https://realpython.com/python-protocol/) and [Stanza's architecture course](https://www.stanza.dev/courses/python-architecture/protocols/python-architecture-protocols-vs-abc) both recommend Protocols for adapter/plugin boundaries.

**Trade-offs:**
- **Pro:** Third parties can drop in any class with the right shape — no inheritance, no need to import `ultra_claude.adapters.base`. Reduces coupling at the boundary.
- **Pro:** Mocks in tests work without a metaclass dance.
- **Con:** No runtime enforcement — a missing method shows up as `AttributeError` at call time, not at import. *Mitigation:* mark the Protocol `@runtime_checkable` and `isinstance(x, Adapter)`-check on registration.
- **Con:** Less obvious to discover; the Protocol must be documented loudly in the README.

**Example:**
```python
# src/ultra_claude/adapters/base.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class Adapter(Protocol):
    """Spawns an LLM CLI as a subprocess. Implementations must be stateless w.r.t. the conversation; transcript context is passed in via `prompt`."""
    name: str

    def invoke(self, prompt: str, *, timeout: float) -> str:
        """Run the CLI with `prompt`, return stdout text. Raise AdapterError on failure."""
        ...
```

```python
# src/ultra_claude/adapters/claude.py
import subprocess
from .base import Adapter  # only for type-checking; not required for duck typing
from ..errors import AdapterError, AdapterTimeout

class ClaudeAdapter:
    name = "claude"

    def __init__(self, binary: str = "claude") -> None:
        self._binary = binary

    def invoke(self, prompt: str, *, timeout: float) -> str:
        try:
            result = subprocess.run(
                [self._binary, "-p", prompt],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                shell=False,
                check=False,
            )
        except FileNotFoundError as e:
            raise AdapterError(f"`{self._binary}` not on PATH; install Claude Code or set `binary:` in config") from e
        except subprocess.TimeoutExpired as e:
            raise AdapterTimeout(f"claude exceeded {timeout}s timeout") from e
        if result.returncode != 0:
            raise AdapterError(f"claude exited {result.returncode}: {result.stderr.strip()[:500]}")
        return result.stdout
```

> **Trade-off the user must explicitly choose:** ABC gives you runtime enforcement (instantiating an incomplete subclass raises immediately) and a place for shared helpers (`_run_subprocess()`). Protocol gives you zero-friction third-party adapters. **Recommendation: Protocol for the public contract, plus a small *internal* `_SubprocessAdapterMixin` (regular class, optional) for code reuse across the three bundled adapters.** This is the "Protocol at the boundary, ABC/mixin internally" pattern from the modern consensus.

### Pattern 2: Plugin Discovery via `[project.entry-points]`, with `import_string` Escape Hatch

**What:** Third-party adapters register themselves by adding to their `pyproject.toml`:

```toml
[project.entry-points."ultra_claude.adapters"]
ollama = "ultra_claude_ollama:OllamaAdapter"
```

`ultra-claude` discovers them at startup with `importlib.metadata.entry_points(group="ultra_claude.adapters")` and adds them to a name->factory registry. Built-in adapters are pre-registered in `adapters/__init__.py` so they don't need entry-points (that's circular for the package itself).

**When to use:** Once you have any external adapters at all. Modeled on pytest's `pytest11` group, Pygments' lexer/style discovery, and the Python Packaging Guide's [official plugin pattern](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/).

**Trade-offs:**
- **Pro:** Zero-config for the user — `pip install ultra-claude-ollama` and the adapter Just Appears.
- **Pro:** Standard Python idiom; new contributors recognize it.
- **Con:** Friction for one-off / private adapters: writing a `pyproject.toml` and `pip install -e .` is heavier than dropping a .py file in a folder.
- **Con:** Requires consumers to follow naming conventions and packaging discipline.

**Mitigation: Provide a YAML escape hatch.** YAML config can specify an adapter by **import path** without entry points:

```yaml
agents:
  - name: ollama
    adapter: "mypkg.MyAdapter"   # <-- arbitrary import path; loaded via importlib
    role: "..."
```

The loader falls back to `importlib.import_module(...)` + `getattr(...)` when the name isn't in the registry. This is **the best of both worlds**: entry points for "polished, packaged" adapters; import path for "I have a .py file in $PWD." Config validation rejects names that resolve to neither.

**Loading order at startup:**
1. Register built-ins (`claude`, `gemini`, `codex`) into the registry.
2. Iterate `entry_points(group="ultra_claude.adapters")` and register each.
3. At config load, for each `agents[].adapter` value: lookup in registry; if missing, treat as import path and load lazily.

Source: [Python Packaging User Guide — Creating and discovering plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/), [importlib.metadata docs](https://docs.python.org/3/library/importlib.metadata.html), [pytest plugin discovery](https://docs.pytest.org/en/stable/how-to/writing_plugins.html).

### Pattern 3: Orchestrator as a Single Function (not a class)

**What:** `def run(config: RoundtableConfig, task: str, *, log: Logger) -> Path:` — a top-level function that owns the loop. State that needs to persist across iterations (turn counter, transcript, registry) lives as locals.

**When to use:** When the loop has one entry point, no concurrency, and all state is local. Adding a class adds attribute lookups and `self.` prefixes for no functional benefit — and tests can't easily reuse a half-run state object anyway.

**Trade-offs:**
- **Pro:** Fewer moving parts. Reads top-to-bottom.
- **Pro:** Easier to test — pass mock adapters in via the registry, assert on the returned `Path`.
- **Con:** If v2 adds parallel speakers (a "speaker_chooses" turn order with concurrent agents), a class with `_pending_turns: list[Future]` becomes nicer. **Plan for promotion, not premature class-ification.**

**Example skeleton:**
```python
# src/ultra_claude/orchestrator.py
import logging
from pathlib import Path
from .config import RoundtableConfig
from .transcript import Transcript, Turn
from .adapters import resolve_adapter
from .stop_conditions import build_stop_condition
from .errors import AdapterError, AdapterTimeout

log = logging.getLogger("ultra_claude.orchestrator")

def run(config: RoundtableConfig, task: str, *, output_dir: Path) -> Path:
    transcript = Transcript(task=task, agents=config.agents)
    adapters = {a.name: resolve_adapter(a) for a in config.agents}
    stop = build_stop_condition(config.stop)

    speakers = list(config.agents)  # round-robin
    for turn_idx in range(config.stop.max_turns):
        agent = speakers[turn_idx % len(speakers)]
        prompt = transcript.render_prompt(for_agent=agent)
        log.info("turn %d: %s thinking...", turn_idx, agent.name)
        try:
            output = adapters[agent.name].invoke(prompt, timeout=config.timeout_per_turn)
        except AdapterTimeout as e:
            log.warning("turn %d: %s timed out: %s", turn_idx, agent.name, e)
            transcript.append(Turn.timeout(agent.name, str(e)))
            continue  # other agents continue
        except AdapterError as e:
            log.error("turn %d: %s failed: %s", turn_idx, agent.name, e)
            transcript.append(Turn.error(agent.name, str(e)))
            if config.abort_on_error:
                break
            continue
        transcript.append(Turn(agent=agent.name, content=output))
        if stop.check(transcript):
            log.info("stop condition met after turn %d", turn_idx)
            break
    return transcript.write(output_dir)
```

**Error policy decision (call out for the user):** *One adapter throws — what does the loop do?* Recommend **continue by default, with a `abort_on_error: bool = false` config knob**. A timed-out Codex shouldn't kill a 30-minute roundtable. Errors are written into the transcript as `## codex (error)` blocks so subsequent agents see "Codex couldn't respond" and can comment.

### Pattern 4: Transcript as Dual Format — Markdown (canonical) + JSONL (sidecar)

**What:** Each run produces two files:

```
runs/2026-05-02T14-30-12_debate/
├── transcript.md      # human-readable canonical form, also re-prompted to agents
└── transcript.jsonl   # one Turn per line, machine-parseable for resume/analysis
```

**Why both:** The user's question lists three competing constraints (readable artifact, re-promptable input, parseable). Markdown alone handles the first two but not the third reliably (regex parsing of Markdown is fragile). JSONL alone handles 1.5 of them — agents can read JSONL but it's less natural in the prompt. The hybrid is what Claude Code itself does internally ([claude-JSONL-browser](https://github.com/withLinda/claude-JSONL-browser) tool exists exactly because Claude logs JSONL and people want Markdown).

**When to use:** Whenever you need the transcript to be both human-facing (the user reads it after the run) and tool-facing (a future `ultra-claude resume` reads it back). Adopt now even if `resume` is v3 — JSONL is essentially free to write.

**Trade-offs:**
- **Pro:** Markdown is what gets shown to agents in the next turn's prompt; JSONL is what `resume`/analysis tools consume. No fragile parsing of `## agent_name` headings.
- **Pro:** YAML frontmatter at the top of the .md captures run metadata (config snapshot, ultra-claude version, start timestamp) without polluting the conversation body.
- **Con:** Two write paths to keep in sync. *Mitigation:* `Transcript.append()` writes to both atomically; `write()` is the only filesystem write site.
- **Con:** Slightly larger storage (negligible — turns are 1-10 KB each).

**Example markdown form (canonical):**
```markdown
---
ultra_claude_version: "0.1.0"
preset: "debate.yaml"
agents:
  - {name: architect, adapter: claude}
  - {name: critic, adapter: gemini}
  - {name: implementer, adapter: codex}
started_at: 2026-05-02T14:30:12Z
task_file: task.md
---

# Task

Fix the failing auth test in test_auth.py.

# Turn 1 — architect (claude)

The failure looks like a missing fixture. We should…

# Turn 2 — critic (gemini)

I disagree about the fixture; the real issue is…

# Turn 3 — implementer (codex)

```diff
- def test_auth():
+ def test_auth(tmp_path):
```
```

**Example JSONL sidecar (one line per turn):**
```jsonl
{"turn":1,"agent":"architect","adapter":"claude","started_at":"2026-05-02T14:30:14Z","duration_s":12.4,"prompt_chars":1832,"output_chars":421,"content":"The failure looks like..."}
{"turn":2,"agent":"critic","adapter":"gemini","started_at":"2026-05-02T14:30:27Z","duration_s":9.1,"prompt_chars":2261,"output_chars":538,"content":"I disagree about..."}
```

**Re-prompting rule:** When building the prompt for turn N, the orchestrator concatenates the YAML frontmatter's `# Task` section + every Turn header & body up to N-1, plus a trailing `# Turn N — {agent} ({adapter})\n\n` so the agent is "speaking next." The agent doesn't need to know about the JSONL sidecar.

Source: [DEV: Markdown + frontmatter for agent tasks](https://dev.to/battyterm/the-case-for-markdown-as-your-agents-task-format-6mp), [claude-JSONL-browser README](https://github.com/withLinda/claude-JSONL-browser), [Frontmatter-First](https://medium.com/@michael.hannecke/frontmatter-first-is-not-optional-context-window-survival-for-local-llms-in-opencode-15809b207977).

### Pattern 5: Stop Conditions via Strategy + AnyOf Composite

**What:** Each stop condition is a small class with `check(transcript: Transcript) -> bool`. A composite `AnyOf([cond, cond, ...])` short-circuits on the first true.

**When to use:** Always. The user already listed three stop types; tomorrow's `regex_match`, `tool_called`, `cost_limit` slot in without touching the orchestrator.

**Trade-offs:**
- **Pro:** Each strategy is independently testable.
- **Pro:** YAML-configurable: `stop:` block lists conditions; `build_stop_condition` constructs the composite.
- **Con:** Slight indirection. For v1's two conditions, a single `if` would suffice — but the cost is one file and the payoff is "v2 added file_exists in 5 lines."

**Example:**
```python
# src/ultra_claude/stop_conditions.py
from typing import Protocol, Sequence
from pathlib import Path
from .transcript import Transcript

class StopCondition(Protocol):
    def check(self, transcript: Transcript) -> bool: ...

class Keyword:
    def __init__(self, words: Sequence[str], in_last_n_turns: int = 1) -> None:
        self.words = [w.upper() for w in words]
        self.window = in_last_n_turns

    def check(self, transcript: Transcript) -> bool:
        for turn in transcript.last(self.window):
            up = turn.content.upper()
            if any(w in up for w in self.words):
                return True
        return False

class MaxTurns:
    def __init__(self, n: int) -> None:
        self.n = n

    def check(self, transcript: Transcript) -> bool:
        return len(transcript.turns) >= self.n

class FileExists:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def check(self, transcript: Transcript) -> bool:
        return self.path.exists()

class AnyOf:
    def __init__(self, conditions: Sequence[StopCondition]) -> None:
        self.conditions = list(conditions)

    def check(self, transcript: Transcript) -> bool:
        return any(c.check(transcript) for c in self.conditions)

def build_stop_condition(cfg: "StopConfig") -> StopCondition:
    items: list[StopCondition] = [MaxTurns(cfg.max_turns)]
    if cfg.keywords:
        items.append(Keyword(cfg.keywords, in_last_n_turns=cfg.keyword_window))
    if cfg.file_exists:
        items.append(FileExists(cfg.file_exists))
    return AnyOf(items)
```

YAML form:
```yaml
stop:
  max_turns: 12
  keywords: ["AGREED", "SHIP IT"]
  keyword_window: 1     # only check the last turn
  file_exists: null     # v2
```

Source: [Refactoring Guru — Strategy in Python](https://refactoring.guru/design-patterns/strategy/python/example), [Real Python — Strategy pattern](https://realpython.com/lessons/implement-strategy-design-pattern/).

### Pattern 6: Logging — stdlib `logging` to stderr, plus optional Rich progress to stdout

**What:** Use the **stdlib `logging` module**, configured at CLI startup, with a single named logger tree (`ultra_claude.*`). Logs go to **stderr**. Stdout is reserved for the run's "result" output (the final transcript path). Rich is used **only** for the live "agent is thinking" indicator and is auto-disabled when stdout/stderr is not a TTY.

**Why not structlog for v1:** Adds a dependency and a learning surface for users who fork the package, with little benefit at v1's scale (a single user watching a single run). The [Dash0 2026 Python logging guide](https://www.dash0.com/guides/python-logging-libraries) and structlog's own [best practices](https://www.structlog.org/en/stable/logging-best-practices.html) note that *practices matter more than the library*. Stick to stdlib + reserve `structlog` for v2 if/when JSON output is requested.

**When to use Rich:** For the user-visible "Claude is thinking…" progress (Rich's `Status` spinner). It's already the dominant CLI UX library and integrates with Click via the `rich-click` ecosystem.

**Stdout vs stderr discipline:**
- **stdout:** the path to the transcript on success (so `ultra-claude run task.md | xargs cat` works). Nothing else.
- **stderr:** all logs, all progress, all errors. This is the [Twelve-Factor logs convention](https://12factor.net/logs).
- **Logfile (optional):** `--log-file path.log` flag adds a `FileHandler`. Default off.

**Verbosity:** `-v / -vv` toggle log level (`INFO` / `DEBUG`). Default `WARNING`.

**Example wiring:**
```python
# src/ultra_claude/cli.py
import logging
import sys
import click
from rich.logging import RichHandler

@click.group()
@click.option("-v", "--verbose", count=True)
def cli(verbose: int) -> None:
    level = [logging.WARNING, logging.INFO, logging.DEBUG][min(verbose, 2)]
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False, console=...)],
    )
```

Sources: [Click + entry points](https://click.palletsprojects.com/en/stable/entry-points/), [Rich progress display](https://rich.readthedocs.io/en/stable/progress.html), [Better Stack — structlog guide](https://betterstack.com/community/guides/logging/structlog/).

### Pattern 7: Live Progress — Rich `Status` spinner, replaced per turn

**What:** Wrap each `adapter.invoke(...)` call in a `with rich.status.Status(f"{agent.name} ({agent.adapter}) is thinking…")` so the user sees:

```
⠋ architect (claude) is thinking…    [00:14]
```

After the call returns, print a one-line summary (`✓ architect (claude) — 421 chars in 12.4s`) and start the next status. **Critically, the spinner runs on the main thread** because `subprocess.run` is blocking and Rich's `Status` uses an async refresh thread internally that doesn't conflict — see [Rich progress docs](https://rich.readthedocs.io/en/stable/progress.html). No threading needed in our code.

**TTY guard:** Rich auto-detects non-TTY stderr and degrades to plain text, so piping `ultra-claude run task.md > out.log 2> err.log` produces clean linewise logs in `err.log`.

Sources: [Brian Linkletter — Rich status module](https://brianlinkletter.com/2021/03/using-python-rich-library-status-module/), [Rich progress display](https://rich.readthedocs.io/en/stable/progress.html).

---

## Data Flow

### Run Flow (one `ultra-claude run task.md` invocation)

```
                     ┌─────────────────┐
                     │  ultra-claude.  │
                     │      yaml       │
                     └────────┬────────┘
                              │ yaml.safe_load
                              ▼
   argv ──▶ cli.py ──▶ Config ──▶ Orchestrator.run(config, task)
                                          │
                                          │ for turn in turns:
                                          ▼
                              ┌──────────────────────┐
                              │  Transcript.render_  │
                              │  prompt(for_agent)   │ (read prior turns)
                              └──────────┬───────────┘
                                         │ str
                                         ▼
                              ┌──────────────────────┐
                              │  adapter.invoke(     │
                              │     prompt, timeout) │
                              └──────────┬───────────┘
                                         │ subprocess.run(...)
                                         ▼
                              ┌──────────────────────┐
                              │  external CLI proc   │  (claude/gemini/codex)
                              │   stdout: turn text  │
                              └──────────┬───────────┘
                                         │ str
                                         ▼
                              ┌──────────────────────┐
                              │ Transcript.append(   │
                              │   Turn(...))         │  (writes .md + .jsonl)
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │ stop.check(transcript)?
                              └──────────┬───────────┘
                                         │ false: next turn
                                         │ true:  break
                                         ▼
                                 transcript.path
                                         │
                                         ▼
                                stdout: <path>
                                exit code: 0
```

### Failure Flow

```
adapter.invoke()
    │
    ├── FileNotFoundError    ──▶  AdapterError("`claude` not on PATH; install Claude Code")
    │                                  │
    │                                  ▼
    │                             Turn.error(agent, msg) appended
    │                                  │
    │                                  ▼
    │                             config.abort_on_error?
    │                                  ├── true:  break loop, exit 1
    │                                  └── false: continue with next agent
    │
    ├── TimeoutExpired        ──▶  AdapterTimeout(...) ──▶ Turn.timeout(agent, msg) ──▶ continue
    │
    └── returncode != 0       ──▶  AdapterError(stderr.strip()[:500]) ──▶ Turn.error ──▶ same as above
```

### Plugin Discovery Flow (startup)

```
ultra_claude.adapters.__init__.py loaded
    │
    ├── register("claude",  ClaudeAdapter)   # builtin
    ├── register("gemini",  GeminiAdapter)   # builtin
    ├── register("codex",   CodexAdapter)    # builtin
    │
    └── for ep in importlib.metadata.entry_points(group="ultra_claude.adapters"):
            cls = ep.load()
            register(ep.name, cls)            # third-party

config.py.resolve_adapter(agent_config)
    │
    ├── name in registry?       ──▶ instantiate
    │
    └── else: import_module(name) + getattr(...)  ──▶ instantiate (escape hatch)
```

---

## Suggested Build Order

The user requested fine granularity. Here is the natural dependency chain so each phase ships a usable slice:

| Phase | Title | Ships | Depends On | Verification |
|-------|-------|-------|-----------|--------------|
| **0** | Repo skeleton | `pyproject.toml` (hatch), `src/ultra_claude/__init__.py`, `LICENSE`, `README.md` stub, `.gitignore`, `.github/workflows/test.yml` (matrix). | — | `pip install -e .` succeeds; `pytest` runs (zero tests). |
| **1** | Config & errors | `config.py` (Pydantic models, YAML loader), `errors.py` (`AdapterError`, `AdapterTimeout`, `ConfigError`). | Phase 0 | `RoundtableConfig.from_yaml(path)` round-trips a fixture YAML; pytest asserts validation errors. |
| **2** | Transcript | `transcript.py` (Turn dataclass, Transcript class, append/render/write). | Phase 1 (uses `AgentConfig` in metadata). | Unit test: append three turns, render markdown, parse JSONL back. |
| **3** | Adapter Protocol + one adapter (`ClaudeAdapter`) | `adapters/base.py`, `adapters/claude.py`, `adapters/__init__.py` (registry, no entry-points yet). | Phase 0 | Unit test with `pytest-subprocess`: `fp.register([...])` and assert `invoke` returns expected text. |
| **4** | Stop conditions | `stop_conditions.py` (Strategy + AnyOf, plus `Keyword` and `MaxTurns`). | Phase 2 (consumes Transcript). | Unit test: synthesize transcripts, assert `check()` results. |
| **5** | Orchestrator | `orchestrator.py` (the `run` function). | Phases 1-4 | Unit test with mock adapters: assert N turns happen, transcript written, stop condition observed. |
| **6** | CLI entry point | `cli.py` (Click group + `run` subcommand), `[project.scripts]` in `pyproject.toml`, bundled `presets/debate.yaml`. | Phase 5 | E2E test using `pytest-subprocess` faking the CLIs: `ultra-claude run task.md` produces a transcript file. |
| **7** | Other adapters (`Gemini`, `Codex`) | `adapters/gemini.py`, `adapters/codex.py`. | Phase 3 (Adapter contract) | Adapter unit tests parallel to Claude's. |
| **8** | Cross-platform polish | Verify on Windows runner: encoding, path quoting, no `cmd` window flash, signal handling for timeouts. | Phase 6 | GitHub Actions matrix passes on `windows-latest`, `macos-latest`, `ubuntu-latest`. |
| **9** | Live progress UI | Rich Status spinner in `cli.py`, summary lines per turn. | Phase 6 | Manual smoke test on a real run; ensure non-TTY output is clean. |
| **10** | Documentation & v0.1.0 release | README with quickstart, GIF placeholder, "extending to new CLIs" guide. Tag and `hatch publish`. | Phase 9 | `pip install ultra-claude` from PyPI works on a clean machine. |

**Why this order:**
- Config → Transcript → Adapter → Stop → Orchestrator → CLI is the natural dependency stack. Each layer is testable without the next.
- Cross-platform polish (Phase 8) intentionally lands *after* Phase 7 because Windows quirks are most exposed when all three adapters run, not just one.
- Live progress UI (Phase 9) is the only piece you can defer past v0.1.0 if needed (the run still works without a spinner). Everything before it is mandatory for the "agents debate end-to-end" promise.
- Phases are small enough that each PR is reviewable independently. Phases 1-5 each deliver a green test suite for a single module.

**v2 phases (after v0.1.0 ships):**
- 11: Plugin entry-points discovery + import-path escape hatch.
- 12: Additional stop conditions (`FileExists`, `RegexMatch`).
- 13: `speaker_chooses` turn order.
- 14: Auto-publish on tag (`PYPI_TOKEN` secret + tag-triggered workflow).
- 15: Examples directory with real recorded transcripts.

---

## Cross-Platform Concerns (Windows-Specific Call-Outs)

### 1. Subprocess Encoding (the #1 Windows footgun)

**Problem:** `subprocess.run(..., text=True)` on Windows uses the **OEM codepage** (e.g., cp1252 on US English, GBK on Chinese systems) to decode child stdout, *not* UTF-8. This crashes on emoji, Asian text, or any non-ASCII output. ([CPython issue #105312](https://github.com/python/cpython/issues/105312), [bugs.python.org #6135](https://bugs.python.org/issue6135).)

**Solution:** **Always pass `encoding="utf-8", errors="replace"`** explicitly. This was already in the project constraints; reinforce in every adapter.

```python
subprocess.run(
    [self._binary, "-p", prompt],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",     # never crash on a single bad byte
    timeout=timeout,
    shell=False,          # never; we control argv
    check=False,          # we inspect returncode ourselves
)
```

**`PYTHONIOENCODING` is not enough** — that only affects the parent's stdio, not subprocess decoding.

### 2. `shell=False` is mandatory

Pass `args` as a **list** (`["claude", "-p", prompt]`), never a string. Reasons:
- Avoids shell injection if `prompt` contains shell metacharacters.
- Avoids quoting headaches across platforms (Windows `cmd` quoting is gnarly and differs from POSIX).
- `shell=True` on Windows hides exit codes for some CLIs.

### 3. CLI Discovery — `.exe`, `.cmd`, `.bat` on Windows

**Problem:** A user installs `claude` via `npm i -g @anthropic-ai/claude-code`, which on Windows places `claude.cmd` (a shim script) on PATH, not `claude.exe`. `subprocess.run(["claude", ...])` works because Python's `subprocess` resolves PATHEXT, **but** if you ever use `shutil.which("claude")` to pre-validate, you must include `.cmd` and `.bat` in PATHEXT (the default does on Windows).

**Mitigation:** Use `shutil.which(name)` for pre-flight ("CLI found / not found") error messages. Don't hardcode `.exe`.

### 4. No `CREATE_NO_WINDOW` Flash for v1 (skip)

If the user runs `ultra-claude` from a non-terminal context (Windows scheduled task, GUI launcher), each subprocess can briefly flash a console window. Setting `creationflags=subprocess.CREATE_NO_WINDOW` (Windows-only) suppresses this. **Skip for v1** — interactive CLI use is the only blessed path; if v2 sprouts a service-mode, add this then.

### 5. Timeout Behavior

`subprocess.run(timeout=N)` works cross-platform. On timeout, Python sends:
- POSIX: `SIGKILL` after the `terminate()` grace period.
- Windows: `TerminateProcess()` (the Win32 equivalent of `kill -9`; no grace period, but no zombie risk either since Windows has no zombies).

Both cases raise `subprocess.TimeoutExpired`. **Catch it** and surface as `AdapterTimeout` so the orchestrator can decide whether to abort or continue. ([Python subprocess docs](https://docs.python.org/3/library/subprocess.html), [bugs.python.org #25942](https://bugs.python.org/issue25942).)

### 6. Path Handling

Use `pathlib.Path` everywhere. Never string-concatenate paths with `/` or `\\`. `Path("runs") / "2026-05-02_debate" / "transcript.md"` is identical on all OSes.

### 7. Test Matrix on GitHub Actions

```yaml
# .github/workflows/test.yml (sketch)
strategy:
  fail-fast: false
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    python-version: ["3.10", "3.11", "3.12", "3.13"]
```

`fail-fast: false` so one Windows-only failure doesn't abort the macOS run while you're debugging. Source: [GitHub Actions Python matrix guide](https://docs.github.com/en/actions/guides/building-and-testing-python).

### 8. Line Endings in Transcript Files

Open transcript writes with `newline="\n"` so Windows doesn't `\r\n`-pollute the markdown. Test by reading the file back with `Path.read_bytes()` and asserting `b"\r\n" not in data`.

```python
self.path.open("a", encoding="utf-8", newline="\n").write(...)
```

---

## Testing Architecture

### The Subprocess Test Problem

**Tension:** CI runs without `claude`/`gemini`/`codex` installed. So adapter tests cannot literally invoke the CLIs. But fully mocking `subprocess.run` makes tests dance around the abstraction (you assert "we called subprocess with these args" — pure tautology).

**Recommended layered approach:**

#### Layer 1 — Adapter unit tests with `pytest-subprocess`

Use the [`pytest-subprocess`](https://pypi.org/project/pytest-subprocess/) plugin's `fp` fixture to register canned subprocess responses. This replaces `subprocess.run` itself, not the adapter, so we test the adapter's argv construction, stderr handling, and return parsing.

```python
# tests/test_adapters/test_claude.py
def test_claude_adapter_invokes_with_prompt(fp):
    fp.register(
        ["claude", "-p", "fix the auth test"],
        stdout="The fix is to add tmp_path fixture.",
    )
    adapter = ClaudeAdapter()
    output = adapter.invoke("fix the auth test", timeout=30)
    assert "tmp_path" in output

def test_claude_adapter_raises_on_timeout(fp):
    fp.register(["claude", "-p", "x"], wait=10)  # simulate hang
    adapter = ClaudeAdapter()
    with pytest.raises(AdapterTimeout):
        adapter.invoke("x", timeout=0.1)

def test_claude_adapter_raises_on_missing_binary(fp):
    fp.register(["claude", "-p", fp.any()], returncode=127)  # or use FileNotFoundError simulation
    # ...
```

Source: [pytest-subprocess on PyPI](https://pypi.org/project/pytest-subprocess/), [Simon Willison's TIL](https://til.simonwillison.net/pytest/pytest-subprocess).

#### Layer 2 — Integration tests with a fake CLI binary

Ship a tiny Python script `tests/fixtures/echo_cli.py` that mimics the real CLIs' interface:

```python
# tests/fixtures/echo_cli.py
"""Fake CLI used in integration tests. Behaves like `claude -p <prompt>`."""
import sys
import time
import os

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "-p":
        prompt = sys.argv[2]
        # Configurable failure modes via env vars for adversarial tests
        if os.environ.get("ECHO_CLI_FAIL"):
            print("simulated failure", file=sys.stderr)
            sys.exit(1)
        if delay := os.environ.get("ECHO_CLI_DELAY"):
            time.sleep(float(delay))
        # Echo a stable response that integration tests can assert on
        print(f"ECHO[{prompt[:40]}...]")
        sys.exit(0)
    print("usage: echo_cli.py -p <prompt>", file=sys.stderr)
    sys.exit(2)
```

Then point the adapter at it:

```python
# tests/test_orchestrator_e2e.py
def test_full_run_writes_transcript(tmp_path, monkeypatch):
    fake = sys.executable, str(Path(__file__).parent / "fixtures" / "echo_cli.py")
    config = RoundtableConfig(
        agents=[
            AgentConfig(name="a", adapter=ClaudeAdapter(binary=fake[1]), role="..."),
            # Or pass via factory: ClaudeAdapter(binary_argv=[*fake])
        ],
        stop=StopConfig(max_turns=3),
    )
    path = run(config, task="hello", output_dir=tmp_path)
    assert path.exists()
    content = path.read_text("utf-8")
    assert "ECHO[hello..." in content
```

This tests the **whole pipeline end-to-end** — config → orchestrator → real `subprocess.run` → real fake-CLI → real transcript file — without any production CLI installed. **Worth shipping.** It catches subprocess argv assembly, encoding, file IO, and CLI flag parsing in one go.

> **Adapter constructor takes a `binary` parameter** so tests can substitute the fake without monkeypatching PATH. Production callers pass nothing and get the default (`"claude"`, `"gemini"`, `"codex"`).

#### Layer 3 — Manual smoke tests (uncommitted)

A `scripts/smoke_test.sh` that runs the real `ultra-claude` against the real CLIs on a trivial task. Documented in CONTRIBUTING.md, run by maintainer before tagging a release. **Not** in CI — that would require API-authenticated CLIs in CI which contradicts the project's "no API keys" pitch.

### Test Pyramid Summary

```
       ▲
       │
       │   smoke_test.sh (manual, pre-release)
       │
       ├── orchestrator E2E tests with fake CLI binary  (~5-10 tests)
       │
       │     adapter integration tests (pytest-subprocess `fp`)  (~10-20 tests)
       │
       │           unit tests (config, transcript, stop_cond, errors)  (~30-50 tests)
       ▼
```

Sources: [pytest-subprocess docs](https://pytest-subprocess.readthedocs.io/), [Simon Willison's pytest-subprocess TIL](https://til.simonwillison.net/pytest/pytest-subprocess), [pytest-mock](https://pypi.org/project/pytest-mock/).

---

## Anti-Patterns

### Anti-Pattern 1: A `BaseAgent` ABC with `_run_turn`, `_format_prompt`, `_parse_output`, etc.

**What people do:** Treat each agent as a class hierarchy with five hookable methods, "for extensibility."

**Why it's wrong:** The abstraction is the **adapter** (call a CLI), not the **agent** (a name + role-prompt). Bundling agent logic with adapter logic into a fat `BaseAgent` ABC means every third party needs to subclass it and override 3-of-5 methods, half of which they didn't need to touch. Also collides with the user's existing `agent.py` instinct — and `Agent` doesn't *do* anything in v1, it's data.

**Do this instead:** Keep `AgentConfig` as data (Pydantic model in `config.py`) and `Adapter` as a tiny Protocol in `adapters/base.py`. The orchestrator owns turn formatting; agents are just inputs.

### Anti-Pattern 2: Per-adapter prompt templating ("Claude wants prompts formatted differently")

**What people do:** Each adapter overrides a `format_prompt(transcript) -> str` method to build its CLI-specific prompt.

**Why it's wrong:** All three target CLIs accept arbitrary prose via `-p`/`exec`. The prompt format is the user's choice (per-agent role text + transcript context), not the CLI's. Putting prompt-templating in adapters splatters one logical concern (prompt construction) across three adapters and forces third parties to re-implement it.

**Do this instead:** `Transcript.render_prompt(for_agent: AgentConfig) -> str` builds the prompt centrally. Adapters take a string and run a CLI — nothing more.

### Anti-Pattern 3: Mocking `subprocess.run` directly with `monkeypatch.setattr`

**What people do:** `monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult(...))` in every adapter test.

**Why it's wrong:** Brittle (every test has bespoke mock setup), tautological (asserts "we called subprocess.run" — meaningless), misses argv assembly bugs (you stub the call away), and breaks when an adapter switches to `subprocess.Popen` for streaming in v3.

**Do this instead:** Use `pytest-subprocess`'s `fp` fixture (intercepts at the OS-call layer; verifies your real argv) for unit-ish tests, plus a fake CLI binary for E2E.

### Anti-Pattern 4: Streaming output in v1 ("but the user wants to see Claude type")

**What people do:** Switch from `subprocess.run` to `subprocess.Popen` + `stdout=PIPE` line-reading, just to surface progress.

**Why it's wrong:** Out of scope per `PROJECT.md`. Per-CLI special-casing for streaming markers blows up the simple model. Each turn is one LLM call — Rich's `Status` spinner already gives the user "thinking" feedback without per-CLI surgery.

**Do this instead:** Block on `subprocess.run`. Show a Rich spinner. After the call returns, print the result section. **Defer streaming to v3** if it's ever requested (it probably won't be — the transcript is the artifact).

### Anti-Pattern 5: "I'll just use `os.system` / `shell=True`"

**What people do:** `subprocess.run(f"claude -p {prompt}", shell=True)`.

**Why it's wrong:** Shell injection if `prompt` contains `;`, `|`, `` ` ``, etc. Inconsistent quoting between Linux/macOS (POSIX shell) and Windows (`cmd.exe`). Lost ability to programmatically inspect argv in tests.

**Do this instead:** Always pass argv as a list with `shell=False`.

### Anti-Pattern 6: Rolling your own YAML schema validation

**What people do:** Hand-write `if "agents" not in raw: raise ValueError(...)` and friends.

**Why it's wrong:** Pydantic v2 already does this with localized error messages, type coercion, and JSON-schema export for free. Hand-rolled validation diverges from the schema and gives bad errors.

**Do this instead:** `RoundtableConfig.model_validate(yaml.safe_load(f))`. Pydantic's [error format](https://docs.pydantic.dev/latest/errors/validation_errors/) is already good.

---

## Integration Points

### External Services (the spawned CLIs)

| Service | Integration Pattern | Notes / Gotchas |
|---------|---------------------|-----------------|
| Claude Code (`claude`) | `subprocess.run(["claude", "-p", prompt], ...)` | One-shot mode. Requires user logged in via `claude login`. Returns text on stdout, JSON on `--output-format json` (not used in v1). |
| Gemini CLI (`gemini`) | `subprocess.run(["gemini", "-p", prompt], ...)` | Same shape as Claude. Requires `gcloud auth` or Gemini-specific auth. |
| Codex CLI (`codex`) | `subprocess.run(["codex", "exec", prompt], ...)` | Subcommand syntax differs (`exec`, not `-p`). Adapter encodes this. |

**Common gotchas across all three:**
- All can be missing on PATH — adapter raises `AdapterError` with install hint.
- All can hit CLI-side rate limits → non-zero exit + stderr message. Treat as an `AdapterError` so the run continues if `abort_on_error=false`.
- All can output ANSI color codes if they detect a TTY. **Mitigation:** subprocess pipes are not TTYs by default, so most CLIs auto-disable color. If a CLI doesn't, strip ANSI in the adapter using `re.sub(r"\x1b\[[0-9;]*m", "", output)` before returning.

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `cli.py` ↔ `orchestrator.py` | Direct function call: `run(config, task, output_dir=...)` | One entry point. CLI translates argv & exit codes; orchestrator is unaware of Click. |
| `orchestrator.py` ↔ `adapters/*` | Protocol method call: `adapter.invoke(prompt, timeout=...)` | The most-decoupled boundary. Orchestrator uses the registry; never imports specific adapters. |
| `orchestrator.py` ↔ `transcript.py` | Direct method calls: `Transcript.render_prompt`, `Transcript.append` | Orchestrator owns the Transcript instance for a run. |
| `orchestrator.py` ↔ `stop_conditions.py` | Strategy: `stop.check(transcript)` | Composite is built once at run start; checked each turn. |
| `config.py` ↔ everywhere | Pydantic models passed by value | Immutable inputs after parse. Orchestrator never mutates config. |

---

## Scaling Considerations

This is a **local CLI**, not a service — "scale" here means *complexity of a run*, not *concurrent users*.

| Run scale | Architecture posture |
|-----------|---------------------|
| **2-3 agents, 1-12 turns** (v1 target) | Single-threaded round-robin loop. ~Seconds-to-minutes per run. **Current design is sufficient.** |
| **5-10 agents, 50+ turns** (v2 power user) | Same loop. Watch transcript size — at ~10 KB/turn × 500 turns = 5 MB, prompt rendering becomes a real cost. **Add per-turn prompt-truncation strategy** (last N turns + summary). |
| **Parallel speakers** (hypothetical v3 "swarm") | Orchestrator becomes a class with `concurrent.futures.ThreadPoolExecutor`. Keep `subprocess.run` (each thread blocks; we have I/O parallelism). The single-function design promotes naturally. |

### What Breaks First

1. **Transcript prompt size.** At 500 turns × 10 KB = 5 MB, you start hitting individual CLIs' context-window limits before you hit any orchestrator limit. Add summarization or sliding-window before fixing imagined orchestrator bottlenecks.
2. **Subprocess startup latency.** Each turn pays the full `claude` startup cost (~1-2s). For 100-turn runs that's ~3 minutes of pure cold-start. **No fix in v1** — subprocesses are the model. v3 might explore CLI's daemon mode if available.
3. **YAML config human-readability.** At 10+ agents, YAML gets unwieldy. **Add `extends:` / preset-inheritance** in config schema before the file becomes unreadable.

---

## Architecture Trade-Offs the User Should Know

These are the calls where you should decide explicitly, not by accident:

1. **Protocol vs ABC for `Adapter`** — Protocol recommended (boundary), with a small internal mixin for code reuse across the three bundled adapters. **Locking in Protocol means** "third parties don't subclass anything," which we should advertise loudly in README. (See Pattern 1.)

2. **Single function vs class for orchestrator** — Function recommended for v1. Promote to class when you need concurrent speakers. (See Pattern 3.)

3. **Markdown-only vs Markdown+JSONL transcript** — Hybrid recommended. Costs negligible IO; pays off the first time someone wants to write a `resume` or `analyze` tool. (See Pattern 4.)

4. **Plugin discovery: entry-points only vs entry-points + import-path** — Both, with import-path as the escape hatch for private adapters. (See Pattern 2.)

5. **Error policy: abort-on-first-error vs continue-and-log** — Continue by default (timeouts and rate limits shouldn't kill a multi-agent debate), with `abort_on_error: bool` config knob. (See Pattern 3.)

6. **Drop `agent.py` from proposed module split** — `Agent` is data, lives in `config.py` as `AgentConfig`. Promote to its own module if it grows real behavior in v2. (See "Push-Back" section.)

7. **stdlib `logging` vs `structlog`** — stdlib for v1. Switch to structlog only if/when JSON log output is requested by users. (See Pattern 6.)

8. **Rich for progress UI** — Yes, but only for the live "thinking" indicator. Don't let Rich creep into core orchestration logic. (See Pattern 7.)

---

## Sources

### Primary (HIGH confidence — Context7 / official docs)

- [PEP 544 — Protocols: Structural subtyping](https://peps.python.org/pep-0544/) — adapter Protocol pattern.
- [Click — Packaging Entry Points](https://click.palletsprojects.com/en/stable/entry-points/) — `[project.scripts]` for CLI entry, `[project.entry-points]` for plugins. (Verified via Context7 `/pallets/click`.)
- [Click — Advanced Groups and Context](https://click.palletsprojects.com/en/stable/commands/) — group/subcommand pattern for `ultra-claude run`.
- [Pydantic v2 docs — Models](https://docs.pydantic.dev/latest/concepts/models/) — `model_validate`, nested models, config. (Verified via Context7 `/pydantic/pydantic`.)
- [Python Packaging User Guide — Creating and discovering plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) — entry-points group convention.
- [importlib.metadata docs](https://docs.python.org/3/library/importlib.metadata.html) — `entry_points(group=...)` API.
- [Python subprocess docs](https://docs.python.org/3/library/subprocess.html) — `run`, `TimeoutExpired`, `shell=False`, encoding parameters.
- [Hatch build configuration](https://hatch.pypa.io/latest/config/build/) — `src/` layout with hatchling.
- [pyOpenSci packaging guide — Get to know Hatch](https://www.pyopensci.org/python-package-guide/tutorials/get-to-know-hatch.html) — modern PyPI package layout.

### Tooling (HIGH confidence)

- [pytest-subprocess](https://pypi.org/project/pytest-subprocess/) — `fp` fixture for faking subprocess in unit tests.
- [pytest-subprocess docs](https://pytest-subprocess.readthedocs.io/) — registration semantics, behavior modes.
- [pytest-mock](https://pypi.org/project/pytest-mock/) — `mocker` fixture wrapper.
- [Rich — Progress Display](https://rich.readthedocs.io/en/stable/progress.html) — Status spinner used for "thinking" UI.

### Patterns & guides (MEDIUM confidence — single secondary source, but consistent with primary docs)

- [Real Python — Python Protocols: Leveraging Structural Subtyping](https://realpython.com/python-protocol/) — Protocol vs ABC trade-offs.
- [Stanza — Protocols vs Abstract Base Classes](https://www.stanza.dev/courses/python-architecture/protocols/python-architecture-protocols-vs-abc) — "Protocol at boundary, ABC internally" pattern.
- [Refactoring Guru — Strategy in Python](https://refactoring.guru/design-patterns/strategy/python/example) — Strategy pattern reference.
- [Better Stack — structlog guide](https://betterstack.com/community/guides/logging/structlog/) — when to escalate from stdlib logging.
- [Dash0 — Choosing a Python Logging Library in 2026](https://www.dash0.com/guides/python-logging-libraries) — practices > library.

### Cross-platform / Windows (HIGH confidence — CPython issue tracker)

- [CPython issue #105312 — subprocess.run() defaults to wrong text encoding under Windows](https://github.com/python/cpython/issues/105312)
- [bugs.python.org issue #6135 — subprocess seems to use local encoding](https://bugs.python.org/issue6135)
- [bugs.python.org issue #25942 — Do not immediately SIGKILL on ^C](https://bugs.python.org/issue25942)
- [GitHub Docs — Building and testing Python](https://docs.github.com/en/actions/guides/building-and-testing-python) — matrix workflow.

### Transcript format (MEDIUM confidence — extrapolated from adjacent ecosystem)

- [DEV — The Case for Markdown as Your Agent's Task Format](https://dev.to/battyterm/the-case-for-markdown-as-your-agents-task-format-6mp)
- [claude-JSONL-browser](https://github.com/withLinda/claude-JSONL-browser) — proof Claude Code itself uses JSONL internally; markdown is the human-facing layer.
- [Frontmatter-First (OpenCode)](https://medium.com/@michael.hannecke/frontmatter-first-is-not-optional-context-window-survival-for-local-llms-in-opencode-15809b207977) — YAML frontmatter as structured metadata in markdown.
- [Twelve-Factor — Logs](https://12factor.net/logs) — stdout/stderr discipline.

---

*Architecture research for: ultra-claude (subprocess-based multi-agent orchestrator)*
*Researched: 2026-05-02*
