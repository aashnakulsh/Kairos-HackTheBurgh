# TeamRelay: model scope analysis and next-chat handover

> **Latest implementation:** Aashna approved the general scenario plan after the
> continuous-CPI milestone below. Read [the general scenario handover](general-scenario-handover.md)
> first. The new `APP_MODE=scenario` bypasses CPI-only parsing and validation:
> OpenAI researches arbitrary events, measures analogues from local history,
> proposes explicit covariate paths, and Chronos produces baseline/scenario paths.
> This is real inference, not a claim that historical associations establish causality.
> Earlier scope restrictions and live-test status below are historical.

> **Implementation update — 8 November 2026, approximately 06:00 London:**
> Aashna subsequently authorized fixes under the noon deadline. The continuous
> CPI repair is now implemented locally in this repository, with focused tests
> and real offline Chronos/replay checks passed. Read
> [the current implementation and frontend handover](continuous-cpi-demo-handover.md)
> first. It supersedes this document's analysis-only instruction, old worktree
> states, five-case restrictions and proposed first implementation step.
> New live OpenAI/Ollama interpretation and the rendered UI journey remain
> unverified: execution approval for the live check was declined. No new live
> provider call was made. The broader economic-model limitations below still apply.
>
> **The remainder is the historical pre-fix analysis**, retained so the diagnosis,
> earlier evidence and limits remain reviewable. Do not follow its old next-chat
> prompt or assume its Git/server state is current.

**Prepared for Aashna and Aditya · 8 November 2026 · Europe/London.**

This document answers the concern raised after the Mac live verification:

> Is the AI actually interpreting scenarios and predicting a market path, or are
> we just showing hardcoded CPI cases? How do we reach the original product goal?

**Current instruction: analysis and documentation only.** No application code was
changed for this report. No new forecasts, paid model calls, model downloads,
test-suite runs, commits, pushes, merges or deployments were performed to prepare
it. The analysis uses inspected source, the preceding live verification, read-only
calculations over its saved results, and the model publisher's documentation.

## 1. Executive finding

**The accepted scenarios are hardcoded; the research forecast numbers are produced
by real model inference. The current application is a tightly restricted CPI
demonstration, not the general economic-scenario engine originally envisioned.**

Three separate components explain the apparent contradiction:

1. **Language interpretation is real, but constrained.** OpenAI or local Qwen can
   recognize ordinary wording, but they are instructed to map it into just five
   approved CPI instruction combinations. Independent code then rejects any other
   combination. Exact preset text bypasses the LLM entirely.
2. **Numerical inference is real in research mode.** Chronos receives historical
   indexed prices and CPI/release-indicator sequences and produces median/q10/q90
   values. These are not a table of five saved stock-market answers, and there is
   no research-mode rule saying “CPI X means SPY changes by Y percent.”
3. **Descriptions are real generated prose, but come after the numbers.** OpenAI
   summarizes the saved forecast and assumptions. It does not decide the plotted
   prices or independently establish why CPI caused a particular market move.

The live test proved that the bounded integration works. It did **not** prove
general scenario understanding, reliable market prediction, a learned CPI effect,
or causal counterfactual validity. Earlier statements that PR #6 was ready for
review referred to that bounded implementation and its fixes, not completion of
the broader product or proof of forecasting skill.

The most important additional finding is about the data actually reaching Chronos:
the live run used **20 historical trading sessions with CPI fixed at 0.2 throughout,
and only one release-indicator session**. A model cannot estimate a historical
CPI-response relationship from variation that is absent in that supplied context.
Pretraining can provide general time-series patterns, but the app has not shown
that those patterns constitute a useful macroeconomic response model for SPY.

## 2. The intended product versus the implemented product

### Intended experience

The user's original goal is a system that:

- Understands a user's economic or policy scenario in ordinary language.
- Resolves what changes, when, by how much, and relative to what baseline.
- Uses relevant historical data and an appropriate numerical model to generate a
  market scenario, rather than choosing a prepared answer.
- Explains the result using the supplied assumptions, model outputs and evidence.
- Lets the user add events, change an earlier assumption, and replay later events.
- Makes uncertainty, missing information and unsupported cases understandable.

This does not require accepting every imaginable proposition as a numerical
forecast. A finite model/data domain is normal. What it does require is meaningful
variation within that domain, rather than a short list of approved sentences and
approved values presented as broad intelligence.

### Actual current implementation

The implemented quantitative domain is:

| Dimension | Current restriction |
|---|---|
| Market target | SPY only |
| Economic input | Headline monthly seasonally adjusted CPI-U |
| First fork | June 11, 2025 |
| Other intervention dates | July 15 and August 12, 2025 |
| Accepted instruction combinations | Five fixed date/operation/value/reference tuples |
| Active prompts | Three |
| Final segment | Five trading sessions |
| Total simulated horizon | At most 65 sessions |
| Live tested snapshot | Original four-release snapshot, 20 eligible pre-fork sessions |
| Text role | Parse into that restricted scope; narrate its results separately |
| Other events/instruments | No numerical representation or model path implemented |

