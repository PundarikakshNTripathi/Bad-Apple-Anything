"""
e2e_benchmark.py -- runs the full BAA pipeline against a synthetic
fixture and records wall-clock time and peak resident memory to a JSON
file consumed by benchmark_update.py.

This script deliberately never accepts a path under assets/ as its
fixture argument. Per docs/adr/ADR-0007-test-fixture-policy-no-copyrighted-media-in-vcs.md,
automated benchmarking, like automated testing, runs only against
synthetic, code-generated fixtures. The manual QA checklist in
docs/06_QA_TEST_PLAN.md section 7 is where timing against the real local
asset is observed and recorded, by the project owner, outside of this
script and outside of CI.

Usage:
    python harness/e2e_benchmark.py --fixture out/synthetic_fixture.mp4 --out out/bench_e2e.json --baa-bin target/release/baa
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


ASSETS_DIR_MARKER = "assets" + "/"  # constructed to avoid a literal path match false-flagging this file itself


def assert_not_under_assets(fixture_path: Path) -> None:
    resolved = str(fixture_path.resolve())
    if f"/{ASSETS_DIR_MARKER}" in resolved or resolved.startswith(ASSETS_DIR_MARKER):
        print(
            "error: e2e_benchmark.py refuses to run against a fixture path "
            "under assets/. Automated benchmarks use synthetic fixtures only. "
            "See docs/adr/ADR-0007-test-fixture-policy-no-copyrighted-media-in-vcs.md.",
            file=sys.stderr,
        )
        sys.exit(1)


def run_pipeline_and_measure(baa_bin: Path, fixture: Path, out_dir: Path) -> dict:
    """Runs the pipeline as a subprocess and samples peak RSS via a
    polling thread, since the simplest portable way to get a child
    process's peak memory without platform-specific resource module
    differences (Linux's getrusage semantics for children versus macOS's)
    is to sample /proc or psutil while it runs, not to trust a single
    post-hoc read."""
    import threading

    try:
        import psutil
    except ImportError:
        print(
            "error: psutil is required for e2e_benchmark.py memory sampling. "
            "Install it in the baa_ingest environment.",
            file=sys.stderr,
        )
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(baa_bin), "run", "--input", str(fixture), "--out", str(out_dir)]

    peak_rss_bytes = 0
    stop_flag = threading.Event()

    start = time.monotonic()
    proc = subprocess.Popen(cmd)

    def sample_memory():
        nonlocal peak_rss_bytes
        try:
            ps_proc = psutil.Process(proc.pid)
        except psutil.NoSuchProcess:
            return
        while not stop_flag.is_set():
            try:
                children = ps_proc.children(recursive=True)
                total = ps_proc.memory_info().rss
                for c in children:
                    total += c.memory_info().rss
                peak_rss_bytes = max(peak_rss_bytes, total)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            time.sleep(0.1)

    sampler = threading.Thread(target=sample_memory, daemon=True)
    sampler.start()
    return_code = proc.wait()
    stop_flag.set()
    sampler.join(timeout=1.0)
    elapsed = time.monotonic() - start

    if return_code != 0:
        print(f"error: pipeline exited with code {return_code}", file=sys.stderr)
        sys.exit(return_code)

    return {
        "wall_clock_seconds": round(elapsed, 3),
        "peak_memory_mb": round(peak_rss_bytes / (1024 * 1024), 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--baa-bin", default=Path("target/release/baa"), type=Path)
    parser.add_argument("--pipeline-out-dir", default=Path("out/e2e_bench_run"), type=Path)
    args = parser.parse_args()

    assert_not_under_assets(args.fixture)

    if not args.baa_bin.exists():
        print(
            f"error: baa binary not found at {args.baa_bin}. "
            "Build with 'cargo build --release' first.",
            file=sys.stderr,
        )
        return 1

    results = run_pipeline_and_measure(args.baa_bin, args.fixture, args.pipeline_out_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}: {results}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
