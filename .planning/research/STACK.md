# Stack Research

**Domain:** Python CLI tool — multi-agent orchestration via subprocess invocation
**Project:** ultra-claude
**Researched:** 2026-05-02
**Confidence:** HIGH

---

## TL;DR for the roadmapper

| Decision area | User proposed | Recommendation | Verdict |
|---|---|---|---|
| Build/packaging | `hatch` | **`hatchling` build backend (no `hatch` project manager required)** | CONFIRM with nuance — see below |
| CLI framework | `click >= 8.3` | **`click >= 8.3`** | CONFIRM |
| Config validation | `pydantic >= 2` | **`pydantic >= 2.13`** | CONFIRM |
| YAML loader | `pyyaml >= 6` | **`pyyaml >= 6.0.3`** (use `yaml.safe_load`) | CONFIRM |
| Testing | (pytest implied) | **`pytest >= 8`, `pytest-mock`, `pytest-cov`** | CONFIRM |
| Lint/format | (none specified) | **`ruff >= 0.13` (one tool replaces black+isort+flake8)** | NEW |
| Type checking | (none specified) | **`mypy >= 1.18` (skip pyright for v1)** | NEW |
| Subprocess style | `subprocess.run` (blocking) | **`subprocess.run` blocking with `timeout`, `text=True`, `encoding="utf-8"`, `errors="replace"`** | CONFIRM |
| Distribution | (PyPI) | **PyPI Trusted Publishing via `pypa/gh-action-pypi-publish` (no API tokens)** | NEW (defer to v2 per roadmap) |
| Docs | (README only implied) | **README + GitHub `gh-pages` for v2 (mkdocs-material)** | CONFIRM |
| Python minimum | `>= 3.10` | **`>= 3.10` for v0.1, plan to bump to `>= 3.11` post Oct 2026** | CONFIRM with timeline note |

**One critical finding for naming:** `ultra-claude`, `ultraclaude`, and `ultra_claude` are all **AVAILABLE on PyPI** (verified 2026-05-02). `consilium` and `roundtable` are taken — `consilium` is in fact a competing product (multi-model deliberation CLI by Terry Li, BUT it uses OpenRouter API keys, so the "no-API-key" pitch of ultra-claude is still differentiated). Ship as `ultra-claude`.

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | `>= 3.10` | Runtime | 3.10 supports `Literal`, `match`/`case`, modern type hints (`list[int]`). Note: 3.10 EOLs **2026-10-31**. Plan to bump minimum to 3.11 by end of 2026. |
| `click` | `>= 8.3.3` | CLI framework | Mature, stable decorator-based CLI; Click 8.3 requires Python 3.10+ (matches project minimum). Pallets project, used by Flask, Black, Mkdocs, etc. |
| `pydantic` | `>= 2.13.3` | Config validation | v2 has Rust core (`pydantic-core`), 5-50x faster than v1. `model_validate(yaml.safe_load(f))` is the canonical YAML config pattern (per Pydantic docs). |
| `pyyaml` | `>= 6.0.3` | YAML parsing | De-facto standard; widest community familiarity; `safe_load` is sufficient (no comment preservation needed for read-only config). |
| `hatchling` | `>= 1.29` | Build backend | PEP 517 build backend. Used standalone in `pyproject.toml` — no need for the full `hatch` project manager. Stable, PyPA-blessed, simple `[tool.hatch.build.targets.wheel]` config. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `>= 8.4` (or 9.x once stable) | Test runner | Universal Python test runner. Note: pytest 9.x requires Python 3.10+. Pin to `>= 8.4, < 10` for safety. |
| `pytest-mock` | `>= 3.15` | `mocker` fixture | Replaces verbose `with patch(...)` blocks with `mocker.patch(...)`. Cleaner for subprocess mocking patterns. Thin wrapper over `unittest.mock`. |
| `pytest-cov` | `>= 6.0` | Coverage reporting | Standard pytest coverage plugin; integrates `coverage.py`; emits XML for CI. |
| `ruff` | `>= 0.13` | Linter + formatter | Replaces `black`, `isort`, `flake8`, `pyupgrade`, `pydocstyle`, etc. in a single Rust-based tool. 10-100x faster than legacy chain. Config in `pyproject.toml`. |
| `mypy` | `>= 1.18` | Type checker | The standard for type-checking Python libraries. **Library users will type-check against your `py.typed` package using mypy** — making it the right choice for library-side validation. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `pip` | Install for development | `pip install -e ".[dev]"` after the package is initialized. No need for poetry/uv at the project-management level for v1. |
| `python -m build` | Build wheels/sdist | Stdlib-blessed, backend-agnostic. Equivalent to `hatch build` but without the extra dep. |
| `twine check` (optional) | Validate dist before publish | Run on built wheels in CI before uploading. Replaced by `pypa/gh-action-pypi-publish` in v2. |
| GitHub Actions | CI / publish | v1: pytest matrix on push/PR. v2: Trusted Publishing on `v*` tag. |
| `pypa/gh-action-pypi-publish` | PyPI release | OIDC-based, no API token required. Mandatory for v2. |

