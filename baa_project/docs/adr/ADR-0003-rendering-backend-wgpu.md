# ADR-0003: wgpu as the rendering backend, with mandatory software fallback

Status: Accepted
Date: 2026-08-10
Deciders: project owner

## Context

The renderer needs to rasterize tens of thousands of tessellated polygons
per full-length run at the throughput targets in TRD section 6. Native
Vulkan/Metal/DX12 bindings, a game-engine dependency (Bevy), and wgpu were
the three realistic options given the language decision in ADR-0001.

Native graphics API bindings (raw Vulkan via `ash`, or platform-specific
Metal/DX12 bindings) give maximum control and the least abstraction
overhead, but require maintaining three separate backend code paths for
cross-platform support (TRD section 7 requires Linux, macOS, and
best-effort Windows), which is a disproportionate maintenance burden for
this project's scope, which needs 2D polygon rasterization with a simple
compositing model, not general-purpose 3D rendering.

Bevy was considered since it is the most mature Rust game engine as of
this writing. Rejected for v1 because it brings a full ECS, scene graph,
asset pipeline, and windowing/input stack that this project does not
need (the renderer is headless and batch-oriented, not an interactive
application), and because pulling in Bevy's full dependency surface for
what is fundamentally a 2D polygon rasterizer is not a good complexity
trade. This is not a rejection of Bevy in general; if the project later
grows an interactive preview/editor mode, Bevy becomes a much more
directly relevant option and should be reconsidered at that point.

wgpu gives a single cross-platform abstraction over Vulkan, Metal, and
DirectX 12 (and WebGPU, not currently needed but a plausible future
target if an in-browser preview is ever built), with a smaller
dependency surface than a full engine, and is mature enough in 2026 to be
production-viable for this scope.

## Decision

Use `wgpu` directly (not through a game engine) for the render pipeline:
polygon tessellation via `lyon` feeding a `wgpu` render pass, with a
headless framebuffer readback path for encoding.

A software (CPU) rasterization fallback is a hard requirement, not a
nice-to-have, because TRD section 7 and SDD NFR-7 require the full render
path to execute in CI without GPU hardware present. The fallback is
selected automatically when `wgpu` cannot acquire a suitable adapter at
startup, and this selection is always logged at warning level so a CI run
or a headless server run is never silently producing output through an
unexpected code path without a trace of why.

## Consequences

Positive: one rendering code path across all three target operating
systems. Direct control over the exact draw calls issued, which matters
for hitting the throughput targets in TRD section 6 without fighting a
general-purpose engine's abstractions. A clean base to add WebGPU/browser
output later if ever needed.

Negative: wgpu's ecosystem, while production-viable, moves faster and has
thinner documentation than a decade-old engine like Unreal or even
Bevy's own abstractions over wgpu; some rough edges (long clean-build
compile times, occasional lag behind the newest Vulkan extensions) are
accepted as a known cost, consistent with the general Rust-graphics
tradeoffs identified during the initial technology research. The software
fallback path is a second rendering implementation to keep correct and
in sync with the GPU path; this is mitigated by both paths being tested
against the same golden-frame fixtures in the QA/Test Plan.

## Revisit triggers

If an interactive editor/preview mode becomes a real requirement (not
speculative), reconsider Bevy at that point, since its ECS and windowing
stack would then be solving a real problem instead of adding unused
surface area.
