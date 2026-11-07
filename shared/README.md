# Shared handoff v1

This is a starter contract, not a running app. Architecture section 5 remains the
behavioral agreement. `api/contracts.py` is the schema source; generated JSON Schema
and TypeScript must not be edited independently. Aashna coordinates contract changes.

With Python and Pydantic v2 installed:

```sh
python tools/export_contracts.py
python tools/export_contracts.py --check
python tools/check_fixtures.py
```

The generator was verified with Pydantic 2.13.4. Aashna should pin the complete backend
environment when scaffolding. No frontend dependency installation is needed yet.

All fixtures are synthetic examples, not market observations or forecast quality
evidence. UI must display `data_label`. Null is explicit, not an omitted field.
Dates are ISO date strings; services still must validate calendar, units, references,
quantile ordering and business rules. These structural schemas do not implement them.

For a suffix, require the currently cached revision to equal `parent_revision`.
Keep only cached points strictly before `changed_from`, then append new points.
Discard the entire old tail even when the replacement is empty. Replace prompts and
panels together. On mismatch restore a full snapshot; never append blindly.
Restore and first responses use `series_mode=full`. Ignore obsolete request responses.

`Problem` is a proposed common body: HTTP 409 conflict, 422 invalid, 503 unavailable;
clarification and unsupported are domain responses. Failed requests preserve the
committed workspace. An explicitly accepted qualitative revision may instead contain
an empty suffix and unsupported panel. Aashna must implement this distinction.

Still to add before endpoint implementation: capabilities, successful interpreted
draft (including expiry and revision binding), reveal and source attribution schemas.
Do not invent these independently in frontend components.
