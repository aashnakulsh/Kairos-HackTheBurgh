"""Exercise the real June durable API; run against a local research-mode server."""
import argparse
import json
import math
from pathlib import Path
import sys
from uuid import uuid4

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.contracts import RunResponse

DATES = ["2025-06-11", "2025-06-12", "2025-06-13", "2025-06-16", "2025-06-17"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--expected-forecast", type=Path, help="Optional standalone forecast.json to compare")
    parser.add_argument("--receipt", type=Path, help="Save full snapshots for exact comparison after restart")
    parser.add_argument("--restore-from", type=Path, help="Only compare stored snapshots after server restart")
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url, timeout=60) as client:
        def get(path):
            response = client.get(path)
            response.raise_for_status()
            return response.json()

        def post(path, body, status=None):
            response = client.post(path, json=body)
            response.raise_for_status()
            result = response.json()
            if result.get("status") != status:
                raise RuntimeError(result)
            return result

        if args.restore_from:
            receipt = json.loads(args.restore_from.read_text())
            url = f"/api/timelines/{receipt['latest']['timeline_id']}"
            assert get(url) == receipt["latest"], "Latest snapshot changed across restart"
            assert get(url + "/revisions/1") == receipt["first"], "Original revision changed across restart"
            assert post(url + "/commit", receipt["first_commit"]) == receipt["first"]
            print("PASS: exact latest/previous snapshots and original commit retry survive server restart")
            return

        caps = get("/api/capabilities")
        assert caps["mode"] == "live" and caps["max_prompts"] == 3, "Start the research-mode server first"
        initial = post("/api/timelines", dict(target_id="SPY", request_id=uuid4().hex))
        RunResponse.model_validate(initial)
        assert initial["evidence_cutoff"] == "2025-06-11T12:29:59Z"
        observed_count = len(initial["series"]["points"])
        assert observed_count >= 20
        assert all(p["kind"] == "observed" and p["date"] < DATES[0] for p in initial["series"]["points"])
        url = f"/api/timelines/{initial['timeline_id']}"
        expected = json.loads(args.expected_forecast.read_text()) if args.expected_forecast else None
        if expected:
            assert expected["dataset_version"] == initial["dataset_version"]
        first = first_commit = None
        for revision, value in enumerate((0.4, 0.2)):
            draft = post(url + "/interpret", dict(text=f"Set June 11 CPI to {value}%",
                mode="replace" if revision else "add", selected_prompt_id="p1" if revision else None,
                expected_revision=revision), status="ready")
            body = dict(draft_id=draft["draft_id"], expected_revision=revision, request_id=uuid4().hex)
            result = post(url + "/commit", body)
            RunResponse.model_validate(result)
            assert result["revision"] == revision + 1
            assert result["series_mode"] == ("suffix" if revision else "full")
            points = [p for p in result["series"]["points"] if p["kind"] == "simulated"]
            assert [p["date"] for p in points] == DATES
            assert all(p["engine"] == "chronos-2-cpu" and p["segment_id"] == "p1" for p in points)
            if expected:
                expected_result = next(s["result"] for s in expected["scenarios"] if s["cpi"] == value)
                assert result["model_version"] == expected_result["model_version"]
                for actual, wanted in zip(points, expected_result["points"]):
                    for field in ("value", "q10", "q90"):
                        assert math.isclose(actual[field], wanted[field], rel_tol=1e-6, abs_tol=1e-5), (value, field)
            if revision == 0:
                first, first_commit = result, body
            print(f"PASS: CPI {value}%, revision {result['revision']}, {result['series_mode']}, five ordered forecast points")
        latest = get(url)
        RunResponse.model_validate(latest)
        assert latest["series"]["points"][:observed_count] == initial["series"]["points"]
        assert latest["series"]["points"][observed_count:] == result["series"]["points"]
        assert latest["prompts"][0]["id"] == first["prompts"][0]["id"] == "p1"
        assert get(url + "/revisions/1") == first
        assert post(url + "/commit", first_commit) == first
        assert get(url) == latest
        print("PASS: unchanged observed prefix, immutable first revision and original commit retry")
        if expected:
            print("PASS: HTTP quantiles match both standalone Chronos scenarios")
        if args.receipt:
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            args.receipt.write_text(json.dumps(dict(first=first, latest=latest, first_commit=first_commit), indent=2) + "\n")
            print(f"After restarting the server: python tools/research_backend_demo.py --base-url {args.base_url} --restore-from {args.receipt}")
        print(f"Timeline: {args.base_url}{url}")


if __name__ == "__main__":
    main()
