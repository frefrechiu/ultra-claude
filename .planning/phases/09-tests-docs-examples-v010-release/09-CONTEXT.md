# Phase 9: Tests, Docs, Examples & v0.1.0 Release - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode — final phase)

<domain>
## Phase Boundary

Lock the v1 quality bar (test coverage, type checks, README/CONTRIBUTING/examples) and prepare `v0.1.0` for manual PyPI release.

Scope:
- Bump `__version__` from "0.0.1" to "0.1.0" in `src/ultra_claude/__init__.py`
- `README.md` — full README replacing the stub from Phase 1: 1-line pitch, GIF placeholder block, 3-command quickstart, "why this exists" section, config example, "extending to new CLIs" pointer at the `Adapter` Protocol
- `CONTRIBUTING.md` — dev setup (`pip install -e ".[dev]"`), how to add an adapter (subclass `_SubprocessAdapterMixin`, implement `name`/`cli_name`/`auth_error_markers`/`invoke`), v1 policy that core ships only the three bundled adapters
- `CHANGELOG.md` — flesh out `## [0.1.0]` section with the v1 feature list
- `examples/` directory with one captured transcript + its YAML config (uses fake/mock data since real CLI invocations are not autonomous-feasible)
- `tests/fixtures/echo_cli.py` — fake CLI that echoes prompt back, used for E2E orchestrator tests (TST-04)
- `tests/test_e2e_with_echo_cli.py` — E2E tests using the fake CLI script (verifies the full pipeline beyond mocked-subprocess unit tests)
- Add `pytest-cov` test invocation to verify coverage > 80% on `src/ultra_claude/`
- Build artifacts: `python -m build` produces wheel + sdist for 0.1.0
- Document the `twine upload dist/ultra_claude-0.1.0*` command for the user (must run manually with their PyPI creds)

Out of scope: Trusted Publishing OIDC (deferred to v2), GitHub Actions release workflow (post-v0.1.0)

</domain>

<decisions>
## Implementation Decisions

### Locked from REQUIREMENTS.md (PKG-01, PKG-06, PRE-02, TST-01..04, TST-06, TST-07, DOC-01, DOC-02)

#### Version bump (PKG-06)

`src/ultra_claude/__init__.py`:
- Change `__version__ = "0.0.1"` to `__version__ = "0.1.0"`
- Update CHANGELOG.md `[Unreleased]` -> `[0.1.0]` heading + dated entry

#### README.md (DOC-01)

Sections (in order):
1. Title + 1-line pitch ("Three CLI agents debating your problem in a transcript file — using only your existing CLI logins")
2. GIF placeholder block (markdown comment placeholder; user adds real GIF post-launch)
3. Quickstart (3 commands: `pip install ultra-claude`, then `ultra-claude doctor`, then `ultra-claude run --preset debate --inline "Should we add an undo button?"`)
4. "Why this exists" — value prop: no API keys, three viewpoints, transcript IS the memory
5. Config example — paste the bundled `presets/debate.yaml` and explain the fields
6. "Extending to new CLIs" — short guide to the `Adapter` Protocol with a 10-line GeminiAdapter-style example
7. Trademark disclaimer (Claude/Gemini/Codex are vendor trademarks)
8. Links: PyPI, GitHub, license

#### CONTRIBUTING.md (DOC-02)

Sections:
1. Dev setup: clone, `pip install -e ".[dev]"`, `pytest`
2. Adding an adapter: structural diagram + minimal example
3. v1 policy: core ships only claude/gemini/codex; third-party adapters live in their own packages
4. PR checklist: tests, mypy --strict, ruff check, README mention if user-visible
5. How to file an issue (link to GitHub issues)

#### `examples/` directory (PRE-02)

- `examples/debate.yaml` — copy of `presets/debate.yaml` (so users see what a config file looks like outside the package)
- `examples/transcripts/sample-debate.md` + `.jsonl` — a synthetic 3-turn transcript captured from the FakeAdapter test infrastructure. Annotated header explaining "this is a synthetic example; real runs require Claude/Gemini/Codex CLIs installed and logged in"
- `examples/README.md` — orient users; instructions to capture their own transcript

#### `tests/fixtures/echo_cli.py` (TST-04)

A small standalone Python script that:
- Reads stdin (the prompt)
- Prints "echo: " + prompt to stdout
- Exits 0
- Used by E2E test as a fake CLI: monkey-patch the registry to return an adapter whose `cli_name` invokes this script

