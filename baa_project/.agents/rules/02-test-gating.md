# Rule: test gating

A phase is not complete, must not be described as complete, and must not
be handed back to the project owner as finished, until every condition
below is true. This rule exists specifically because the project owner
has required it explicitly: stop only after all tests have passed, not
after most of them have passed or after a plausible-looking implementation
has been written.

## Gate conditions, all required

1. Every unit test relevant to the modules touched in this phase passes,
   per `docs/06_QA_TEST_PLAN.md` section 3.
2. Every integration test relevant to this phase passes, per
   `docs/06_QA_TEST_PLAN.md` section 4.
3. If this phase touches rendering output, golden-frame regression tests
   pass at the SSIM threshold defined in
   `docs/06_QA_TEST_PLAN.md` section 5, or, if a visual change was
   intentional, the reference frames were regenerated in their own
   reviewed commit as described in that section, not silently.
4. The security and hygiene checks in `docs/06_QA_TEST_PLAN.md` section 6
   pass, specifically including the no-network-calls check and the
   repository hygiene check for committed media.
5. Benchmarks relevant to this phase have been run per
   `04-benchmark-recording.md` and show no unflagged regression beyond
   the 15 percent policy in `docs/06_QA_TEST_PLAN.md` section 8.
6. The full workspace builds cleanly (`cargo build --workspace` and the
   Python package's own build/lint step) with no new compiler warnings
   introduced by this phase's changes that were not already present
   before it.

## Procedure on failure

If any test fails, the correct response is to diagnose and fix the
underlying cause, the same way the phase 0 prototype's documented bugs
were diagnosed by inspecting actual output (a rendered frame, a raw mask
array) rather than assumed from the error message alone. Do not:

- Comment out or skip a failing test to make the suite pass.
- Loosen a test's assertion (for example, widening an SSIM threshold or a
  benchmark tolerance) without a documented, reviewed reason recorded in
  the commit message, and never as a way to make a genuine regression
  disappear.
- Report the phase as complete with a caveat that "one test is flaky" or
  "this will be fixed later." A flaky test is itself a bug in either the
  test or the code under test and must be resolved before the phase is
  considered done.

Keep iterating: run the test suite, read the actual failure output, form
a specific hypothesis about the cause, make one change, rerun. Repeat
until green. This mirrors the debugging discipline already demonstrated
in the phase 0 prototype work, where each bug (frame scale, a hip/ground
coordinate confusion, a background-subtraction failure mode) was found by
inspecting real intermediate output, not guessed at from surface symptoms.

## Reporting

When a phase's gate conditions are all satisfied, state explicitly, in
the phase summary and in the pull request description, which test
commands were run and that they passed, by name, not merely "tests
pass." Example: "cargo test --workspace: 42 passed, 0 failed. pytest
python/baa_ingest: 18 passed, 0 failed. Benchmarks: all within policy,
see README.md benchmarks section for current values."
