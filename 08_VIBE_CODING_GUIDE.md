# Vibe Coding Guide: building Bad Apple Anything with Antigravity CLI

Status: Draft v1.0
Last updated: 2026-08-10
Depends on: every other document in this set, and every file under `harness/`

## 1. What this guide is

This is the operational guide for actually building the system described
in the PRD, TRD, SDD, and ADRs, using Antigravity CLI (`agy`) in a
sequential, single-agent-session-per-phase workflow, not parallel
subagents. It assumes you have already read, or are willing to have the
agent read, every document listed in `AGENTS.md`'s required reading
section. It does not repeat this project's technical decisions; it
tells you how to drive the agent that will implement them, phase by
phase, with tests gating every step and documentation and benchmarks
updated automatically along the way.

## 2. One-time setup: what you do, what is scripted, what the agent does

The table below is the honest breakdown. Some things are structurally
impossible for an agent to do on your behalf (anything requiring
interactive OAuth in a browser, or a credential only you should ever
hold). Some things the agent can fully automate once you have granted it
the necessary local permissions. Everything in between is scripted by the
agent as code you review and run, or approve when prompted, with your
credentials supplied at that point, never typed into a prompt or a
committed file.

| Setup item | Who does it | Detail |
|---|---|---|
| Install Antigravity CLI (`agy`) | You, manually | Download and sign in with your Google account. This is an interactive OAuth flow; no agent can do this for you, since the agent does not exist yet until this step is complete. |
| Antigravity CLI initial config (`/config`, permissions, keybindings) | You, manually, once | Run `/config` inside `agy` after first launch to set tool-approval behavior. Recommendation for this project: require explicit approval for destructive filesystem operations and for any `git push`, and allow automatic approval for read-only operations (running tests, reading files), so phase-gating tests can run without you approving every single command, while destructive actions still pause for your review. |
| Install Rust toolchain (`rustup`, stable) | Agent, scripted, you approve | The agent can run the standard `rustup` install script as part of phase 01's bootstrap session if it detects the toolchain is missing, but this modifies your system PATH and installs a compiler toolchain, so treat the tool-approval prompt for this specific command as one to actually read, not rubber-stamp. |
| Install Python 3.11+ | Agent, scripted, you approve | Same category as Rust: the agent can invoke your OS package manager, but a system-level package install is worth reviewing at the approval prompt rather than blanket-approving. |
| Install `ffmpeg` >= 6.0 | Agent, scripted, you approve | Same category. On macOS this is typically `brew install ffmpeg`; on Ubuntu, `apt install ffmpeg`; the agent should detect your platform and propose the right command rather than you having to know it. |
| GPU driver setup (Vulkan/Metal/DX12) | You, manually | This is OS and hardware-vendor specific driver installation, entirely outside anything a coding agent can or should manage. If you skip this, the software rasterizer fallback (`docs/adr/ADR-0003-rendering-backend-wgpu.md`) handles rendering correctly, just slower; this is not a blocking requirement to start development. |
| Create the GitHub repository | You authenticate, agent executes | Authenticate `gh` (the GitHub CLI) yourself once (`gh auth login`), which is an interactive credential flow you must complete. After that, the agent can run `gh repo create` and all subsequent `git push` / pull request operations using your authenticated session, without ever seeing or needing your actual GitHub token directly. |
| Configure branch protection on `main` and `develop` | You authenticate, agent executes | Same category as repository creation: once `gh` is authenticated as you, the agent can run the `gh api` calls to set branch protection rules matching `docs/adr/ADR-0006-git-branching-and-release-strategy.md` (no direct pushes, require status checks). Review the exact rules it proposes before it applies them, since these are access-control settings. |
| Place the project documents and harness files in the repository | You, once, trivially | Copy this entire document set into `docs/` and the entire `harness/` directory (including `.agents/rules/` and `harness/phase_prompts/`) into the repository root before starting phase 01. The phase 01 prompt explicitly checks for these and stops if they are missing, so this has to happen first. |
| Place your source video | You, manually | Copy your source video to `assets/source.mp4` yourself. Never ask the agent to fetch it from anywhere; it should only ever come from your local filesystem, consistent with `docs/05_SECURITY_PRIVACY_THREAT_MODEL.md` section 2 and 6. |
| GitHub Actions CI enabled on the repository | Agent, once `gh` is authenticated | The workflow file itself (`.github/workflows/ci.yml`) is written by the agent in phase 01; enabling Actions on a repository is typically on by default for a repository you own, but if your GitHub organization has it disabled by policy, that is an org-level setting only you (or your org admin) can change. |
| Future LLM/vision API credentials (phase 2/3 authoring modes, not part of the 6 phases in this guide) | You supply the credential, agent wires the plumbing | When that work begins, the agent will scaffold `.env.example` (committed, no real values) and the loading code that reads `.env` (git-ignored, never committed, per `docs/05_SECURITY_PRIVACY_THREAT_MODEL.md` section 8). You create the actual `.env` file locally with your real API key. The agent never sees, logs, or commits the key itself; the log-redaction requirement in that section's threat model addendum is a test case, not just a promise. |