Allowing arbitrary wording around these five instructions improved usability. It
did not expand the numerical scenario domain. That is why an LLM can understand
“20% CPI” and still reject it, and why a prompt about interest rates, oil or a
political event cannot currently drive a corresponding model input.

## 3. What is hardcoded, learned, calculated or synthetic?

| Component | Category | What it does |
|---|---|---|
| `PRESETS` dictionary | Hardcoded demo scope | Lists the five permitted canonical CPI instructions |
| Parser system instructions | Hardcoded demo scope | Tells OpenAI/Qwen to accept only those combinations |
| `_DATES` and `_grounded` | Handwritten checks | Restrict date wording, explicit values and references |
| `_supported` | Hardcoded whitelist | Rejects canonical tuples absent from PRESETS |
| `ResearchBackend.instruction` | Second hardcoded whitelist | Rechecks the same permitted tuples before drafting/committing |
| Prompt/dependency resolution | Deterministic application logic | Resolves set/add/carry, including .4/.5/.5 → .2/.3/.3 |
| Data/session/provenance checks | Deterministic validation | Bind inputs to dates, units, a snapshot and a frozen cutoff |
| `ChronosAdapter` | Real pretrained neural inference | Produces numeric quantile forecasts from supplied sequences |
| Forecast percentage summaries | Deterministic calculations | Compute changes from saved index levels |
| Basic panel summary | Template text | Displays the resolved CPI assumption without an LLM |
| OpenAI description relay | Real text generation | Describes already-computed forecast numbers and assumptions |
| Browser `mockApi.ts` | Synthetic simulation | Uses text keywords, hashing and seeded noise to draw a fake path |
| Backend `SyntheticAdapter` | Synthetic test arithmetic | Adds the CPI value to levels and constructs fixed-offset bands |

The last two rows are deliberate development tools. They must remain visibly
synthetic. The preceding live verification used `VITE_API=server` and
`APP_MODE=research`, with API requests observed in DevTools and the new backend's
logs. It did not use those synthetic price generators.

The UI's default mock can accept many more topics than the research backend.
Switching back to it would make the application appear more flexible while
replacing real inference with invented paths. That would not satisfy the user's
request for a data-based product.

## 4. Exactly where the restrictions are enforced

The relevant working implementation is in the isolated task checkout at
`/Users/aashn/hackathon/TeamRelay-CPI-parser-check`, commit `d90c447`.
The original backend folder is still on an earlier branch state; do not confuse
the two when reading source or starting a server.

### 4.1 Shared preset dictionary

`shared/fixture_service.py`, near line 12, defines:

| Text example | Date | Operation | Stored value | Reference |
|---|---|---|---:|---|
| Set June 11 CPI to 0.4% | 2025-06-11 | set | 0.4 | null |
| Set June 11 CPI to 0.2% | 2025-06-11 | set | 0.2 | null |
| July 15: add 0.1 percentage points to preceding reading | 2025-07-15 | add_pp | 0.1 | preceding |
| August 12: keep July simulated reading | 2025-08-12 | carry | null | p2 |
| Set July 15 CPI to 0.2% | 2025-07-15 | set | 0.2 | null |

These are examples and a demo whitelist simultaneously. The research runtime
imports a dictionary from the fixture service as its domain policy. The issue is
the dependency on a finite list of tuples, not simply the presence of helpful UI
example buttons.

### 4.2 LLM instructions

`api/provider_parser.py` explicitly says that June supports .4 or .2, July supports
the fixed +.1 delta, and August supports a carry. It instructs the model to return
unsupported for other values, instruments and events. This is a deliberate
application instruction; the underlying text model's broader language capability
is not being exposed as a broader numerical domain.

### 4.3 Handwritten grounding checks

The same file's `_grounded` function, near line 136, recognizes only the three
named 2025 dates. The relative-change branch specifically requires a text value
of `0.1`. The carry branch requires July wording and a keep/carry/unchanged term.

Some checks are useful safeguards, but they are tightly coupled to this demo.
Source inspection also indicates formatting limitations to address when expanding
scope: a numeric value serialized as `0.4` is matched literally against the text,
so equivalent forms such as `0.40%` or a number written in words may be rejected.
This is a code-review inference, not a newly executed test in this analysis.

### 4.4 Parser tuple whitelist

`_supported`, near line 171, requires the tuple of date, operation, numeric value
and reference to belong to `PRESETS.values()`. Even perfect LLM interpretation of
a new valid CPI number is rejected here.

### 4.5 Research service tuple whitelist

`api/research_backend.py`, `ResearchBackend.instruction`, independently performs
the same membership check. Removing the restriction only from the parser prompt
or `_supported` would not make the HTTP product accept a new value.

### 4.6 Numerical loader restrictions

`data/real_market.py` has additional checks that are distinct from the five-case
whitelist:

- The historical seed and metadata must match the pinned snapshot.
- The observed prefix cannot be changed by the caller.
- Subsequent context can contain only valid preceding simulated medians.
- Sessions must be contiguous within the 65-session limit.
- CPI can change only at an explicit intervention on one of the three dates.
- CPI values must lie in the engineering interval **[-2%, 2%]**.
- The standalone request builder is pinned to the June 11 cutoff.

