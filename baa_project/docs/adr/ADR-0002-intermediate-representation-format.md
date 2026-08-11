# ADR-0002: BAA Scene Format (BSF) as a versioned binary IR, decoupling ingestion from rendering

Status: Accepted
Date: 2026-08-10
Deciders: project owner

## Context

A naive implementation could have the ingestion stage write raw video
frames or masks directly, and have the renderer simply re-encode them.
That would not satisfy PRD FR-4 and FR-5: the system is required to
reconstruct the subject as vector data and render it procedurally, not
replay pixels. It would also tightly couple the two stages' internal
representations, making ADR-0001's subprocess boundary far more fragile,
since any change to how masks are represented in Python would ripple
directly into the renderer's expectations.

## Decision

Define an explicit, versioned Intermediate Representation, the BAA
Scene Format (BSF), as the only contract between ingestion and rendering.
BSF is a MessagePack-encoded stream: one header object followed by one
object per frame, containing normalized polygon lists plus a small set of
audio-derived scalar signals (loudness envelope now, beat/onset flags
added in phase 2 without breaking the schema, since consumers are
required to ignore unknown fields per the TRD's compatibility rule).

MessagePack was chosen over plain JSON for size and parse speed at
scale (a full-length source produces on the order of 6,500 frame
records; at that count, MessagePack's binary encoding measurably reduces
both file size and deserialization time versus JSON, and unlike a custom
binary format, MessagePack has mature, well-tested libraries in both
Rust and Python, which matters directly for ADR-0001's subprocess
boundary). Protocol Buffers and FlatBuffers were considered and rejected
for v1: both require a schema compiler step and code generation pipeline
that adds build complexity disproportionate to the benefit at this data
volume and this team size (one developer). This can be revisited if
profiling shows serialization is a bottleneck, which is not expected
given the throughput targets in the TRD.

## Decision detail: streaming, not batch

Both the writer (Python) and reader (Rust) are required to stream frame
records rather than buffer the full scene in memory. This is a direct
consequence of the NFR-4 memory budget: buffering ~6,500 frames of
polygon data for a full-length source is unnecessary memory pressure when
a streaming design costs little additional implementation complexity.

## Consequences

Positive: the renderer never needs to know how a mask was produced,
whether by the phase 1 classical matting backend or a future learned
model. A future "descriptive mode" (PRD FR-12) can generate BSF files
directly from an LLM-driven choreography without touching the renderer
at all. The format is independently testable: a round-trip
serialize/deserialize test (QA/Test Plan section 4.2) is sufficient to
validate the contract without running the full pipeline.

Negative: an additional file format to design, document, and version.
Any bug in the BSF writer or reader is a cross-cutting failure that can
be harder to localize than a bug confined to one stage; this is mitigated
by the round-trip test and by validating the header's declared frame
count against the actual number of frame records read, which the reader
is required to enforce.

## Revisit triggers

If a future phase requires random access into the middle of a scene
(seeking) rather than sequential streaming, reconsider a format with a
frame index/table of contents rather than a pure append stream. This is
not required for phase 1's linear read pattern.
