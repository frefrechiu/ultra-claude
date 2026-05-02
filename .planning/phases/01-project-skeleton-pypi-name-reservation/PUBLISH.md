# Publishing the 0.0.1 Stub to PyPI

**Status:** Manual step — REQUIRES USER ACTION with PyPI credentials. Claude cannot perform this autonomously per `.planning/phases/01-project-skeleton-pypi-name-reservation/01-CONTEXT.md`.

**Why this exists:** Tasks 1 and 2 of plan `01-03` produced and verified `dist/ultra_claude-0.0.1.tar.gz` and `dist/ultra_claude-0.0.1-py3-none-any.whl`. This file documents how to push them to PyPI to satisfy requirement **PKG-05** (Phase 1's name-reservation goal).

---

## Prerequisites

Before running the upload command:

1. **Have a PyPI account.** Register at <https://pypi.org/account/register/> if needed.
2. **Two-factor authentication enabled** on the account — PyPI has required 2FA for new uploads since 2024.
3. **Generate an API token:**
   - Go to <https://pypi.org/manage/account/token/>.
   - Click "Add API token".
   - Name: `ultra-claude initial upload` (or similar).
   - Scope: **"Entire account"** for the very first upload of a new project (project-scoped tokens cannot be created until the project exists on PyPI).
   - Copy the token (starts with `pypi-AgEI...`). It's shown ONCE.
4. **Confirm the artifacts exist.** From the repo root:
   ```bash
   ls dist/ultra_claude-0.0.1*
   # Expected:
   # dist/ultra_claude-0.0.1-py3-none-any.whl
   # dist/ultra_claude-0.0.1.tar.gz
   ```
5. **Re-validate before uploading** (fast — avoids a failed upload):
   ```bash
   python -m twine check dist/ultra_claude-0.0.1*
   # Expected: both files report `PASSED`.
   ```

If either artifact is missing or `twine check` fails, re-run plan `01-03` Task 1 (`python -m build`) before continuing.

---

## Upload command

From the repo root, with `twine` available (it's in the `[dev]` extras from `pyproject.toml`; if you're not in an active venv, run `python -m pip install --user twine` to make it available):

### Option A — One-time interactive upload (recommended for first-time)

```bash
python -m twine upload dist/ultra_claude-0.0.1*
```

twine will prompt:
- `Enter your username:` -> type `__token__` (literally, with the underscores).
- `Enter your password:` -> paste the API token (starts with `pypi-`). It will not echo to the screen.

### Option B — Environment-variable upload (scriptable / CI-safe)

```bash
export TWINE_USERNAME="__token__"
export TWINE_PASSWORD="pypi-AgEI...your-token-here..."
python -m twine upload dist/ultra_claude-0.0.1*
unset TWINE_USERNAME TWINE_PASSWORD
```

### Option C — `~/.pypirc` configuration (if you publish often)

Edit `~/.pypirc`:

```ini
[pypi]
username = __token__
password = pypi-AgEI...your-token-here...
```

Set permissions: `chmod 600 ~/.pypirc` (POSIX) or restrict ACLs on Windows.

Then: `python -m twine upload dist/ultra_claude-0.0.1*`.

---

## Expected output

A successful upload looks roughly like this:

```
Uploading distributions to https://upload.pypi.org/legacy/
Uploading ultra_claude-0.0.1-py3-none-any.whl
100%|███████████████████████████████| 4.12k/4.12k [00:00<00:00, 8.92kB/s]
Uploading ultra_claude-0.0.1.tar.gz
100%|███████████████████████████████| 6.78k/6.78k [00:00<00:00, 13.4kB/s]

View at:
https://pypi.org/project/ultra-claude/0.0.1/
```

Visit the URL and confirm:
- The project page exists at <https://pypi.org/project/ultra-claude/>.
- Version 0.0.1 is shown.
- The README renders (the trademark disclaimer paragraph should be visible).
- The MIT license and Python `>=3.10` requirement are shown.

---

## Verify the reservation worked

From any other machine (or even just a fresh shell on this one):

```bash
python -m venv .verify-venv
source .verify-venv/Scripts/activate     # Windows
# or: source .verify-venv/bin/activate   # POSIX
pip install ultra-claude==0.0.1
python -c "import ultra_claude; print(ultra_claude.__version__)"
# Expected output: 0.0.1
deactivate
rm -rf .verify-venv
```

If this prints `0.0.1`, ROADMAP.md success criterion 1 is satisfied: **`pip install ultra-claude==0.0.1` from PyPI succeeds and resolves to a stub package owned by the project author.**

---

## Post-upload follow-ups

After the first upload succeeds:

1. **Replace the broad token with a project-scoped one.**
   - Go to <https://pypi.org/manage/project/ultra-claude/settings/>.
   - Generate a token scoped to project `ultra-claude` only.
   - Replace the token in `~/.pypirc` (or your env vars).
   - Revoke the original "entire account" token at <https://pypi.org/manage/account/token/>.

2. **Reserve typo-aliases (recommended per `.planning/research/PITFALLS.md` Pitfall 14):**
   - Optional: also push `ultra_claude` and `ultraclaude` as 0.0.1 stubs pointing at the same project, to prevent typosquatting. Pip normalizes dashes/underscores so `pip install ultra-claude` and `pip install ultra_claude` resolve to the same distribution — but typosquatters can still register `ultraclaude` (no separator). Decide whether to pre-register that name too.

3. **Mark requirement PKG-05 as complete** in the relevant tracking (the next phase's verifier will confirm via a `pip install ultra-claude==0.0.1` smoke check).

---

## What can go wrong

| Symptom | Cause | Fix |
|---------|-------|-----|
| `HTTPError: 403 Forbidden ... The user 'foo' isn't allowed to upload to project 'ultra-claude'` | Someone else already registered the name | Pick a backup name (e.g. `ultraclaude` per Pitfall 14) and update `[project] name` in `pyproject.toml`, then re-build and re-upload. |
| `HTTPError: 400 Bad Request ... File already exists` | You already pushed `0.0.1` (PyPI is immutable per version) | Bump to `0.0.2` in `src/ultra_claude/__init__.py`, re-build, re-upload. |
| `InvalidDistribution: Cannot find file ... .whl` | Wrong path / artifacts not built | Re-run plan 01-03 Task 1. |
| `twine: error: Bad credentials` | Token typo, expired, or wrong username | Username MUST be `__token__` (literally). Regenerate the token if expired. |
| README does not render on PyPI page | `Description-Content-Type` metadata mismatch | `twine check dist/*` would have caught this — re-run; if it still passes locally but not on PyPI, file an issue. |

---

## Sanity checklist before running

- [ ] PyPI account exists and has 2FA enabled.
- [ ] API token generated and copied (will not be shown again).
- [ ] `dist/ultra_claude-0.0.1.tar.gz` and `dist/ultra_claude-0.0.1-py3-none-any.whl` both exist locally.
- [ ] `python -m twine check dist/*` shows `PASSED` for both.
- [ ] You're aware that PyPI versions are immutable: once `0.0.1` is uploaded, you cannot replace it.

When all five boxes are checked, run the upload command from the section above.

---

# Publishing v0.1.0 (the FIRST FUNCTIONAL release)

**Status:** Manual step -- REQUIRES USER ACTION with PyPI credentials. The autonomous portion (`python -m build` + `twine check` + clean-venv smoke install + `pytest --cov` + `ruff check` + `mypy`) was executed by Phase 9 plan 09-04 and PASSED.

**Why this section exists:** Plan 09-04 produced and validated `dist/ultra_claude-0.1.0.tar.gz` and `dist/ultra_claude-0.1.0-py3-none-any.whl`. The 0.0.1 stub above was NEVER uploaded by the user (PKG-05 still pending); the v0.1.0 release supersedes it. A fresh PyPI account upload of `0.1.0` claims the `ultra-claude` distribution name AND ships the functional package in a single step.

**This closes:** PKG-06 (the v0.1.0 PyPI publish requirement). After this upload, `pip install ultra-claude` from any machine returns the real functional package.

## Prerequisites for v0.1.0 upload

Identical to the 0.0.1 prerequisites above. Re-check:

1. PyPI account with 2FA. Same account.
2. API token. If you generated a token for 0.0.1 and revoked it, generate a new one. Scope: **"Entire account"** (project-scoped tokens cannot exist until the project exists on PyPI -- which is precisely what this upload accomplishes).
3. `dist/ultra_claude-0.1.0.tar.gz` and `dist/ultra_claude-0.1.0-py3-none-any.whl` exist locally:

   ```bash
   ls dist/ultra_claude-0.1.0*
   # Expected:
   # dist/ultra_claude-0.1.0-py3-none-any.whl
   # dist/ultra_claude-0.1.0.tar.gz
   ```

4. Re-validate before uploading:

   ```bash
   python -m twine check dist/ultra_claude-0.1.0*
   # Expected: both files report `PASSED`.
   ```

If either artefact is missing, re-run plan 09-04 Task 1 (`rm -rf dist/ && python -m build`) before continuing.

## Upload command

From the repo root, with `twine` available (it's in the `[dev]` extras from `pyproject.toml`):

### Option A -- Interactive upload

```bash
python -m twine upload dist/ultra_claude-0.1.0*
```

twine will prompt:
- `Enter your username:` -> type `__token__` (literally, with the underscores).
- `Enter your password:` -> paste the API token (starts with `pypi-`).

### Option B -- Environment-variable upload

```bash
export TWINE_USERNAME="__token__"
export TWINE_PASSWORD="pypi-AgEI...your-token-here..."
python -m twine upload dist/ultra_claude-0.1.0*
unset TWINE_USERNAME TWINE_PASSWORD
```

### Option C -- `~/.pypirc` configuration

(See the 0.0.1 section above for the `[pypi]` config format. If you set this up for 0.0.1, no changes needed -- the same config publishes 0.1.0.)

## Expected output

```
Uploading distributions to https://upload.pypi.org/legacy/
Uploading ultra_claude-0.1.0-py3-none-any.whl
100%|...| 9.XXk/9.XXk [00:00<00:00, ...]
Uploading ultra_claude-0.1.0.tar.gz
100%|...| 12.XXk/12.XXk [00:00<00:00, ...]

View at:
https://pypi.org/project/ultra-claude/0.1.0/
```

Visit the URL and confirm:
- The project page renders the FULL v0.1.0 README (not the 12-line stub).
- The Quickstart section is visible at the top.
- The trademark disclaimer paragraph is present.
- The MIT license and Python `>=3.10` requirement are shown.

## Verify the v0.1.0 reservation worked

From any other machine (or just a fresh shell):

```bash
python -m venv .verify-venv
source .verify-venv/Scripts/activate     # Windows
# or: source .verify-venv/bin/activate   # POSIX
pip install --no-cache-dir ultra-claude==0.1.0

# 1. Version cross-check
python -c "import ultra_claude; print(ultra_claude.__version__)"
# Expected: 0.1.0

# 2. CLI entry point on PATH
ultra-claude --version
# Expected: ultra-claude, version 0.1.0

# 3. Functional smoke (no agent CLIs needed -- --dry-run is offline)
ultra-claude run --preset debate --inline "test" --dry-run
# Expected: 9-turn planned schedule with Architect/Critic/Implementer.

deactivate
rm -rf .verify-venv
```

If all three smoke checks PASS, ROADMAP success criterion 4 is satisfied: **`pip install ultra-claude` on a fresh machine pulls the real release; `ultra-claude --version` prints `0.1.0`**.

## Post-upload follow-ups

1. **Replace the broad token with a project-scoped one.**
   - <https://pypi.org/manage/project/ultra-claude/settings/> -> generate project-scoped token.
   - Replace in your `~/.pypirc` or env vars.
   - Revoke the original "entire account" token.

2. **Mark requirement PKG-06 as complete** in `.planning/REQUIREMENTS.md` (replace `[ ]` with `[x]`).

3. **Mark requirement PKG-01 as complete** in `.planning/REQUIREMENTS.md` (the user-actionable half: `pip install ultra-claude` from PyPI works on a fresh machine -- the verify step above proves this).

4. **Tag the release**:

   ```bash
   git tag -a v0.1.0 -m "ultra-claude v0.1.0 -- first functional release"
   git push origin v0.1.0
   ```

5. **Update STATE.md** to mark Phase 9 fully closed (after PKG-06 / PKG-01 are checked).

## What can go wrong

The same error table from the 0.0.1 section applies, with one addition specific to v0.1.0:

| Symptom | Cause | Fix |
|---------|-------|-----|
| `HTTPError: 400 Bad Request ... File already exists` for `0.1.0` | You already pushed `0.1.0` (PyPI is immutable) | Bump to `0.1.1` (or `0.2.0`) in `src/ultra_claude/__init__.py`, re-build, re-upload. The 0.1.0 release is a one-shot. |
| `twine upload` for `0.1.0` succeeds but the README on PyPI looks empty | `Description-Content-Type` mismatch | `python -m twine check dist/*` would have caught this -- re-run; then re-build with `rm -rf dist/ && python -m build`. |

## Sanity checklist before running v0.1.0 upload

- [ ] PyPI account exists and has 2FA enabled.
- [ ] API token generated and copied.
- [ ] `dist/ultra_claude-0.1.0.tar.gz` and `dist/ultra_claude-0.1.0-py3-none-any.whl` both exist locally (re-check after any clean build).
- [ ] `python -m twine check dist/ultra_claude-0.1.0*` shows `PASSED` for both.
- [ ] Plan 09-04's smoke-install + quality gates all PASSED (recorded in `.planning/phases/09-tests-docs-examples-v010-release/09-04-SUMMARY.md`).
- [ ] You're aware that PyPI versions are immutable: once `0.1.0` is uploaded, you cannot replace it. Bump to 0.1.1 if you need to fix anything post-upload.

When all six boxes are checked, run the upload command from the v0.1.0 section above.
