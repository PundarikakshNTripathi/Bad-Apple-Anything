# Rule: documentation update at the end of each phase

Documentation drift, where the docs describe an earlier state of the
system than the code, is treated as a defect in this project, not an
acceptable side effect of moving fast. This rule is what prevents it.

## What to update, every phase, without exception

- `README.md` benchmarks section, via the automated harness described in
  `04-benchmark-recording.md`, if this phase touched any benchmarked code
  path.
- `CHANGELOG.md`: add an entry under an "Unreleased" heading (or the
  current release heading if one is open) describing what this phase
  added, using the same plain, specific style required by
  `00-anti-slop-style.md`. Do not write "various improvements."
- `docs/03_SDD.md` section 9 (requirements traceability matrix): if this
  phase implements or changes the test coverage for a functional
  requirement, update the corresponding row.

## What to update, only when it actually changed

- Any PRD, TRD, SDD, or ADR content that this phase's work has made
  inaccurate. This should be rare and deliberate: these documents are the
  specification the phase was built against, not documents that passively
  follow whatever the code happens to do. If implementation reveals that
  a documented decision was wrong or incomplete, the correct response is
  either a small precise edit to the specific inaccurate sentence, or, for
  anything decision-level, a new ADR that explicitly supersedes the old
  one (see `AGENTS.md`'s instruction on this), not a silent rewrite of the
  original document's reasoning.
- `docs/07_SUPPORT_INCIDENT_RUNBOOK.md`, if this phase's work surfaced a
  new failure mode worth documenting for future diagnosis, following the
  format already established in that document's section 3.

## What not to do

Do not touch a document's content just because it is technically
possible to improve its wording while in the area. Documentation changes
in a phase's pull request should be scoped to what that phase's actual
work requires, reviewable in the same way the code changes are, not a
drive-by rewrite that makes the diff harder to review.

## Verification before considering this rule satisfied

Reread the specific sections of `README.md`, `CHANGELOG.md`, and
`docs/03_SDD.md` section 9 that this phase should have touched, and
confirm the content actually reflects the code as committed at the end of
this phase, not as it was planned to be at the start. This is a concrete
read-back check, not an assumption that the update happened correctly
because the instruction to update was followed.