### What NOT to Add (Keep Surface Tight)

| Tool | Why Excluded |
|------|--------------|
| `rich` / `rich-click` | Adds 1-2 MB transitive deps; v1 transcript output is plain markdown to a file; terminal output is minimal `click.echo`. Re-evaluate for v2 if interactive turn-by-turn UX is added. |
| `typer` | Built on Click; adds a layer of type-hint magic; no advantage at this scale where the CLI has 1-3 commands. Click is more transparent and the user already knows it. See "Alternatives Considered". |
| `pydantic-settings` | Designed for env-var/dotenv config; this project loads from a YAML file the user explicitly points at. `BaseModel.model_validate(yaml_dict)` is enough. |
| `ruamel.yaml` | Heavier API, comment-preservation we don't need. PyYAML is sufficient for read-only config. |
| `attrs` / `dataclasses-json` / plain `dataclasses` | Pydantic v2 wins on validation messages, JSON Schema, and ecosystem familiarity. Plain dataclasses give zero validation. |
| `asyncio` / `trio` / `anyio` | The roadmap explicitly excludes streaming output (PROJECT.md "Out of Scope"). Each turn is a discrete blocking call; async adds complexity without payoff. |
| `tomli` / `tomli-w` | Config is YAML, not TOML. Keep the format choice consistent. |
| `click-plugins`, `click-completion`, `click-help-colors` | Premature; v1 is a single `run` command. |
| `poetry` / `pdm` / full `hatch` project manager / `uv` for project mgmt | For a library this small, plain `pip` + `pyproject.toml` works. The user's preference for `hatch` is fine **as a build backend (`hatchling`) only** — they don't need to install or use the `hatch` CLI itself. |

---

## Installation

```bash
# Project init (one time)
python -m pip install --upgrade pip build

# Editable install with dev tools
pip install -e ".[dev]"

# Run tests
pytest

# Lint / format
ruff check .
ruff format .

# Type-check
mypy src/

# Build wheel + sdist
python -m build
```

`pyproject.toml` skeleton (for the roadmapper / scaffolder):

