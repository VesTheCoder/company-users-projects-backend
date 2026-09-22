import json
from datetime import datetime
from pathlib import Path


def main():
    root = Path("docs/benchmarks")
    rows = [
        "| Scenario | Requests/s | p50 ms | p95 ms | p99 ms | "
        "HTTP failures | Dropped iterations |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in [
        "login",
        "companies",
        "employees",
        "projects",
        "assignments",
        "mixed-baseline",
        "mixed",
        "saturation",
    ]:
        path = root / f"{name}.json"
        if not path.exists():
            continue
        metrics = json.loads(path.read_text())["metrics"]
        duration = metrics["http_req_duration"]
        rate = metrics["http_reqs"]["rate"]
        failures = metrics["http_req_failed"]["value"]
        dropped = metrics.get("dropped_iterations", {}).get("count", 0)
        rows.append(
            f"| {name} | {rate:.2f} | {duration['med']:.2f} | "
            f"{duration['p(95)']:.2f} | {duration['p(99)']:.2f} | "
            f"{failures:.2%} | {dropped} |"
        )
    (root / "results.md").write_text("\n".join(rows) + "\n")
    print("\n".join(rows))
    series = Path(".local/saturation.ndjson")
    if series.exists():
        write_saturation_curve(series, root)


def write_saturation_curve(series, root):
    samples = []
    with series.open() as stream:
        for line in stream:
            point = json.loads(line)
            if (
                point.get("type") == "Point"
                and point.get("metric") == "http_req_duration"
            ):
                data = point["data"]
                stamp = datetime.fromisoformat(data["time"].replace("Z", "+00:00"))
                samples.append(
                    (stamp.timestamp(), data["value"], int(data["tags"]["status"]))
                )
    start = min(row[0] for row in samples)
    buckets = {}
    for stamp, duration, status in samples:
        buckets.setdefault(int((stamp - start) // 10), []).append((duration, status))
    rows = [
        "| Completion window | Requests/s | p95 ms | p99 ms | HTTP failures |",
        "|---|---:|---:|---:|---:|",
    ]
    for bucket, samples in sorted(buckets.items()):
        values = sorted(sample[0] for sample in samples)
        p95, p99 = values[int(len(values) * 0.95)], values[int(len(values) * 0.99)]
        failures = sum(sample[1] >= 400 for sample in samples)
        rows.append(
            f"| {bucket * 10}-{(bucket + 1) * 10}s | {len(values) / 10:.1f} | "
            f"{p95:.2f} | {p99:.2f} | {failures} |"
        )
    rows.append(
        "\nWindows use completion time; the last window may be partial. "
        "This is a local 100-to-300 iteration/s ramp, not a scaled validation."
    )
    (root / "saturation-curve.md").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    main()
