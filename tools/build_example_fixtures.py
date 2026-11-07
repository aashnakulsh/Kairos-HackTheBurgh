"""Rebuild deterministic synthetic UI examples. No market/model claims."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "shared/fixtures"
DEST.mkdir(parents=True, exist_ok=True)


def save(name, value):
    (DEST / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def point(date, value, kind="simulated"):
    return dict(date=date, kind=kind, value=value,
                q10=value - 1 if kind == "simulated" else None,
                q90=value + 1 if kind == "simulated" else None,
                engine="synthetic" if kind == "simulated" else None,
                segment_id="p1" if kind == "simulated" else None)


empty = dict(contract_version="1", data_label="Synthetic example — not market data",
             timeline_id="example", revision=0, parent_revision=None,
             changed_from=None, replace_through=None, series_mode="full", prompts=[],
             series=dict(target_id="SPY", base_date="2025-06-10", base_value=100,
                         unit="index", frequency="trading_session", points=[]), panels={})
save("empty", empty)
first = copy.deepcopy(empty)
first.update(revision=1, parent_revision=0, changed_from="2025-06-11", replace_through="2025-06-12")
first["prompts"] = [dict(id="p1", display_number=1, text="Set June 11 CPI to 0.4%",
    date_precision="day", requested_start="2025-06-11", requested_end=None,
    effective_start="2025-06-11", effective_end=None, scope="release", operation="set",
    value=0.4, unit="percent", reference=None, status="supported")]
first["series"]["points"] = [point("2025-06-10", 100, "observed"), point("2025-06-11", 101), point("2025-06-12", 102)]
first["panels"] = {"p1": dict(summary="Synthetic example for chart integration only.",
    hypotheses=[], evidence=[], impacts=[], horizon="2 synthetic sessions",
    comparison=None, engine="synthetic", support_count=0, status="supported")}
save("first-run", first)
edit = copy.deepcopy(first)
edit.update(revision=2, parent_revision=1, series_mode="suffix")
edit["prompts"][0].update(text="Set June 11 CPI to 0.2%", value=0.2)
edit["series"]["points"] = [point("2025-06-11", 99)]
save("shorter-suffix", edit)
qualitative = copy.deepcopy(edit)
qualitative["series"]["points"] = []
qualitative["prompts"][0]["status"] = "unsupported"
qualitative["panels"]["p1"].update(status="unsupported", summary="Synthetic qualitative-only revision; no numerical forecast.")
save("empty-suffix", qualitative)
for name, status, reason, choices in [
    ("clarification", "needs_clarification", "Choose a release date.", ["2025-06-11"]),
    ("unsupported", "unsupported", "Requested date is outside supported coverage.", []),
    ("conflict", "conflict", "Expected revision does not match; restore before reapplying.", []),
]:
    save(name, dict(status=status, reason=reason, choices=choices))