```toml
[build-system]
requires = ["hatchling>=1.29"]
build-backend = "hatchling.build"

[project]
name = "ultra-claude"
version = "0.1.0"
description = "Orchestrate Claude Code, Gemini CLI, and Codex CLI in a multi-agent debate — no API keys."
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [{ name = "frefrechiu" }]
keywords = ["claude", "gemini", "codex", "cli", "multi-agent", "llm", "subprocess"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Software Development",
    "Topic :: Utilities",
]
dependencies = [
    "click>=8.3",
    "pydantic>=2.13",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.4",
    "pytest-mock>=3.15",
    "pytest-cov>=6.0",
    "ruff>=0.13",
    "mypy>=1.18",
    "types-PyYAML",
]

[project.scripts]
ultra-claude = "ultra_claude.cli:main"

[project.urls]
Homepage = "https://github.com/frefrechiu/ultra-claude"
Issues = "https://github.com/frefrechiu/ultra-claude/issues"
Repository = "https://github.com/frefrechiu/ultra-claude.git"

[tool.hatch.build.targets.wheel]
packages = ["src/ultra_claude"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]
ignore = ["E501"]  # line length handled by formatter

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.10"
strict = true
warn_unused_ignores = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --cov=ultra_claude --cov-report=term-missing"
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `hatchling` (build backend only) | `uv_build` | If you want to also use `uv` as project manager. **In 2026, `uv` is the default for new projects per Astral**, but it's a *project manager + build backend*. Hatch's discussion thread #1867 confirms both are first-class. The user picked `hatch`; honor that. If they want to switch to `uv` later, the migration is `requires = ["hatchling"]` → `requires = ["uv_build"]` in `[build-system]`. |
| `hatchling` | `setuptools` | Avoid for new projects. setuptools still works but the API surface and history of `setup.py` add friction. |
| `hatchling` | `poetry-core` | Use only if your team already uses Poetry. `poetry-core` works, but Poetry's ecosystem has slipped behind uv in 2026. |
| `click` | `typer` | Use Typer if your CLI has many subcommands and benefits from type-hint inference. For a 1-3 command tool, `typer`'s magic is overhead. |
| `click` | `argparse` | Use argparse only if you want zero dependencies. Click is one tiny dep and gives you better UX (auto-help, prompts, colors, testing harness). |
| `click` | `rich-click` | Use only if you need colored help output. Adds `rich` as a transitive dep (~1.5 MB). Skip for v1, reconsider for v2 polish. |
| `pydantic v2` | `attrs` + `cattrs` | Use if you need *only* dataclass-style typing without validation. ultra-claude needs validation (helpful error messages on bad YAML). |
| `pydantic v2` | Plain `dataclasses` | Use if you have zero validation needs. Bad fit here — you want "agent name must not be empty", "max_turns > 0", etc. |
| `pyyaml` | `ruamel.yaml` | Use if you need to write YAML back with comments preserved. Not needed for read-only config. |
| `pytest-mock` | `unittest.mock` directly | Both work. `pytest-mock`'s `mocker` fixture is just nicer in pytest contexts. Pick one and stick with it. |
| `mypy` | `pyright` / `basedpyright` | Pyright is faster and ships in VS Code's Pylance. **However**, library *users* will run `mypy` against your package, so the library author should match what users will use. For a small library, just `mypy --strict` in CI is sufficient. |
| `mypy` | `ty` (Astral) | `ty` is in pre-release (alpha as of mid-2026). Don't bet on it for v0.1. Worth re-evaluating in 2027. |
| README only | MkDocs Material | Use MkDocs only when README outgrows ~500 lines. v1 README is enough. **PROJECT.md already calls for full docs in v2** — `mkdocs-material` + `mkdocs-click` is the right choice when you get there. |
| README only | Sphinx | Avoid for new small projects. RST syntax + heavier toolchain than needed. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `subprocess.Popen` directly with raw streams | Easy to deadlock on full pipe buffers; harder to set timeouts | `subprocess.run(cmd, capture_output=True, timeout=...)` |
| `subprocess.call` / `subprocess.check_output` | Older API, less ergonomic | `subprocess.run(cmd, check=True)` |
| `shell=True` in `subprocess.run` | Security hazard if any prompt content reaches the call; cross-platform shell quoting is hell | Pass a list `["claude", "-p", prompt]` and let Python handle spawning |
| Default subprocess encoding on Windows | Decodes as cp1252 / GBK / etc. — breaks on emoji or non-ASCII LLM output. Real bug in `SuperClaude_Framework` issue #492. | Explicit `encoding="utf-8", errors="replace", text=True` |
| `pipenv` | Dead — last meaningful release predates uv/hatch ecosystem maturation | `pip install -e ".[dev]"` |
| `requirements.txt` for app dev | Splits truth from `pyproject.toml` | `dependencies = [...]` in `pyproject.toml`; export only if a downstream consumer demands it |
| Pydantic v1 | EOL'd; v2 is 5-50x faster, better errors, JSON Schema 2020-12 | Pydantic v2.13+ |
| `flake8` + `black` + `isort` + `pyupgrade` chain | 4 tools, slow, conflicting configs | `ruff` (one tool, ~100x faster) |
| `tox` for matrix testing | Heavyweight; GitHub Actions matrix is enough for OSS at this scale | GH Actions `strategy.matrix` |
| `setup.py`, `setup.cfg` | Legacy; PEP 621 metadata in `pyproject.toml` is the standard | `pyproject.toml` `[project]` table |
| API tokens for PyPI publishing | Long-lived secret; theft = silent supply chain compromise | Trusted Publishing (OIDC) — see Distribution section |
| `print()` for CLI output | No way for tests to suppress; bypasses click's testing harness | `click.echo()` / `click.secho()` |
| `os.system` | Same problems as `shell=True` | `subprocess.run` with list args |

---

## Subprocess Invocation Pattern (Critical for v1)

The user proposed `subprocess.run` (blocking). **Confirmed correct.** No streaming-output pressure exists because:

1. PROJECT.md "Out of Scope" explicitly excludes "Real-time streaming output mid-turn"
2. Each turn is one discrete LLM call; the orchestrator simply needs the final string
3. No interactive UI in v1 — the transcript file is the UI
4. Async would force every adapter to be `async def` and force the orchestrator into an event loop — increases test mocking complexity (you'd need `pytest-asyncio` and async patches)

Canonical invocation pattern:

```python
import subprocess