The numerical layer can already accept more continuous CPI values than the HTTP
product currently exposes. That does not establish that predictions across that
entire interval are reliable. An engineering input bound is not an empirically
validated economic-response range.

The seed call using `request(0.2, ...)` builds initial history/provenance context.
It does not force every scenario's future CPI to .2 or return a fixed .2 answer.
Scenario future rows are assembled separately and passed into the model.

## 5. Interpreting the supplied screenshots

### Screenshot: “20% is not a supported June 11 CPI value”

This message is consistent with the parser's explicit .4/.2 scope. The rejection
occurs in the interpretation/validation stage, before an accepted numerical run.
It is not evidence that Chronos was asked to forecast 20% and failed to understand
the number. The screenshot does not identify which rejecting layer produced its
wording; both the LLM instructions and backend policy constrain it.

However, the issue is broader than this extreme example: ordinary new values such
as **0.3% or 0.35% for June** are outside the current tuple whitelist too. That is
the clearest demonstration that the application exposes prepared cases rather
than a continuous economic input.

Monthly CPI at 20% is also far outside the current numerical range and local
history. A future version should clarify whether the user means monthly inflation,
annual inflation, a relative increase or another measure. It should not silently
convert 20 to .2, or produce a confident numeric path merely to avoid rejection.
Removing a five-case whitelist does not mean removing unit, coverage and
out-of-distribution safeguards.

### Screenshot: near-flat forecast and rising actual path

The blue median and shaded band are real outputs of the configured numerical
pipeline in the verified research mode. A relatively flat path does not mean the
line is a hardcoded constant. It may reflect the supplied recent history, the
model's inductive behavior, weak information from the covariates, recursive use of
simulated medians, or other issues requiring controlled investigation.

The yellow actual path rose substantially above the displayed scenario forecast.
That is a visible divergence worth investigating. But the actual economy did not
follow either of the hypothetical CPI paths in the demo, so it is not a clean
accuracy score for those counterfactual scenarios. The screenshot alone cannot
show whether the forecast difference was caused by CPI, whether the model ignored
CPI, or whether it would have forecast the factual outcome well under factual
assumptions.

The graph's later band widths should not be read as fully propagated uncertainty
from June through August. They are conditional on preceding simulated median
levels. A narrow final band does not mean the whole multi-event scenario has
become highly certain.

## 6. What the models actually receive

### 6.1 Text interpreter

The OpenAI parser receives the user's text, a bounded instruction prompt and a
structured JSON schema. The local fallback receives an equivalent task. Neither
receives the full raw price dataset for an independent market analysis.

The result is a typed scenario instruction with fields such as date, operation,
value, unit and reference. The result contains no market prices. The parser is a
translator into implemented domain variables, not the numerical forecaster.

### 6.2 Numerical model

`training/chronos_adapter.py` creates numeric frames containing:

- Historical SPY indexed levels as the target.
- Historical CPI readings available by their release dates.
- A release indicator.
- Hypothetical future CPI/release-indicator rows for the current segment.

It calls the pinned pipeline's `predict_df`, requesting q10/q50/q90. It validates
the returned dates, finite numbers and quantile ordering before saving them.
There is no raw user prompt, political name, news passage or general scenario
description in this boundary.

There is no application mechanism here that asks Chronos to read economic text or
derive an economic theory from the column name `cpi_percent`. It conditions on
numeric sequences. Naming a covariate does not itself establish that its economic
meaning or causal effect has been learned.

