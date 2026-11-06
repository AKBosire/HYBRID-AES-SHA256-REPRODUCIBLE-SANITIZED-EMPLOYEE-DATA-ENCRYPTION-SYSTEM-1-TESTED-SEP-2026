import argparse
import csv
import json
import math
import platform
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests
import urllib3


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)
DEFAULT_LEVELS = [("baseline", 100, 1), ("low", 250, 10), ("moderate", 500, 25), ("high", 1000, 50), ("stress", 1000, 100)]


def percentile(values, percentage):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentage / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def send_request(index, target, timeout, verify_tls):
    started = time.perf_counter_ns()
    status_code = None
    outcome = "completed"
    error_type = ""
    try:
        response = requests.post(
            target,
            data={"email": "synthetic.nonexistent@example.invalid", "password": "fixed-invalid-password"},
            timeout=timeout,
            verify=verify_tls,
            allow_redirects=False,
        )
        status_code = response.status_code
    except requests.Timeout:
        outcome, error_type = "failed", "timeout"
    except requests.ConnectionError:
        outcome, error_type = "failed", "connection_error"
    except requests.RequestException as error:
        outcome, error_type = "failed", type(error).__name__
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    return {
        "request_index": index,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status_code": status_code if status_code is not None else "",
        "outcome": outcome,
        "error_type": error_type,
        "response_time_ms": round(elapsed_ms, 6),
    }


def run_once(level, total, concurrency, repetition, target, timeout, verify_tls):
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}_{level}_r{repetition}"
    started = time.perf_counter_ns()
    rows = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(send_request, i + 1, target, timeout, verify_tls) for i in range(total)]
        for future in as_completed(futures):
            rows.append(future.result())
    duration_seconds = (time.perf_counter_ns() - started) / 1_000_000_000
    rows.sort(key=lambda row: row["request_index"])

    raw_path = RESULTS_DIR / f"{run_id}_raw.csv"
    with raw_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    latencies = [float(row["response_time_ms"]) for row in rows]
    completed = sum(row["outcome"] == "completed" for row in rows)
    failed = total - completed
    summary = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "repetition": repetition,
        "target": target,
        "total_requests": total,
        "concurrency": concurrency,
        "timeout_seconds": timeout,
        "tls_verification": verify_tls,
        "duration_seconds": round(duration_seconds, 6),
        "completed_requests": completed,
        "failed_requests": failed,
        "completion_percentage": round(100 * completed / total, 4),
        "failure_percentage": round(100 * failed / total, 4),
        "throughput_requests_per_second": round(completed / duration_seconds, 6),
        "mean_response_time_ms": round(statistics.fmean(latencies), 6),
        "median_response_time_ms": round(statistics.median(latencies), 6),
        "p95_response_time_ms": round(percentile(latencies, 95), 6),
        "minimum_response_time_ms": round(min(latencies), 6),
        "maximum_response_time_ms": round(max(latencies), 6),
        "raw_results_file": raw_path.name,
        "environment": {"python": sys.version.split()[0], "operating_system": platform.platform()},
    }
    summary_path = RESULTS_DIR / f"{run_id}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (RESULTS_DIR / "latest_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description="Measured concurrent-login workload experiment")
    parser.add_argument("--target", default="https://127.0.0.1:5000/login")
    parser.add_argument("--timeout", type=float, default=1.2)
    parser.add_argument("--verify-tls", action="store_true")
    parser.add_argument("--suite", action="store_true", help="Run five workload levels, each three times")
    parser.add_argument("--total", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()

    if not args.verify_tls:
        # Expected for the isolated self-signed laboratory certificate.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    levels = DEFAULT_LEVELS if args.suite else [("custom", args.total, args.concurrency)]
    all_summaries = []
    for level, total, concurrency in levels:
        for repetition in range(1, args.repetitions + 1):
            all_summaries.append(run_once(level, total, concurrency, repetition, args.target, args.timeout, args.verify_tls))
            time.sleep(1)
    (RESULTS_DIR / "experiment_manifest.json").write_text(json.dumps(all_summaries, indent=2), encoding="utf-8")

    aggregate_rows = []
    for level, _, _ in levels:
        selected = [row for row in all_summaries if row["level"] == level]
        aggregate_rows.append({
            "level": level,
            "runs": len(selected),
            "total_requests_per_run": selected[0]["total_requests"],
            "concurrency": selected[0]["concurrency"],
            "mean_throughput_requests_per_second": round(statistics.fmean(row["throughput_requests_per_second"] for row in selected), 6),
            "mean_completion_percentage": round(statistics.fmean(row["completion_percentage"] for row in selected), 6),
            "mean_failure_percentage": round(statistics.fmean(row["failure_percentage"] for row in selected), 6),
            "mean_response_time_ms_across_runs": round(statistics.fmean(row["mean_response_time_ms"] for row in selected), 6),
            "mean_p95_response_time_ms_across_runs": round(statistics.fmean(row["p95_response_time_ms"] for row in selected), 6),
            "throughput_sample_standard_deviation": round(statistics.stdev(row["throughput_requests_per_second"] for row in selected), 6) if len(selected) > 1 else 0.0,
        })
    with (RESULTS_DIR / "aggregate_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(aggregate_rows[0]))
        writer.writeheader()
        writer.writerows(aggregate_rows)


if __name__ == "__main__":
    main()