## 3. Repository layout before you start phase 01

```
your-repo/
  docs/                      <- this entire document set
  harness/                   <- entire harness directory as provided
    AGENTS.md                <- copy or move this to the repo ROOT, not left inside harness/
    .agents/
      rules/
    phase_prompts/
    benchmark_update.py
    e2e_benchmark.py
    README_TEMPLATE.md
  assets/                    <- create this empty directory, put your source video in it
```

Important: `AGENTS.md` must live at the repository root for Antigravity
CLI to read it automatically at session start, per Antigravity's own
discovery convention. Move it there from `harness/AGENTS.md` (or copy it
and delete the harness copy) before your first `agy` session. Likewise,
`.agents/rules/` must live at the repository root (`your-repo/.agents/rules/`),
not nested under `harness/`. Everything else under `harness/` (the phase
prompt files, the benchmark scripts, the README template) can stay under
`harness/` permanently; the phase prompts and rule files reference
`harness/benchmark_update.py` and `harness/e2e_benchmark.py` at that path
specifically.

## 4. Why sequential, single-agent, not parallel subagents

Antigravity's newer versions support dynamic subagents that the root
agent can spawn on the fly to parallelize subtasks. This project
deliberately does not use that mode. Two reasons. First, the phases in
`docs/03_SDD.md` section 8 are intentionally sequential and dependent:
phase 3's IR format depends on phase 2's matting output shape being
settled, phase 4's renderer depends on phase 3's IR being real and
tested, and so on; parallelizing them would mean building against a
moving, unfinished contract. Second, the test-gating discipline in
`.agents/rules/02-test-gating.md` depends on one coherent agent session
being able to see the full state of what it just built and iterate on
failures with full context; splitting that across isolated-context
subagents makes the "keep iterating until every test passes" instruction
much harder to actually enforce, since no single subagent has visibility
into the whole picture.

In practice, this means: do not type `/goal` with a broad multi-part
instruction that would trigger subagent decomposition. Instead, open a
fresh `agy` session per phase and paste that phase's prompt file
(`harness/phase_prompts/phase_0N_*.md`) directly as your message. Let the
root agent work through it as a single continuous session. If the agent
itself proposes spawning a subagent for some part of the work, decline
and ask it to continue in the current session instead; this is stated
explicitly in `AGENTS.md`'s "Workflow mode" section so the agent should
not suggest it in the first place, but it is worth knowing how to
redirect if it does.

## 5. Running a phase

1. Confirm your local `develop` branch is current
   (`git checkout develop && git pull`).
2. Open a fresh `agy` session in the repository root.
3. Paste the full contents of the relevant
   `harness/phase_prompts/phase_0N_*.md` file as your first message. Do
   not summarize or abbreviate it; the prompts are written to be pasted
   verbatim, including their instruction to reread `AGENTS.md` and the
   relevant docs first, which matters because a fresh session has no
   memory of a previous one.
4. Let the agent work. It will read the required documents, create the
   phase branch, implement the phase's scope, write and run tests,
   iterate until they pass (per `.agents/rules/02-test-gating.md`), run
   benchmarks and update `README.md` and `docs/BENCHMARK_HISTORY.md` if
   the phase touches a benchmarked path, update `CHANGELOG.md` and the
   traceability matrix, and open a pull request into `develop`.
5. Review the pull request yourself: read the diff, confirm the stated
   test results in the PR description actually match what CI reports,
   confirm the benchmark numbers look plausible, and only then merge.
6. Delete the local phase branch, pull `develop`, and move to the next
   phase's prompt in a fresh session.

