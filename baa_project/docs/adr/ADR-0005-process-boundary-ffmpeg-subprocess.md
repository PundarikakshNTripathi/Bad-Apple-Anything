# ADR-0005: ffmpeg invoked as a subprocess, not linked via FFI bindings

Status: Accepted
Date: 2026-08-10
Deciders: project owner

## Context

Two approaches exist for using ffmpeg's functionality from Rust: link
against libav*/libffmpeg via FFI bindings (several crates offer this,
with varying levels of safety wrapping), or shell out to the `ffmpeg`
CLI binary as a subprocess, communicating over stdin/stdout/files. The
same choice exists on the Python side, where `opencv-python`'s video I/O
and direct `ffmpeg` subprocess invocation are both viable.

FFI bindings avoid subprocess spawn overhead and give programmatic access
to more granular control (filter graphs, per-frame codec parameters)
without shelling out. They also tie the build to whichever ffmpeg/libav
version the bindings target, which is a real maintenance burden across
three target operating systems (TRD section 7), and any unsafe FFI
surface is exactly the kind of risk ADR-0001 already argued Rust should
be used to avoid.

Subprocess invocation depends only on an `ffmpeg` binary being present on
the system, decouples the project from any specific libav ABI, and is
the same pattern already validated in the project's phase 0 prototype
(raw frames piped to an `ffmpeg -f rawvideo` subprocess, muxing a second
audio stream in a follow-up call), which produced correct output.

## Decision

Use the `ffmpeg` CLI binary as a subprocess for all demux, mux, and
encode operations, on both the Rust and Python sides. `ffmpeg` availability
is a documented, checked system requirement (verified at CLI startup with
a clear error message if missing, not discovered as an obscure failure
partway through a run).

All invocations use an explicit argument vector (`std::process::Command`
in Rust, `subprocess.run([...])` in Python), never a shell string that
concatenates user-controlled paths, directly satisfying TR-SEC-1.

## Consequences

Positive: no FFI unsafe surface for media codec handling, which is
historically a common source of memory-safety vulnerabilities in
C/C++ media libraries; shelling out to a well-audited external binary
sidesteps that risk class entirely for this project's own code, though
see the Security & Privacy / Threat Model document for the residual risk
of ffmpeg itself parsing an untrusted/malformed input file. Simple to
reason about, simple to test (subprocess exit code and captured
stderr are the entire contract), and consistent with the already-proven
phase 0 approach.

Negative: subprocess spawn and pipe I/O overhead versus in-process calls,
not expected to be material at this project's throughput targets but
noted for completeness. Error messages from a failed ffmpeg invocation
require parsing stderr text to present a useful diagnostic to the user,
which is inherently less structured than a typed error from an FFI
binding; `baa-encode` and `baa_ingest`'s wrappers are required to
capture and surface the last N lines of stderr on failure specifically to
mitigate this.

## Revisit triggers

If per-frame encode latency ever becomes a measured bottleneck at the
granularity where subprocess/pipe overhead is a meaningful fraction of
total time (not expected given the batch nature of this pipeline),
reconsider FFI bindings for the encode path specifically, keeping demux
on the subprocess path regardless since demux is not on the hot path in
the same way.
