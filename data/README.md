# Local market inputs

Start with one target and two complete release windows. Record source, version/hash,
coverage, release availability timestamps, units, missing-data policy, attribution
and allowed ingestion/display/redistribution in a manifest. Verify source rights before
enabling a feed. Do not commit restricted raw data or local environment files.

Produce an exchange-session calendar and as-released CPI inputs; distinguish the
reference month from publication time. Keep reveal outcomes in a separate reader.
Expose the coverage and source metadata needed by capabilities and panels.

The local SPY/CPI/session loader is now implemented in `real_market.py`. Run
`python tools/prepare_market_data.py` from the repository root. Read
[the real-data and API guide](../docs/real-data-adapter.md) for the audited coverage,
ignored output paths, source rights, frozen-cutoff rules and separate reveal reader.
