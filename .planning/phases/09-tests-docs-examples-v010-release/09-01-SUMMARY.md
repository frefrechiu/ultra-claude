---
phase: 09-tests-docs-examples-v010-release
plan: 01
subsystem: release-prep
tags: [release, version-bump, py.typed, changelog, pep561]
requirements: [PKG-06]
dependency_graph:
  requires:
    - 08-03 complete (Phase 8 fully closed; 83/83 tests passing as the regression baseline)
    - hatchling [tool.hatch.version] path = src/ultra_claude/__init__.py wired in pyproject.toml
  provides:
    - 0.1.0 version literal for hatchling to extract at build time (consumed by 09-04 python -m build)
    - PEP 561 py.typed marker for downstream typed users (consumed by 09-04 wheel)
    - CHANGELOG.md [0.1.0] section (referenced by 09-03 README "see CHANGELOG" link and by 09-04 release notes)
  affects:
    - All later 09-* plans depend on the 0.1.0 literal (09-04 wheel filename, 09-03 README install command)
tech_stack:
  added: []
  patterns: []
key_files:
  created:
    - src/ultra_claude/py.typed (0 bytes -- empty PEP 561 marker)
  modified:
    - src/ultra_claude/__init__.py (1 byte rearrangement: "0.0.1" -> "0.1.0"; same total length 162 bytes)
    - CHANGELOG.md (684 bytes -> 6776 bytes; rewritten to add v1 feature surface under [0.1.0])
decisions:
  - Version 0.1.0 chosen as the first functional release (the never-uploaded 0.0.1 was a name-reservation stub per Phase 1 PKG-05)
  - py.typed marker is empty (0 bytes) -- the smallest valid PEP 561 form; mypy detects by filename, never reads contents
  - CHANGELOG hyphen separator normalised from em-dash to ASCII hyphen ("## [0.0.1] - 2026-05-02") for consistency with the new [0.1.0] heading and Keep a Changelog convention
  - All three edits land in three atomic commits (one per task) for clean per-requirement bisection
metrics:
  duration: "276s (~4.6 min)"
  start: "2026-05-02T06:40:03Z"
  end: "2026-05-02T06:44:39Z"
  completed_date: "2026-05-02"
  tasks_completed: 3
  files_changed: 3
---

# Phase 9 Plan 1: Version Bump 0.0.1 -> 0.1.0 + py.typed + CHANGELOG Summary

**One-liner:** Bumped `__version__` to `0.1.0`, added empty PEP 561 `py.typed` marker, and rewrote CHANGELOG.md with the full v1 feature surface under a `[0.1.0] - 2026-05-02` section -- foundation work consumed by every later 09-* plan (wheel build, README install command, release notes).

## What Changed

### 1. `src/ultra_claude/__init__.py` -- 1-character logical edit, 0 net byte change

The only edit is the literal swap on line 3:

```diff
-__version__ = "0.0.1"
+__version__ = "0.1.0"
```

The docstring on line 1 (em-dash + parentheses) and the blank line on line 2 are untouched. File size stays at exactly **162 bytes** because `0.0.1` and `0.1.0` are byte-equal; the swap rearranges the dot positions but does not change the byte count. LF-only on disk (162 bytes / 0 CRLF / 3 LF). Verified via `git cat-file -p HEAD:src/ultra_claude/__init__.py` after autocrlf=true conversion attempt.

`hatchling` (`pyproject.toml` line 71-72: `[tool.hatch.version] path = "src/ultra_claude/__init__.py"`) extracts the literal via regex at build time -- the bare-string-literal shape is preserved (no f-string, no import, no dynamic computation), so `python -m build` in 09-04 will read `0.1.0` correctly.

End-to-end smoke check passed: `ultra-claude --version` (the click `version_option` from CLI-01 wired in `cli.py`) prints `ultra-claude, version 0.1.0` -- the chain `__init__.py` -> `from . import __version__` -> `click.version_option(version=__version__)` flows the new literal through to the CLI flag.

