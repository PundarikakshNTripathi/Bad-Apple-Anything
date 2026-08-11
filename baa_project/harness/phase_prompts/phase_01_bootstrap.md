# Phase 01: repository bootstrap

Paste this prompt into the Antigravity CLI (agy) root agent session, in
this repository's root directory, as the first message of a fresh
session. Do not run this alongside any other phase.

---

Before doing anything else, read `AGENTS.md` at the repository root in
full, then read every document it lists under "Required reading before
any work," in the order given: `docs/01_PRD.md`, `docs/02_TRD.md`,
`docs/03_SDD.md`, every file under `docs/adr/`,
`docs/05_SECURITY_PRIVACY_THREAT_MODEL.md`, `docs/06_QA_TEST_PLAN.md`,
`docs/07_SUPPORT_INCIDENT_RUNBOOK.md`, and every file under
`.agents/rules/`. These documents are the actual specification for this
project. Confirm you have read them before proceeding, and if any of
them are missing from this repository, stop and tell me before doing
anything else, since this phase assumes they are already present at the
paths listed.

This is phase 1 of 6 in the engineering phase breakdown defined in
`docs/03_SDD.md` section 8. Its scope is repository scaffolding only:
no functional ingestion, rendering, or encoding code yet. Follow
`.agents/rules/01-git-workflow.md` exactly: create branch
`phase/01-bootstrap` from `develop` before making any change. If `develop`
does not exist yet, create it from `main` first (or from the current
state of the repository if this is a brand new repository with no commits
yet, in which case create an initial commit on `main` containing only
this document set and the harness files first, then branch `develop` from
it, then branch `phase/01-bootstrap` from `develop`).

## Scope for this phase

1. Create the Cargo workspace at the repository root with the crate
   layout described in `docs/03_SDD.md` section 1 and section 3:
   `crates/baa-ir`, `crates/baa-render`, `crates/baa-encode`,
   `crates/baa-pipeline`, `crates/baa-cli`. Each crate gets a minimal
   `Cargo.toml` and a `src/lib.rs` (or `src/main.rs` for `baa-cli`)
   with a placeholder that compiles, plus a single placeholder unit test
   per crate that passes, so `cargo test --workspace` succeeds from the
   end of this phase onward. Do not implement real logic yet; that is
   later phases' scope.
2. Create the Python package skeleton at `python/baa_ingest/` per
   `docs/03_SDD.md` section 3.6: `pyproject.toml`, the module files listed
   there as empty modules with docstrings stating their eventual purpose
   and a `NotImplementedError` placeholder function where relevant, and a
   `tests/` directory with one placeholder test that passes.
3. Add `.gitignore` at the repository root. It must ignore `assets/` and
   `out/` in their entirety, `target/` (Rust build artifacts), Python
   build artifacts and virtual environments, and standard OS/editor
   cruft. Cross-check this against `docs/adr/ADR-0007-test-fixture-policy-no-copyrighted-media-in-vcs.md`
   before finishing this step; the ignore rules for `assets/` and `out/`
   are a hard requirement of that ADR, not a convenience default.
4. Add `.github/workflows/ci.yml`. At minimum for this phase: a job that
   runs `cargo build --workspace` and `cargo test --workspace`, and a
   separate job that installs the Python package and runs its test suite
   (`pytest python/baa_ingest`). Add `cargo audit` and `pip-audit` as
   required jobs per `docs/05_SECURITY_PRIVACY_THREAT_MODEL.md` section
   5, even though there are barely any dependencies yet; this establishes
   the pattern for every later phase rather than retrofitting it.
5. Add the repository hygiene check described in
   `docs/06_QA_TEST_PLAN.md` section 6 as its own CI job: a script that
   scans the current pull request's diff for committed video/audio file
   extensions above a small size threshold and fails the build if found.
   Write this as an actual script under `scripts/ci/`, not an inline
   shell one-liner in the workflow file, so it is independently testable.
6. Copy `README_TEMPLATE.md` (from wherever you were given the harness
   files, likely `harness/README_TEMPLATE.md` in this repository if it
   was placed there, otherwise ask me for it) to `README.md` at the
   repository root, adjusting only what is factually necessary at this
   stage (nothing is built yet, so the benchmarks section stays as the
   template's "not yet run" placeholder).
7. Create `CHANGELOG.md` with an "Unreleased" heading and one entry
   describing this bootstrap phase.
8. Confirm the harness files themselves (`AGENTS.md`, `.agents/rules/*`,
   `harness/benchmark_update.py`, `harness/e2e_benchmark.py`,
   `harness/README_TEMPLATE.md`, `harness/phase_prompts/*`) are present in
   the repository at the paths `AGENTS.md` references. If I have not
   already placed them, stop and ask me to, since later phases assume
   they exist.

## Test gating for this phase

Follow `.agents/rules/02-test-gating.md`. For this phase specifically,
the gate is: `cargo build --workspace` succeeds with no errors,
`cargo test --workspace` passes (the placeholder tests), `pytest
python/baa_ingest` passes (the placeholder test), the CI workflow file
is syntactically valid (validate with `act` if available locally, or by
careful manual review if not, and note in your summary which method you
used), and the hygiene check script correctly fails when pointed at a
deliberately constructed test case containing a fake committed video
file, and correctly passes when it is not present. Do not report this
phase complete until all of that is true, and state explicitly, by
command name, which commands you ran and their results, per the
reporting requirement in `.agents/rules/02-test-gating.md`.

## Documentation for this phase

Follow `.agents/rules/03-documentation-update.md`. There is no benchmark
data yet, so the benchmark-recording rule does not apply this phase.
Update `docs/03_SDD.md` section 9's traceability matrix only if this
phase's scaffolding changes any test name referenced there from what is
currently written (it should not, since this phase only adds
placeholders, but check).

## End of phase

Follow the "procedure at the end of a phase" section of
`.agents/rules/01-git-workflow.md`: push the branch, open a pull request
into `develop` with the description format specified there, and stop.
Do not proceed to phase 2 in this same session. I will review the pull
request and start a fresh session with the phase 2 prompt myself.
