# ADR-0004: Temporal-median background differencing as the phase 1 matting backend, behind a pluggable interface

Status: Accepted
Date: 2026-08-10
Deciders: project owner

## Context

Foreground/background separation (matting) is the step with the widest
range of possible implementations, from simple background subtraction to
deep-learning video matting models (Robust Video Matting, MODNet,
SAM2-video and similar). The project's own early prototyping work
directly tested two classical approaches.

The first attempt used OpenCV's adaptive MOG2 background subtractor.
Direct inspection of its raw output showed it failing specifically on
slow-moving or momentarily still foreground subjects: the raw foreground
mask at a representative frame had only a few hundred nonzero pixels
(thin edge fragments), which subsequent cleanup morphology then erased
entirely, producing a blank mask. The mechanism is well understood: MOG2
adapts its background model over time and absorbs a subject that is not
moving relative to the camera into the background, which is precisely
the condition a dance choreography with held poses produces regularly.

The second attempt used pixelwise temporal-median background estimation
(sample a set of frames across the clip, take the per-pixel median,
treat that as the static background) followed by simple absolute-difference
thresholding against that fixed estimate. This does not have an
adaptation mechanism to fail in the same way, and was confirmed correct
on the same test case that broke MOG2, including at the slowest-motion
point in the test cycle.

A learned matting model was considered for phase 1 and explicitly
deferred, not rejected. Reasons: it introduces a model weights dependency
(download, licensing, versioning), a heavier Python dependency surface
(a deep learning runtime), and GPU/CPU inference cost that is unnecessary
complexity for a phase 1 goal whose reference source material is already
a high-contrast, effectively pre-silhouetted video, where classical
differencing is expected to perform well. Phase 2 explicitly plans to add
a learned-model backend for the general "any video" case, where classical
differencing's assumption of a largely static background and single
consistent subject will not hold as well.

## Decision

Ship temporal-median background differencing as the sole matting backend
for phase 1, implemented behind a `MattingBackend` interface (see SDD
section 3.6) so that phase 2 can add a learned-model implementation
without changing any code downstream of the interface (vectorization, IR
writing, or anything in the Rust core).

## Consequences

Positive: zero external model dependencies, no network access required
(directly satisfying TR-SEC-4 for phase 1), fast, predictable, and
already empirically validated against the specific failure mode that
matters most for this content (held dance poses). Simple enough to unit
test deterministically against synthetic fixtures without any risk of
model-version nondeterminism.

Negative: will not generalize well to source videos with a moving camera,
a genuinely dynamic (non-static) background, or multiple subjects with
overlapping motion. This is an accepted, explicit limitation of phase 1,
not an oversight; PRD section 3 lists broader "any video" support as a
later-phase goal specifically because of this gap.

## Revisit triggers

Any phase 2 work item that requires processing a source video with a
moving camera or a non-static background should trigger implementing the
learned-model backend before that work item is considered done. The
interface exists specifically so this is an additive change.