### 2. `src/ultra_claude/py.typed` -- new file, 0 bytes

Empty file at the canonical PEP 561 location (sibling of `__init__.py` inside the package). Per PEP 561, the file's existence -- not its contents -- is the signal to type checkers that `ultra_claude` ships type information inline. mypy walks the package tree and detects the file by name; it never reads the contents.

`pyproject.toml` line 75 (`[tool.hatch.build.targets.wheel] packages = ["src/ultra_claude"]`) ensures hatchling automatically bundles `py.typed` into the built wheel in 09-04 -- no manifest tweaks required.

Downstream impact: typed users of `ultra-claude` (e.g. via `pip install ultra-claude` then `from ultra_claude import run`) will now see the package as fully type-checked under mypy / pyright; previously mypy treated it as an opaque module.

### 3. `CHANGELOG.md` -- 684 bytes -> 6776 bytes (~10x growth)

Rewrote the file with the canonical Keep a Changelog 1.1.0 structure. Three sections in order:

1. **`## [Unreleased]`** -- empty placeholder for next-release work.
2. **`## [0.1.0] - 2026-05-02`** -- the new section. Lists the v1 feature surface under `### Added` (10 bullet groups: CLI surface / Config schema / Transcript module / Adapter Protocol + 3 adapters / Stop conditions / Orchestrator loop / Bundled preset / py.typed marker / Documentation / Examples / Test suite / CI lint tripwire), one bullet under `### Changed` (README replaces stub), and a `### Notes` block citing PKG-05's never-uploaded stub being superseded plus the `python -m build` + `twine upload` release procedure.
3. **`## [0.0.1] - 2026-05-02`** -- preserved verbatim from prior file (Keep a Changelog convention -- never delete history). Heading separator normalised from em-dash to ASCII hyphen for consistency with `[0.1.0]`.

