# Software Design Document (SDD)

Project codename: Bad Apple Anything
Status: Draft v1.0
Last updated: 2026-08-10
Depends on: 01_PRD.md, 02_TRD.md, docs/adr/*

## 1. Repository layout

```
baa/
  Cargo.toml                     workspace manifest
  Cargo.lock
  crates/
    baa-ir/                    IR types, BSF serde, versioning
    baa-render/                wgpu renderer, tessellation, compositor
    baa-encode/                ffmpeg subprocess wrapper (demux/mux)
    baa-pipeline/               stage trait, DAG runner, run summary
    baa-cli/                    clap entrypoint, binary name `baa`
  python/
    baa_ingest/
      pyproject.toml
      baa_ingest/
        __init__.py
        demux.py                  ffmpeg-based audio/video extraction
        background.py               temporal-median background estimation
        matting.py                  pluggable matting backend interface + classical impl
        vectorize.py                 marching squares + polygon simplification
        ir_writer.py                  BSF v1 msgpack writer
        cli.py                        `python -m baa_ingest`
      tests/
      requirements.lock
  assets/                          user media, gitignored, never committed
  out/                              pipeline artifacts, gitignored
  docs/                              this document set
  harness/                           agent harness, phase prompts, benchmark tooling
  .agents/
    rules/                           persistent Antigravity CLI rules
  .github/
    workflows/
      ci.yml
  AGENTS.md
  README.md
  CHANGELOG.md
  .gitignore
```

## 2. Component overview

```
[assets/source.mp4]
        |
        v
+----------------------+
|  baa_ingest (Py)    |  demux -> matting -> vectorize -> BSF + audio.wav
+----------------------+
        |
        v
   out/scene.umsf   out/audio.wav
        |                |
        v                |
+----------------------+ |
|  baa-render (Rust)  | |     tessellate polygons, rasterize via wgpu,
|                        | |     stream raw frames to ffmpeg encode
+----------------------+ |
        |                |
        v                v
   out/video_noaudio.mp4 -> mux (baa-encode) -> out/final.mp4
```

`baa-pipeline` owns the DAG: ingest -> render -> encode, plus the
run-summary emission. `baa-cli` is the thin argument-parsing layer that
constructs a `PipelineConfig` and calls into `baa-pipeline`.

## 3. Module design

### 3.1 `baa-ir`

Responsibilities: define `SceneHeader`, `SceneFrame`, `Polygon` (a
`Vec<[f32; 2]>` newtype with validation: minimum 3 points, no NaN/Inf),
and the BSF reader/writer built on `serde` + `rmp_serde`. Provides a
streaming reader (`SceneReader::next_frame() -> Option<SceneFrame>`) so
the renderer never holds the full scene in memory at once, which matters
for the NFR-4 memory budget on longer sources.

Versioning: `SceneHeader.version` is matched against a
`SUPPORTED_VERSIONS` constant in this crate. An unsupported version is a
hard error at load time with a message naming both the file's version and
the supported range, not a silent best-effort parse.

### 3.2 `baa-render`

Responsibilities: polygon tessellation (via `lyon`, converting each
`Polygon` into a triangle mesh), a `wgpu` render pipeline that draws the
tessellated silhouette against a configurable background (solid color,
vertical gradient, or a procedural moon/petal scene matching the phase 0
prototype's look), and a headless render path that reads back the GPU
framebuffer into a CPU buffer for encoding. Also owns the software
rasterizer fallback used when no suitable GPU adapter is available,
selected automatically at startup with a logged warning, not a silent
quality change.

`RenderConfig` fields: output width/height, output fps (may differ from
source fps; frame resampling is nearest-timestamp against the BSF's
`t_ms` field), background style enum, fill color, anti-aliasing sample
count.

### 3.3 `baa-encode`

Responsibilities: two subprocess wrappers around `ffmpeg`.
`RawFrameEncoder` accepts a stream of raw BGR24 frame buffers over stdin
and produces a silent H.264 MP4 (mirrors the phase 0 prototype's proven
approach). `Muxer` combines that video with an audio file into the final
output using stream copy for video (`-c:v copy`) and AAC re-encode for
audio, with `-shortest` disabled in favor of explicit duration matching
against the BSF header's frame count, so a mismatched audio length is
detected and reported rather than silently truncating either stream.

All `ffmpeg` invocations use `std::process::Command` with an explicit
argument vector; no argument is ever built via string concatenation of
user-controlled paths into a shell string (TR-SEC-1).

### 3.4 `baa-pipeline`

Responsibilities: defines a `Stage` trait (`run(&self, ctx: &mut RunContext) -> Result<StageReport>`),
a fixed-order runner for phase 1 (ingest, render, encode are not yet a
general DAG since phase 1 is linear; the trait exists so phase 2's
pluggable-backend work can insert stages without redesigning the runner),
and `RunSummary` assembly, written to `out/run_summary.json` after every
run (success or failure, with a `status` field), consumed by the
benchmark-recording harness.

### 3.5 `baa-cli`

Responsibilities: `clap`-derived argument parsing, subcommands `ingest`,
`render`, `encode`, and `run` (the end-to-end command). Resolves and
validates the output directory against TR-SEC-2 before invoking the
pipeline. Configures `tracing` subscribers (human-readable to stderr,
optional JSON log file via `--log-file`).

### 3.6 `python/baa_ingest`

`demux.py`: wraps `ffmpeg -i <input> <output.wav>` and
`ffmpeg -i <input> -f rawvideo ...` (or frame-by-frame decode via
`cv2.VideoCapture`) for the video side. Explicit argument lists only,
mirroring TR-SEC-1 on the Python side.

`background.py`: implements `estimate_background(frames_iterable, n_samples)`
using pixelwise temporal median, as validated in the phase 0 prototype and
documented in ADR-0004 (chosen over adaptive background subtraction
specifically because adaptive methods absorb slow-moving or momentarily
still subjects into the background model, which is common in dance
choreography).

`matting.py`: defines a `MattingBackend` protocol
(`extract_mask(frame, context) -> np.ndarray`) with one implementation in
phase 1 (`TemporalMedianMatting`), so phase 2 can add a learned-model
backend behind the same interface without touching `vectorize.py` or
`ir_writer.py`.

`vectorize.py`: marching-squares contour extraction
(`skimage.measure.find_contours` or an equivalent pure implementation if
that dependency proves too heavy) on the binary mask, followed by
Douglas-Peucker polygon simplification with an epsilon tuned to keep
silhouette edges visually clean at target resolution while keeping
polygon vertex counts bounded (a hard cap per polygon, configurable,
default 200 points, to bound tessellation cost downstream).

`ir_writer.py`: streams `SceneFrame` records to the `.umsf` output as
they are produced, rather than buffering the full scene, mirroring the
streaming design of `baa-ir`'s reader.

## 4. Data flow for the first deliverable (phase 1)

1. User places the source video at `assets/source.mp4`.
2. `baa run --input assets/source.mp4 --out out/` invoked.
3. Ingest stage: `demux.py` extracts `out/audio.wav` (original audio,
   lossless PCM or user-configured codec) and provides a frame iterator
   over the source video. `background.py` estimates a static background
   from a sample of frames. `matting.py` produces a binary mask per frame.
   `vectorize.py` converts each mask into simplified polygons.
   `ir_writer.py` streams these into `out/scene.umsf` alongside a
   per-frame loudness envelope computed from `audio.wav` (RMS over the
   frame's time window; beat/onset detection is a phase 2 requirement,
   phase 1 only needs the continuous loudness envelope for optional
   audio-reactive rendering parameters, not for retiming, since phase 1
   is a 1:1 reconstruction of the source timing).
4. Render stage: `baa-render` reads `out/scene.umsf` frame by frame,
   tessellates polygons, rasterizes via `wgpu` against the configured
   background style, and streams raw frames to `baa-encode`'s
   `RawFrameEncoder`, producing `out/video_noaudio.mp4`.
5. Encode stage: `baa-encode`'s `Muxer` combines
   `out/video_noaudio.mp4` and `out/audio.wav` into `out/final.mp4`,
   verifying duration match against the BSF header's frame count and fps.
6. `RunSummary` is written to `out/run_summary.json`.

## 5. Rendering style for phase 1

The first deliverable's visual target is a faithful vector reconstruction
of the source silhouette: solid fill silhouette matching the source
subject's outline per frame, rendered against a background style selected
by config (default: the vertical gradient plus procedural moon and petals
established in the phase 0 prototype, since the reference material shares
that visual vocabulary; this is original artwork generated by
`baa-render`'s procedural scene code, not extracted from the source).
Because the animation's source of truth is the vector polygon stream
(FR-4), not the original pixels, this counts as procedural/programmatic
animation rather than pixel playback, which is the phase 1 acceptance
criterion.

## 6. Error handling strategy

Every stage returns `Result<StageReport, StageError>`. `StageError` is a
structured enum (not a stringly-typed error) with variants covering:
input validation failure, subprocess failure (with captured stderr tail),
resource limit exceeded (TR-SEC-3), IR version mismatch, and I/O error.
The CLI maps `StageError` to a process exit code (1 for user/input error,
2 for environment error such as missing `ffmpeg`, 3 for internal/panic
class errors) so the harness's test-gating and any future CI consumer can
distinguish failure classes programmatically rather than parsing text.

## 7. Configuration

A single `baa.toml` at the repository root (or path passed via
`--config`) holds defaults for resolution, fps, background style, matting
backend selection, and resource limits. CLI flags override config file
values. Config is validated eagerly at startup (fail fast, before any
stage runs) using a schema check, not lazily when a value happens to be
read.

## 8. Phase breakdown (engineering phases, distinct from PRD release
   phases; these map many-to-one, see section 9)

- Phase 0: prototype (complete, see project history; not part of this
  repository's phase numbering, it validated the rig/renderer/ingestion
  approach in an unstructured script and is superseded by this design).
- Phase 1: repository bootstrap, workspace scaffolding, CI skeleton, no
  functional code yet.
- Phase 2: `baa_ingest` demux + background estimation + classical
  matting, unit tested against synthetic fixtures.
- Phase 3: vectorization (`vectorize.py`) and BSF writer, with a
  round-trip serialization test and a golden-fixture visual regression
  test.
- Phase 4: `baa-render` core: tessellation, wgpu pipeline, software
  fallback, rendering the phase 3 fixture's BSF output to frames.
- Phase 5: `baa-encode` and full end-to-end wiring via `baa-cli`,
  producing a real playable MP4 from a real source video for the first
  time.
- Phase 6: benchmarking harness wired to real measurements, README
  benchmark section populated, QA hardening pass, phase 1 (first
  deliverable) release to `main`.

This breakdown is the one the Vibe Coding Guide's phase prompts follow
directly; each phase prompt in `harness/phase_prompts/` corresponds to one
row above.

## 9. Requirements traceability matrix

| PRD requirement | SDD phase | Primary test(s) |
|---|---|---|
| FR-1 input acceptance | Phase 2 | `test_demux_accepts_valid_input` |
| FR-2 audio extraction | Phase 2 | `test_demux_audio_extraction_lossless` |
| FR-3 matting | Phase 2 | `test_temporal_median_matting_synthetic_fixture` |
| FR-4 vectorization/IR | Phase 3 | `test_vectorize_polygon_count_bounded`, `test_usf_roundtrip` |
| FR-5 stylized render | Phase 4 | `test_render_matches_golden_frame_ssim` |
| FR-6 audio-accurate mux | Phase 5 | `test_mux_duration_matches_header` |
| FR-7 CLI stages | Phase 5 | `test_cli_subcommands_e2e` |
| FR-8 configurability | Phase 1, 5 | `test_config_overrides_applied` |
| FR-9 full-length run | Phase 6 | `test_e2e_full_length_fixture` |
| FR-10 structured logs | Phase 1, 5 | `test_run_summary_schema` |
| NFR-1..4 performance | Phase 6 | benchmark suite, TRD section 6 table |
| NFR-5 idempotency | Phase 6 | `test_e2e_repeat_run_identical` |
| NFR-7 GPU-less CI | Phase 4 | `test_software_rasterizer_fallback` |
| NFR-9 no path escape / no network | Phase 1, 2, 6 | `test_output_path_containment`, `test_no_network_calls` |
| FR-11, FR-12, FR-13 | Phase 2 (PRD) engineering phases, not in this document's phase 1-6 range | tracked in a future SDD revision |
