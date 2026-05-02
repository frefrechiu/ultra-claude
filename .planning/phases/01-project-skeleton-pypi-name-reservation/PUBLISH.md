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
