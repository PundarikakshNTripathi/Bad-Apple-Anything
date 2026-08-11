# AGENTS.md

This file is read automatically by Antigravity CLI (agy) at the start of
every session in this repository. It is the persistent, project-wide
instruction set. Do not duplicate its content into individual phase
prompts; phase prompts reference it and add only what is specific to that
phase.

## Required reading before any work

Before writing or modifying any code in this repository, read, in this
order:

1. `docs/01_PRD.md`
2. `docs/02_TRD.md`
3. `docs/03_SDD.md`
4. `docs/adr/` (all files, they are short)
5. `docs/05_SECURITY_PRIVACY_THREAT_MODEL.md`
6. `docs/06_QA_TEST_PLAN.md`
7. `docs/07_SUPPORT_INCIDENT_RUNBOOK.md`
8. `.agents/rules/` (all files)

Treat these documents as the actual specification. If an instruction in a
phase prompt appears to conflict with these documents, stop and surface
the conflict instead of guessing which one takes precedence.

## Project identity

Codename: Bad Apple Anything. A pipeline that reconstructs a source video's
subject as a vector silhouette animation, synced to the video's own
extracted audio, and renders it procedurally rather than replaying
source pixels. Architecture: Rust core (`crates/`) plus a Python
ingestion package (`python/baa_ingest/`), communicating only through
the BAA Scene Format (BSF) defined in `docs/02_TRD.md` section 4.2 and
`docs/adr/ADR-0002-intermediate-representation-format.md`.

## Workflow mode

This project is driven sequentially, one phase at a time, by a single
root agent session. Do not spawn parallel subagents, do not use
multi-agent decomposition for phase work, and do not run more than one
phase concurrently. Complete the current phase, including all gating
steps in `.agents/rules/02-test-gating.md`, before starting the next one.
If a task is genuinely large enough that it seems to want parallel
decomposition, break it into smaller sequential steps within the current
phase instead of spawning subagents for it.

## Standing rules

All of the following are always in effect and are detailed in
`.agents/rules/`:

- `00-anti-slop-style.md`: writing and comment style for all code,
  commits, and documentation.
- `01-git-workflow.md`: branching, committing, and pull request
  conventions.
- `02-test-gating.md`: a phase is not complete until its full test suite
  passes; do not report completion otherwise.
- `03-documentation-update.md`: which documents to update at the end of
  a phase, and how.
- `04-benchmark-recording.md`: how to run and record benchmarks into
  `README.md` using the provided harness script.

## Non-negotiable technical constraints

- Never commit anything under `assets/` or `out/` (`docs/adr/ADR-0007-test-fixture-policy-no-copyrighted-media-in-vcs.md`).
- Never invoke `ffmpeg` or any subprocess via a shell string built from a
  path; always use an explicit argument list
  (`docs/adr/ADR-0005-process-boundary-ffmpeg-subprocess.md`).
- Never write outside the configured output directory; validate and
  contain output paths before any write
  (`docs/02_TRD.md` TR-SEC-2).
- Never add a network call to phase 1 code
  (`docs/02_TRD.md` TR-SEC-4).
- All automated tests run against synthetic, code-generated fixtures,
  never the real source asset in `assets/`
  (`docs/adr/ADR-0007-test-fixture-policy-no-copyrighted-media-in-vcs.md`).

## What to do if something in this repository is missing or unclear

State plainly what is missing or ambiguous and what you assumed in order
to proceed, before proceeding. Do not silently invent requirements that
are not in the documents listed above. If a genuine decision is required
that is not covered by an existing ADR, propose one in the same style as
the existing ADRs under `docs/adr/`, using the next sequential number,
and flag it clearly in the phase's summary for the project owner to
review, rather than deciding unilaterally and moving on.
