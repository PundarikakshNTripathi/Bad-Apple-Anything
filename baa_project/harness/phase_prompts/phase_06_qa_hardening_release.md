# Phase 06: QA hardening, benchmarking pass, and the first release to main

Paste this prompt into a fresh Antigravity CLI (agy) root agent session,
after phase 05's pull request has been merged into `develop` and your
local `develop` is up to date. This phase concludes with the first
deliverable being released to `main` as `v1.0.0`, so read it in full
before starting, including the manual steps reserved for the project
owner rather than the agent.

---

Before doing anything else, reread `AGENTS.md` in full and every document
it references. This is phase 6 of 6 per `docs/03_SDD.md` section 8, the
final phase of the first deliverable. Create branch
`phase/06-qa-hardening-release` from `develop` per
`.agents/rules/01-git-workflow.md` before making any change.

## Scope for this phase (agent-executed)

1. Run the full test suite across both languages
   (`cargo test --workspace`, `pytest python/baa_ingest`) and the full
   benchmark suite (`cargo bench --workspace`,
   `pytest python/baa_ingest --benchmark-only`,
   `harness/e2e_benchmark.py`), and fix anything that fails or regresses
   beyond the 15 percent policy in `docs/06_QA_TEST_PLAN.md` section 8.
   This is a hardening pass across everything phases 1 through 5 built,
   not new functional scope.
2. Run `harness/benchmark_update.py` and confirm `README.md` and
   `docs/BENCHMARK_HISTORY.md` reflect current, real numbers for every
   benchmark defined in `docs/02_TRD.md` section 6, with the specific
   exception of the 1920x1080 GPU render throughput figure and the
   real-asset end-to-end timing, both of which depend on hardware or
   assets not available to CI or possibly not available to you depending
   on your development environment; state plainly in the phase summary
   which figures are recorded from your own run versus which remain
   pending the project owner's manual step below.
3. Run every security and hygiene check in `docs/06_QA_TEST_PLAN.md`
   section 6 explicitly and report the result of each by name: the
   no-network-calls test, the output path containment test, the
   repository hygiene check for committed media, `cargo audit`,
   `pip-audit`.
4. Review `docs/03_SDD.md` section 9's full traceability matrix against
   the actual current state of the codebase and correct any row that has
   drifted from reality across all six phases, not just this one.
5. Review every document under `docs/` against `.agents/rules/00-anti-slop-style.md`
   one more time now that the full first deliverable exists, since minor
   style drift across six phases of edits is expected and this is the
   designated point to catch it, not something to defer indefinitely.
6. Finalize `CHANGELOG.md`: move the "Unreleased" entries accumulated
   across phases 1 through 6 under a `## [1.0.0]` heading with today's
   date.
7. Do not tag or merge into `main` yourself. Open the pull request from
   `phase/06-qa-hardening-release` into `develop` as usual, and once that
   is merged, open the `develop` into `main` pull request per
   `.agents/rules/01-git-workflow.md`'s release boundary procedure, but
   stop before tagging `v1.0.0` and explicitly tell me it is ready, so I
   can complete the manual QA checklist below before the tag is applied.

## Manual steps reserved for the project owner (not the agent)

These are listed here so the agent's phase summary can reference them
correctly, and so you have them in one place at the point you need them.

1. Run the manual QA checklist in `docs/06_QA_TEST_PLAN.md` section 7 in
   full, against your real local asset at `assets/source.mp4`, on your
   own development machine with GPU hardware present. This exercises the
   hardware-accelerated render path and the real content, neither of
   which the agent's automated work in this phase can cover, per
   `docs/adr/ADR-0007-test-fixture-policy-no-copyrighted-media-in-vcs.md`
   and `docs/06_QA_TEST_PLAN.md` section 2.
2. Record the real-asset end-to-end timing and the 1920x1080 GPU render
   throughput figure from that run. You can do this by running
   `harness/e2e_benchmark.py` yourself with a fixture argument pointed at
   a synthetic large fixture for the automated record, and separately
   noting the real-asset wall clock time observed during step 1 as a
   manual annotation in `docs/06_QA_TEST_PLAN.md` section 7's checklist
   record (the script itself will refuse to run against `assets/source.mp4`
   directly, by design, per `docs/adr/ADR-0007-test-fixture-policy-no-copyrighted-media-in-vcs.md`).
3. Once satisfied, tell the agent (or perform yourself) the final tag
   step: `git tag v1.0.0` on the merged `main` commit.

## Test gating for this phase

Follow `.agents/rules/02-test-gating.md` in full for everything in the
agent-executed scope above. This phase's definition of done additionally
includes the phase-specific requirement in `docs/06_QA_TEST_PLAN.md`
section 9: phase 1 (the first deliverable) is done only when the manual
QA checklist has been run at least once by the project owner, which the
agent cannot satisfy on its own and must not claim as satisfied on the
project owner's behalf.

## End of phase

Open the pull request into `develop`, then, after merge, the pull
request from `develop` into `main`, and stop before tagging, per the
scope section above.
