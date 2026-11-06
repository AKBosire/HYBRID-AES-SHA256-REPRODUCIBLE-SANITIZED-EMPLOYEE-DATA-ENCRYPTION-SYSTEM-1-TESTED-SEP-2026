import argparse
import csv
import hashlib
import json
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"
DATA_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)


def measured(operation, value):
    started = time.perf_counter_ns()
    output = operation(value)
    return output, (time.perf_counter_ns() - started) / 1_000_000


def main():
    parser = argparse.ArgumentParser(description="Actual Fernet and SHA-256 timing benchmark")
    parser.add_argument("--iterations", type=int, default=1000)
    args = parser.parse_args()
    key_path = DATA_DIR / "fernet.key"
    if not key_path.exists():
        key_path.write_bytes(Fernet.generate_key())
    fernet = Fernet(key_path.read_bytes())

    rows = []
    tamper_tests_rejected = 0
    for index in range(1, args.iterations + 1):
        payload = f"Synthetic employee field {index:04d}".encode()
        token, encryption_ms = measured(fernet.encrypt, payload)
        recovered, decryption_ms = measured(fernet.decrypt, token)
        digest, sha256_ms = measured(lambda item: hashlib.sha256(item).hexdigest(), payload)
        rows.append({
            "iteration": index,
            "payload_bytes": len(payload),
            "token_bytes": len(token),
            "encryption_time_ms": round(encryption_ms, 6),
            "decryption_time_ms": round(decryption_ms, 6),
            "sha256_time_ms": round(sha256_ms, 6),
            "round_trip_verified": recovered == payload,
            "digest_length_hex_characters": len(digest),
        })

        modified = bytearray(token)
        modified[len(modified) // 2] = modified[len(modified) // 2] ^ 1
        try:
            fernet.decrypt(bytes(modified))
        except InvalidToken:
            tamper_tests_rejected += 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_path = RESULTS_DIR / f"crypto_benchmark_{timestamp}_raw.csv"
    with raw_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "iterations": args.iterations,
        "verified_round_trips": sum(row["round_trip_verified"] for row in rows),
        "modified_tokens_rejected": tamper_tests_rejected,
        "mean_encryption_time_ms": statistics.fmean(row["encryption_time_ms"] for row in rows),
        "mean_decryption_time_ms": statistics.fmean(row["decryption_time_ms"] for row in rows),
        "mean_sha256_time_ms": statistics.fmean(row["sha256_time_ms"] for row in rows),
        "raw_results_file": raw_path.name,
        "environment": {"python": sys.version.split()[0], "operating_system": platform.platform()},
    }
    (RESULTS_DIR / f"crypto_benchmark_{timestamp}_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
