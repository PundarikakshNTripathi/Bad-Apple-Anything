# Rule: benchmark recording

Every phase that touches ingestion, rendering, or encoding performance
must run the benchmark harness and confirm `README.md` reflects current
numbers before the phase is considered done. This is mechanical, not
optional, and it is a scripted process specifically so it is not
performed inconsistently by hand each time.

## Procedure

1. Run the full benchmark suite:
   - `cargo bench --workspace` (Criterion, writes to
     `target/criterion/**/estimates.json`)
   - `pytest python/baa_ingest --benchmark-only --benchmark-json=out/bench_python.json`
   - `python harness/e2e_benchmark.py --fixture <synthetic fixture path> --out out/bench_e2e.json`
     (end-to-end wall clock and peak memory against the synthetic
     fixture, per `docs/06_QA_TEST_PLAN.md` section 8; this script's own
     docstring explains why it never runs against the real asset in
     `assets/`)
2. Run the recording script, which parses all three result sources and
   updates `README.md` in place:
   `python harness/benchmark_update.py`
3. The script locates the section of `README.md` between the literal
   markers `<!-- BENCHMARKS:START -->` and `<!-- BENCHMARKS:END -->`
   using a regular expression, replaces only the content between those
   markers with a freshly generated table, and leaves everything else in
   `README.md` untouched. Do not hand-edit the content between those
   markers; the next automated run will overwrite manual edits there, by
   design, since the table is meant to be a generated artifact, not
   prose.
4. The script also appends one row to `docs/BENCHMARK_HISTORY.md` (an
   append-only log, created on first use) recording the current git
   commit hash, timestamp, and the same figures, so performance trends
   over time remain visible even though `README.md` itself only ever
   shows the latest run.
5. Review the diff to `README.md` and `docs/BENCHMARK_HISTORY.md` before
   committing, the same as any other change; confirm the numbers are
   plausible (not zero, not identical to the previous run by coincidence
   in a way that suggests the benchmark did not actually execute) before
   trusting the automated update.
6. Commit the resulting `README.md` and `docs/BENCHMARK_HISTORY.md`
   changes as part of this phase's normal commits, using
   `docs(harness): update benchmark results` as the commit message unless
   it is naturally folded into a larger commit for this phase.

## If a benchmark regresses

Follow `docs/06_QA_TEST_PLAN.md` section 8's regression policy: greater
than 15 percent regression against the value most recently recorded on
`develop` blocks the phase from being considered done until investigated
and either fixed or, in the rare case the regression is an accepted
tradeoff, explicitly called out in the pull request description with the
reasoning, per the same section's guidance that this must never happen
silently.

## Script locations

`harness/benchmark_update.py` and `harness/e2e_benchmark.py` are checked
into the repository under `harness/` and are part of the codebase, not
throwaway tooling; they receive the same code quality and test-gating
treatment (docs/06_QA_TEST_PLAN.md) as any other Python module in this
project, including their own unit tests for the regex extraction and
replacement logic specifically, since a bug in a benchmark-recording
script that silently fails to update the table is worse than no
automation at all.
