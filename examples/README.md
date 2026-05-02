# Examples

This directory contains:

- **`debate.yaml`** -- a copy of the bundled `presets/debate.yaml`. You can copy this verbatim into any project as a starting point for a 3-agent roundtable, or run `ultra-claude run --preset debate --inline "<task>"` to use it from the package directly.
- **`transcripts/sample-debate.md`** + **`transcripts/sample-debate.md.jsonl`** -- a synthetic 3-turn transcript demonstrating the on-disk format ultra-claude writes during a real run.

## Synthetic, not real

The transcript here is SYNTHETIC -- generated using ultra-claude's test infrastructure (FakeAdapter), not a real LLM run. The reason: capturing a real debate requires `claude` / `gemini` / `codex` installed and authenticated on the machine producing the example, which is environment-specific and not reproducible in repository fixtures.

The sample is structurally identical to a real run -- same markdown sentinels, same JSONL schema -- so it accurately demonstrates what your transcript file will look like after `ultra-claude run --preset debate --inline "..."`. Only the agent OUTPUTS are stand-ins.

## Capturing your own real transcript

Once you have the three CLIs installed and authenticated (`ultra-claude doctor` reports `PASS` for each), capture a real run:

```bash
ultra-claude run --preset debate --inline "Should we adopt Postgres or stick with SQLite for v1?" --output examples/transcripts/my-debate.md
```

That writes BOTH `examples/transcripts/my-debate.md` (markdown, human-readable, `tail -f`-friendly during the run) AND `examples/transcripts/my-debate.md.jsonl` (JSONL sidecar, one record per turn).

PRs adding interesting captured transcripts (with the user's permission, of course) are welcome -- see [CONTRIBUTING.md](../CONTRIBUTING.md).