The E2E test confirms:
- subprocess.Popen IS being called (not mocked at the Popen level)
- the prompt makes it via stdin
- the orchestrator's transcript writing is wired correctly

#### Coverage check (TST-06, TST-07)

Run `pytest --cov=src/ultra_claude --cov-report=term-missing` in plan execution. Assert `coverage > 80%` (TST-06). Document the actual coverage in SUMMARY.

If coverage falls short, add focused unit tests for uncovered branches.

#### Build + release prep (PKG-01, PKG-06)

- Run `python -m build` to produce `dist/ultra_claude-0.1.0.tar.gz` and `dist/ultra_claude-0.1.0-py3-none-any.whl`
- Update `.planning/phases/01-project-skeleton-pypi-name-reservation/PUBLISH.md` to add v0.1.0 commands (the existing PUBLISH.md is for the 0.0.1 stub release; this phase appends v0.1.0 instructions)
- Smoke-test: `pip install dist/ultra_claude-0.1.0-py3-none-any.whl` in a clean venv → `ultra-claude --version` prints `0.1.0`; `ultra-claude run --preset debate --inline "test" --dry-run` works
- The actual `twine upload` is a USER ACTION — same as Phase 1's stub upload

#### Module structure (after this phase)

```
ultra-claude/                  # repo root
├── README.md                  # rewritten from stub
├── CONTRIBUTING.md            # NEW
├── CHANGELOG.md               # updated for 0.1.0
├── LICENSE
├── pyproject.toml
├── .gitignore
├── src/ultra_claude/
│   ├── __init__.py            # __version__ = "0.1.0"
│   ├── cli.py
│   ├── config.py
│   ├── exceptions.py
│   ├── orchestrator.py
│   ├── registry.py
│   ├── stop_conditions.py
│   ├── transcript.py
│   ├── adapters/...
│   └── presets/debate.yaml
├── tests/
│   ├── test_*.py               # all existing
│   ├── test_e2e_with_echo_cli.py    # NEW
│   └── fixtures/
│       └── echo_cli.py        # NEW
├── examples/                   # NEW
│   ├── README.md
│   ├── debate.yaml
│   └── transcripts/
│       ├── sample-debate.md
│       └── sample-debate.md.jsonl
└── dist/
    ├── ultra_claude-0.1.0-py3-none-any.whl
    └── ultra_claude-0.1.0.tar.gz
```

### Claude's Discretion

- Tone of README — recommend: clear, terse, opinionated; no marketing-speak
- Length of CONTRIBUTING — recommend: short and actionable, not a manifesto
- Whether to add CI scaffolding (GitHub Actions YAML for `pytest+ruff+mypy` on push) — recommend: NO for v0.1.0 (post-release add-on, keeps the release diff focused)
- Whether to add `py.typed` marker — recommend: yes (types are valuable; one-line file)
- Whether to add `.pre-commit-config.yaml` — recommend: NO (deferred to v2)

</decisions>

<code_context>
## Existing Code Insights

After Phases 1-8:
- 83/83 tests pass
- Full CLI works (`ultra-claude --version`, `--help`, `run`, `doctor`)
- All adapters implemented and tested
- Config validation, transcript IO, stop conditions, orchestrator all in place
- Phase 1's PUBLISH.md exists for the 0.0.1 stub upload — this phase adds the v0.1.0 upload instructions

The codebase is FUNCTIONALLY COMPLETE after Phase 8. Phase 9 is the polish + ship pass.

</code_context>

<specifics>
## Specific Ideas

- Phase 9 is the only phase that needs to TOUCH multiple existing files extensively (README.md was a stub, CHANGELOG.md needs flesh, __init__.py version bump, pyproject.toml might want new classifiers like `Development Status :: 4 - Beta`)
- The e2e echo CLI test is the difference between "we mocked subprocess and it works" and "the real Popen pipe-stdin path works end-to-end". Important.
- The user's manual `twine upload` for v0.1.0 closes PKG-06; it's the only success criterion that requires a human action.

</specifics>

<deferred>
## Deferred Ideas

- GitHub Actions CI workflow — post-v0.1.0 (separate PR after the user confirms v0.1.0 is published)
- Trusted Publishing (PyPI OIDC) — v2
- Documentation site (mkdocs/Sphinx) — not v1
- Coverage badge in README — added after CI lands
- Pre-commit hooks — v2

</deferred>

---

*Phase: 09-tests-docs-examples-v010-release*
*Context auto-generated 2026-05-02 (autonomous mode — final phase)*
