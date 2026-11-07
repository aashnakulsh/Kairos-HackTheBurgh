"""Validate every registered fixture with JSON Schema and Pydantic semantics."""
import json
import sys
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api import contracts

schema = json.loads((ROOT / "shared/contracts.schema.json").read_text(encoding="utf-8"))
directory = ROOT / "shared/fixtures"
manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
actual = {p.name for p in directory.glob("*.json")} - {"manifest.json"}
if actual != set(manifest):
    raise SystemExit(f"Unregistered/missing fixtures: {actual ^ set(manifest)}")
for filename, model_name in manifest.items():
    value = json.loads((directory / filename).read_text(encoding="utf-8"))
    sub = {"$ref": f"#/$defs/{model_name}", "$defs": schema["$defs"]}
    Draft202012Validator(sub).validate(value)
    getattr(contracts, model_name).model_validate(value)
print(f"PASS: {len(manifest)} fixtures match JSON Schema and Pydantic validators.")
