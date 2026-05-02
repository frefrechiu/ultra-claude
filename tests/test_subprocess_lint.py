"""TST-05: lint test that fails the build on any subprocess.run/Popen call
in src/ultra_claude/ that is missing the safe-contract keywords.

Mandatory keywords on every subprocess.run / subprocess.Popen call:
    - text=True
    - encoding="utf-8"
    - errors="replace"
    - shell=False (or `shell` keyword absent -- shell=True is forbidden)

Why this test exists:
    Pitfall #3 (Windows cp1252 encoding crash) and Pitfall #1 (cmd.exe argv
    limit) are mitigated by *every* subprocess call passing the same set of
    keywords. Forgetting one -- on a single new call added to a future
    adapter or to the orchestrator -- silently regresses the safety
    contract. This test is the tripwire.

How it works:
    Walk every .py file under src/ultra_claude/, parse with ast, find every
    Call node whose func is `subprocess.run` or `subprocess.Popen` (or
    bare-imported `run` / `Popen`), and assert each call has the four
    mandatory kwargs.

What this test does NOT do:
    - It does not check the test suite itself; tests/ is allowed to have
      bare subprocess calls because tests are intentionally constructing
      synthetic processes (e.g. timeout simulation) where the safety
      keywords would obscure the assertion.
    - It does not infer keyword values when they come from a variable
      (e.g. `subprocess.run(argv, **kwargs)`); a future refactor that
      pushes kwargs into a helper should leave the helper itself as a
      visible-keywords site so this test can find them.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Source tree we lint -- everything under the package root, recursively.
PACKAGE_ROOT = Path(__file__).resolve().parent.parent / "src" / "ultra_claude"

# Required keyword arguments on every subprocess.run / subprocess.Popen call.
REQUIRED_KEYWORDS: dict[str, object] = {
    "text": True,
    "encoding": "utf-8",
    "errors": "replace",
}

# Names that, when called, count as "a subprocess invocation site". Both the
# fully-qualified attribute access (subprocess.run) and a bare name (run) --
# from `from subprocess import run` -- are caught.
SUBPROCESS_CALL_NAMES = {"run", "Popen"}


def _python_files() -> list[Path]:
    """Every .py file under src/ultra_claude/, recursively."""

    return sorted(p for p in PACKAGE_ROOT.rglob("*.py") if p.is_file())


def _is_subprocess_call(node: ast.Call) -> bool:
    """Detect ``subprocess.run(...)``, ``subprocess.Popen(...)``, or the
    bare-import variants ``run(...)`` / ``Popen(...)``.

    We're deliberately permissive on the bare form because the file might
    do ``from subprocess import run`` -- that's still a subprocess call site
    and must obey the contract. False positives on locally-defined
    functions named ``run`` are acceptable; they should be renamed.
    """

    func = node.func
    # subprocess.run / subprocess.Popen
    if (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id == "subprocess"
        and func.attr in SUBPROCESS_CALL_NAMES
    ):
        return True
    # bare run() / Popen() from `from subprocess import run, Popen`
    return isinstance(func, ast.Name) and func.id in SUBPROCESS_CALL_NAMES


def _kwargs_of(call: ast.Call) -> dict[str, ast.expr]:
    """Map each keyword argument name to its AST value node.

    Keyword names of None (i.e. ``**kwargs``-style splats) are skipped --
    we cannot statically inspect the contents of a splat, so we assume
    those calls have already been audited and any new direct call must
    keep the keywords visible at the call site.
    """

    return {kw.arg: kw.value for kw in call.keywords if kw.arg is not None}


def _literal_value(node: ast.expr) -> object:
    """Best-effort extraction of a literal value from an AST node.

    Returns the value if the node is an ast.Constant; otherwise returns
    a sentinel object that compares unequal to anything we care about.
    """

    if isinstance(node, ast.Constant):
        return node.value
    return object()  # sentinel -- never equals our expected values


def _enumerate_subprocess_calls() -> list[tuple[Path, int, ast.Call]]:
    """Walk PACKAGE_ROOT and return every (file, lineno, Call) site."""

    sites: list[tuple[Path, int, ast.Call]] = []
    for path in _python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as err:
            pytest.fail(f"{path}: failed to parse: {err}")

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _is_subprocess_call(node):
                sites.append((path, node.lineno, node))
    return sites


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_package_root_exists() -> None:
    """Sanity check -- if PACKAGE_ROOT vanishes, every other test passes
    vacuously. Catch that here."""

    assert PACKAGE_ROOT.is_dir(), f"Expected package at {PACKAGE_ROOT}"


def test_at_least_one_subprocess_call_exists_in_package() -> None:
    """The whole point of the lint test is to check subprocess calls. If
    none exist, the test is silently passing -- so we assert at least one
    site exists (the mixin's _run_subprocess + _kill_process_tree provide
    at least two: the Popen launch and the Windows taskkill run).
    """

    sites = _enumerate_subprocess_calls()
    assert len(sites) >= 1, (
        f"Expected at least one subprocess.run/Popen call under "
        f"{PACKAGE_ROOT}, found 0. Did the mixin land in "
        f"src/ultra_claude/adapters/base.py?"
    )


def test_every_subprocess_call_has_required_keywords() -> None:
    """The headline TST-05 assertion: every subprocess.run / subprocess.Popen
    call site under src/ultra_claude/ must pass text=True, encoding="utf-8",
    errors="replace", and must NOT pass shell=True.

    Failure message lists every offending site so a developer running this
    test in CI sees ALL violations at once, not just the first.
    """

    failures: list[str] = []

    for path, lineno, call in _enumerate_subprocess_calls():
        kwargs = _kwargs_of(call)
        rel = path.relative_to(PACKAGE_ROOT.parent.parent)

        # 1) Required keywords must be present AND set to the canonical value.
        for kw_name, expected in REQUIRED_KEYWORDS.items():
            if kw_name not in kwargs:
                failures.append(
                    f"{rel}:{lineno}: subprocess call missing required "
                    f"keyword `{kw_name}={expected!r}`"
                )
                continue
            actual = _literal_value(kwargs[kw_name])
            if actual != expected:
                failures.append(
                    f"{rel}:{lineno}: subprocess call has "
                    f"`{kw_name}={actual!r}`, expected `{kw_name}={expected!r}`"
                )

        # 2) shell=True is FORBIDDEN. Either the keyword is absent (shell
        #    defaults to False) or it must be the literal False.
        if "shell" in kwargs:
            actual_shell = _literal_value(kwargs["shell"])
            if actual_shell is not False:
                failures.append(
                    f"{rel}:{lineno}: subprocess call sets "
                    f"`shell={actual_shell!r}`; shell=True is forbidden -- "
                    f"use list-form argv with shell=False."
                )

    if failures:
        pytest.fail(
            "TST-05: subprocess invocation contract violated. Every "
            "subprocess.run / subprocess.Popen call under src/ultra_claude/ "
            'must pass text=True, encoding="utf-8", errors="replace", '
            "and must NOT pass shell=True.\n\n" + "\n".join(failures)
        )