The publisher describes Chronos-2 as a pretrained time-series model supporting
covariate-informed and known-future-covariate forecasting. That supports the
technical choice to supply future scenario values. It is not evidence that our
particular CPI/SPY configuration is accurate or causal. See the
[pinned model card](https://huggingface.co/amazon/chronos-2/blob/29ec3766d36d6f73f0696f85560a422f50e8498c/README.md).

No TeamRelay-specific model training or fine-tuning was performed in this build.
The `training/` directory currently contains inference adapters, baselines and
evaluation code, not a newly fitted broad macroeconomic market model.

### 6.3 Narrator

The frontend forwards a saved numerical segment to the description relay. The
relay verifies it, then adds saved assumptions, base/provenance, a starting level,
computed median change, and source metadata. OpenAI turns this into prose.

The narrator's output cannot change the plotted points. A fluent explanation is
not an independent validation of the numerical model. The current instructions
also prevent it from inventing industry impact percentages or claiming to know
Chronos's causal reasoning.

Source metadata is not the original article text. No complete evidence-retrieval
service supplies all the economic mechanisms contemplated by the original plan.
Adding more expressive prose without adding relevant data or a sound model would
not fix the underlying product gap.

## 7. The important data bottleneck

The raw local SPY file contains hundreds of thousands of minute rows, but those
rows are not all supplied to every forecast. The pipeline extracts eligible daily
close proxies, freezes them before the fork, aligns CPI by publication, truncates
after missing closes, and caps contiguous context.

Read-only inspection during this analysis found:

| Snapshot | Pre-fork history actually built | CPI values present | Release-indicator sessions |
|---|---:|---|---:|
| `spy-99baca8c94f5871aff6b` | 20 sessions, May 13–June 10, 2025 | Only 0.2% | 1 |
| `spy-8c865e107520d2cdab66` | 114 sessions, Dec 24, 2024–June 10, 2025 | -0.1%, 0.2%, 0.3%, 0.4%, 0.5% | 5 |

The first snapshot was used for the live verification. Its CPI history is
constant, so it supplies no within-context examples of how different CPI readings
relate to later SPY behavior. The observed target history can still drive a real
time-series forecast. That is different from having demonstrated a market
response to changing inflation.

The expanded snapshot is a better starting point for examining covariate behavior,
but 114 repeated daily rows do not equal 114 independent inflation events. There
are only five release-indicator sessions inside that contiguous context. Its
additional earlier archives help standalone historical baselines, while the
missing December 23 close limits the current contiguous model context.

Do not casually fill missing closes or use post-cutoff observations to obtain a
longer history. Address context policy or model/data design explicitly.

No pre-release consensus series is currently provided. Consequently a CPI value
or change from the previous reading must not be described as a market “surprise”
relative to expectations. These are different quantities. Nor is there a full
set of yields, policy rates, oil prices, earnings, employment and other potential
drivers in the current numerical input.

## 8. Read-only examination of the saved live results

These numbers come from the preceding verification database, not estimates read
from screenshot pixels. They may differ from another timeline the user created.
No new inference was performed for this report.

**Provenance**

- SQLite: original backend's ignored
  `data/local/pr6-openai-live-1794114164263991000.sqlite`.
- Timeline: `timeline-f4f6144527c84f15b8d789b39d6ead58`.
- Dataset: `spy-99baca8c94f5871aff6b`.
- Model: pinned CPU Chronos-2 `cpu-cpi-v2` implementation.
- Observed June 10 starting level: approximately **143.7767**.
- Original scenario, revision 3: CPI **.4/.5/.5**.
- Revised scenario, revision 4: CPI **.2/.3/.3**.

| Saved run | End date | Forecast terminal index | Change from June 10 |
|---|---|---:|---:|
| First June .4% prompt, five-session run, revision 1 | June 17 | 142.1855 | -1.1067% |
| Three-prompt .4/.5/.5 scenario, revision 3 | August 18 | 141.9839 | -1.2469% |
| Three-prompt .2/.3/.3 scenario, revision 4 | August 18 | 141.9219 | -1.2900% |

For visual context, the actual August 18 index was approximately **153.3864**,
or **+6.6838%** from the same June 10 base. This is a factual-path comparison,
**not a counterfactual ground-truth accuracy score**: actual published CPI values
were .1% in June, .3% in July and .2% in August, unlike either complete scenario.

Across the 47 simulated sessions, revision 3 versus revision 4 had:

- Mean absolute difference between their median levels: **0.2211 index points**.
- Maximum absolute median difference: **0.7685 index points**.
- Difference in terminal levels: approximately **0.0619 index points**.

These observations establish that the saved numerical outputs changed. They do
not measure the causal effect of lowering CPI, and they do not by themselves prove
that the model uses CPI usefully. In particular, this was not a controlled
single-input sensitivity experiment, for the reason below.

### Replay/inference chunking is an additional confounder to investigate

Source inspection of `api/replay.py` shows two different construction paths:

- Adding a July event can retain June's initial five-session simulated path and
  forecast a bridge from its saved median state to July.
- Replacing June after all events exist can forecast the June-to-July segment
  again as one longer segment, then replay the later segments.

The model can therefore see different inference horizons and different lengths
of earlier simulated context, in addition to the changed CPI assumptions. The
before/after live comparison cannot isolate those effects from CPI sensitivity.

**This is a source-derived risk, not a new experimentally confirmed bug in this
analysis.** A small, controlled follow-up should check that equivalent canonical
scenarios constructed through different edit/add histories produce the intended
consistent numerical behavior. At minimum, compare scenarios under the same
segmentation, context and horizon before assigning meaning to their difference.
Do not claim the observed difference is a pure CPI response.

## 9. What the live test did and did not establish

| Established by the preceding task | Not established |
|---|---|
| Real OpenAI parser and description requests succeeded | Broad topic/value/date support |
| Real local Qwen fallback succeeded for a supported question | Reliable fallback for every possible wording |
| Real pinned CPU Chronos produced and replayed numeric forecasts | Useful learned CPI sensitivity |
| .4/.5/.5 changed to .2/.3/.3 with stable IDs | General economic reasoning or arbitrary scenarios |
| Numeric suffix changed and observed prefix was preserved | A causal effect of CPI on SPY |
| Narration remained separate from the forecast | Narrative truth as independent model validation |
| Clarification saved no revision | Complete semantic ambiguity handling |
| Reload and idempotent persistence worked | Universal path consistency across construction histories |
| Actual reveal stayed separate and its clipping bug was fixed | A leakage-free historical backtest or calibrated joint bands |

The API, persistence and replay work is useful infrastructure worth preserving.
The conclusion is a **product/modeling scope gap**, not that all work must be
discarded or that every plotted value was fake.

## 10. Why merely removing the whitelist is insufficient

Removing the .4/.2 membership checks would make continuous CPI assumptions
possible within the current numerical interface. It would not supply:

- A policy-rate, oil, employment, earnings, fiscal or geopolitical input series.
- A mapping from vague events to confirmed, measurable assumptions.
- Publication-time alignment and units for those new variables.
- Evidence that the chosen numerical model responds appropriately to them.
- A calibrated causal mechanism or independently observed counterfactual truth.

Likewise, asking OpenAI to produce all the prices from general prose would move
the numerical problem into a text generator without demonstrating a data-trained
market response. It may produce plausible stories and numbers, but that is not
enough for the stated data-based product.

The distinction to preserve is:

- **Hardcoded answers:** prepared stock returns or paths selected by prompt.
  This is not the intended quantitative product.
- **Explicit supported model inputs:** typed variables with units, coverage,
  transformations and validation. These are normal and necessary.
- **Learned relationships:** model behavior inferred from relevant training or
  conditioning data, then checked for usefulness. This needs evidence, not labels.
- **Scenario assumptions:** values/dates or transmission assumptions the user
  explicitly chooses. They should be visible and remain editable.

A bounded, parameterized model is a reasonable first product. A list of five
approved tuples is too narrow to fulfill the currently stated goal.

## 11. Recommended next product architecture

Preserve the durable timeline and separate narration/reveal design. Expand the
meaningful scenario pipeline between language understanding and inference:

```text
User scenario in ordinary language
        ↓
Language interpretation
  event family, variable, date/span, amount, unit, reference, ambiguity
        ↓
Scenario resolution and support assessment
  available data/model, baseline, publication timing, missing assumptions
        ↓
User-visible resolved assumptions or a specific clarification
        ↓
Canonical event log with parameterized numeric values
        ↓
Feature/scenario builder
  aligned historical features and explicit hypothetical future paths
        ↓
Numerical engine selected for this supported domain
        ↓
Conditional forecast + baseline + reproducible metrics + provenance
        ↓
Frontend chart
        ↓
Frontend forwards saved numbers to the server-side OpenAI narration relay
        ↓
Description grounded in verified metrics and supplied source passages

Actual-history reveal remains a separate optional comparison branch.
```

An input registry can specify each implemented variable's measure, units,
publication rules, coverage, operations, model mapping and extrapolation policy.
It should not specify a prepared market-price answer for each user value.

“We understood the event but lack a quantitative model/data path” should be
distinguishable from “the wording is ambiguous.” A qualitative explanation or
a request for a measurable policy assumption can be useful without pretending a
numeric engine supports that event.

### Examples of the intended distinction

| Prompt | Desired resolution |
|---|---|
| “June CPI is 0.35%” | Parse a numeric CPI value; validate scope/units; build that covariate scenario rather than search a value list |
| “Inflation rises 20%” | Clarify measure, monthly/annual basis, relative change and horizon before numerical acceptance |
| “The Fed cuts by 50 basis points” | Resolve a policy-rate change and timing; use actual rate data/model support, not the CPI column |
| “Oil doubles over three months” | Resolve the commodity/reference and path assumptions; assess model/data coverage |
| “A different president wins” | Ask which measurable policies or economic assumptions change; a name alone is not a numeric market feature |
| “Keep the previous reading” | Retain the relative expression and replay it against the edited chronological state |

These are design examples, not promises that those additional model paths already
exist or are automatically scientifically valid.

## 12. Prioritized next work, with stopping points

The user asked for analysis only in the current task. The stages below are proposed
future work, to start when the human chooses implementation scope.

### Stage 1: Replace prepared CPI cases with a continuous CPI scenario input

This is the shortest product step that directly addresses the complaint.

- Separate UI examples from domain eligibility. Keep useful presets as examples.
- Remove exact tuple membership as the definition of valid numeric CPI input in
  both the provider router and research service.
- Define explicit supported measures, dates, operations, units and numeric domain
  policy; initially retaining a bounded calendar is acceptable if stated clearly.
- Make `set`, relative `add_pp`, and `carry` parameterized rather than tied to one
  numeric amount or a fixed prompt slot.
- Retain ambiguous-value clarification, finite-number checks, provenance and
  no-future-target leakage rules.
- Make grounding compare normalized numeric meanings, not only literal strings.
- Ensure capabilities advertise actual implemented support. Do not silently
  expose a value the numerical adapter will reject later.
- Preserve template fallback, typed errors, stable IDs and replay semantics.

**Completion example:** a supported-date CPI scenario such as .25%, .35% or .6%
can be interpreted and sent as its actual numeric value to the model without adding
that number to a list of allowed cases. Equivalent wording resolves consistently.
These examples require an agreed range policy; they are not new accuracy claims.

**Stop condition:** ship the continuous CPI feature and its visible assumptions
once the focused path works. Do not delay it for extra animation or a large new
model-training project. Separately disclose that numerical usefulness remains
under investigation.

### Stage 2: Check numerical usefulness with a small controlled analysis

Avoid an endless testing loop, but answer the central modeling question once.

- Hold snapshot, cutoff, history, model weights, inference segmentation, dates,
  horizon and other covariates fixed.
- Vary a small set of CPI assumptions; record the exact model inputs and outputs.
- Compare against a same-setup reference scenario, not a different construction
  history or the unrelated actual future path.
- Compare a version without informative CPI/release covariates against the version
  that uses them, to see whether those inputs add measurable value.
- Prefer the richer eligible history where appropriate, while preserving the old
  dataset and saved timelines. Do not overwrite them to improve appearances.
- Check the replay/chunking concern above with equivalent event logs.
- Use a few factual historical release cases to compare against simple baselines
  on the same supported folds and horizons. Document pretrained-data limitations.

Do not require a predetermined sign such as “higher CPI must always lower stocks.”
A consistent-looking sign alone is not proof of skill. Do not force sensitivity
by adding an arbitrary manual stock-return multiplier.

**Decision:** retain Chronos as the scenario engine only if it shows useful behavior
for the selected product domain; otherwise adapt or replace the numerical model.
If CPI contributes little reliable information, report that result and move to a
better-specified data/model approach rather than hiding it with stronger prose.

### Stage 3: Add a small number of meaningful additional economic levers

Choose one or two concrete families after checking data availability, publication
timing and numerical modeling feasibility. For each new lever:

1. Define the exact measured variable and unit.
2. Obtain an eligible historical series and release/availability timestamps.
3. Define a user-visible baseline and how a scenario changes its future path.
4. Add typed canonical representation and model-facing features.
5. Verify the numerical engine supports those features and has useful behavior.
6. Add focused evidence/description support and one demonstration journey.

Do not create a new keyword-to-percentage lookup table. If a rate-cut scenario is
quantified, its market path must come from a disclosed learned/empirical model or
an explicitly labeled assumption, not a prose rule disguised as inference.

### Stage 4: Broaden the model/data domain deliberately

General dated scenarios need a parameterized historical cutoff, eligible history,
release calendars and target coverage. Current code fixes June 2025 in several
places. Parameterizing just the text parser is not enough.

Possible numerical approaches include keeping a foundation model where it proves
useful, fitting an economic/event-response model to suitable historical data,
or combining a statistical baseline with explicitly modeled response variables.
No single approach is selected by this report. A causal claim would require a
separately justified identification strategy; ordinary conditional prediction
does not acquire that property from adding more data or using an LLM.

Training from scratch is not automatically necessary. Relevant data, a justified
model boundary and a modest useful baseline matter more than choosing the most
complex model. Decide against a concrete product question before collecting
unbounded datasets or launching extensive experiments.

### Stage 5: Ground richer descriptions and comparisons

- Continue generating prose after numerical commit through the approved relay.
- Compute return differences, comparisons and quantified impacts outside the LLM.
- Supply actual source passages with publication/provenance, not merely URLs.
- Label proposed economic mechanisms as hypotheses unless supported more strongly.
- Distinguish a forecast from a measured causal contribution.
- Present a baseline and explain when a scenario lies outside reliable support.

Narrative quality should improve the user's understanding of the actual model,
not make weak numerical evidence sound stronger.

## 13. What should remain in place

Preserve the work that already supports a usable product:

- FastAPI route structure, canonical schema generation and typed clients.
- SQLite immutable revisions, request-ID retry behavior and draft binding.
- Stable prompt IDs and explicit relative operations.
- Atomic numerical commits and preservation of graph/draft on failure.
- Separation of observed history, simulated history and revealed actuals.
- Explicit units, session alignment and provenance.
- Server-side credentials and separate post-commit narration.
- The repaired actual-history chart range and its regression check.

Do not delete working code, reset branches, silently enable synthetic fallback,
or merge separate frontend work just to simplify the analysis. Broader scope
should build on these interfaces where they remain appropriate.

## 14. Current codebase/worktree handover

Verified local state when this report was prepared:

| Folder | HEAD | Purpose/state |
|---|---|---|
| `/Users/aashn/hackathon/TeamRelay-Hackathon` | `9723145`, branch `backend` | Original backend; clean before this new analysis document |
| `/Users/aashn/hackathon/TeamRelay-CPI-parser-check` | `d90c447`, detached | Clean isolated task source including the live parser fixes |
| `/private/tmp/teamrelay-frontend-integration` | `f272c22`, detached | Original complete UI with eight preserved local edits |
| `/private/tmp/teamrelay-pr6-ui-verify` | `f272c22`, detached | Complete UI plus updated patch and reveal-range fix; used for verification |

The preceding task pushed `d90c447` to `5-cpi-parser-frontend-patch` as a normal
fast-forward. PR [#6](https://github.com/aashnakulsh/TeamRelay-Hackathon/pull/6) was
last verified open, draft, based on `backend`, and unmerged. Recheck its current
state before acting; this report did not fetch or modify remote branches.

The original backend folder does **not** contain the complete React app or the
latest provider-parser implementation. Use the task checkout for the latter and
the correct complete UI worktree for frontend work.

Current listeners were observed on 8770 (test research backend) and 5175 (isolated
Vite UI). Processes and temporary folders are mutable. Do not kill an older server
or assume these paths will survive cleanup. Inspect before starting replacements.

### Important files and change points

Paths below are relative to the task checkout unless marked otherwise:

| File | Read/change purpose in future work |
|---|---|
| `api/provider_parser.py` | Bounded instructions, schema, grounding, whitelist, OpenAI/local routing |
| `shared/fixture_service.py` | PRESETS source; separate examples from real domain policy |
| `api/research_backend.py` | Second tuple whitelist, capabilities, first-fork restrictions |
| `api/contracts.py` | CPI-specific parsed/canonical and numerical types; generated source of truth |
| `api/durable_service.py` | Parser selection, domain validation, drafts and atomic commits |
| `api/replay.py` | Dependencies, prefix preservation, bridge construction and segment inference |
| `data/real_market.py` | Frozen cutoff, input range, contiguous history and supported release dates |
| `training/chronos_adapter.py` | Exact model inputs, prediction call, weights and output mapping |
| `training/baseline.py`, `training/evaluation.py` | Existing empirical comparisons and historical diagnostics |
| `api/descriptions.py` | Post-commit narration and trusted numerical context |
| `api/settings.py` | Model/provider selection and active timeouts |
| `tools/export_contracts.py` | Regenerate JSON Schema/OpenAPI/TypeScript after schema edits |
| `integration/frontend-research.patch` | Portable complete UI integration diff, targeting f272c22 |
| UI `src/api/mockApi.ts` | Synthetic path generator; do not confuse it with research inference |
| UI `src/features/workspace/useWorkspace.ts` | Submit/restore/description/reveal orchestration |
| UI `src/features/chart/Chart.tsx`, `geometry.ts` | Plotting, updated reveal range, animation |

The repaired frontend patch now includes a regression change to
`tests/web-ui.test.mjs`. It is already applied in the verification UI. The older
original UI matches the earlier patch, not the new reveal-range addition. Do not
blindly apply the full updated patch over either existing modified worktree.

## 15. API and model-call boundaries to preserve

| Endpoint/action | Responsibility |
|---|---|
| `GET /api/capabilities` | Tell the UI the actual supported domain, limits, units and coverage |
| `POST /api/timelines` | Create revision 0 with eligible observed context |
| `POST /api/timelines/{id}/interpret` | Text → canonical candidate or specific clarification/unsupported reason |
| `POST /api/timelines/{id}/commit` | Forecast affected segments and save one immutable revision |
| `GET /api/timelines/{id}` | Restore the full current saved run |
| `GET /api/timelines/{id}/revisions/{n}` | Inspect immutable prior run |
| `POST /api/timelines/{id}/revisions/{n}/description` | Frontend forwards raw saved segment; relay calls OpenAI; return separate prose |
| `GET /api/timelines/{id}/revisions/{n}/reveal` | Separate factual actual-history overlay |

The frontend must reconstruct suffixes using `applyRun` before forwarding a
complete prompt segment for narration. Match timeline/revision/run/prompt identity
before displaying asynchronous descriptions. Never merge narrated values into
the series or feed revealed actuals back into replay.

For future scope expansion, the interpretation stage can become richer while
commit/revision semantics remain stable. Existing `ParsedScenario`/`Instruction`
types are currently CPI-oriented: supporting new families may need a typed event
family/variable representation, rather than putting interest rates into a field
that downstream code still treats as CPI.

The configured real text model used in the preceding test was **gpt-5.6-sol**.
The earlier `gpt-6-sol` setting returned 404; the working model was overridden only
in the test process. This report has not inspected or changed the current secret
files. Check availability/settings privately if a later run is authorized.

The local parser model was already-installed **qwen3.5:9b**, with thinking disabled,
temperature 0 and a 512-token prediction cap. OpenAI parser and description output
budgets were 600 and 800 respectively; parser/local/narration timeouts were 5/12/20
seconds. The pinned CPU model was `amazon/chronos-2`, weights
`29ec3766d36d6f73f0696f85560a422f50e8498c`, package `chronos-forecasting==2.3.2`.

Keep keys server-side. Do not print, paste, stage or transmit local credential
files such as `.env.local` or the `openai_details` files. No such content is needed
to understand or implement the modeling changes described in this report.

## 16. Data/state needed by a new chat

Local assets are not transferred by giving another chat this Markdown file.

| Asset | Location/meaning |
|---|---|
| Original live snapshot | `data/local/processed/spy-99baca8c94f5871aff6b/` in original backend |
| Expanded snapshot | `data/local/processed/spy-8c865e107520d2cdab66/` |
| Actuals | Separate `data/local/reveal/<version>/spy_actuals.parquet` |
| Verification database | `data/local/pr6-openai-live-1794114164263991000.sqlite` |
| Verification receipt | `data/local/results/pr6-live-verification-receipt.json` |
| Cached Chronos weights | Existing Hugging Face cache on the Mac; not tracked |
| Python environment | Original backend `.venv`, reused by the isolated task checkout |
| Node used for recent checks | `/private/tmp/node-v24.11.0-darwin-arm64/bin`, if still present |

The IDE's open `forecast.json` may reflect an older standalone run/model identity.
This report's numeric comparison came from the saved live `cpu-cpi-v2` revisions,
not an assumption that every old result JSON matches current code. Do not overwrite
old results or follow `latest.txt` implicitly to make comparisons appear consistent.

Neither switching to the expanded dataset nor reading all local raw prices solves
the general-modeling problem automatically. Dataset/model/corpus changes also
affect old timeline write compatibility. Preserve prior timelines and pin the
configuration for any controlled comparison.

## 17. Suggested next-chat workflow

1. Read [AGENTS.md](../AGENTS.md), this report, and the prior handovers below.
2. Inspect Git status/worktrees, running servers and what source each server uses.
3. Preserve all local changes; do not merge or reset the task branch automatically.
4. Confirm the human's chosen product scope: continuous CPI first, or a specified
   broader set of supported economic variables with an explicit data/model plan.
5. Keep analysis separate from implementation until the human requests coding.
6. When authorized, implement a small complete vertical slice, then run the
   focused checks and one product journey that can actually falsify its claims.
7. Record scope, assumptions, model inputs and limitations alongside the result.
8. Do not repeat unchanged suites or costly model experiments without a new reason.
9. Commit/push only when that workflow is authorized for the new task. The prior
   authorization for the verified PR #6 fix does not authorize publishing this
   analysis or starting unrelated product changes.

Useful read-only starting commands:

```sh
cd /Users/aashn/hackathon/TeamRelay-Hackathon
git status --short --branch
git worktree list
bash tools/board inbox
git -C /Users/aashn/hackathon/TeamRelay-CPI-parser-check status --short --branch
git -C /Users/aashn/hackathon/TeamRelay-CPI-parser-check log -1 --oneline
git -C /private/tmp/teamrelay-frontend-integration status --short --branch
git -C /private/tmp/teamrelay-pr6-ui-verify status --short --branch
lsof -nP -iTCP:8770 -iTCP:5175 -sTCP:LISTEN
```

The same three old inbox notices were present during this analysis. They remain
coordination data and were not acted on or acknowledged. The user explicitly
chose this analysis, so do not restart older board tasks from those notices.

### Prompt to continue analysis in a new chat

> I am Aashna. Read docs/model-scope-analysis-handover.md and AGENTS.md in
> /Users/aashn/hackathon/TeamRelay-Hackathon. Our goal is a data-based economic
> scenario product, not five hardcoded CPI cases. The current research path uses
> real OpenAI/Qwen interpretation, real Chronos inference and separate narration,
> but its input domain is whitelisted and its live CPI context is weak. Preserve
> all worktrees and existing data. Inspect the task checkout at d90c447 as well as
> the original backend; they differ. Explain the smallest meaningful product and
> modeling change to pursue next, including how we would establish useful input
> sensitivity without fabricating market responses. Do not change application
> code, run paid calls, commit, push, merge or deploy unless I ask you to proceed.

If the human later explicitly authorizes implementation, the recommended first
slice is continuous validated CPI input with honest scope labels, followed by a
small controlled assessment of its numerical behavior. Broader levers need their
own data/features/model support, not just a more permissive LLM prompt.

## 18. Supporting references and evidence status

- [Detailed OpenAI/frontend handover](aditya-openai-frontend-handover.md): broad
  architecture, API contract details, worktree and environment background. Its
  earlier snapshot predates the live parser verification; do not repeat its
  “parser not implemented” statements as current task-branch facts.
- [Real-data guide](real-data-adapter.md): snapshots, calendar/unit/provenance and
  local research behavior. Read the version in the chosen worktree.
- [Frontend/backend contract](frontend-backend-contract.md): immutable runs,
  full/suffix application and separate narration/reveal.
- [PR #6 live-verification report at the verified commit](https://github.com/aashnakulsh/TeamRelay-Hackathon/blob/d90c4478ef4e93789b8714627e13bbadb5638673/docs/pr6-live-verification.md):
  the preceding real-provider/browser test, its fixes and scope.
- [Parser source at that commit](https://github.com/aashnakulsh/TeamRelay-Hackathon/blob/d90c4478ef4e93789b8714627e13bbadb5638673/api/provider_parser.py):
  direct evidence of the five-case language policy and parser checks.
- [Pinned Chronos-2 model card](https://huggingface.co/amazon/chronos-2/blob/29ec3766d36d6f73f0696f85560a422f50e8498c/README.md):
  publisher's description of pretrained numeric/covariate forecasting capability.
- [Official Chronos repository](https://github.com/amazon-science/chronos-forecasting):
  primary implementation documentation. General model benchmarks are not a
  validation of TeamRelay's CPI/SPY setup.

Claims about the whitelist, frames, replay and narrator come from local source
inspection. Claims about successful live calls and UI behavior come from the
preceding verification and its report. Counts and numeric comparisons in this
document were calculated read-only from the saved snapshot/database. The replay
chunking concern and proposed architecture are explicitly analysis/recommendations,
not newly completed experiments or implemented features.
