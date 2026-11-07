"""Check fixture structure and the critical suffix replacement expectation."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api.contracts import RunResponse, Problem

fixtures = {}
for path in sorted((ROOT / "shared/fixtures").glob("*.json")):
    value = json.loads(path.read_text(encoding="utf-8"))
    (RunResponse if "revision" in value else Problem).model_validate(value)
    fixtures[path.stem] = value
    print(f"Valid: {path.name}")
first = fixtures["first-run"]
for name in ("shorter-suffix", "empty-suffix"):
    edit = fixtures[name]
    assert edit["parent_revision"] == first["revision"]
    prefix = [p for p in first["series"]["points"] if p["date"] < edit["changed_from"]]
    combined = prefix + edit["series"]["points"]
    assert combined[0] == first["series"]["points"][0]
    assert all(p["date"] != "2025-06-12" for p in combined)
    assert [p["id"] for p in edit["prompts"]] == ["p1"]
print("Suffix examples preserve the prefix and remove the old tail.")
