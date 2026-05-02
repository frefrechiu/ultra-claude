"""Fake CLI for orchestrator end-to-end tests (TST-03, TST-04).

Reads the prompt from stdin and prints `echo: <prompt>` to stdout. The
orchestrator's E2E test (`tests/test_e2e_with_echo_cli.py`) invokes this
file via `python <path-to-echo_cli.py>` so the FULL Popen pipe-stdin path
through `_SubprocessAdapterMixin._run_subprocess` is exercised against a
real Python child process -- no `pytest-subprocess` mocking layer between
the orchestrator and this script.

Exit codes:
    0 -- always (this fake never fails)

Encoding:
    UTF-8 on stdin AND stdout. The mixin opens the child with
    `encoding="utf-8"` so we must reconfigure stdout/stdin similarly,
    otherwise the Windows default cp1252 corrupts smart quotes / em-dashes
    in transcript-so-far inputs.
"""

from __future__ import annotations

import sys


def main() -> int:
    # Reconfigure UTF-8 on Python 3.10+. Pre-3.10 already-defaults are
    # acceptable on POSIX but Windows defaults to cp1252 -- the mixin's
    # encoding="utf-8" on the child needs the child to also be UTF-8.
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    prompt = sys.stdin.read()
    sys.stdout.write(f"echo: {prompt}")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
