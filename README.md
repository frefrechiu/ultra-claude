# ultra-claude

> Three CLI agents debating your problem in a transcript file -- using only your existing CLI logins.

[![PyPI version](https://img.shields.io/pypi/v/ultra-claude.svg)](https://pypi.org/project/ultra-claude/)
[![Python versions](https://img.shields.io/pypi/pyversions/ultra-claude.svg)](https://pypi.org/project/ultra-claude/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<!-- GIF placeholder: a 30-second cast of `ultra-claude run --preset debate --inline "Should we add an undo button?"` showing three agents take turns. Lands post-launch. -->
<!-- ![ultra-claude in action](docs/demo.gif) -->

## Quickstart

```bash
pip install ultra-claude
ultra-claude doctor
ultra-claude run --preset debate --inline "Should we add an undo button?"
```

That's it. If `ultra-claude doctor` reports any of the three CLIs as `FAIL`, follow the per-CLI install + login instructions:

| CLI | Install | Login |
|-----|---------|-------|
| `claude` | <https://docs.claude.com/en/docs/claude-code/setup> | `claude login` |
| `gemini` | <https://github.com/google-gemini/gemini-cli> | `gemini auth login` |
| `codex` | <https://github.com/openai/codex> | `codex login` |

## Why this exists

Most multi-agent LLM frameworks force you to wire up API keys for every model. That works, but it means:

1. You're paying per-token instead of using your existing $20/month subscriptions.
2. You're wiring up auth for every vendor instead of leveraging the auth you already did to log into the official CLIs.
3. The framework owns the conversation -- not you. The transcript lives inside an SDK abstraction.

ultra-claude inverts those trade-offs:

- **No API keys.** It invokes `claude -p`, `gemini -p`, and `codex exec` as subprocesses. Whatever auth you set up to use the CLIs interactively also works here.
- **Three viewpoints.** A 3-agent roundtable (Architect on Claude, Critic on Gemini, Implementer on Codex) hits the same problem from three different model architectures. When all three reach `AGREED`, that's a stronger signal than one model's confidence.
- **The transcript IS the memory.** Every turn appends to a markdown file you can `tail -f`. That file is the entire state of the run -- there's no SDK, no vector store, no hidden context. You can re-prompt it, archive it, paste it into a PR description, anything.

## Config example

Drop a `ultra-claude.yaml` in any directory and run `ultra-claude run task.md`. Or use the bundled `--preset debate` (this is its YAML, verbatim):

```yaml
agents:
  - name: Architect
    role: high-level design
    adapter: claude
    system_prompt: |
      You design system architecture. Prioritize simplicity, explicit data flow,
      and minimal dependencies. Push back on over-engineering. Lead with constraints.

  - name: Critic
    role: skeptic
    adapter: gemini
    system_prompt: |
      You poke holes in proposed designs. Reference past production failures.
      Challenge assumptions. Ask "what happens when X fails?" Be ruthless but constructive.

  - name: Implementer
    role: hands-on coder
    adapter: codex
    system_prompt: |
      You write the actual code. Flag any unbuildable parts of the proposed design.
      Estimate effort. Push back on vague requirements with specific clarifying questions.

max_turns: 9
stop_keywords:
  - AGREED
  - SHIP IT
```

Field reference:

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `agents[].name` | str | required | Display name (e.g. "Architect") |
| `agents[].role` | str | required | Short label (e.g. "high-level design") |
| `agents[].adapter` | `claude` \| `gemini` \| `codex` | required | Which CLI drives this agent |
| `agents[].system_prompt` | str | required | Per-agent system prompt prepended every turn |
| `max_turns` | int | `12` | Hard cap; orchestrator stops once reached |
| `stop_keywords` | list[str] | `["AGREED", "DONE"]` | Stops when seen in the last 2 turns from 2 distinct agents |
| `turn_order` | `round_robin` | `round_robin` | Only legal v1 value |
| `transcript_path` | path | auto | Default: `./ultra-claude-transcript.md` |
| `abort_on_error` | bool | `false` | If true, halt on first adapter failure (default: continue with placeholder turn) |

## Extending to new CLIs

ultra-claude treats CLIs as plug-in subprocesses. Adding a fourth CLI takes ~10 lines:

```python
# my_pkg/myadapter.py
from ultra_claude.adapters.base import _SubprocessAdapterMixin

class MyAdapter(_SubprocessAdapterMixin):
    name = "mycli"
    cli_name = "mycli"
    auth_error_markers = ("please run `mycli login`", "not authenticated")

    def invoke(self, prompt: str, timeout: int) -> str:
        return self._run_subprocess(["mycli", "--prompt-stdin"], prompt, timeout)
```

The `_SubprocessAdapterMixin` enforces the safe-subprocess contract for free: stdin-piped prompts (Windows ~8 KB cmd.exe argv limit defense), UTF-8 with `errors="replace"`, mandatory timeout, cross-platform process-tree kill, and the empty-stdout defense that catches the live `codex exec` 0.124.0+ TTY bug ([openai/codex#19945](https://github.com/openai/codex/issues/19945)).

The structural `Adapter` Protocol (`typing.Protocol`, `runtime_checkable`) means third-party adapters do NOT need to inherit from anything. Any class with `name: str` and `invoke(prompt: str, timeout: int) -> str` qualifies. Per the v1 policy in [CONTRIBUTING.md](CONTRIBUTING.md), third-party adapters live in their own packages -- ultra-claude's core ships only the three bundled adapters (claude / gemini / codex).

## Trademark disclaimer

ultra-claude is an independent open-source project. It is not affiliated with, endorsed by, or sponsored by Anthropic, Google, or OpenAI.

- "Claude" is a trademark of Anthropic.
- "Gemini" is a trademark of Google.
- "Codex" is a trademark of OpenAI.

ultra-claude is a third-party orchestrator that invokes their respective official CLIs as subprocesses.

## Links

- **PyPI:** <https://pypi.org/project/ultra-claude/>
- **GitHub:** <https://github.com/frefrechiu/ultra-claude>
- **License:** [MIT](LICENSE)
- **Changelog:** [CHANGELOG.md](CHANGELOG.md)
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)

## Status

v0.1.0 -- first functional release. The previous `0.0.1` was a never-uploaded name-reservation stub.
