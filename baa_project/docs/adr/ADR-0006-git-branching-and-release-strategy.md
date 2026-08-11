# ADR-0006: Git branching model, commit convention, and release strategy

Status: Accepted
Date: 2026-08-10
Deciders: project owner

## Context

The project is developed by a single owner working with an AI coding
agent in a sequential, one-phase-at-a-time workflow (see the Vibe Coding
Guide). It still needs a branching discipline that keeps `main` always
in a releasable state, gives each engineering phase (SDD section 8) a
clean, reviewable unit of change, and produces a legible history without
relying on any tooling beyond standard git and GitHub.

Simpler alternatives were considered. Trunk-based development (committing
directly to `main`) was rejected because it removes the natural review
checkpoint between an agent finishing a phase and that phase's code
becoming part of the permanent history, and because a broken `main` would
block every subsequent phase prompt, which assumes a working base to
branch from. A single long-lived `develop` branch with no per-phase
branches was rejected because it would make it harder to isolate which
phase introduced a given change when reading history later, and would
make reverting a single bad phase without affecting others more
difficult.

## Decision

Three-tier branch structure:

- `main`: always releasable. Every commit on `main` corresponds to a
  tagged release. Protected: no direct pushes, only merges from
  `develop` at phase or milestone boundaries.
- `develop`: integration branch. Always expected to build and pass its
  full test suite, but not necessarily "released." Protected: no direct
  pushes, only merges from phase branches via pull request.
- `phase/<NN>-<kebab-slug>`: one branch per engineering phase (SDD
  section 8), cut from `develop`, merged back into `develop` via pull
  request once that phase's acceptance criteria (QA/Test Plan) are met.

Flow for one phase: branch `phase/NN-slug` from `develop`, commit
incrementally as work proceeds, open a pull request into `develop` when
the phase's tests pass locally, merge (squash or regular merge, regular
merge preferred to preserve the incremental commit history for later
debugging), then at a release boundary (end of an SDD phase group that
constitutes a PRD release phase, at minimum at the end of phase 6 for the
first deliverable) open a pull request from `develop` into `main` and tag
the resulting `main` commit.

Branch naming: `phase/<two-digit-number>-<kebab-case-slug>`, matching the
phase numbers in SDD section 8. Example: `phase/02-ingestion-matting`.

Commit convention: Conventional Commits.
`<type>(<scope>): <short summary>`, types limited to `feat`, `fix`,
`docs`, `test`, `perf`, `refactor`, `build`, `ci`, `chore`. Scope is the
crate or package name (`render`, `ir`, `ingest`, `encode`, `pipeline`,
`cli`, `docs`, `harness`). Example: `feat(render): add polygon
tessellation via lyon`. Body text explains what changed and why when the
summary line is not self-explanatory; it does not restate the diff.

Tagging: pre-release tags `v0.<phase>.0` on `develop` at the end of each
phase (informational, not published as a GitHub Release), and `v1.0.0` on
`main` at the first deliverable's completion (end of phase 6). Subsequent
PRD release phases (phase 2 onward) continue as `v1.x.0` minor releases
unless a breaking IR or CLI change occurs, in which case a major version
bump follows semantic versioning.

## Consequences

Positive: `main` is always safe to check out and run. History clearly
shows which phase introduced which change, which materially helps when a
later phase's tests fail because of an earlier phase's code, since the
phase branch boundary narrows the search space immediately. The
convention is standard enough that no custom tooling is required to
enforce or read it.

Negative: more branches and pull requests than a simpler workflow for a
single-developer project; accepted as a worthwhile tradeoff given the
project also needs a clean checkpoint structure for the agent-driven
phase prompts to hook into (each phase prompt in the Vibe Coding Guide
starts by creating its phase branch and ends by opening its pull
request).

## Revisit triggers

If a second human contributor joins the project, add branch protection
rules requiring at least one review before merge to `develop` and `main`
(currently self-merged by the project owner after CI passes, since there
is no second reviewer). No other change to this ADR is anticipated from
that trigger alone.
