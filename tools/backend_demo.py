"""Exercise the durable HTTP API locally with the four accepted preset submissions."""
import argparse
from uuid import uuid4
import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--restore", help="Only check an existing completed demo timeline")
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url, timeout=30) as client:
        if args.restore:
            response = client.get(f"/api/timelines/{args.restore}")
            response.raise_for_status()
            restored = response.json()
            assert restored["revision"] == 4 and restored["series_mode"] == "full"
            assert [p["resolved_value"] for p in restored["prompts"]] == [0.2, 0.3, 0.3]
            assert [p["id"] for p in restored["prompts"]] == ["p1", "p2", "p3"]
            print("PASS: persisted revision 4 restored with p1/p2/p3 and CPI 0.2/0.3/0.3")
            return
        def post(path, body):
            response = client.post(path, json=body)
            response.raise_for_status()
            value = response.json()
            if value.get("status") not in (None, "ready"):
                raise RuntimeError(value)
            return value
        run = post("/api/timelines", dict(target_id="SPY", request_id=uuid4().hex))
        url = f"/api/timelines/{run['timeline_id']}"
        texts = ["Set June 11 CPI to 0.4%",
            "July 15: add 0.1 percentage points to preceding reading",
            "August 12: keep July simulated reading", "Set June 11 CPI to 0.2%"]
        for revision, text in enumerate(texts):
            draft = post(url + "/interpret", dict(text=text, mode="replace" if revision == 3 else "add",
                selected_prompt_id="p1" if revision == 3 else None, expected_revision=revision))
            run = post(url + "/commit", dict(draft_id=draft["draft_id"], expected_revision=revision, request_id=uuid4().hex))
            print(f"revision={run['revision']} mode={run['series_mode']} CPI={[p['resolved_value'] for p in run['prompts']]}")
        response = client.get(url)
        response.raise_for_status()
        restored = response.json()
        assert restored["series_mode"] == "full" and restored["revision"] == 4
        assert [p["id"] for p in restored["prompts"]] == ["p1", "p2", "p3"]
        assert [p["resolved_value"] for p in restored["prompts"]] == [0.2, 0.3, 0.3]
        print(f"PASS. Restore after server restart: {args.base_url}{url}")
        print(f"Earlier revision: {args.base_url}{url}/revisions/3")


if __name__ == "__main__":
    main()