def invoke(cmd: list[str], stdin_text: str | None = None, timeout: float = 120.0) -> str:
    """Cross-platform subprocess call returning combined stdout."""
    result = subprocess.run(
        cmd,
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",   # tolerate non-UTF-8 stderr on Windows
        timeout=timeout,
        check=False,        # let caller decide on non-zero
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{cmd[0]} exited {result.returncode}: {result.stderr.strip()[:500]}"
        )
    return result.stdout
```

Why each option:

- `text=True, encoding="utf-8"` — ensures consistent decoding; prevents Windows cp1252 / GBK surprises (cpython issue #105312, SuperClaude_Framework #492 are real bugs)
- `errors="replace"` — never crash on non-UTF8 byte from a misbehaving CLI; replace the byte with `?`
- `timeout=...` — required so a wedged CLI doesn't hang the orchestrator forever
- `capture_output=True` — captures stdout AND stderr; stderr surfaces in the error message
- `check=False` + manual `raise` — gives a friendlier error message than `CalledProcessError`'s default
- List `cmd`, never `shell=True` — security + cross-platform argument escaping

**Test mocking pattern (v1):**

```python
def test_claude_adapter(mocker):
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = subprocess.CompletedProcess(
        args=["claude", "-p", "hi"],
        returncode=0,
        stdout="hello back\n",
        stderr="",
    )
    adapter = ClaudeAdapter()
    out = adapter.invoke("hi", timeout=10)
    assert out == "hello back\n"
    mock_run.assert_called_once()