Key citations included:
- `[openai/codex#19945](https://github.com/openai/codex/issues/19945)` for ADP-03 / Pitfall #2 (the live `codex exec` empty-stdout bug that the `_SubprocessAdapterMixin` defends against).
- All 12 requirement IDs (CFG-01..05, TRX-01..05, ADP-01..08, STP-02..05, ORC-01..06, CLI-01..11, PRE-01) inline-tagged on each feature bullet.
- The Pitfall numbers (#1 stdin pipe / #2 empty stdout / #3 cp1252 / #4 unanimity / #5 process-tree kill / #6 GOAL ANCHOR) tagged where each defense lives.

LF-only on disk (6776 bytes / 0 CRLF / 68 LF / 0 non-ASCII). Achieved by writing via `Path.write_bytes(content.encode("utf-8"))` in a Python heredoc, bypassing the host's `core.autocrlf=true` working-tree filter. Staged blob verified LF-only via `git cat-file -p HEAD:CHANGELOG.md`.

## Verification Gate Results

All 6 plan-specified gates PASS:

| # | Gate | Result |
|---|------|--------|
| 1 | `python -c "import ultra_claude; assert ultra_claude.__version__ == '0.1.0'"` | PASS |
| 2 | `python -c "from pathlib import Path; assert Path('src/ultra_claude/py.typed').is_file()"` | PASS |
| 3 | `python -c "data = ...; assert b'\r\n' not in data; assert b'## [0.1.0] - 2026-05-02' in data"` | PASS |
| 4 | `pytest tests/` -- **83/83 PASS in 1.15s** (zero regression vs Phase 8 baseline) | PASS |
| 5 | `mypy --strict src/ultra_claude` -- "Success: no issues found in 13 source files" | PASS |
| 6 | `ruff check` on edited files (`src/ultra_claude/__init__.py`, `py.typed`) -- "All checks passed!" | PASS |

Bonus end-to-end gate: `ultra-claude --version` prints `ultra-claude, version 0.1.0` (CLI-01 wiring confirmed working with new literal).

## Threat Register Mitigations Applied

| Threat ID | Mitigation Status |
|-----------|-------------------|
| T-09-01 (Tampering, `__init__.py` version literal) | MITIGATED -- edited only the literal `__version__` line; docstring preserved verbatim; verified via `python -c "assert ultra_claude.__version__ == '0.1.0'"` |
| T-09-02 (Tampering, CHANGELOG historical entries) | MITIGATED -- preserved the prior `[0.0.1]` section (its 2 bullets verbatim); only normalised heading separator from em-dash to ASCII hyphen for Keep a Changelog convention consistency |
| T-09-03 (Information Disclosure, py.typed contents) | ACCEPTED (per plan) -- empty file has nothing to disclose; canonical PEP 561 form |
| T-09-04 (Denial of Service, hatchling build pipeline) | MITIGATED (runtime side) -- bare double-quoted literal preserved; full `python -m build` smoke test deferred to 09-04 per plan |

## Deferred Issues

**Pre-existing ruff errors** (NOT caused by this plan, NOT actioned per scope rule):

| File | Rule | Origin |
|------|------|--------|
| `src/ultra_claude/config.py:38` | RUF022 (`__all__` not sorted) | Phase 2 |
| `src/ultra_claude/config.py:110` | UP037 (quoted type annotation) | Phase 2 |
| `tests/test_config.py:12` | I001 (import block un-sorted) | Phase 2 |
| `tests/test_config.py:24` | F401 (unused `format_validation_error` import) | Phase 2 |

All 4 errors confirmed pre-existing in 07-01 via `git stash` round-trip and logged at `.planning/phases/07-gemini-codex-adapters/deferred-items.md`. They remain out of scope: 09-01 touches no Phase 2 files. Verified by running `ruff check src/ultra_claude/__init__.py` and `ruff check src/ultra_claude/py.typed` -- both report "All checks passed!".

## Deviations from Plan

**None.** Plan executed exactly as written:

- Task 1: literal swap via `Edit` tool (preserved docstring; LF-only; same byte count)
- Task 2: empty `py.typed` written via `Write` tool with empty content
- Task 3: CHANGELOG written via Python `Path.write_bytes` to bypass autocrlf=true (the plan's recommended approach for cross-platform LF-only output)

**One mechanical note**: the plan's `<action>` block for Task 3 included a fallback Bash recipe `Path('CHANGELOG.md').write_bytes(open('CHANGELOG.md.tmp','rb').read())` for if the `Write` tool produced CRLFs. This wasn't needed -- writing the bytes directly via inline `Path.write_bytes(content.encode("utf-8"))` from a Bash heredoc with single-quoted Python script bypassed the host's autocrlf filter cleanly on the first attempt. Confirmed via `data.count(b'\r\n') == 0` post-write.

## Atomic Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | `8ade3e6` | `chore(09-01): bump __version__ from 0.0.1 to 0.1.0` |
| 2 | `bc8e3d1` | `feat(09-01): add PEP 561 py.typed marker` |
| 3 | `6155dc6` | `docs(09-01): flesh out CHANGELOG.md [0.1.0] section` |

3 commits, 1 per task. Per-requirement bisection enabled.

## What Unblocks

- **09-04 (build artifacts + release notes)**: now has the 0.1.0 literal for `python -m build` to extract; the `py.typed` marker auto-bundles into the wheel; the CHANGELOG `[0.1.0]` section is the authoritative release-notes source.
- **09-03 (README rewrite)**: can now reference `pip install ultra-claude==0.1.0` and link to the `[0.1.0]` CHANGELOG section.
- **09-02 (E2E test fixtures + examples directory)**: independent of this plan but runs in parallel.

## Self-Check: PASSED

All 3 artifacts verified to exist on disk:
- FOUND: `src/ultra_claude/__init__.py`
- FOUND: `src/ultra_claude/py.typed`
- FOUND: `CHANGELOG.md`

All 3 commits verified to exist in git log:
- FOUND: `8ade3e6` (Task 1)
- FOUND: `bc8e3d1` (Task 2)
- FOUND: `6155dc6` (Task 3)
