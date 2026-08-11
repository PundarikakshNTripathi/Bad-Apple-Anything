# Rule: git workflow

Full rationale lives in `docs/adr/ADR-0006-git-branching-and-release-strategy.md`.
This file is the operational checklist to follow mechanically during a
phase; the ADR is the reasoning, this is the procedure.

## Branch structure

- `main`: always releasable, protected, only receives merges from
  `develop`.
- `develop`: integration branch, protected, only receives merges from
  `phase/*` branches.
- `phase/<NN>-<kebab-slug>`: one per engineering phase, `NN` is the
  two-digit phase number from `docs/03_SDD.md` section 8, `kebab-slug` is
  a short descriptive name. Example: `phase/03-vectorization-ir`.

## Procedure at the start of a phase

1. Confirm the local `develop` branch is up to date with its remote.
2. Create `phase/<NN>-<slug>` from `develop`.
3. Do not begin writing implementation code before this branch exists;
   commits belong on the phase branch, not on `develop` directly.

## Procedure during a phase

- Commit incrementally as logically complete units of work are finished,
  not as one giant commit at the end. A commit that mixes an unrelated
  refactor with a new feature should be split.
- Every commit message follows Conventional Commits:
  `<type>(<scope>): <summary>`, types restricted to `feat`, `fix`, `docs`,
  `test`, `perf`, `refactor`, `build`, `ci`, `chore`. Scope is the crate
  or package touched: `render`, `ir`, `ingest`, `encode`, `pipeline`,
  `cli`, `docs`, `harness`. Use `chore(deps):` specifically for
  dependency updates.
- The summary line is imperative mood, lowercase after the colon, no
  trailing period, under 72 characters. Body text, when needed, is
  separated by a blank line and wraps at roughly 72 characters, written
  per the style rule in `00-anti-slop-style.md`.
- Never commit anything under `assets/` or `out/`. If `git status` shows
  either as staged, stop and investigate before committing; do not commit
  first and clean up after.

## Procedure at the end of a phase

1. Confirm the test-gating rule (`02-test-gating.md`) is satisfied: full
   test suite green, locally.
2. Confirm the documentation-update rule (`03-documentation-update.md`)
   is satisfied and its changes are included in this phase's commits.
3. Confirm the benchmark-recording rule (`04-benchmark-recording.md`) has
   been run and `README.md` reflects current numbers, if this phase
   touched any benchmarked code path.
4. Push the phase branch and open a pull request into `develop`. The pull
   request description states: what this phase implemented, which PRD
   functional requirements and SDD phase it corresponds to, which tests
   were added, and the current benchmark numbers if applicable.
5. After CI passes on the pull request, merge into `develop` using a
   regular merge commit, not squash, so the incremental commit history
   is preserved for later debugging.
6. Tag the resulting `develop` commit `v0.<NN>.0` locally
   (informational, not pushed as a GitHub Release) where `NN` matches the
   phase number.
7. Delete the local phase branch after a successful merge. Do not delete
   the remote branch until confirming the merge is present on `develop`.

## Procedure at a release boundary (end of phase 6, and subsequent PRD release phases)

1. Confirm `develop` is green (CI passing) and every phase in the release
   has completed the per-phase procedure above.
2. Open a pull request from `develop` into `main`.
3. After CI passes and the pull request is merged, tag the `main` commit
   with the release version per ADR-0006 (`v1.0.0` for the first
   deliverable, subsequent releases follow semantic versioning based on
   whether the change includes a breaking IR or CLI change).

## What this rule does not authorize

This rule does not authorize committing directly to `main` or `develop`
under any circumstance, including for a "trivial" documentation fix.
Every change, without exception, goes through a phase branch and a pull
request.
