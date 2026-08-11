# Phase 05: encode, CLI, and full end-to-end wiring

Paste this prompt into a fresh Antigravity CLI (agy) root agent session,
after phase 04's pull request has been merged into `develop` and your
local `develop` is up to date.

---

Before doing anything else, reread `AGENTS.md`, and specifically reread
`docs/adr/ADR-0005-process-boundary-ffmpeg-subprocess.md`,
`docs/03_SDD.md` sections 3.3, 3.4, 3.5, and 6, and `docs/02_TRD.md`
section 4.3. This is phase 5 of 6 per `docs/03_SDD.md` section 8, and it
is the phase where the pipeline first produces a complete, playable
output file from a real source video end to end. Create branch
`phase/05-encode-cli-e2e` from `develop` per
`.agents/rules/01-git-workflow.md` before making any change.

## Scope for this phase

1. Implement `crates/baa-encode`: `RawFrameEncoder` (raw BGR24 frames
   over stdin to an `ffmpeg` subprocess producing a silent MP4, mirroring
   the approach already validated during earlier prototyping) and
   `Muxer` (combining that video with the audio file into the final
   output, verifying duration match against the BSF header rather than
   silently truncating either stream on mismatch). Explicit argument
   vectors only, per ADR-0005; write
   `test_ffmpeg_invocation_uses_argument_vector_not_shell_string` as a
   structural test, not merely an integration test that happens to pass.
2. Implement `crates/baa-pipeline`: the `Stage` trait, the fixed-order
   phase 1 runner (ingest, render, encode), and `RunSummary` assembly
   written to `out/run_summary.json` after every run, success or failure,
   per `docs/03_SDD.md` section 3.4.
3. Implement `crates/baa-cli`: `clap`-derived subcommands `ingest`,
   `render`, `encode`, and `run`, output path resolution and containment
   validation (TR-SEC-2) before any stage runs, `tracing` subscriber
   setup, and the `baa.toml` config loading and validation described in
   `docs/03_SDD.md` section 7, including the eager fail-fast validation
   before any stage runs, and the documented exit code mapping (1 input
   error, 2 environment error, 3 internal error) from `docs/03_SDD.md`
   section 6.
4. Wire the Rust CLI's invocation of the Python ingestion subprocess per
   the exact contract in `docs/02_TRD.md` section 4.1: stdout progress
   line parsing (tolerant of unknown fields, warning-logged on malformed
   lines rather than crashing), stderr passthrough to diagnostics, and
   treating any non-zero exit as a hard failure with no attempt to use
   partial output.
5. Write the unit tests listed in `docs/06_QA_TEST_PLAN.md` sections 3.3
   and 3.4: `test_raw_frame_encoder_produces_valid_mp4` (validated via
   `ffprobe`, not merely a non-empty file check),
   `test_muxer_output_duration_matches_header`,
   `test_muxer_rejects_mismatched_duration_with_clear_error`,
   `test_run_summary_schema`, `test_stage_error_maps_to_documented_exit_code`,
   `test_config_overrides_applied`, `test_output_path_containment`
   (including the `../` traversal and absolute-path-override cases),
   `test_missing_ffmpeg_produces_clear_startup_error`.
6. Write `test_e2e_full_pipeline_synthetic_fixture` per
   `docs/06_QA_TEST_PLAN.md` section 4.1: run `baa run` end to end
   against the synthetic fixture established in phase 2, assert a valid
   playable MP4 with correct duration, resolution, and a non-silent audio
   track.
7. Write `test_e2e_repeat_run_identical` per `docs/06_QA_TEST_PLAN.md`
   section 4.3: two runs against the same unchanged synthetic fixture
   produce byte-identical or SSIM >= 0.999 output.

## Test gating for this phase

Follow `.agents/rules/02-test-gating.md` in full. Run `cargo test
--workspace` and confirm every test above passes, including the full
end-to-end synthetic-fixture test actually producing a file you can
independently verify plays back correctly (state in your summary what
you checked: duration, resolution, presence and non-silence of the audio
track, by what tool, `ffprobe` or otherwise).

## Benchmarking for this phase

This phase's code touches the end-to-end wall clock and peak memory
benchmark (`docs/02_TRD.md` section 6, target under 5 minutes, target
under 2GB peak, for a full-length source; the automated version of this
benchmark runs against the synthetic fixture per
`harness/e2e_benchmark.py`'s documented restriction, not the real asset).
Follow `.agents/rules/04-benchmark-recording.md`: run
`harness/e2e_benchmark.py` against the synthetic fixture now that
`baa run` actually exists end to end, and run
`harness/benchmark_update.py` to record the result.

## Documentation for this phase

Follow `.agents/rules/03-documentation-update.md`: update
`docs/03_SDD.md` section 9's rows for FR-6, FR-7, FR-8, FR-10, add the
`CHANGELOG.md` entry. This phase is a good point to also update
`README.md`'s "Setup" and "Quick start" sections if the actual CLI
invocation differs in any way from what is currently documented there
(flag names, subcommand structure), since this is the first phase where
that section becomes literally testable against real behavior rather than
aspirational.

## End of phase

Follow `.agents/rules/01-git-workflow.md`'s end-of-phase procedure: push,
open the pull request into `develop`, and stop there.

Note for the next session: phase 6 (QA hardening and the phase 1
release to `main`) is the point at which you, the project owner, run the
manual QA checklist in `docs/06_QA_TEST_PLAN.md` section 7 against your
real local asset. Do not run that checklist as part of this phase; it is
explicitly out of scope here per the phase boundary in
`docs/03_SDD.md` section 8.
