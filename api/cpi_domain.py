"""Numerical coverage, independent of UI example prompts or a text provider."""
import math

RELEASE_DATES = ("2025-06-11", "2025-07-15", "2025-08-12")
MIN_CPI, MAX_CPI = -2.0, 2.0


def instruction_error(parsed):
    if (parsed.date_precision != "day" or parsed.scope != "release"
            or parsed.requested_end is not None
            or parsed.requested_start not in RELEASE_DATES
            or parsed.release_dates != [parsed.requested_start]):
        return "Use one CPI release: June 11, July 15 or August 12, 2025."
    if parsed.operation == "set":
        if parsed.value is None or not math.isfinite(parsed.value) or not MIN_CPI <= parsed.value <= MAX_CPI:
            return "Monthly CPI must be between -2% and 2%. Annual/core CPI uses a different measure; please specify monthly headline CPI."
    elif parsed.operation == "add_pp":
        if parsed.value is None or not math.isfinite(parsed.value) or abs(parsed.value) > MAX_CPI - MIN_CPI:
            return "Specify a percentage-point change that keeps resolved monthly CPI between -2% and 2%."
    elif parsed.operation != "carry":
        return "Set a CPI level, add/subtract percentage points, or keep an earlier simulated reading."
    if parsed.operation != "set" and parsed.reference not in {
            "preceding", "p1", "p2", "p3", *("date:" + d for d in RELEASE_DATES)}:
        return "Reference the preceding simulated reading, a prompt ID, or an earlier supported release date."
    return None
