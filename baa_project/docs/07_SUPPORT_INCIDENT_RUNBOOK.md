# Support and Incident Runbook

Project codename: Bad Apple Anything
Status: Draft v1.0
Last updated: 2026-08-10
Depends on: 05_SECURITY_PRIVACY_THREAT_MODEL.md (severity taxonomy), 06_QA_TEST_PLAN.md

## 1. Purpose and audience

This is a local CLI tool with a single maintainer as of phase 1; there is
no on-call rotation and no external user base yet. This runbook exists
anyway, for two reasons: it forces the failure modes to be thought
through before they happen rather than during an actual bad run, and it
is the document that scales up cleanly if the project ever gains other
users or contributors, without needing to be written from scratch at that
point.

## 2. Severity taxonomy

Defined in the Security, Privacy, and Threat Model document, section 7.
Restated here for convenience: Sev 1 (data loss or a real security
defect), Sev 2 (silent incorrect output), Sev 3 (loud failure on a
legitimate input), Sev 4 (performance regression under CI's failure
threshold, cosmetic issues, doc gaps).

## 3. Common failure modes and diagnostic steps

### 3.1 `ffmpeg` not found

Symptom: CLI exits immediately with an environment error (exit code 2
per SDD section 6) naming `ffmpeg` as missing.
Diagnosis: this is a deliberate, checked startup failure
(`test_missing_ffmpeg_produces_clear_startup_error`), not a bug to
investigate in the code; it means the system dependency is not installed
or not on `PATH`.
Resolution: install `ffmpeg` >= 6.0 via the platform package manager and
confirm with `ffmpeg -version` before re-running.

### 3.2 Pipeline run produces a video with no audio, or audio that drifts out of sync

Symptom: `out/final.mp4` plays but audio is missing, silent, or
progressively desyncs.
Severity: Sev 2 if this happened without any error being reported (worse
case, silent incorrectness), Sev 3 if the CLI itself reported the mux
duration mismatch and exited non-zero (better case, expected behavior
per `test_muxer_rejects_mismatched_duration_with_clear_error`).
Diagnosis steps:
1. Check `out/run_summary.json` for the encode stage's reported status
   and any duration figures it recorded.
2. Confirm `out/audio.wav` in isolation has correct duration and is not
   silent, to isolate whether the defect is in extraction or in muxing.
3. Confirm the BSF header's declared `frame_count` and `fps` match what
   the render stage actually produced, since a resampling mismatch (SDD
   section 3.2, frame resampling when output fps differs from source) is
   a plausible root cause if a non-default output fps was configured.
Resolution: if reproducible, this is a Sev 2 defect against
`baa-encode`'s `Muxer` or the render stage's resampling logic; file it
as such, do not work around it by manually re-muxing outside the tool,
since that would mask the underlying defect from ever being fixed.

### 3.3 Matting produces a blank or near-blank silhouette for part of the video

Symptom: `out/final.mp4` shows the silhouette disappearing or becoming
fragmented during a specific segment.
Diagnosis: this is the exact failure class ADR-0004 documents and
`test_temporal_median_matting_synthetic_fixture` guards against. First
check whether the affected segment involves the subject being
essentially motionless relative to the temporal-median background
estimate for an extended period, longer than what the background
sampling in `background.py` accounts for; if so this may be a genuine
limitation of the phase 1 classical approach on that specific footage,
not a regression, and should be logged as a known limitation rather than
chased as a bug, pending the phase 2 learned-matting backend (ADR-0004's
revisit trigger).
If the affected segment does not fit that pattern (normal motion, still
blank), this is a Sev 2/3 regression in `matting.py` or `background.py`
and should be reproduced against a new synthetic fixture that captures
the specific motion pattern before attempting a fix, per the QA/Test
Plan's fixture-driven regression discipline.

### 3.4 Out of memory or extremely slow run on a large source file

Symptom: process killed by the OS, or wall clock far exceeds the TRD
section 6 thresholds.
Diagnosis: check the source file's resolution, frame count, and file size
against the limits enforced by TR-SEC-3. If the file exceeds configured
limits and the pipeline still attempted to process it rather than
rejecting it up front, this is a Sev 1 (the resource-limit enforcement
itself failed, which is a security-relevant control per the Threat
Model, not merely a performance issue). If the file is within configured
limits and still exhausts memory or badly misses the performance
threshold, this is a Sev 3/4 performance defect, and the relevant
benchmark in section 8 of the QA/Test Plan should be exercised locally to
reproduce and characterize it before attempting a fix.

### 3.5 GPU render path silently falling back to software rendering

Symptom: render stage completes but is far slower than the GPU throughput
threshold in TRD section 6.
Diagnosis: check the logs for the fallback warning that
`test_software_rasterizer_fallback_selected_without_gpu_adapter` requires
to always be present when this path is taken (ADR-0003 explicitly
requires this to never happen silently). If the warning is present,
this is expected behavior on a machine without a suitable GPU adapter,
not a defect. If the warning is absent but performance still matches the
software path's profile, that is itself a Sev 3 defect: the logging
contract for this fallback has been violated.

## 4. Escalation path

Single maintainer as of phase 1: all issues are self-triaged and
self-assigned by the project owner. If the project gains contributors,
this section must be updated with an actual escalation contact and
expected response time per severity before that becomes operative; a
runbook that names an escalation path without a real person behind it is
worse than one that honestly states there is none yet.

## 5. Rollback procedure

Because `main` is required to always be releasable (ADR-0006), rollback
of a bad release is a `git revert` of the merge commit that introduced
the regression, re-tagged, not a hotfix built under time pressure on top
of the broken state. For a regression discovered on `develop` before it
ever reached `main`, revert the specific phase branch's merge commit on
`develop` and reopen that phase's work on a fresh branch rather than
attempting to patch forward blindly.

## 6. Incident log and postmortem template

Every Sev 1 or Sev 2 incident gets a short written record, even for a
single-maintainer project, appended to `docs/INCIDENT_LOG.md` (created at
the point of the first real incident, not scaffolded empty). Template:

```
## INCIDENT-<sequential number>: <one line summary>

Date:
Severity: (Sev 1-4, per section 2)
Detected by: (which test, which manual run, or which observation)
Impact: (what was actually affected: data, output correctness, time lost)
Root cause:
Fix: (commit hash or PR link)
Prevention: (what test or check now exists, or is planned, so this
             specific failure mode cannot recur silently)
```

The "prevention" field is mandatory and is not satisfied by "will be more
careful"; it must name a concrete test, check, or process change, mapped
back into the QA/Test Plan or this runbook as an update to the relevant
section, keeping the documentation set a living record rather than a
snapshot that drifts from reality after the first real incident.

## 7. Support channel

Phase 1: none beyond the project owner's own use. If this project is
ever made public, this section must be updated with an actual issue
tracker link and response expectations before that happens, consistent
with the honesty principle in section 4.
