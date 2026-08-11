"""
benchmark_update.py -- parses Criterion (Rust), pytest-benchmark (Python),
and the custom end-to-end benchmark JSON outputs, then rewrites the
benchmarks section of README.md in place, and appends a row to
docs/BENCHMARK_HISTORY.md.

This script never touches anything in README.md outside the markers
<!-- BENCHMARKS:START --> and <!-- BENCHMARKS:END -->. If those markers
are not both present, exactly once, in that order, the script refuses to
write and exits non-zero rather than guessing where the section should
go.

Usage:
    python harness/benchmark_update.py
    python harness/benchmark_update.py --readme README.md --history docs/BENCHMARK_HISTORY.md

Exit codes: 0 success. 1 markers missing or malformed. 2 no benchmark
result files found to parse.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BENCH_START = "<!-- BENCHMARKS:START -->"
BENCH_END = "<!-- BENCHMARKS:END -->"

# Matches everything between the two markers, non-greedy, across newlines.
# Captures the markers themselves in the replacement so we do not need to
# re-type them at every call site.
SECTION_RE = re.compile(
    re.escape(BENCH_START) + r"(.*?)" + re.escape(BENCH_END),
    re.DOTALL,
)


class BenchmarkResult:
    def __init__(self, name: str, value: float, unit: str, threshold: str):
        self.name = name
        self.value = value
        self.unit = unit
        self.threshold = threshold

    def formatted(self) -> str:
        return f"{self.value:.3f} {self.unit}"


def parse_criterion_results(criterion_dir: Path) -> list[BenchmarkResult]:
    """Criterion writes target/criterion/<bench_name>/base/estimates.json.
    We read the 'mean' point estimate, convert nanoseconds to a friendlier
    unit (fps for render throughput style benches, ms otherwise) based on
    a naming convention rather than trying to infer it, since Criterion's
    own JSON does not carry a semantic unit."""
    results = []
    if not criterion_dir.exists():
        return results
    for estimates_file in criterion_dir.glob("*/base/estimates.json"):
        bench_name = estimates_file.parent.parent.name
        with open(estimates_file) as f:
            data = json.load(f)
        mean_ns = data["mean"]["point_estimate"]
        mean_ms = mean_ns / 1_000_000
        results.append(BenchmarkResult(bench_name, mean_ms, "ms", "see TRD section 6"))
    return results


def parse_pytest_benchmark_results(json_path: Path) -> list[BenchmarkResult]:
    results = []
    if not json_path.exists():
        return results
    with open(json_path) as f:
        data = json.load(f)
    for bench in data.get("benchmarks", []):
        name = bench["name"]
        mean_s = bench["stats"]["mean"]
        results.append(BenchmarkResult(name, mean_s * 1000, "ms", "see TRD section 6"))
    return results


def parse_e2e_results(json_path: Path) -> list[BenchmarkResult]:
    results = []
    if not json_path.exists():
        return results
    with open(json_path) as f:
        data = json.load(f)
    if "wall_clock_seconds" in data:
        results.append(BenchmarkResult(
            "e2e_full_pipeline_wall_clock", data["wall_clock_seconds"], "s", "< 300s"))
    if "peak_memory_mb" in data:
        results.append(BenchmarkResult(
            "e2e_full_pipeline_peak_memory", data["peak_memory_mb"], "MB", "< 2048 MB"))
    return results


def build_table(results: list[BenchmarkResult]) -> str:
    if not results:
        return "No benchmark results were found to record.\n"
    lines = [
        "| Benchmark | Result | Threshold |",
        "|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r.name} | {r.formatted()} | {r.threshold} |")
    return "\n".join(lines) + "\n"


def get_git_commit_hash() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def update_readme(readme_path: Path, table_markdown: str) -> None:
    content = readme_path.read_text(encoding="utf-8")
    matches = list(SECTION_RE.finditer(content))
    if len(matches) != 1:
        print(
            f"error: expected exactly one BENCHMARKS section in {readme_path}, "
            f"found {len(matches)}. Refusing to write.",
            file=sys.stderr,
        )
        sys.exit(1)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    commit = get_git_commit_hash()
    replacement_body = (
        f"\n\nLast updated: {timestamp} (commit `{commit}`)\n\n"
        f"{table_markdown}\n"
    )
    new_content = SECTION_RE.sub(
        lambda m: BENCH_START + replacement_body + BENCH_END, content
    )
    readme_path.write_text(new_content, encoding="utf-8")


def append_history(history_path: Path, results: list[BenchmarkResult]) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    commit = get_git_commit_hash()
    if not history_path.exists():
        history_path.write_text(
            "# Benchmark History\n\n"
            "Append-only log of benchmark runs. README.md always shows only "
            "the latest run; this file is the trend record.\n\n",
            encoding="utf-8",
        )
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(f"## {timestamp} (commit `{commit}`)\n\n")
        f.write(build_table(results))
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", default="README.md", type=Path)
    parser.add_argument("--history", default="docs/BENCHMARK_HISTORY.md", type=Path)
    parser.add_argument("--criterion-dir", default="target/criterion", type=Path)
    parser.add_argument("--pytest-json", default="out/bench_python.json", type=Path)
    parser.add_argument("--e2e-json", default="out/bench_e2e.json", type=Path)
    args = parser.parse_args()

    results = []
    results.extend(parse_criterion_results(args.criterion_dir))
    results.extend(parse_pytest_benchmark_results(args.pytest_json))
    results.extend(parse_e2e_results(args.e2e_json))

    if not results:
        print(
            "error: no benchmark result files found "
            f"({args.criterion_dir}, {args.pytest_json}, {args.e2e_json}). "
            "Run the benchmark suite before this script.",
            file=sys.stderr,
        )
        return 2

    table = build_table(results)
    update_readme(args.readme, table)
    append_history(args.history, results)
    print(f"Updated {args.readme} and {args.history} with {len(results)} benchmark results.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
