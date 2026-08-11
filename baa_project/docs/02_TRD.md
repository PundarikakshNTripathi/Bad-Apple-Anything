# Technical Requirements Document (TRD)

Project codename: Bad Apple Anything
Status: Draft v1.0
Last updated: 2026-08-10
Depends on: 01_PRD.md

## 1. Purpose

This document translates the PRD's functional and non-functional
requirements into concrete technical requirements: languages, runtime
targets, data formats, interfaces between components, and the acceptance
thresholds engineering work is measured against. It does not describe
internal module design; that is the SDD's job.

## 2. Language and runtime selection

Decision record: ADR-0001. Summary of the outcome used throughout this
document:

- Core engine (IR types, rendering, encoding orchestration, CLI): Rust,
  stable toolchain, 2021 edition minimum, workspace-based monorepo.
- Ingestion and CV/vectorization stage: Python 3.11+, a separate installable
  package (`baa_ingest`), invoked by the Rust CLI as a subprocess with a
  defined stdin/stdout/exit-code contract, not via FFI. This keeps the
  Rust core free of a Python runtime dependency, and keeps the ML/CV
  ecosystem (where Python is materially stronger) isolated to the one
  stage that needs it.
- Rendering backend: `wgpu` (Rust), targeting Vulkan on Linux, Metal on
  macOS, DirectX 12 on Windows, with a software (CPU) rasterizer fallback
  for CI and headless environments without a GPU.
- Video/audio demux and mux: the `ffmpeg` CLI binary, invoked as a
  subprocess (ADR-0005), not linked via FFI bindings.

## 3. System boundary and external dependencies

Required system binaries: `ffmpeg` (>= 6.0), a Vulkan/Metal/DX12-capable
GPU driver for hardware-accelerated rendering (optional; falls back to
software rendering if absent).

Required Rust crates (pinned in `Cargo.lock`, see SDD section 4 for the
full dependency table): `wgpu`, `lyon` (polygon tessellation), `clap`
(CLI), `serde` + `rmp-serde` (MessagePack IR serialization), `tracing`
(structured logging), `criterion` (benchmarking, dev-dependency).

Required Python packages (pinned in `python/baa_ingest/requirements.lock`):
`opencv-python-headless`, `numpy`, `msgpack`, `click` (ingestion CLI).
No network access and no model weight downloads are required for the
phase 1 matting backend (classical temporal-median differencing); this is
a deliberate v1 constraint, see ADR-0004.

## 4. Interfaces between components

### 4.1 Rust CLI to Python ingestion stage

Invocation contract: the Rust CLI invokes
`python -m baa_ingest ingest --input <path> --out-dir <path> --config <path>`
as a subprocess. The Python process:
- Writes structured progress lines to stdout as single-line JSON objects
  (`{"stage": "matting", "frame": 120, "total": 6570}`), one per reported
  checkpoint (at minimum every 1% of total frames).
- Writes human-readable diagnostics to stderr.
- Writes the IR artifact to `<out-dir>/scene.umsf` (BAA Scene Format,
  see 4.2) and the extracted audio to `<out-dir>/audio.wav`.
- Exits 0 on success. Any non-zero exit is treated as a hard pipeline
  failure; the Rust side does not attempt to interpret partial output from
  a non-zero exit.
- The Rust CLI parses stdout progress lines to drive its own progress bar
  and structured run summary; malformed lines are logged as warnings and
  otherwise ignored (forward compatible: unknown JSON fields are ignored,
  not treated as errors).

### 4.2 BAA Scene Format (BSF), v1

Binary MessagePack stream. Two top-level objects:

Header (first object in the stream):
```
{
  "format": "BSF",
  "version": 1,
  "fps": 30.0,
  "width": 960,
  "height": 540,
  "frame_count": 6570,
  "source_sha256": "<hex digest of the original input file, NOT the file itself>",
  "created_at_unix": 1770000000
}
```

Then exactly `frame_count` frame records, each:
```
{
  "i": 0,                     // frame index, 0-based
  "t_ms": 0,                  // presentation timestamp in milliseconds
  "polygons": [                // list of closed polygons, normalized [0,1] coords
    [[0.41, 0.22], [0.44, 0.20], ...],
    ...
  ],
  "audio_rms": 0.0,            // 0..1, loudness envelope sample for this frame
  "beat": false,                // true if a beat/onset was detected at this frame
  "onset_strength": 0.0         // 0..1 continuous onset detection function value
}
```

