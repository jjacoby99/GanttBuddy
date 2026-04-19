"""
Benchmark Excel import performance for GanttBuddy.

Cold benchmark only:
- No Streamlit
- No caching
- Re-runs the actual loader functions repeatedly
- Separates:
    - analyze vs load
    - infer_predecessors on vs off

Usage examples:

    python scripts/benchmark_excel_import.py \
        --files tests/data/small.xlsx tests/data/large.xlsx \
        --repeats 7 \
        --warmups 1

    python scripts/benchmark_excel_import.py \
        --files tests/data/large.xlsx \
        --mode both \
        --infer both \
        --repeats 10 \
        --profile

"""

from __future__ import annotations

import argparse
import cProfile
import io
import json
import pstats
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Literal

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from logic.load_project import ExcelProjectLoader, ExcelParameters, DataColumn


@dataclass
class BenchmarkResult:
    file: str
    file_size_kb: float
    mode: Literal["analyze", "load"]
    infer_predecessors: bool
    repeats: int
    warmups: int
    runs_seconds: list[float]
    min_seconds: float
    median_seconds: float
    mean_seconds: float
    max_seconds: float


def default_excel_parameters(start_row: int = 8) -> ExcelParameters:
    return ExcelParameters(
        start_row=start_row,
        columns=[
            DataColumn(name="ACTIVITY", column=2),
            DataColumn(name="PLANNED DURATION (HOURS)", column=3),
            DataColumn(name="PLANNED START", column=4),
            DataColumn(name="PLANNED END", column=5),
            DataColumn(name="ACTUAL DURATION", column=7),
            DataColumn(name="ACTUAL START", column=8),
            DataColumn(name="ACTUAL END", column=9),
            DataColumn(name="NOTES", column=10),
            DataColumn(name="PREDECESSOR", column=11),
            DataColumn(name="UUID", column=12),
            DataColumn(name="PLANNED", column=13),
        ],
    )

def bench_function(
    fn: Callable[..., Any],
    *args: Any,
    repeats: int,
    warmups: int,
    **kwargs: Any,
) -> list[float]:
    """
    Run a function several times and return elapsed times in seconds.
    """
    for _ in range(warmups):
        fn(*args, **kwargs)

    runs: list[float] = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn(*args, **kwargs)
        runs.append(time.perf_counter() - t0)

    return runs


def summarize_runs(
    file_path: Path,
    mode: str,
    infer_predecessors: bool,
    runs: list[float],
    repeats: int,
    warmups: int,
) -> BenchmarkResult:
    return BenchmarkResult(
        file=str(file_path),
        file_size_kb=file_path.stat().st_size / 1024.0,
        mode=mode,
        infer_predecessors=infer_predecessors,
        repeats=repeats,
        warmups=warmups,
        runs_seconds=runs,
        min_seconds=min(runs),
        median_seconds=statistics.median(runs),
        mean_seconds=statistics.mean(runs),
        max_seconds=max(runs),
    )


def run_analyze(
    file_bytes: bytes,
    params: ExcelParameters,
    infer_predecessors: bool,
) -> Any:
    return ExcelProjectLoader.analyze_excel_project(
        file=file_bytes,
        params=params,
        infer_predecessors=infer_predecessors,
    )


def run_load(
    file_bytes: bytes,
    params: ExcelParameters,
    infer_predecessors: bool,
) -> Any:
    return ExcelProjectLoader.load_excel_project(
        file=file_bytes,
        params=params,
        infer_predecessors=infer_predecessors,
    )


def profile_once(
    fn: Callable[..., Any],
    *args: Any,
    sort_by: str = "cumtime",
    top_n: int = 40,
    **kwargs: Any,
) -> None:
    profiler = cProfile.Profile()
    profiler.enable()
    fn(*args, **kwargs)
    profiler.disable()

    stats_stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream).sort_stats(sort_by)
    stats.print_stats(top_n)
    print("\ncProfile output")
    print("-" * 80)
    print(stats_stream.getvalue())


def format_seconds(x: float) -> str:
    return f"{x:.3f}s"


