# Phase 03: vectorization and the BAA Scene Format (BSF)

Paste this prompt into a fresh Antigravity CLI (agy) root agent session,
after phase 02's pull request has been merged into `develop` and your
local `develop` is up to date.

---

Before doing anything else, reread `AGENTS.md`, and specifically reread
`docs/adr/ADR-0002-intermediate-representation-format.md` and
`docs/02_TRD.md` section 4.2 in full, since this phase implements that
exact contract on both the Python and Rust sides and any deviation from
the documented schema is a defect, not a design choice available to you
in this phase. This is phase 3 of 6 per `docs/03_SDD.md` section 8.
Create branch `phase/03-vectorization-ir` from `develop` per
`.agents/rules/01-git-workflow.md` before making any change.

## Scope for this phase

1. Implement `crates/baa-ir`: the `SceneHeader`, `SceneFrame`, and
   `Polygon` types exactly as specified in `docs/02_TRD.md` section 4.2,
   with `serde` derives and `rmp_serde` for MessagePack encoding. Implement
   the streaming `SceneReader` and a corresponding streaming writer, per
   `docs/03_SDD.md` section 3.1: the reader must not buffer the full scene
   in memory, since that is a direct NFR-4 memory budget requirement, not
   a style preference.
2. Implement version checking: `SUPPORTED_VERSIONS` and the specific
   error behavior for an unsupported version (a hard, named error, not a
   silent best-effort parse), and the requirement that unknown fields in
   a frame record are ignored, not treated as errors, per the TRD's
   forward-compatibility rule.
3. Implement `vectorize.py` in `python/baa_ingest`: marching-squares
   contour extraction on the binary mask produced by phase 2's matting
   backend, followed by Douglas-Peucker polygon simplification with a
   configurable epsilon and a hard, configurable cap on vertex count per
   polygon (default 200), per `docs/03_SDD.md` section 3.6. Polygons with
   fewer than 3 points after simplification must be dropped, not passed
   through and rejected downstream, since `baa-ir`'s `Polygon` type
   itself rejects that case and you want a clear error at the point of
   creation, not a confusing one two layers away.
4. Implement `ir_writer.py`: streams `SceneFrame` records to a `.umsf`
   file as they are produced by the vectorization step, matching the
   streaming design of the Rust reader, not buffering the full scene
   before writing.
5. Write the unit tests listed in `docs/06_QA_TEST_PLAN.md` sections 3.1
   and 3.5 relevant to this phase: the `baa-ir` serialization round-trip
   tests, the unsupported-version and forward-compatible-unknown-field
   tests, `test_vectorize_polygon_count_bounded`,
   `test_vectorize_produces_closed_polygons`.
6. Write `test_usf_roundtrip` as a genuine cross-language test per
   `docs/06_QA_TEST_PLAN.md` section 3.5: a scene written by
   `ir_writer.py` must be readable by `baa-ir`'s Rust reader, and a
   scene written by a small Rust test writer must be readable by a Python
   reader you add to `baa_ingest` for this purpose (even if the Python
   side has no other reason to read BSF files yet, this test needs it to
   actually validate both directions of the contract, not just one).
7. Write the integration test `test_usf_v1_fixture_still_parses` per
   `docs/06_QA_TEST_PLAN.md` section 4.2: generate one fixture BSF file
   now, check it into the test fixtures directory as structured
   MessagePack data (not a media file, this does not conflict with
   ADR-0007), and write the test that asserts it still parses correctly.
   This fixture becomes a permanent regression check for future phases;
   do not regenerate or delete it later without a deliberate, reviewed
   reason.

## Test gating for this phase

Follow `.agents/rules/02-test-gating.md` in full. Run `cargo test -p
baa-ir` and `pytest python/baa_ingest -v` and confirm every test
above passes, with particular attention to the cross-language round-trip
test actually exercising both directions, not just one, since a
one-directional pass can hide a real incompatibility in the other
direction.

## Benchmarking for this phase

This phase's code is on the IR round-trip benchmark path (`docs/02_TRD.md`
section 6, `bench_usf_roundtrip`, target under 500ms combined for 6570
frames). Follow `.agents/rules/04-benchmark-recording.md`: write this
Criterion benchmark against a synthetically generated 6570-frame scene
(not the real asset), run it, and run `harness/benchmark_update.py`
before considering this phase done.

## Documentation for this phase

Follow `.agents/rules/03-documentation-update.md`: update
`docs/03_SDD.md` section 9's row for FR-4, add the `CHANGELOG.md` entry.
If implementing the marching-squares step reveals a need for a dependency
not anticipated in `docs/02_TRD.md` section 3 (for example, if
`scikit-image` proves too heavy and you substitute a lighter
implementation), note this explicitly in the pull request description
and in `CHANGELOG.md`, and update `docs/02_TRD.md` section 3's dependency
list to match reality.

## End of phase

Follow `.agents/rules/01-git-workflow.md`'s end-of-phase procedure: push,
open the pull request into `develop`, and stop there.
