# QA and Test Plan

Project codename: Bad Apple Anything
Status: Draft v1.0
Last updated: 2026-08-10
Depends on: 01_PRD.md, 02_TRD.md, 03_SDD.md

## 1. Testing philosophy

Every phase in SDD section 8 is gated by its own test suite. A phase is
not considered complete, is not merged to `develop`, and its branch is
not deleted, until every test in this plan that applies to that phase
passes locally and in CI. This is not a soft guideline; it is the literal
gate encoded in the harness's test-gating rule (see the Vibe Coding
Guide and `harness/.agents/rules/02-test-gating.md`), which instructs the
coding agent to keep iterating on failures rather than reporting a phase
complete with failing tests.

Test categories, in the order they are expected to run: unit tests
(fast, no subprocess, no I/O beyond in-memory fixtures), integration
tests (exercise real subprocess boundaries, `ffmpeg`, cross-language IR
round trips, using synthetic fixtures per ADR-0007), golden-frame
regression tests (compare rendered output against a stored reference
using a perceptual similarity threshold, not exact pixel match, since
minor floating point and anti-aliasing differences across platforms are
expected and acceptable), benchmark tests (measure and assert against the
TRD section 6 thresholds), and one manual QA checklist that a human
(the project owner) runs against the real local asset, which by
ADR-0007's policy can never be part of the automated CI suite.

## 2. Environment matrix

CI runs on Linux (Ubuntu 22.04 runner) without GPU hardware, exercising
the software rasterizer fallback path exclusively. This is the required
minimum bar. The project owner is responsible for running the manual QA
checklist (section 7) locally on their actual development machine,
which does have GPU hardware, to validate the hardware-accelerated path,
since CI structurally cannot do this per NFR-7's own premise.

## 3. Unit test requirements by module

### 3.1 `baa-ir`

- `test_polygon_rejects_fewer_than_three_points`
- `test_polygon_rejects_nan_or_inf_coordinates`
- `test_scene_header_serialization_roundtrip`
- `test_scene_frame_serialization_roundtrip`
- `test_reader_rejects_unsupported_version` (asserts a clear, specific
  error, not a silent best-effort parse, per SDD section 3.1)
- `test_reader_forward_compatible_with_unknown_fields` (a frame record
  with an extra field the current reader does not know about must parse
  successfully, per the TRD section 4.2 compatibility rule)

### 3.2 `baa-render`

- `test_tessellation_triangle_count_matches_polygon_complexity`
- `test_software_rasterizer_fallback_selected_without_gpu_adapter`
- `test_render_matches_golden_frame_ssim` (SSIM >= 0.98 against a stored
  reference PNG for a fixed synthetic BSF fixture, generous enough to
  tolerate anti-aliasing differences, strict enough to catch a real
  regression)
- `test_render_respects_output_resolution_config`
- `test_render_frame_resampling_when_output_fps_differs_from_source`

### 3.3 `baa-encode`

- `test_raw_frame_encoder_produces_valid_mp4` (validated by invoking
  `ffprobe` against the output and asserting expected stream properties,
  not merely asserting the file is non-empty)
- `test_muxer_output_duration_matches_header`
- `test_muxer_rejects_mismatched_duration_with_clear_error` (rather than
  silently truncating either stream)
- `test_ffmpeg_invocation_uses_argument_vector_not_shell_string` (a
  static/structural test asserting the subprocess call site never
  constructs a shell command string from a path)

### 3.4 `baa-pipeline` and `baa-cli`

- `test_run_summary_schema` (asserts every required field is present and
  correctly typed)
- `test_stage_error_maps_to_documented_exit_code` (input error to 1,
  environment error to 2, internal error to 3, per SDD section 6)
- `test_config_overrides_applied` (CLI flag overrides config file value
  overrides built-in default, in that precedence order)
- `test_output_path_containment` (includes `../` traversal attempts and
  absolute path overrides pointing outside the configured output root;
  all must be rejected before any write occurs)
- `test_missing_ffmpeg_produces_clear_startup_error` (not a raw
  "file not found" from deep in a subprocess call)

### 3.5 `python/baa_ingest`

- `test_demux_accepts_valid_input`
- `test_demux_audio_extraction_lossless` (extracted audio's sample data
  matches the source track's decoded samples within floating point
  tolerance)
- `test_temporal_median_matting_synthetic_fixture` (this is the direct
  regression test for the MOG2 failure discovered during initial
  prototyping: the fixture specifically includes a held/slow-motion
  segment, and the test asserts the extracted mask's nonzero pixel count
  stays within an expected range through that segment, not dropping to
  near zero the way the earlier adaptive approach did)
- `test_vectorize_polygon_count_bounded` (asserts the configured maximum
  vertex count per polygon, default 200, is respected)
- `test_vectorize_produces_closed_polygons`
- `test_usf_roundtrip` (write then read back a scene, cross-language:
  written by Python, read by Rust, and vice versa, since ADR-0002's value
  depends specifically on both sides agreeing on the wire format, not
  merely each side being internally consistent)
- `test_ingest_enforces_resource_limits` (TR-SEC-3, oversized/malformed
  input dimensions rejected before buffer allocation)
- `test_ingest_subprocess_calls_use_argument_list` (Python-side
  equivalent of the Rust structural test in 3.4)

## 4. Integration tests