def print_result_table(results: Iterable[BenchmarkResult]) -> None:
    results = list(results)
    if not results:
        return

    headers = [
        "File",
        "KB",
        "Mode",
        "Infer",
        "Min",
        "Median",
        "Mean",
        "Max",
    ]

    rows: list[list[str]] = []
    for r in results:
        rows.append(
            [
                Path(r.file).name,
                f"{r.file_size_kb:.1f}",
                r.mode,
                "on" if r.infer_predecessors else "off",
                format_seconds(r.min_seconds),
                format_seconds(r.median_seconds),
                format_seconds(r.mean_seconds),
                format_seconds(r.max_seconds),
            ]
        )

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(row: list[str]) -> str:
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    print("\nBenchmark summary")
    print("-" * 80)
    print(fmt_row(headers))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(fmt_row(row))


def save_results_json(results: list[BenchmarkResult], out_path: Path) -> None:
    payload = [asdict(r) for r in results]
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nSaved results to {out_path}")


def parse_mode(value: str) -> list[str]:
    value = value.lower().strip()
    if value == "analyze":
        return ["analyze"]
    if value == "load":
        return ["load"]
    if value == "both":
        return ["analyze", "load"]
    raise ValueError(f"Invalid mode: {value}")


def parse_infer(value: str) -> list[bool]:
    value = value.lower().strip()
    if value == "on":
        return [True]
    if value == "off":
        return [False]
    if value == "both":
        return [False, True]
    raise ValueError(f"Invalid infer option: {value}")


def validate_files(file_paths: list[str]) -> list[Path]:
    paths = [Path(p).resolve() for p in file_paths]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing files:\n" + "\n".join(missing))
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Excel import performance.")
    parser.add_argument(
        "--files",
        nargs="+",
        required=True,
        help="One or more Excel files to benchmark.",
    )
    parser.add_argument(
        "--mode",
        choices=["analyze", "load", "both"],
        default="both",
        help="Which workflow to benchmark.",
    )
    parser.add_argument(
        "--infer",
        choices=["on", "off", "both"],
        default="both",
        help="Whether to benchmark predecessor inference on, off, or both.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=7,
        help="Number of measured runs per case.",
    )
    parser.add_argument(
        "--warmups",
        type=int,
        default=1,
        help="Number of warmup runs before measured runs.",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Also run cProfile once for the first case only.",
    )
    parser.add_argument(
        "--profile-sort",
        default="cumtime",
        choices=["cumtime", "tottime", "ncalls"],
        help="Sort key for cProfile output.",
    )
    parser.add_argument(
        "--profile-top",
        type=int,
        default=40,
        help="Number of lines to print from cProfile.",
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default="",
        help="Optional path to save raw benchmark results as JSON.",
    )

    args = parser.parse_args()

    try:
        files = validate_files(args.files)
        params = default_excel_parameters()
    except Exception as exc:
        print(f"Setup error: {exc}", file=sys.stderr)
        return 1

    modes = parse_mode(args.mode)
    infer_values = parse_infer(args.infer)

    results: list[BenchmarkResult] = []
    did_profile = False

    for file_path in files:
        file_bytes = file_path.read_bytes()

        for mode in modes:
            for infer_predecessors in infer_values:
                if mode == "analyze":
                    fn = run_analyze
                elif mode == "load":
                    fn = run_load
                else:
                    raise ValueError(f"Unexpected mode: {mode}")

                print(
                    f"\nRunning: file={file_path.name}, mode={mode}, "
                    f"infer_predecessors={infer_predecessors}, "
                    f"repeats={args.repeats}, warmups={args.warmups}"
                )

                runs = bench_function(
                    fn,
                    file_bytes,
                    params,
                    infer_predecessors,
                    repeats=args.repeats,
                    warmups=args.warmups,
                )

                result = summarize_runs(
                    file_path=file_path,
                    mode=mode,
                    infer_predecessors=infer_predecessors,
                    runs=runs,
                    repeats=args.repeats,
                    warmups=args.warmups,
                )
                results.append(result)

                if args.profile and not did_profile:
                    profile_once(
                        fn,
                        file_bytes,
                        params,
                        infer_predecessors,
                        sort_by=args.profile_sort,
                        top_n=args.profile_top,
                    )
                    did_profile = True

    print_result_table(results)

    if args.json_out:
        save_results_json(results, Path(args.json_out).resolve())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
