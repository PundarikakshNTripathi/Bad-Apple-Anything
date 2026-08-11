# Product Requirements Document (PRD)

Project codename: Bad Apple Anything
Document owner: (assign)
Status: Draft v1.0
Last updated: 2026-08-10

## 1. Problem statement

Silhouette-style music videos, most famously "Bad Apple!!", are produced
today through manual rotoscoping and hand animation. There is no tool that
takes an arbitrary video plus its audio track and produces a stylized,
procedurally-generated silhouette animation synced to the beat, nor one
that lets a person describe a silhouette animation in plain language and
get a rendered result. Existing rotoscoping software (Boris FX Silhouette
and similar) targets professional VFX pipelines, requires per-shot manual
supervision, and is not designed around a scriptable, repeatable,
song-driven pipeline.

## 2. Goals

1. Given a source video file and nothing else, produce a procedurally
   rendered, audio-synced silhouette animation that reconstructs the
   subject's motion as vector silhouettes rather than replaying source
   pixels.
2. Extract the audio track from the source video and use it both as the
   output soundtrack and as a driving signal for animation timing (beat
   and onset reactive effects).
3. Support two authoring modes for future MVs beyond the first deliverable:
   a. Reference mode: import a video and/or image references, extract
      motion and style from them.
   b. Descriptive mode: a natural-language description drives a
      procedurally generated choreography, independent of any source
      footage.
4. Be fast enough to be genuinely usable: full-length processing measured
   in minutes, not hours, on a single developer workstation.
5. Be a real, maintainable software system: modular, tested, versioned,
   documented, with a CI pipeline and a defined release process. Not a
   single script.

## 3. Non-goals (explicitly out of scope for v1)

- Real-time interactive editing UI (v1 is a batch CLI pipeline).
- Cloud hosting, multi-tenant SaaS, or a web front end.
- Full 3D scene reconstruction or camera-aware compositing.
- Redistribution or hosting of any copyrighted source media. The tool
  operates on media the user supplies locally; it does not fetch, mirror,
  or ship copyrighted content.
- Photoreal or ML-generated in-betweening of animation frames (interesting
  future work, not required for the first deliverable).

## 4. Users and use cases

Primary user (v1): a single technically proficient hobbyist/developer
(the project owner) using the tool locally via CLI.

Use case A (first deliverable, phase 1): the user places a source video
file in `assets/`. Running the pipeline produces an output video where the
original subject motion has been reconstructed as a vector silhouette
animation, with the original audio track extracted and muxed back in,
timed exactly to the source footage.

Use case B (later phase): the user points the pipeline at a different
source video and a different song; the tool infers a beat grid from the
song and retimes/generates the animation to that grid instead of a 1:1
frame mapping to the source.

