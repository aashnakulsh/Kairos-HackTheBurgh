# Shared handoff v1

Read `docs/frontend-backend-contract.md` for the complete fixture-backed handoff.
`api/contracts.py` is the schema source; generated OpenAPI, JSON Schema and TypeScript
must not be edited independently. Aashna coordinates contract changes. A local fixture
server exists, but the production app/model/database do not.

With dependencies from `requirements-contracts.txt` installed:

```sh
python tools/export_contracts.py
python tools/export_contracts.py --check
python tools/build_example_fixtures.py --check
python tools/check_fixtures.py
```

The generator was verified with Pydantic 2.13.4. Aashna should pin the complete backend
environment when scaffolding. No frontend dependency installation is needed yet.

All fixtures are synthetic examples, not market observations or forecast quality
evidence. UI must display `data_label`. Null is explicit, not an omitted field.
Dates are validated ISO strings; schemas check units, quantiles and several invariants.
Services must still validate calendar membership, references, data rights and replay.

For a suffix, require the currently cached revision to equal `parent_revision`.
Keep only cached points strictly before `changed_from`, then append new points.
Discard the entire old tail even when the replacement is empty. Replace prompts and
panels together. On mismatch restore a full snapshot; never append blindly.
Restore and first responses use `series_mode=full`. Ignore obsolete request responses.

`Problem` is the common body: HTTP 409 conflict, 422 invalid, 503 unavailable;
clarification and unsupported are domain responses. Failed requests preserve the
committed workspace. An explicitly accepted qualitative revision may instead contain
an empty suffix and unsupported panel. Aashna must implement this distinction.

`fixtures/manifest.json` maps every fixture to its schema. `journey.json` traces the
complete three-prompt/edit/reveal HTTP sequence. The fixture server implements named
release presets only; intervals/recurrence, providers and SQLite remain production work.
