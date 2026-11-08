# Shared forecast and evaluation work

Use pretrained inference for the first release through the typed segment interface
described in `api/README.md`. The Chronos adapter and disclosed empirical baseline
return supported results or explicit unsupported reasons. Pin weights and data
versions and warm the model on the demo host.

Test session mapping, units, ordered quantiles, missing coverage, frozen information
cutoff and no future-data leakage. Evaluate chronological held-out releases separately
from synthetic application fixtures. Record count, error, range coverage and width,
baseline comparison and cold/warm latency alongside timeline replay and storage tests.

`chronos_adapter.py` and `baseline.py` now implement the existing numerical boundary
for the bounded June 11 example. Run `python tools/real_forecast.py` after preparing
the local inputs. See [the real-data and API guide](../docs/real-data-adapter.md) for CPU
setup, tests and limitations. `APP_MODE=research` connects this boundary to the durable
HTTP API for one June prompt and replacement. The current real dataset cannot support
the empirical floor. Aashna and Aditya continue the remaining work together here.
