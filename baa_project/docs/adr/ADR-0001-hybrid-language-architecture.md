# ADR-0001: Hybrid Rust and Python architecture over a single-language system

Status: Accepted
Date: 2026-08-10
Deciders: project owner

## Context

The system has two categories of work with materially different tooling
maturity. The rendering/encoding/orchestration core benefits from a
systems language: predictable performance, no garbage collector pauses
during frame streaming, straightforward static binaries for
distribution. The ingestion stage (video decode, background estimation,
matting, contour extraction, and in later phases learned matting models
and beat detection) sits in a domain where Python's ecosystem (OpenCV,
NumPy, scikit-image, and eventually PyTorch/ONNX Runtime for learned
matting) is significantly more mature than either Rust's or C++'s
equivalents, per the research summarized in the project's initial
exploration.

Three options were considered.

Option A: pure C++. Mature ecosystem, direct access to OpenCV's native
API, mature GPU tooling. Rejected primarily on memory-safety grounds for
a codebase that will do substantial manual buffer manipulation across the
render/encode boundary, and because it does not meaningfully improve on
Python for the CV/ML-heavy ingestion stage regardless of language choice.

Option B: pure Rust, including the ingestion stage via Rust CV crates or
FFI bindings to OpenCV. Rejected because the Rust CV/ML ecosystem is
materially behind Python's for the matting and future learned-model work,
and because wrapping Python's model ecosystem via FFI would reintroduce
Python as a dependency anyway while adding an unsafe FFI boundary for no
benefit.

Option C (chosen): Rust core (IR, renderer, encoder, orchestration, CLI)
with a Python ingestion package invoked as a subprocess with a strict,
versioned data contract (the BSF format, see ADR-0002) at the boundary.

## Decision

Adopt Option C. The Rust core owns everything downstream of the
Intermediate Representation: IR types, rendering, encoding, pipeline
orchestration, and the CLI. The Python package owns everything upstream
of the IR: demuxing, background estimation, matting, and vectorization.
The two communicate exclusively through the BSF file format and a
stdout progress-line protocol, both defined in the TRD, never through FFI
or shared memory.

## Consequences

Positive: each stage uses the language best suited to it. The Rust core
has no Python runtime dependency for anyone who only wants to consume
pre-generated BSF files (for example, a future "any MV" pipeline that
generates BSF directly from a natural-language description without ever
invoking the Python ingestion package). The subprocess boundary makes
the ingestion stage trivially replaceable (a different language or a
remote ingestion service could produce BSF files without any change to
the Rust side).

Negative: two toolchains, two dependency management systems, and two test
suites to maintain. Debugging across the process boundary requires
correlating two sets of logs rather than one stack trace. Startup latency
for short runs is slightly higher due to Python interpreter startup and
subprocess spawn overhead; this is not expected to be material at the
target runtime of minutes for a full-length source, but should be kept in
mind if the tool is later used for very short clips where the fixed
overhead becomes proportionally larger.

## Revisit triggers

If the Python ingestion stage ever needs to hand back per-frame data at a
rate that makes subprocess/file-based IPC a measured bottleneck (not
merely a suspicion), consider a lower-overhead IPC mechanism (a local
Unix domain socket streaming BSF records) before considering a language
change. A full rewrite of ingestion into Rust should only be reconsidered
if the Python ML ecosystem's advantage narrows enough that maintaining
two toolchains stops paying for itself, which is not the case as of this
writing.
