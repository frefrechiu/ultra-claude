# Phase 1: Project Skeleton & PyPI Name Reservation - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode, infrastructure-only phase per smart-discuss heuristic)

<domain>
## Phase Boundary

Reserve the PyPI name `ultra-claude` as a stub release and ship the bare repository scaffolding so every later phase has a working `pip install -e .` foundation.

Scope:
- `pyproject.toml` (hatchling backend, pinned deps for click/pydantic v2/pyyaml/dev tools)
- `LICENSE` (MIT) at repo root
- `.gitignore` (Python build artifacts + editor files)
- `src/ultra_claude/__init__.py` exposing `__version__ = "0.0.1"`
- `README.md` stub (placeholder — full README lands in Phase 9)
- Build artifacts via `python -m build` and prep for manual `twine upload` of `0.0.1` stub
- `pip install -e ".[dev]"` works end-to-end in a clean virtualenv

Out of scope: actual ultra-claude functionality (later phases), Trusted Publishing OIDC (deferred to v2), v0.1.0 release (Phase 9).

</domain>

<decisions>
## Implementation Decisions

### Locked from CLAUDE.md / research/

- **Build backend:** hatchling (NOT full hatch CLI — `pip install -e ".[dev]"` is sufficient)
- **Python floor:** `>= 3.10` (3.10 EOLs 2026-10-31 — bump in late 2026)
- **Package layout:** `src/ultra_claude/` (src layout, not flat)
- **Runtime deps (pinned):** `click >= 8.3.3`, `pydantic >= 2.13.3`, `pyyaml >= 6.0.3`
- **Dev deps (pinned):** `ruff >= 0.13`, `mypy >= 1.18`, `pytest >= 8.4`, `pytest-mock`, `pytest-cov`, `pytest-subprocess`, `build`, `twine`
- **License:** MIT (single LICENSE file at repo root, SPDX `MIT` in pyproject.toml)
- **`__version__` source-of-truth:** literal in `src/ultra_claude/__init__.py`. `pyproject.toml` reads it via `[tool.hatch.version] path = "src/ultra_claude/__init__.py"`. Single source — no duplication.
- **Stub package contents (0.0.1):** just the `__init__.py` with `__version__` and a one-line module docstring. NO CLI entry point yet (Phase 8 ships that). NO functional imports. The 0.0.1 release exists only to squat the name.
- **PyPI publishing:** v1 uses manual `python -m build && twine upload` from the maintainer's machine. Trusted Publishing (OIDC) deferred to v2.
- **Project URLs:** GitHub repo `https://github.com/frefrechiu/ultra-claude` (set in pyproject.toml `[project.urls]`).

### Claude's Discretion

- Exact text of stub README (1-3 lines pointing at GitHub for now)
- `[project]` description text in pyproject.toml (one short sentence)
- Specific `.gitignore` entries beyond standard Python (add: `.venv/`, `dist/`, `build/`, `*.egg-info/`, `__pycache__/`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`, `.coverage`, editor files like `.vscode/`, `.idea/`, OS files like `.DS_Store`, `Thumbs.db`)
- Whether to ship a `CHANGELOG.md` skeleton at this phase (recommend: yes, with `## 0.0.1` heading only — keeps Phase 9's release work mechanical)
- Whether to add CI scaffolding files this phase (recommend: NO — CI lint test lands in Phase 4 per ROADMAP, full CI in Phase 9)

### PyPI Upload Step (REQUIRES USER ACTION)

- The 0.0.1 upload itself **cannot** be performed autonomously — it requires the user's PyPI API token / `~/.pypirc` / Trusted Publishing config.
- Plan must end with a clearly-flagged "Run this manually" task: `python -m build && twine upload dist/ultra_claude-0.0.1*` with documented prerequisites (PyPI account, `__token__` configured).
- The CI lint test for `subprocess.run` discipline is NOT in this phase (lands in Phase 4 per ROADMAP — TST-05 is in Phase 4's requirements, not Phase 1).

</decisions>

<code_context>
## Existing Code Insights

Greenfield repository. No prior code. Project root contains only:
- `.planning/` (PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md, research/, config.json)
- `CLAUDE.md` (project instructions — locked constraints listed above)

No reusable assets, no patterns to mirror — this phase establishes the patterns for everything else.

</code_context>

<specifics>
## Specific Ideas

- The squat protection is the entire point of this phase per Pitfall #5 in research/PITFALLS.md. The 0.0.1 stub is a **functional** sdist+wheel that installs and imports cleanly — not an empty placeholder — so PyPI does not yank it.
- Verify `python -c "import ultra_claude; print(ultra_claude.__version__)"` prints exactly `0.0.1` after `pip install -e .` — this success criterion is testable and must hold.

</specifics>

<deferred>
## Deferred Ideas

- Trusted Publishing (PyPI OIDC) — v2
- GitHub Actions release workflow — Phase 9 introduces CI; release workflow is post-v0.1.0
- pre-commit hooks — not in v1 scope
- `py.typed` marker file — recommended for v0.1.0 (Phase 9), not for the 0.0.1 stub

</deferred>

---

*Phase: 01-project-skeleton-pypi-name-reservation*
*Context auto-generated 2026-05-02 (autonomous mode + infrastructure-only phase)*
