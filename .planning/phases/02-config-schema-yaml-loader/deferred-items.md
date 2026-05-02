# Phase 02 Deferred Items

Out-of-scope discoveries during plan execution. Logged per executor SCOPE BOUNDARY policy (do not auto-fix; track for later).

## 2026-05-02 — Plan 02-01

### `core.autocrlf=true` on Windows host risks CRLF on checkout

**Found:** While committing `src/ultra_claude/exceptions.py`, `git add` warned:
```
warning: in the working copy of 'src/ultra_claude/exceptions.py',
LF will be replaced by CRLF the next time Git touches it
```

**Status:**
- Working-tree file is LF-only (1387 bytes, verified).
- Git index has the file as LF (1387 bytes, verified via `git show :path`).
- Risk: a future `git checkout`/clone on Windows with `core.autocrlf=true` will materialise CRLF in the working tree, breaking the "LF-only on disk" cross-platform discipline (CLAUDE.md constraint #6).

**Impact scope:** Project-wide, not isolated to this plan — applies to ALL Python source files Phase 2+ will create.

**Recommended fix (out of scope for Plan 02-01):**
Add a `.gitattributes` at the repo root forcing LF for all text/code files:
```gitattributes
* text=auto eol=lf
*.py text eol=lf
*.toml text eol=lf
*.md text eol=lf
*.yaml text eol=lf
*.yml text eol=lf
*.json text eol=lf
```

**Suggested owner:** A small chore plan in Phase 2 or a follow-up to Plan 01-02 (pyproject.toml). Do NOT bundle into 02-01 — that plan's scope is exclusively `exceptions.py`.