```

`pytest-mock` makes this 3 lines instead of nested `with patch(...)` context managers. It also auto-cleans up between tests.

---

## Distribution

### v1 (Manual Release for v0.1.0)

```bash
python -m build
python -m twine check dist/*
python -m twine upload dist/*  # using a one-time API token
```

Manual is fine for the first release. Keeps the v1 surface tight per PROJECT.md.

### v2 (Automated, Trusted Publishing)

PyPI Trusted Publishing **eliminates API tokens** and is the 2026 standard for OSS Python releases.

GitHub Actions workflow (`.github/workflows/release.yml`):

```yaml
name: Release
on:
  push:
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install build
      - run: python -m build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write    # mandatory for OIDC trusted publishing
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
```

Setup steps (one-time):
1. PyPI account → Project (`ultra-claude`) → Settings → Add a trusted publisher
2. Owner: `frefrechiu`, Repo: `ultra-claude`, Workflow: `release.yml`, Environment: `pypi`
3. GitHub repo → Settings → Environments → New environment `pypi`

This is **the** path the python-packaging community has converged on by 2026. Sigstore-signed attestations are now default-on.

### CI Test Matrix (also v2)

```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12', '3.13']
    os: [ubuntu-latest, macos-latest, windows-latest]
```

12-cell matrix. Drop `3.10` once it EOLs (Oct 2026). Add `3.14` once it stabilizes (released October 2025, mature in 2026). For initial v2: stick to 3.10–3.13 for first ship.

---

## Stack Patterns by Variant

**If user later wants async streaming output (v3+):**
- Switch adapter base class to `async def invoke(...)`
- Add `anyio>=4.0` (works with both asyncio and trio)
- Use `anyio.run_process` or `asyncio.create_subprocess_exec` with `proc.stdout` line streaming
- Update tests to use `pytest-anyio` plugin
- Note: Click 8.x supports async commands via `@click.command()` + `asyncio.run()` wrapper

**If user later wants speaker_chooses turn order (v2 per roadmap):**
- No stack change needed — pure orchestrator logic
- Maybe add `pydantic.discriminated_union` for `TurnPolicy` config variants

**If user later wants a config file in TOML instead of YAML:**
- Drop `pyyaml`, add `tomllib` (stdlib in 3.11+) or `tomli` (3.10 backport)
- Keep `pydantic` — `model_validate(tomllib.load(f))` works identically

**If 3.10 minimum becomes a problem (Oct 2026):**
- Bump to `requires-python = ">=3.11"` in a `0.x.0` version
- Gain: PEP 654 ExceptionGroup, stdlib `tomllib`, ~10% faster interpreter

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `click >= 8.3` | Python 3.10+ | Click 8.3.0 dropped 3.9 support. Aligns with project minimum. |
| `pydantic >= 2.13` | Python 3.9+ | Wider Python support than Click. Pydantic 2.x has been stable since June 2023. |
| `pyyaml >= 6.0` | Python 3.6+ | No surprises. 6.0.3 ships LibYAML wheels for major platforms. |
| `pytest 9.x` | Python 3.10+ | Pytest 9 dropped 3.9. Pin `< 10` for safety. |
| `hatchling >= 1.29` | Python 3.10+ for the *tool*, builds packages targeting any Python | Build-time only; consumer Python version is set by `requires-python`. |
| `mypy >= 1.18` | Any Python 3.9+ source | Mypy 1.18+ supports PEP 695, PEP 696. |
| `ruff >= 0.13` | Any Python source | Standalone Rust binary. |

Cross-cuts:
- **Pydantic v2 + PyYAML**: Pydantic's docs literally show this exact pattern (`yaml.safe_load` then `model_validate`). No friction.
- **Click 8 + Pydantic v2**: No conflict; Click handles arg parsing, Pydantic handles config-file validation. They don't intersect at the type level.
- **Hatchling + everything**: Hatchling is a build backend only — it has no runtime presence. No version conflicts possible.

---

## Critical Project Risks Flagged

### 1. Name availability — VERIFIED CLEAR

| Name | PyPI status | Action |
|------|-------------|--------|
| `ultra-claude` | **AVAILABLE** (404) | **Reserve immediately** by uploading a v0.0.1 placeholder if there's a long delay before v0.1.0. |
| `ultraclaude` | AVAILABLE | nice-to-have backup |
| `ultra_claude` | AVAILABLE | (same package as `ultra-claude` per PEP 503 normalization, so this is redundant) |
| `roundtable` | TAKEN — by Jim Kitchen, an unrelated table-data library (Python 2/3) | Avoid. |
| `consilium` | TAKEN — by Terry Li, **a competing multi-model deliberation CLI** but it uses OpenRouter API keys, not subprocess | Avoid name. **Note for positioning:** ultra-claude differentiates by *not requiring API keys* — this is your headline. Mention `consilium` in the README's "Alternatives" section to acknowledge prior art. |

**Action item for the roadmapper:** Flag a "claim PyPI name" task in v1, *before* any further public mentions of the name. PyPI normalizes `ultra-claude` and `ultra_claude` to the same package, so just `pip install ultra-claude` works.

### 2. Python 3.10 EOL is October 31, 2026

Project ships May 2026. That's ~6 months of supported runtime for the lowest version. Recommendation:
- Ship v0.1.0 with `requires-python = ">=3.10"` per user constraint
- Plan a v0.2.0 in late 2026 / early 2027 that bumps to `>=3.11`
- Document the policy in README ("Supports Python versions still receiving security updates")

### 3. Cross-platform Windows subprocess encoding

Real bug pattern in adjacent projects (e.g., `SuperClaude_Framework` issue #492). **Mitigation is the explicit `encoding="utf-8", errors="replace"` shown above.** Add a Windows row to the GHA test matrix.

### 4. CLI binary discovery

Users must have `claude`, `gemini`, or `codex` on `PATH`. The `BaseAdapter.invoke()` should:
- Catch `FileNotFoundError` from `subprocess.run`
- Raise a custom `AdapterUnavailable("claude CLI not found on PATH. Install: <link>")` exception
- Orchestrator catches and reports cleanly per PROJECT.md constraint

This isn't a stack decision but it's a stack-implication: factor it into the `BaseAdapter` ABC design.

---

## Sources

### Verified via Context7 (HIGH confidence)
- `/pypa/hatch` — `pyproject.toml` structure, entry-points, `[project.scripts]` schema
- `/pydantic/pydantic` — `BaseModel.model_validate(yaml.safe_load(f))` is the canonical YAML config pattern (per Pydantic's own examples docs)
- `/pallets/click` — `@click.group()` + `@click.command()` + `pass_context` pattern, testing harness
- `/astral-sh/ruff` — `pyproject.toml` config schema, `[tool.ruff.lint] select` rule selection
- `/astral-sh/uv` — `uv_build` is the new default backend as of July 2025

### Verified via PyPI JSON API (HIGH confidence, 2026-05-02)
- click 8.3.3 (released 2026-04-22), requires Python ≥3.10
- pydantic 2.13.3 (released 2026-04-20), requires Python ≥3.9
- pyyaml 6.0.3, ruamel.yaml 0.19.1
- hatch 1.16.5 (released 2026-02-27), hatchling 1.29.0
- uv 0.11.8 (released 2026-04-27)
- pytest 9.0.3, pytest-mock 3.15.1, pytest-cov 7.1.0
- ruff 0.15.12, mypy 1.20.2, pyright 1.1.409, basedpyright 1.39.3
- **`ultra-claude` PyPI name: AVAILABLE (HTTP 404)**
- `consilium` PyPI name: TAKEN by Terry Li's "Multi-model deliberation CLI"
- `roundtable` PyPI name: TAKEN by Jim Kitchen's table-data library

### Verified via official docs (HIGH confidence)
- [endoflife.date Python](https://endoflife.date/python) — Python 3.10 EOL = 2026-10-31, 3.11 = 2027-10-31
- [PyPI Trusted Publishing docs](https://docs.pypi.org/trusted-publishers/) — OIDC flow, Sigstore attestations now default-on
- [pypa/gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish) — `id-token: write` permission requirement
- [Astral uv build backend docs](https://docs.astral.sh/uv/concepts/build-backend/) — `uv_build` default since uv init July 2025
- [Hatch metadata config docs](https://github.com/pypa/hatch/blob/master/docs/config/metadata.md) — `[project.scripts]` and entry-point conventions

### WebSearch verified with multiple sources (MEDIUM confidence)
- Click vs Typer 2026 production guidance — multiple comparisons agree Click is the conservative choice for small CLIs, Typer for larger apps with type-hint inference benefit
- Hatch vs uv 2026 — uv is the trending default; hatch is still stable; hatchling-as-build-backend remains a fully valid choice
- Mypy vs pyright for libraries — library authors should match what library users use (mypy is still the common case)
- pytest-mock — convenience wrapper around `unittest.mock`; either is fine, picking one for consistency

### Cross-referenced known issues (HIGH confidence)
- [cpython issue #105312](https://github.com/python/cpython/issues/105312) — Windows subprocess UTF-8 encoding default
- [SuperClaude_Framework issue #492](https://github.com/SuperClaude-Org/SuperClaude_Framework/issues/492) — real-world UnicodeDecodeError on Windows in adjacent project

---

## Confidence Assessment

| Area | Confidence | Reasoning |
|------|------------|-----------|
| Build backend choice | HIGH | hatchling is PyPA-maintained, Pydantic itself uses it, user already prefers it; uv_build is also valid as a future swap |
| CLI framework (click) | HIGH | Click 8.3.3 verified current (April 2026 release), Python ≥3.10 requirement matches project, mature & stable |
| Pydantic v2 + PyYAML | HIGH | Verified via Pydantic's own example docs in Context7; canonical pattern |
| Testing stack | HIGH | pytest is universal; pytest-mock is the standard convenience layer; pytest-cov is the standard coverage integration |
| Linter (ruff) | HIGH | Astral's ruff has won the linter+formatter race in 2025-2026; verified via multiple sources and Context7 |
| Type checker (mypy) | MEDIUM-HIGH | Mypy is correct for libraries because users will check against your `py.typed` with mypy; pyright is also valid but less common in CI |
| Subprocess pattern | HIGH | Direct stdlib usage; cross-platform encoding pitfall verified via real bug reports in cpython tracker and a similar Claude-CLI project |
| PyPI Trusted Publishing | HIGH | Verified via PyPA official docs and pypa/gh-action-pypi-publish marketplace listing |
| Python ≥3.10 minimum | HIGH | endoflife.date confirms 3.10 EOL = 2026-10-31; user constraint matches |
| **PyPI name `ultra-claude` availability** | **HIGH** | **Verified 404 from `https://pypi.org/pypi/ultra-claude/json` on 2026-05-02** |
| Competitive positioning vs `consilium` | HIGH | Inspected `consilium`'s pyproject metadata — it requires `OPENROUTER_API_KEY`. ultra-claude's "no API keys, use existing CLI logins" is a clear differentiator. |

**Overall confidence: HIGH.** Every dependency version is verified against PyPI as of 2026-05-02. Every architectural decision has a stated rationale grounded either in Context7-verified library docs or in widely-corroborated 2026 community consensus.

---

*Stack research for: ultra-claude (Python CLI, multi-agent subprocess orchestration)*
*Researched: 2026-05-02*