Compatibility rule: consumers MUST ignore unknown fields. Producers MUST
NOT remove or repurpose an existing field within the same major version;
a breaking change increments `version` and both producer and consumer
declare the versions they support. This is enforced by a round-trip
serialization test in the test plan (see QA/Test Plan section 4.2).

### 4.3 Renderer input/output contract

Input: a BSF file path plus a `RenderConfig` (resolution override,
background style enum, silhouette fill color, output frame rate if
different from source, anti-aliasing level).

Output: a sequence of raw BGR24 frames written to the stdin of an `ffmpeg`
encode subprocess (the same pattern validated in the phase 0 prototype),
producing an H.264 MP4 with no audio track, followed by a mux step that
combines that video with `audio.wav` from the ingestion stage into the
final deliverable.

## 5. Data and storage requirements

- `assets/` holds user-supplied source media. Read-only from the
  pipeline's perspective. Never committed to version control (see
  ADR-0007); `.gitignore` enforces this at the repository level in
  addition to the CI check in the QA/Test Plan.
- `out/` holds all pipeline artifacts (IR files, extracted audio,
  intermediate video, final output, run summaries). Fully regenerable
  from `assets/` plus the code; never a source of truth; safe to delete
  entirely between runs.
- `out/run_summary.json` is the machine-readable record of a pipeline
  run: per-stage wall-clock time, frame counts, peak memory (via the
  `psutil`/`resource` measurement described in the QA/Test Plan
  benchmarking section), and the git commit hash the run was produced
  from. This file is the direct input to the benchmark-recording harness
  described in the Vibe Coding Guide.

## 6. Performance acceptance thresholds

These are the concrete, testable versions of PRD NFR-1 through NFR-4.
Each has an automated benchmark (Criterion for Rust-side render/tessellate
paths, `pytest-benchmark` for Python-side ingestion, and a custom
end-to-end timer for full-pipeline wall clock). CI fails a pull request
that regresses any threshold by more than 15 percent versus the value
recorded on `develop` at the time of the PR, per the QA/Test Plan
regression policy.

| Metric | Threshold | Measured by |
|---|---|---|
| Ingestion throughput (720p) | >= 0.5x real-time, single core | `bench_ingest_throughput` |
| Render throughput (960x540, headless) | >= 300 fps | `bench_render_throughput` |
| Render throughput (1920x1080, GPU) | >= 60 fps | `bench_render_throughput_1080p` |
| End-to-end wall clock, full-length source | < 5 min (target < 3 min) | `bench_e2e_full_pipeline` |
| Peak resident memory, 5 min 1080p source | < 2 GB | `bench_e2e_full_pipeline` (memory sample) |
| IR round-trip serialize/deserialize, 6570 frames | < 500 ms combined | `bench_usf_roundtrip` |

## 7. Compatibility and platform requirements

- Linux (primary development and CI target): Ubuntu 22.04 or newer,
  x86_64.
- macOS: 13 (Ventura) or newer, both Apple Silicon and x86_64, Metal
  backend via wgpu.
- Windows: best-effort, DirectX 12 backend via wgpu; not part of the CI
  matrix in phase 1, tracked as a follow-up.
- GPU-less environments (CI runners): wgpu's software rasterizer fallback
  is a hard requirement, not optional, since the test plan requires the
  full render path to run in CI without a GPU.

## 8. Security and privacy technical requirements

Full threat model is in a dedicated document. The TRD-level requirements
that constrain implementation:

- TR-SEC-1: the `ffmpeg` subprocess MUST be invoked with an explicit
  argument list (no shell string interpolation), to eliminate command
  injection regardless of file naming.
- TR-SEC-2: all filesystem writes MUST be resolved and checked to remain
  within the configured output directory before any write occurs
  (path traversal defense), regardless of what a config file or CLI flag
  claims the output path is.
- TR-SEC-3: the ingestion process MUST enforce a configurable maximum
  input resolution, frame count, and file size, rejecting inputs that
  exceed them before allocating per-frame buffers, to bound memory usage
  from an oversized or malformed input file.
- TR-SEC-4: no component in the phase 1 deliverable makes outbound network
  calls. This is a testable property (see QA/Test Plan section 6) and a
  regression in it is treated as a release blocker.

## 9. Traceability

Every functional requirement in the PRD (FR-1 through FR-13) maps to at
least one phase in the SDD's phase breakdown and at least one test case
in the QA/Test Plan. The mapping table lives in the SDD, section 9, to
avoid duplicating it across documents and having the copies drift.
