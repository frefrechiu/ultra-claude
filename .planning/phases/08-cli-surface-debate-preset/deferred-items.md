# Phase 8 Deferred Items

Issues discovered during phase 8 execution that are out-of-scope for the
current plan. Per the SCOPE BOUNDARY rule (in
`$HOME/.claude/get-shit-done/agents/gsd-executor.md`), only auto-fix issues
DIRECTLY caused by the current task's changes. Pre-existing or
environment-specific limitations are logged here for future work.

## Windows: subprocess.Popen with shell=False cannot launch `.cmd` shims

**Discovered:** 2026-05-02 during plan 08-02 Task 2 smoke check #5
(`ultra-claude doctor`).

**Symptom:** `shutil.which("gemini")` returns
`C:\Users\fredd\AppData\Roaming\npm\gemini.CMD` (an npm-installed cmd shim);
`subprocess.run(["gemini", "--version"], shell=False, ...)` then raises
`OSError: [WinError 2]` because Windows `CreateProcess` cannot execute
`.cmd` files without going through `cmd.exe`. The doctor command catches
this in its `except OSError` branch and reports
`On PATH=PASS, Auth=UNKNOWN, Notes=OSError: ...`, which is graceful but
inaccurate (the CLI is on PATH and probably authenticated).

**Why this is NOT a plan-08-02 bug:** The production adapters
(`src/ultra_claude/adapters/{gemini,codex}.py`) also use
`subprocess.Popen([cli_name, ...], shell=False)` via
`_SubprocessAdapterMixin._run_subprocess`. This Windows `.cmd` limitation
affects the orchestrator's real run path identically, so the doctor's
behavior is **consistent with what the production code does**. The doctor
is honest: if the CLI binary can't be launched the same way the
orchestrator launches it, that is the user-relevant fact.

**Why we cannot just set `shell=True`:** CLAUDE.md Critical Constraint #1
explicitly forbids `shell=True` for safety (argv injection risk). TST-05
lint test (`tests/test_subprocess_lint.py`) ast-walks the package and
fails the build on `shell=True`.

**Possible v2 mitigations** (NOT implemented in v1):

1. **Per-platform argv augmentation:** on Windows, when the resolved path
   ends in `.cmd` or `.bat`, prepend `["cmd", "/c"]` to the argv. This
   keeps `shell=False` (the safety property is preserved -- we are not
   asking the shell to parse the command, we are asking it to run a
   specific file) while letting Windows execute cmd shims. Same trick
   would apply in the production mixin.

2. **Use the resolved absolute path from `shutil.which`:** invoke the full
   `.cmd` path with `cmd.exe /c` rather than just `cli_name`. Equivalent to
   #1 but routed through `shutil.which`'s output explicitly.

3. **Document in README:** "On Windows, install the CLIs via a method that
   produces a real `.exe` (winget, scoop, manual pip/pipx install) rather
   than via `npm install -g` -- the npm `.cmd` shims do not work with
   subprocess.Popen(shell=False)." Cheapest fix; just a docs update for
   v0.1.0.

The README/docs work in Phase 9 is the natural place to add option #3 if
the v0.1.0 release ships before the per-platform argv fix lands.

**No regression introduced** -- this limitation pre-dated plan 08-02. The
doctor command exposes it (which is good: doctor is supposed to surface
real-world readiness issues) but does not cause it.

**Reproduction:**

```
ultra-claude doctor
# CLI     On PATH  Auth     Notes
# ------  -------  -------  ---------------------------------
# claude  PASS     PASS     version: 2.1.126 (Claude Code)
# gemini  PASS     UNKNOWN  OSError: [WinError 2] ...
# codex   PASS     UNKNOWN  OSError: [WinError 2] ...
```

The same OSError would surface from `ultra-claude run` if the user ran a
real debate using the gemini or codex adapters on Windows with npm-shim
binaries. Documented as "expected" for v1; tracked here for v2 work.