Do not chain phases in one long session. A fresh session per phase is
deliberate: it forces the agent to re-ground itself in the current,
merged state of the documents and code rather than carrying forward
possibly-stale assumptions from earlier in a long conversation, and it
keeps each phase's pull request reviewable as a coherent, bounded unit
matching `docs/adr/ADR-0006-git-branching-and-release-strategy.md`'s
reasoning.

## 6. What "stop only after tests pass" looks like in an actual session

You should expect, and not be alarmed by, an agent session that looks
like: implement a module, run its tests, see a failure, read the actual
failure output (not just the pass/fail count), form a specific hypothesis,
make one targeted change, rerun, repeat, sometimes several times, before
moving to the next module. This mirrors exactly how the earlier
prototyping work for this project found and fixed its own bugs: a
first render had legs cut off the bottom of the frame because of a wrong
scale constant, found by actually looking at a rendered frame rather than
trusting a clean exit code; a second bug was a coordinate-frame confusion
between hip position and ground line, found the same way; a matting bug
where the extracted mask came back completely blank was traced to a
specific, well-understood failure mode in adaptive background subtraction
by directly inspecting the raw intermediate mask array, not by guessing
from the symptom. The harness's test-gating rule is asking the agent to
work this way as standard practice, not as an exceptional debugging
effort reserved for hard problems.

If a session ends with the agent reporting a phase complete, but you
notice it did not explicitly name which test commands it ran and their
pass counts (the exact reporting format required by
`.agents/rules/02-test-gating.md`), treat that as a signal to ask it to
actually run them before you trust the report, not as a formality it
skipped harmlessly.

## 7. The benchmark harness in practice

You do not need to remember the exact commands. Each phase prompt that
touches a benchmarked code path already instructs the agent to run
`harness/.agents/rules/04-benchmark-recording.md`'s procedure, which ends
in `python harness/benchmark_update.py`. What you should know as the
person reviewing the resulting pull request: `README.md`'s benchmarks
section, between the `<!-- BENCHMARKS:START -->` and
`<!-- BENCHMARKS:END -->` markers, is entirely generated; never hand-edit
it, since the next automated run overwrites it by design. If you want to
add commentary near the benchmarks, add it outside those markers, above
or below the section. `docs/BENCHMARK_HISTORY.md` is append-only and is
where you look for trends across phases, not just the latest snapshot.

The regex-based marker replacement in `benchmark_update.py` was tested
directly during this guide's own preparation, including its failure
modes: it refuses to write, and exits with a clear error, if it finds
zero or more than one occurrence of the marker pair in `README.md`,
rather than guessing where the benchmarks section belongs. If a phase
prompt session reports this error, the fix is almost always that
`README.md`'s markers were accidentally edited or duplicated by hand at
some point; restore them from `harness/README_TEMPLATE.md`'s exact marker
text before rerunning.

## 8. The first deliverable specifically

Phase 1 of the PRD's release plan (SDD engineering phases 1 through 6,
this guide's six phase prompts) is: your real source video, placed at
`assets/source.mp4`, processed end to end into a procedurally rendered,
audio-synced silhouette reconstruction at `out/final.mp4`. Nothing in the
six phase prompts asks the agent to fetch, embed, or commit that video or
any part of it; every automated test in every phase runs against a
synthetic, code-generated fixture, per
`docs/adr/ADR-0007-test-fixture-policy-no-copyrighted-media-in-vcs.md`.
The only point where your real asset is actually used is the manual QA
checklist at the end of phase 6, which you run yourself, locally, outside
of both CI and the agent's own automated scope, exactly as
`docs/06_QA_TEST_PLAN.md` section 7 and the phase 06 prompt describe.

## 9. If something in the documents turns out to be wrong once you start building

It will happen; a design document written before any code exists is a
prediction, not a guarantee. `AGENTS.md` already instructs the agent on
this: state the discrepancy plainly, and either make a small precise
correction to the specific wrong sentence, or, for anything decision-
level, write a new ADR that explicitly supersedes the old one, following
the existing ADRs' format. Do not let a session quietly work around a
wrong assumption in the docs without flagging it; the whole point of
building against a written specification is that the specification stays
trustworthy, which only holds if discrepancies are surfaced and fixed at
the source rather than patched around in code while the document quietly
goes stale.