Use case C (later phase): the user provides only a text description
("a lone dancer under a full moon, slow contemplative movement, sudden
sharp motion on the chorus hits") and no reference video; the system
generates an original choreography via the existing procedural rig and
renders it against the imported song's beat grid.

## 5. Functional requirements

FR-1. The system SHALL accept a video file path under `assets/` as
      pipeline input.
FR-2. The system SHALL extract the embedded audio track losslessly (or at
      a user-configurable bitrate/codec) into a separate artifact.
FR-3. The system SHALL extract, per frame, a foreground/background
      separation (matting) of the video's subject.
FR-4. The system SHALL convert the per-frame mask into a vector polygon
      representation (the Intermediate Representation, see TRD/SDD) rather
      than retaining raw pixel data as the animation's source of truth.
FR-5. The system SHALL render the vector representation back into video
      frames using a stylized silhouette look (solid fill, configurable
      background treatment) rather than re-displaying the original pixels.
FR-6. The system SHALL mux the extracted audio back into the rendered
      output with frame-accurate sync (drift under one frame across the
      full duration).
FR-7. The system SHALL expose the pipeline as a scriptable CLI with
      distinct, independently invokable stages (ingest, vectorize, render,
      encode) as well as a single end-to-end command.
FR-8. The system SHALL support configuration of resolution, frame rate,
      and background style without code changes (config file or CLI
      flags).
FR-9. The system SHALL be able to process a full-length (approximately
      3 minutes 40 seconds, matching the reference MV's known runtime)
      source video without manual intervention once started.
FR-10. The system SHALL log structured progress and errors sufficient to
      diagnose a failed run without re-running with extra flags.
FR-11 (later phase). The system SHALL detect beats/onsets in an arbitrary
      imported audio track and expose that as a driving signal to the
      renderer.
FR-12 (later phase). The system SHALL accept a natural-language
      description and translate it into choreography parameters consumed
      by the existing rig/render pipeline.
FR-13 (later phase). The system SHALL accept image references (style
      boards, character references) that influence rendering style
      (silhouette shape treatment, background dressing) without requiring
      a full ML training step per reference.

## 6. Non-functional requirements

NFR-1 Performance: ingestion (demux + matting + vectorization) SHALL
      average at least 0.5x real-time single-threaded on a 720p source on
      a 2023-class consumer CPU, and SHALL scale near-linearly with
      additional cores when parallelized across frame batches.
NFR-2 Performance: rendering SHALL sustain at least 300 frames/second at
      960x540 in headless mode on an integrated GPU baseline, and at least
      60 frames/second at 1920x1080 on a discrete GPU.
NFR-3 Performance: end-to-end wall-clock time for the first deliverable
      (approximately 6,570 frames at 30fps for a 3:39 source) SHALL be
      under 5 minutes on the reference development machine, target under
      3 minutes.
NFR-4 Memory: peak resident memory SHALL stay under 2 GB for a 5 minute,
      1080p source processed end-to-end.
NFR-5 Reliability: a full pipeline run SHALL be idempotent; re-running
      against unchanged inputs SHALL produce byte-identical or
      perceptually identical (SSIM >= 0.999) output.
NFR-6 Portability: the system SHALL run on Linux and macOS without source
      changes; Windows support is desirable but not blocking for v1.
NFR-7 Testability: every stage SHALL be independently unit-testable
      without requiring GPU hardware to be present (a software rasterizer
      fallback or mock is required for CI).
NFR-8 Observability: every pipeline run SHALL emit a machine-parseable run
      summary (JSON) containing timing per stage, frame counts, and
      resource usage, in addition to human-readable logs.
NFR-9 Security: the system SHALL never write outside the designated
      output directory and SHALL never transmit user media over the
      network unless a cloud/LLM feature is explicitly enabled by the
      user and clearly disclosed (see Security & Privacy / Threat Model
      document).
NFR-10 Maintainability: the codebase SHALL carry automated tests with
      meaningful coverage of core logic (ingestion, vectorization,
      rendering math, IR serialization), enforced in CI, and SHALL follow
      the branching and commit conventions defined in ADR-0006.

## 7. Success metrics

- SM-1: Phase 1 (first deliverable) produces a complete, audio-synced,
  full-length silhouette reconstruction of the user's source video, with
  no manual frame-by-frame correction required.
- SM-2: Full pipeline run completes within the NFR-3 time budget on the
  reference machine, and the number is recorded automatically in
  `README.md` (see benchmarking harness in the Vibe Coding Guide).
- SM-3: CI is green (all unit, integration, and benchmark-threshold tests
  passing) on every merge to `develop` and `main`.
- SM-4: Zero instances of copyrighted source media committed to version
  control (verified by the repository hygiene check defined in
  ADR-0007 and the QA/Test Plan).

## 8. Constraints and assumptions

- The user supplies their own source video and has the rights necessary
  for their own personal, local, non-distributed use of it. The system
  does not verify or adjudicate licensing; see the Security & Privacy /
  Threat Model document for the content-rights discussion.
- Development and first-run target hardware: a single workstation with a
  consumer CPU and either an integrated or a mid-range discrete GPU. No
  cluster or cloud compute is assumed for v1.
- The natural-language and reference-image authoring modes (FR-12, FR-13)
  depend on an external LLM/vision API in a later phase; v1's first
  deliverable has no such dependency and works fully offline.

## 9. Release plan (high level, see TRD/SDD for phase breakdown)

Phase 1 (first deliverable): reference-mode reconstruction of the user's
own source video and audio, end to end, CLI-driven, tested, benchmarked.

Phase 2: pluggable matting backends (swap classical CV for a learned
matting model), beat/onset-driven retiming for arbitrary songs.

Phase 3: descriptive (natural-language) authoring mode.

Phase 4: reference-image style transfer and multi-subject scenes.

Each phase is gated by its own test suite and is merged to `main` only
after `develop` is green and the phase's acceptance criteria in the
QA/Test Plan are met.