### 4.1 Full pipeline against synthetic fixture

`test_e2e_full_pipeline_synthetic_fixture`: runs `baa run` end to end
(ingest, render, encode) against the checked-in synthetic clip, asserts
a valid playable MP4 is produced, with the correct duration, resolution,
and an audio track present and non-silent.

### 4.2 IR contract stability

`test_usf_v1_fixture_still_parses`: a BSF v1 file generated at an earlier
point in development is checked into the test fixtures directory (as
structured msgpack, not a media file, so this does not conflict with
ADR-0007) and must still parse correctly by the current reader,
regardless of any refactor since it was generated. This is the concrete
enforcement of ADR-0002's "producers must not repurpose an existing
field within the same major version" rule.

### 4.3 Idempotency

`test_e2e_repeat_run_identical`: running the full pipeline twice against
the same synthetic fixture with no code or config change between runs
produces byte-identical or SSIM >= 0.999 output on both runs, per PRD
NFR-5.

## 5. Golden-frame regression testing methodology

A small, fixed set of representative frames (distinct poses/motion
states) from the synthetic fixture are rendered and compared against
stored reference PNGs using SSIM. The threshold (0.98) is deliberately
not 1.0: exact pixel match across different GPU drivers, or between the
GPU path and the software fallback path, is not a realistic bar and would
make the test suite flaky for reasons unrelated to actual correctness.
Reference PNGs are regenerated and re-committed deliberately (their own
reviewed commit, `test(render): update golden frame reference for
<reason>`) only when an intentional visual change is made, never
silently as a side effect of an unrelated change passing or failing.

## 6. Security and hygiene checks (CI-enforced, cross-referenced to the Threat Model)

- `test_no_network_calls`: runs the full pipeline against the synthetic
  fixture with outbound network access blocked at the process/sandbox
  level and asserts the run still completes successfully, directly
  enforcing TR-SEC-4.
- `test_output_path_containment` (listed in 3.4, restated here as a
  security-relevant test, not merely a functional one).
- Repository hygiene check (`scripts/ci/check_no_media_committed.sh` or
  equivalent): scans the diff of the current pull request and, on a
  scheduled weekly job, the full repository history, for common video and
  audio file extensions above a small size threshold, failing the build
  if any are found. This is the CI enforcement half of ADR-0007.
- `cargo audit` and `pip-audit`, per the Security document section 5,
  run as required CI jobs, not advisory-only.

## 7. Manual QA checklist (run locally by the project owner, not in CI)

This checklist exists specifically because ADR-0007 prevents the real
copyrighted asset from ever being part of the automated suite, and
because the hardware-accelerated GPU render path cannot be exercised in
the CI environment described in section 2.

1. Place the real source video at `assets/source.mp4` locally.
2. Run `baa run --input assets/source.mp4 --out out/` on the actual
   development machine (GPU path, not the software fallback).
3. Confirm the output plays back with audio present and in sync for the
   full duration, not just the first few seconds, by scrubbing to at
   least three points late in the timeline, not only the start.
4. Visually confirm the silhouette reconstruction tracks the source
   subject's motion recognizably throughout, including through any
   fast-motion or held-pose segments.
5. Confirm `out/run_summary.json` was written and its timing figures are
   plausible (not zero, not absurdly large).
6. Confirm the benchmark-recording harness (Vibe Coding Guide) correctly
   updated the benchmarks section of `README.md` after this run, and that
   the recorded numbers are consistent with what was observed during the
   run itself.
7. Confirm `git status` shows no new files under `assets/` or `out/`
   staged for commit, as a final manual check on top of the automated
   hygiene check in section 6.

## 8. Benchmark tests and regression policy

Each threshold in TRD section 6 has a corresponding automated benchmark.
Rust-side benchmarks use `criterion`, writing results to
`target/criterion/**/estimates.json`. Python-side ingestion benchmarks
use `pytest-benchmark`, writing to a JSON report file. The end-to-end
wall clock and peak memory benchmark is a dedicated script
(`harness/e2e_benchmark.py`, documented in the Vibe Coding Guide) that
runs the full pipeline against the synthetic fixture, since the real
asset cannot be used per ADR-0007, and separately documents that the
manual QA checklist step 5/6 is where the real-asset timing is actually
observed and recorded.

Regression policy: CI compares the current pull request's benchmark
results against the values most recently recorded on `develop`. A
regression greater than 15 percent on any TRD section 6 metric fails the
pull request's required checks. A regression of 15 percent or less is
allowed to merge but is flagged clearly in the pull request's CI summary,
on the judgment that small, gradual regressions are sometimes an
acceptable tradeoff for correctness or maintainability improvements, but
should never merge silently unnoticed.

## 9. Definition of done, per phase

A phase (SDD section 8) is done when: all unit tests for the modules it
touches pass, all integration tests that exercise those modules pass, any
golden-frame references it affects are deliberately and reviewedly
updated (not left stale, not silently regenerated), benchmarks run
without CI-failing regression per section 8's policy, the security and
hygiene checks in section 6 pass, the phase's documentation update
(README benchmarks section, and any design doc whose content the phase
changed) is committed in the same pull request as the code, and the pull
request into `develop` is merged. Phase 1 (the first deliverable) is
additionally done only when the manual QA checklist in section 7 has been
run at least once by the project owner against the real asset, since no
automated substitute exists for that step.
