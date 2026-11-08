"""Download original BLS HTML releases into ignored local storage; no keys required."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urljoin
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.real_market import digest, parse_release

INDEX = "https://www.bls.gov/bls/news-release/cpi.htm"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=Path("data/local/raw/bls-expanded"))
    parser.add_argument("--from-date", default="2023-01-01")
    parser.add_argument("--through-date", default="2025-05-13")
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    entries = []
    with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "TeamRelay academic research archive audit"}) as client:
        response = client.get(INDEX); response.raise_for_status()
        for name in sorted(set(re.findall(r"cpi_\d{8}\.htm", response.text))):
            date = datetime.strptime(name[4:12], "%m%d%Y").date().isoformat()
            if not args.from_date <= date <= args.through_date:
                continue
            path = args.destination / name
            url = urljoin(INDEX, "/news.release/archives/" + name)
            if not path.exists():
                response = client.get(url); response.raise_for_status()
                with TemporaryDirectory(dir=args.destination) as tmp:
                    temporary = Path(tmp) / name
                    temporary.write_bytes(response.content)
                    # Keep the expected filename while validating before publication.
                    parse_release(temporary)
                    temporary.replace(path)
            parsed = parse_release(path)
            entries.append(dict(path=name, url=url, sha256=digest(path), published_at=parsed["published_at"]))
            print(f"Validated {name}: {parsed['reference_month']} CPI {parsed['cpi_percent']}%", flush=True)
    if not entries:
        raise SystemExit("No matching archive links found; no data fabricated")
    (args.destination / "download-manifest.json").write_text(json.dumps(dict(index=INDEX,
        checked_at=datetime.now(timezone.utc).isoformat(), files=entries), indent=2) + "\n")


if __name__ == "__main__":
    main()
