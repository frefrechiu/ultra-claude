# Milestones: ultra-claude

Historical record of shipped versions.

---

## v0.1.0 — Release (shipped 2026-05-02)

**Status:** Complete
**Phases:** 9 (1-9, all complete)
**Plans:** 19
**Tests:** 86 passing
**Coverage:** 85% on `src/ultra_claude/`
**Test suite passes** in clean venv with NONE of claude/gemini/codex CLIs installed (uses pytest-subprocess + tests/fixtures/echo_cli.py).
**Known deferred items at close:** 1 (Phase 1 PyPI upload `human_needed` — twine upload requires user PyPI credentials; runbook in `.planning/milestones/v0.1.0-phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md`)

### Delivered

A Python CLI that orchestrates Claude Code, Gemini CLI, and Codex CLI as subprocesses to produce a transcript-based debate. Three CLI agents talk to each other via the transcript file — using only their existing CLI logins, no API keys.

### Key Accomplishments

1. **Subprocess invocation contract locked at one site** — `_SubprocessAdapterMixin._run_subprocess` enforces UTF-8/replace, stdin-piped prompts, mandatory timeout, list-form argv, shell=False, empty-stdout defense (catches the live `codex exec` 0.124.0+ TTY bug per `openai/codex#19945`), cross-platform process-tree kill (POSIX `os.killpg`, Windows `taskkill /T /F`). One mixin = three adapters get every safety property for free.
2. **CI lint tripwire (TST-05)** — `tests/test_subprocess_lint.py` AST-walks `src/ultra_claude/` and fails the build on any `subprocess.run`/`Popen` missing `text=True`/`encoding="utf-8"`/`errors="replace"` or with `shell=True`. Future regressions caught at PR time.
3. **Anchored regex + unanimity-window stop conditions** — `Keyword(["AGREED"])` rejects "I am NOT going to say AGREED yet" via `^AGREED\s*$` (multiline). Unanimity-window (default n=2 turns, m=2 distinct agents) blocks single-agent self-stopping. Mitigates Pitfall #4 (sycophantic false-consensus).
4. **Transcript module is the only durable state** — append-as-you-go markdown with HTML-comment sentinels (`<!-- turn:N agent:Name -->`) plus parseable JSONL sidecar. LF-only newlines, UTF-8 encoded, `tail -f` works during runs.
5. **Goal-anchor re-injection** — every per-turn prompt re-injects the original task at the END of the prompt, mitigating problem drift (Pitfall #6) without growing context window per turn.
6. **Continue-on-error orchestrator** — adapter errors mid-run log to stderr, append a placeholder turn, and the debate continues with remaining agents (configurable via `abort_on_error`).
7. **Zero API keys, three CLIs, one transcript** — the project's core value prop ships exactly: no Anthropic/Google/OpenAI API keys; subscription quotas via the user's existing CLI logins.
8. **Cross-platform from day one** — Windows is in scope. UTF-8 round-trip with em-dashes/smart quotes/emoji verified via E2E test using a real Popen pipe-stdin pipeline (no mocks) on Windows 11 + cp950 system codepage.

### Stats

- 9 phases / 19 plans / ~50 tasks
- ~25 commits
- ~1,400 LOC source (Python)
- ~1,800 LOC tests (Python)
- Test suite: 86 tests, 85% line coverage
- All 58 v1 requirements complete (PKG-01..PKG-07, CFG-01..CFG-05, TRX-01..TRX-05, ADP-01..ADP-08, STP-01..STP-05, ORC-01..ORC-06, CLI-01..CLI-11, PRE-01/PRE-02, TST-01..TST-07, DOC-01/DOC-02)

### Outstanding User Action

The agent does NOT have PyPI credentials. To finalize the release on PyPI, the user must run:

```bash
python -m twine upload dist/ultra_claude-0.1.0*
```

Per `.planning/milestones/v0.1.0-phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md` (post-archive path) — the artifacts are built, twine-checked, and ready. After upload, `pip install ultra-claude` from PyPI will close PKG-01 + PKG-06 + supersede PKG-05.

### Archives

- Roadmap: `milestones/v0.1.0-ROADMAP.md`
- Requirements: `milestones/v0.1.0-REQUIREMENTS.md`
- Audit: `milestones/v0.1.0-MILESTONE-AUDIT.md`

### Tag

`git tag v0.1.0` (locally — push to origin separately when ready).

---

*Generated 2026-05-02 by autonomous milestone close.*
