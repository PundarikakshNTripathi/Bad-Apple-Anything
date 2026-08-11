# Phase 02: ingestion, background estimation, matting

Paste this prompt into a fresh Antigravity CLI (agy) root agent session,
after phase 01's pull request has been merged into `develop` and your
local `develop` is up to date.

---

Before doing anything else, reread `AGENTS.md` and confirm you have the
current state of `docs/` and `.agents/rules/` in context for this
session; do not rely on memory of a previous session. This is phase 2 of
6, scoped per `docs/03_SDD.md` section 8: `baa_ingest` demux, background
estimation, and classical matting, unit tested against synthetic
fixtures. Create branch `phase/02-ingestion-matting` from `develop` per
`.agents/rules/01-git-workflow.md` before making any change.

## Scope for this phase

1. Implement `demux.py` per `docs/03_SDD.md` section 3.6: extract audio
   to a WAV file and provide a frame iterator over the source video, both
   via explicit-argument-list `ffmpeg` subprocess calls per
   `docs/adr/ADR-0005-process-boundary-ffmpeg-subprocess.md`. No shell
   string interpolation of any path, anywhere in this module; write the
   structural test for this (`test_ingest_subprocess_calls_use_argument_list`
   from `docs/06_QA_TEST_PLAN.md` section 3.5) as part of this work, not
   as an afterthought.
2. Implement `background.py`'s `estimate_background`: pixelwise temporal
   median over a sample of frames. This is not a new algorithm to
   invent from scratch; it is documented precisely in
   `docs/adr/ADR-0004-matting-strategy-pluggable-backend.md` and was
   already validated once during earlier prototyping. Read that ADR's
   full reasoning, including why the earlier MOG2-based attempt failed,
   before implementing, so you do not reintroduce the same failure mode.
3. Implement `matting.py`: the `MattingBackend` protocol/interface and
   the one phase 1 implementation (`TemporalMedianMatting`), per
   `docs/03_SDD.md` section 3.6. The interface must be designed so a
   second backend can be added later without changing any calling code;
   write a test that constructs a trivial fake second backend
   implementing the same interface and confirms it can be substituted,
   as a concrete check that the interface is actually decoupled and not
   just decoupled in name.
4. Build a synthetic test fixture generator (a moving subject over a
   genuinely static background, following the corrected approach from
   earlier prototyping where the background must actually be static
   across frames for temporal-median estimation and MOG2-style methods
   alike to be meaningfully tested) as checked-in code, not a checked-in
   media file, per `docs/adr/ADR-0007-test-fixture-policy-no-copyrighted-media-in-vcs.md`.
   The fixture must include a held/motionless segment specifically,
   because that is the exact condition that broke the earlier adaptive
   background-subtraction attempt, and the regression test for that
   failure mode depends on the fixture actually exercising it.
5. Write `test_temporal_median_matting_synthetic_fixture` per
   `docs/06_QA_TEST_PLAN.md` section 3.5: assert the extracted mask's
   nonzero pixel count stays within an expected range through the held
   segment specifically, not just somewhere in the overall clip.
6. Write the remaining unit tests listed in `docs/06_QA_TEST_PLAN.md`
   section 3.5 for this phase's modules: `test_demux_accepts_valid_input`,
   `test_demux_audio_extraction_lossless`,
   `test_ingest_enforces_resource_limits` (TR-SEC-3 from `docs/02_TRD.md`,
   oversized or malformed declared dimensions rejected before buffer
   allocation, not after).

## Test gating for this phase

Follow `.agents/rules/02-test-gating.md` in full. Run `pytest
python/baa_ingest -v` and confirm every test above passes, including
specifically confirming the held-segment matting test passes for the
reason stated above, not merely that the overall test file has no
failures. Also confirm `docs/06_QA_TEST_PLAN.md` section 6's
`test_no_network_calls` equivalent applies to this phase's code (this
phase's code makes no network calls; verify this is actually true by
running it with outbound network blocked, not by assuming it from
reading the code).

## Benchmarking for this phase

This phase's code is on the ingestion throughput benchmark path
(`docs/02_TRD.md` section 6, `bench_ingest_throughput`). Follow
`.agents/rules/04-benchmark-recording.md`: write the `pytest-benchmark`
test for ingestion throughput against the synthetic fixture, run it, and
run `harness/benchmark_update.py` to record the result into `README.md`
and `docs/BENCHMARK_HISTORY.md` before considering this phase done.

## Documentation for this phase

Follow `.agents/rules/03-documentation-update.md`: update
`docs/03_SDD.md` section 9's traceability matrix rows for FR-1, FR-2, and
FR-3 if the actual test names you wrote differ from what is currently
listed there, and add a `CHANGELOG.md` entry under "Unreleased"
describing what this phase implemented, in the plain, specific style
required by `.agents/rules/00-anti-slop-style.md`.

## End of phase

Follow `.agents/rules/01-git-workflow.md`'s end-of-phase procedure: push,
open the pull request into `develop`, and stop there.
