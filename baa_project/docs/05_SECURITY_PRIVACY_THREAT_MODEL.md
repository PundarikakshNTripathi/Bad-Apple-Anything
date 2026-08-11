# Security, Privacy, and Threat Model

Project codename: Bad Apple Anything
Status: Draft v1.0
Last updated: 2026-08-10
Depends on: 01_PRD.md, 02_TRD.md, docs/adr/*

## 1. Scope and system context

Phase 1 of this system is a local, single-user, offline command-line
pipeline. It reads a video file from the local filesystem, invokes local
subprocesses (`ffmpeg`, the Python ingestion package), writes output to
the local filesystem, and makes no network calls. Later phases (natural
language authoring, reference-image style transfer) introduce an external
LLM/vision API dependency; the threat model for those phases is scoped
separately in section 8 and is explicitly not part of the phase 1 attack
surface.

Assets in scope: the user's source media files, the generated IR (BSF)
files, the rendered output, the codebase itself, and the CI/CD pipeline
that builds and tests it.

Out of scope for this document: physical security of the user's
workstation, security of the operating system itself, and security of
third-party binaries (`ffmpeg`, the Rust toolchain, PyPI/crates.io
package infrastructure) beyond the supply-chain mitigations described in
section 5.

## 2. Content rights, briefly, and why this document does not dwell on it

The project owner has stated an intent to use their own locally supplied
copyrighted source video for personal, non-distributed, transformative
use, which is a reasonable position: transformative use, and non-
commercial personal use, are factors that weigh in favor of a fair use
finding under United States law, and this style of derivative silhouette
reinterpretation has ample precedent as fan work. Fair use is nonetheless
a fact-specific, case-by-case legal doctrine decided by courts, not a
blanket permission, and the analysis would be materially different if the
output were later distributed, monetized, or used in a way that competes
with or substitutes for the original work. This document is not legal
advice. The system-level consequence of this, which is where this
document's actual responsibility lies, is ADR-0007: the copyrighted asset
and any output derived from it never enters version control or any
shared/public system this project controls, which removes the question
of the repository's own copyright exposure regardless of how the personal
fair-use analysis eventually resolves.

## 3. Threat model method

STRIDE categories applied per component. Each identified threat has a
likelihood/impact judgment and a stated mitigation, and is cross-
referenced to the TRD requirement or QA test that enforces the
mitigation where one exists, so this document does not describe controls
that are aspirational rather than actually built and tested.

## 4. Threats by component

### 4.1 CLI argument and config parsing (`baa-cli`)

- Spoofing: not applicable, no authentication boundary exists in a local
  single-user CLI.
- Tampering: a maliciously crafted `baa.toml` config file could attempt
  to redirect output outside the intended directory. Mitigated by
  TR-SEC-2 (output path containment check, enforced regardless of what
  the config claims) and tested by `test_output_path_containment`.
- Repudiation: not applicable at this scope; `RunSummary` (SDD section 4)
  provides an audit trail of what a given invocation did, which is useful
  for debugging, not for adjudicating disputes between parties, since
  there is only one party.
- Information disclosure: log files could capture full local file paths,
  which is expected and acceptable for a local developer tool; this
  becomes relevant again in section 8 if logs are ever transmitted
  anywhere.
- Denial of service: a config file specifying an extreme resolution or
  frame count could cause excessive memory allocation before any actual
  processing occurs. Mitigated by TR-SEC-3 (input limits enforced before
  buffer allocation) and eager config validation (SDD section 7).
- Elevation of privilege: not applicable, the CLI runs with the invoking
  user's own privileges and requests none beyond that.

### 4.2 Ingestion stage, video/audio decode (`baa_ingest`, `ffmpeg` subprocess)

- Tampering: a malformed or adversarially crafted video file could
  attempt to exploit a parser vulnerability in `ffmpeg` or `opencv`'s
  decode path. This is the single highest-impact residual risk in the
  system, because it involves parsing complex binary formats from a file
  that, while supplied by the user themselves in the intended use case,
  is still an untrusted-format input from the parser's perspective.
  Mitigation: keep `ffmpeg` and `opencv-python-headless` on current
  patched versions (dependency update policy, section 5), run ingestion
  as the invoking user's own unprivileged account (no elevation, no
  reason to run as root and the CLI does not request it), and treat any
  ffmpeg/opencv non-zero exit or crash as a hard pipeline failure with no
  attempt to recover partial state, rather than continuing to process
  potentially corrupted decoder output.
- Denial of service: an oversized input file or one with an extreme
  declared resolution/frame count could exhaust memory or disk.
  Mitigated by TR-SEC-3, enforced in `baa_ingest` before any per-frame
  buffer is allocated, and tested against fixtures that deliberately
  declare out-of-bound dimensions.
- Information disclosure: none beyond what is already on the local
  filesystem; phase 1 makes no network calls (TR-SEC-4), so there is no
  channel for this stage to leak file contents anywhere.

### 4.3 Subprocess invocation boundary (`ffmpeg`, Python ingestion process)

- Tampering / command injection: mitigated structurally by TR-SEC-1,
  explicit argument vectors only, never shell string interpolation, on
  both the Rust and Python sides (ADR-0005). This is verified by a test
  that constructs a source file path containing shell metacharacters
  (spaces, semicolons, backticks) and asserts the pipeline still
  processes it correctly rather than the metacharacters being interpreted
  by a shell.
- Elevation of privilege: the subprocess inherits the invoking user's
  privileges only; no `sudo`, no setuid invocation, ever.

### 4.4 Filesystem writes (`out/` directory)

- Tampering: path traversal via a crafted output path or filename derived
  from input data. Mitigated by TR-SEC-2, tested by
  `test_output_path_containment`, which specifically includes `../`
  sequences and absolute-path overrides in its test cases.
- Tampering: the pipeline must never write into `assets/`, since that
  would risk corrupting the user's original source file. Enforced by the
  same path containment check plus a stage-level invariant that the
  ingest stage opens `assets/` paths read-only.
- Denial of service: unbounded output growth (for example, from a
  malformed IR file causing an infinite frame loop on the render side).
  Mitigated by the render stage enforcing the frame count declared in the
  BSF header as a hard upper bound (ADR-0002's header validation) rather
  than reading frames until end-of-stream with no ceiling.

### 4.5 Build and CI/CD pipeline

- Supply chain / tampering: a compromised or maliciously updated
  dependency (Rust crate or Python package) could introduce arbitrary
  code execution during build or test. Mitigated by dependency pinning
  (`Cargo.lock`, `requirements.lock`, both committed, never
  auto-updated without review), automated vulnerability scanning
  (`cargo audit` and `pip-audit` as required CI jobs, section 5), and
  restricting CI to run only on pull requests targeting `develop` or
  `main` with no execution of untrusted fork PR code against secrets
  (phase 1 has no secrets to protect, this becomes directly relevant
  again in section 8).
- Denial of service: a runaway benchmark or test could consume CI minutes
  indefinitely. Mitigated by a hard timeout on every CI job.

## 5. Supply chain and dependency management

- Rust dependencies are pinned via `Cargo.lock`, committed to version
  control. `cargo audit` runs in CI on every pull request and on a weekly
  scheduled job against `main`, failing the build on any advisory of
  medium severity or higher with no existing suppression.
- Python dependencies are pinned via `requirements.lock` (generated with
  hashes), committed to version control. `pip-audit` runs under the same
  policy as `cargo audit`.
- Dependency updates are their own pull request (`chore(deps): ...`
  commit type per ADR-0006), reviewed and merged like any other change,
  never bundled silently into an unrelated feature commit.
- No dependency is fetched at runtime; everything required is resolved
  and locked at build time. This is a direct consequence of, and
  reinforces, TR-SEC-4 (no runtime network calls in phase 1).

## 6. Privacy

Phase 1 processes only local files and produces only local files. No
telemetry, no analytics, no crash reporting is implemented or planned for
phase 1; if telemetry is ever proposed for a later phase, it must be
opt-in, clearly disclosed in the README, and must not transmit any
portion of the user's actual media content, only aggregate operational
metrics (for example, anonymized timing data), consistent with the
personal, offline-first posture established here.

## 7. Incident classification

See the Support & Incident Runbook for the operational procedure. This
document defines the severity taxonomy the runbook uses:

- Sev 1 (critical): data loss (the pipeline overwrites or corrupts a
  user's source asset), or a security defect allowing code execution via
  a crafted input file beyond what the underlying `ffmpeg`/`opencv`
  parsers themselves already carry as inherent risk (for example, a
  defect in this project's own code that bypasses TR-SEC-2 or TR-SEC-3).
- Sev 2 (high): a pipeline run silently produces incorrect output
  (desynced audio, corrupted frames) without a non-zero exit code or
  error surfaced, since silent incorrectness is worse than a loud
  failure.
- Sev 3 (moderate): a pipeline run fails loudly (non-zero exit, clear
  error) on a legitimate input that should be supported.
- Sev 4 (low): performance regression below the CI threshold's failure
  point, cosmetic rendering issues, documentation gaps.

## 8. Threat model addendum for later phases (natural language and reference-image authoring)

Recorded here now, ahead of implementation, so the phase 2/3 work items
inherit these requirements rather than discovering them after the fact.

- Any request sent to an external LLM/vision API must contain only the
  user's typed natural-language description or, if reference images are
  explicitly opted into for that feature, the reference image data
  itself. It must never include the source video content, the extracted
  audio, or any content derived from the copyrighted source asset,
  keeping the network-facing surface strictly limited to content the user
  authored or explicitly chose to share for that specific feature.
- API credentials for that external service are supplied via environment
  variable or a local `.env` file that is git-ignored (see the Vibe
  Coding Guide's setup section for the exact mechanism), never
  hardcoded, never committed, and never logged, including in the
  structured JSON logs (a log redaction rule for any field named or
  containing `key`, `token`, or `secret`, case-insensitive, is a required
  test case at the point this phase is implemented).
- This addition to the network attack surface must be re-reviewed against
  section 4's STRIDE analysis before that phase is merged to `develop`,
  not assumed to be adequately covered by this addendum alone.
