# Kairos — HackTheBurgh XIII architecture

<<<<<<< HEAD
**Team implementation agreement · 7 November 2026 · one submission.** A visitor writes a dated “what if”, watches a US equity forecast draw across a timeline, and clicks an earlier prompt to change the subsequent story. The frontend lets a journey hold up to `MAX_PROMPTS` dependent prompts (currently **7**); the real backend accepts **3**, and the shared acceptance example uses three. A usable release has one US market proxy, one measured economic input, an editable timeline, and a forecast that a judge can compare with an actual historical outcome.
=======
**Team implementation agreement · 7 November 2026 · one submission.** A visitor writes a dated “what if”, watches a US equity forecast draw across a timeline, and clicks an earlier prompt to change the subsequent story. A timeline holds up to `MAX_PROMPTS` dependent prompts (currently **7**, the longest journey the start screen allows); the shared acceptance example uses three. A usable release has one US market proxy, one measured economic input, an editable timeline, and a forecast that a judge can compare with an actual historical outcome.
>>>>>>> origin/demo/teamrelay-final

| If you are implementing… | Start here | Coordinate with |
|---|---|---|
| Layout, composer, markers, animation or settings | §2, §3 and §5 | Chohan and Orion |
| Branch state, endpoints, LLM providers or deployment | §3–§6 | Aashna |
| Prices, releases, Chronos-2, evidence or evaluation | §4, §6 and §7 | Aditya and Aashna |
| Integration, judging or release | §1, §8 and §9 | All four |

## Implemented backend (8 November update)

This section records what the `backend` branch actually runs. Where it disagrees with the planning text in §3–§8, this section and the linked handovers win. Details: [general-scenario-handover.md](general-scenario-handover.md) (current product), [continuous-cpi-demo-handover.md](continuous-cpi-demo-handover.md) (CPI research mode), [real-data-adapter.md](real-data-adapter.md) (data audit and evaluation), [frontend-backend-contract.md](frontend-backend-contract.md) (wire fields).

**One FastAPI app, three modes** (`APP_MODE`, read by `api/settings.py`; `uvicorn api.app:create_app --factory`). Every mode shares the same durable SQLite revision store, drafts, idempotent commits and HTTP routes (`api/durable_service.py`).

| Mode | Prompt input | Numbers | Use |
|---|---|---|---|
| `scenario` (current product) | Any ordinary-language event with a date. There is no list of allowed events, people or countries. | Pinned Chronos-2 conditioned on measured covariates (Fed funds rate, WTI oil, VIX and monthly CPI where available) | Demo. Launch with `tools/serve_scenarios.py` (port 8772). |
| `research` | Monthly headline CPI at the June 11, July 15 or August 12, 2025 releases, any value from −2% to 2%, as `set`, `add_pp` or `carry` | Chronos-2 with CPI and release-indicator covariates | Bounded CPI demo. Launch with `tools/serve_research.py` (port 8771). |
| `fixture` (default) | Deterministic presets | `SyntheticAdapter` arithmetic, labelled synthetic | Frontend development and tests. `api/fixture_app.py` stays synthetic. |

**Scenario pipeline.**

1. **Interpret.** `POST /interpret` makes two server-side OpenAI Responses calls with strict JSON schemas (`api/scenario_research.py`):
   - Call 1 always uses web search. It extracts the event, date and horizon (20 sessions by default, at most 65), a hypothesis, cited sources, and up to five earlier comparable events.
   - The backend then measures each comparable event's market window from local SPY/FRED data, ending before the frozen cutoff (`data/scenario_market.py`). It may also fetch up to two small daily GDELT archives (`data/scenario_events.py`).
   - Call 2 turns the research into numerical driver paths over the available features only. Each driver has a feature, an operation (`set`, `add` or `multiply`), a value, transition/duration/recovery sessions, a `basis` (`user_assumption`, `historical_analogue` or `llm_hypothesis`) and citations.
   - Python validates the result: features exist, one driver per feature, citations were actually returned by the search tool, and an analogue claim has a measured window behind it.
   - The validated plan is cached under `data/local/cache/scenario-research/`.
2. **Commit.** `POST /commit` makes no LLM call (`api/scenario_backend.py`). Chronos forecasts two paths in five-session blocks, each feeding its own medians forward:
   - the scenario path, with the planned covariate paths;
   - a baseline path, with covariates held at their last observed values.

   The response carries `series`, `baseline`, `scenario_warnings`, panels (plan explanation, pre-cutoff evidence, baseline comparison, engine) and the saved plan inside `instruction.scenario`.
3. **Describe.** After the chart is installed, the frontend forwards the selected prompt's complete, unrounded simulated segment to `POST /api/timelines/{id}/revisions/{revision}/description`. The relay (`api/descriptions.py`) checks those numbers against the saved revision, calls OpenAI once, and returns plain prose. Prose never changes chart numbers. The UI ignores a description whose timeline, revision, run or prompt no longer matches. If narration fails, the existing panel text stays.
4. **Reveal.** Actual SPY levels for the simulated dates come from the same local market frame. They are never fed to inference, and missing sessions stay gaps.

**No model was trained or fine-tuned.** Every model runs with fixed pretrained weights: Chronos-2 for numbers, and an OpenAI model (verified with `gpt-5.6-sol`) for research, planning and narration. In CPI research mode, local Ollama `qwen3.5:9b` is the parser fallback. The "model" work is data preparation, covariate conditioning, validation, empirical baselines and evaluation (§4, §7).

**Not implemented in the backend.** These remain frontend-only or future work:
- delete-prompt and journey-summary endpoints;
- the FTS5 evidence store;
- curated impact rows (`impacts` is always empty);
- Ollama fallback in scenario mode;
- automatic empirical-baseline fallback over HTTP;
- any data before March 7, 2022.

## Implemented frontend (8 November update)

The UI lives on the `frontend` branch (`web/`) and is **not yet merged** with `backend`; the `backend` branch's `web/` holds only the typed client, `applyRun.ts` and generated contracts. §2 describes the UI as built. Stack: React 19, TypeScript, Vite and `plotly.js-dist-min`, with the bundled VT323 pixel font. Run it with `cd web && npm install && npm run dev` (port 5173).

**Game flow.** Start screen → voyage (one prompt per leg) → end screen. The pirate-ship pixel sea (`PixelSea.tsx`) replaces the planned gradient background. Prompts appear as marker buttons on the Plotly chart (`features/chart/`). Their notes are pixel scrolls (`Panels.tsx`), and the journey's captain's log is `EndScreen.tsx`. State and API calls live in `useWorkspace.ts`.

**Which API it talks to.** By default the browser uses an in-browser mock (`web/src/api/mockApi.ts`). The mock guesses dates from the text, draws a labelled synthetic 1980–2026 path, and simulates delete and summary. Setting `VITE_API=server` switches to the HTTP client (`web/src/api/client.ts`), proxied by Vite from `/api` to `http://127.0.0.1:8000`.

**Gaps against the real backend.** Each of these must be closed during the merge:

| Area | Frontend branch | Backend branch |
|---|---|---|
| Prompt limit | `MAX_PROMPTS = 7` in `web/src/config.ts`; the start screen offers 1–7 legs. | `max_prompts: 3`; the 4th add returns `prompt_limit`. The UI does not read `capabilities.max_prompts`. |
| Years | Examples and "How to play" say 1980–2026. The viewport is taken from `capabilities.default_viewport`. | Data from March 7, 2022. Earlier dates return `data_coverage`. |
| Delete and summary | `deletePrompt` and `summary` calls with hand-written types; the × button and end screen depend on them. | No routes. Against the server, × and the captain's log fail. |
| Description relay | Not called. The client has no `describe`, so notes show only panel text. | `POST …/description` is implemented. |
| Scenario fields | Generated `contracts.ts` predates them. `baseline` and `scenario_warnings` are not drawn, and `operation/unit: "scenario"` are not typed. | Returned on every scenario commit. |
| Dev proxy | `vite.config.ts` hard-codes `127.0.0.1:8000`, so `BACKEND_URL` is ignored. | Scenario server on 8772, research on 8771, fixture on 8000. |
| Chart scale | `SEA_LEVEL = 2000` in `Chart.tsx`, and the y-axis maximum is at least 2500. This suits the mock path, which compounds from 100 in 1980 into the thousands. | Real SPY is indexed to 100 on 2022-03-07 and stays around 100–150, so the line would sit squashed under the sea surface. The sea level must follow the data range. |

## 1. Boundaries and ownership

Use one React/TypeScript/Vite frontend with Plotly.js, one Python FastAPI backend, one local SQLite database (revisions, drafts and commits; the planned FTS5 search was not built), and hashed, versioned Parquet snapshots under `data/local/processed/`. The browser sends commands and displays results. The backend owns dates, prompt meaning, timeline ordering, forecast numbers, evidence and numerical attribution. Package the frontend and backend together for judging. The repo and issue below identify the team's coordination point.

| Person and tool | Ownership for this build | Handoff |
|---|---|---|
| **Aashna** · `aashnakulsh` · Codex | Team lead. Own `api/` routes, replay coordinator, SQLite revisions, provider adapters, shared config, integration and PR review. Coordinate data/model choices with Aditya. | Publish the wire contract and one synthetic response first. Integrate all four workstreams and own sign-off. |
| **Aditya** · `ADI-GHH` · Codex | Own `data/` and `training/`. Build the source manifest, session calendar, dated evidence, Chronos-2 adapter, comparable-event baseline and evaluation. Own the model-facing part of `api/` with Aashna. | Return a versioned forecast result, an unsupported result, and a fixture with a known answer for the edit demonstration. |
| **Chohan** · `yimchohan` · Codex | Own the `web/` chart, timeline ticks, markers, interval shading, settings, playback and partial redraw. | Consume the run response and emit a selected prompt ID or playhead date. Coordinate the CSS/layout boundary with Orion. |
| **Orion** · `wthoreo` · Claude Code CLI | Own the `web/` screen shell, composer, selection/edit state, translucent narrative, impact list, background and responsive layout. | Wire commands and errors to Aashna's API and pass committed chart state to Chohan. |

This is the proposed split inside the flexible focus areas supplied by the team. Keep each person's optional sandbox under `practice/<GitHub login>/` with the exact casing above. Use shared paths for integrated code. Aashna owns changes to the shared response shape. [Team repository](https://github.com/aashnakulsh/TeamRelay-Hackathon) · [Team message board, issue #1](https://github.com/aashnakulsh/TeamRelay-Hackathon/issues/1)

As implemented (scenario mode; research mode swaps the researcher for the CPI parser router):

```mermaid
flowchart TD
    UI["Browser · prompt, timeline and chart"] -->|interpret| RES["ScenarioResearcher · 2 OpenAI calls"]
    RES -->|"call 1 + web search"| OPEN["OpenAI Responses API"]
    RES -->|"measure analogue windows"| DATA["Local data · SPY IEX, FRED DFF/WTI/VIX, BLS CPI, GDELT"]
    RES -->|"call 2 · driver paths"| OPEN
    RES --> DB["SQLite · drafts, revisions, idempotent commits"]
    UI -->|commit| REPLAY["ScenarioBackend · replay + baseline"]
    REPLAY --> FORECAST["Chronos-2 · pinned, offline CPU"]
    DATA --> FORECAST
    REPLAY --> DB
    UI -->|"description · saved points"| RELAY["Description relay"]
    RELAY --> OPEN
    UI -->|reveal| DATA
    CPI["Research mode · CPI parser router"] --> OPEN
    CPI --> LOCAL["Local Qwen via Ollama · fallback"]
```

## 2. Frontend behavior

This table describes the UI as built on the `frontend` branch, running against its in-browser mock. Behaviour the real backend does not yet support (prompts 4–7, dates before 2022, delete, the end-screen summary) is listed under "Implemented frontend" above.

| Surface or action | Required behavior |
|---|---|
| Game flow | The app is a voyage game: **start screen → voyage (one prompt per leg) → end screen**. Each prompt is one leg of the journey. |
| Start screen | A zoomed-in, animated pixel scene of the pirate ship moored at the departure dock (black before it draws). Center one long, keyboard-focused prompt input horizontally, over the water below the ship. Give it an accessible label and a rotating situational example placeholder (see Free-text prompts). Beside it, a **required** “Prompts” picker (1 to `MAX_PROMPTS` = 7) sets the journey length, and the button reads **“Start journey”**; it stays disabled until text and a length are chosen. Enter submits, Shift+Enter adds a line, and Tab in the empty box fills in the shown example (with text present, Tab moves focus as usual). The game title “Kairos” sits large in yellow pixel lettering at the top of the start screen and in the voyage header. **Fonts and buttons:** decorative, low-stakes text (titles, labels, hints, notices, buttons, scrolls) uses the pixel font; chart numbers and details and typed prompt text keep the sans font, while the year boxes and the prompt-count picker (including its opened list where the browser allows styling it) use the pixel font. Primary buttons (“Start journey”, “Continue journey”, “Reveal/Hide actual history”) are the title yellow with brown text. **Text boxes:** solid boxes (the composer, notices, year and prompt-count inputs, marker tooltips and the chart hover box) are solid brown (`#4a2a10`) with yellow text. Translucent boxes (voyage chip, data label, legend, Start/End year boxes, impact rows, quiet buttons) are translucent brown with yellow text. Placeholders are a softer yellow at 14 px, and the start-screen composer is wide enough (up to 1040 px) for every example to fit on one line. The label uses the pixel font. A **“How to play”** button (top right, title yellow with brown text) opens a modal pixel-scroll pop-up. It explains: choose 1–7 prompts; ask “what if” a historical or made-up event happened between 1980 and 2026; name a historical event and the backend finds its date; include the year for a made-up event; gains bring sun and losses bring storms; that a short note appears for each prompt and clicking it unrolls the full description; how to replace or delete a prompt; Tab to use the example; and that the voyage ends with the captain's log. It is a native `<dialog>`: focus is trapped, and Escape, “Got it” or a click outside closes it. |
<<<<<<< HEAD
| End screen | **Never forced.** Once the active prompts reach the chosen length, an **“End journey”** button (title yellow, brown text) appears pinned to the screen's bottom-right corner. The player may keep replacing or deleting prompts first. Pressing it switches to a zoomed-in pixel scene of the ship at the finishing dock. Its weather follows the whole voyage's net change. On the left, a giant pixel scroll shows the journey summary (§5 `summary`, currently served only by the mock): headline, net result, narrative and each leg's gain/loss. Focus moves to its heading. “Sail again” starts a new journey on a fresh timeline; “Review the chart” returns to the voyage view, where “End journey” reopens the scroll. Deleting a prompt hides “End journey” until the length is reached again. |
=======
| End screen | **Never forced.** Once the active prompts reach the chosen length, an **“End journey”** button (title yellow, brown text) appears pinned to the screen's bottom-right corner. The player may keep replacing or deleting prompts first. Pressing it switches to a zoomed-in pixel scene of the ship at the finishing dock. Its weather follows the whole voyage's net change. On the left, a giant pixel scroll shows the backend's journey summary (§5 `summary`): headline, net result, narrative and each leg's gain/loss. Focus moves to its heading. “Sail again” starts a new journey on a fresh timeline; “Review the chart” returns to the voyage view, where “End journey” reopens the scroll. Deleting a prompt hides “End journey” until the length is reached again. |
>>>>>>> origin/demo/teamrelay-final
| First submission | Transition to the workspace immediately. Preserve the submitted text while the API responds. Center the same composer near **80% of viewport height** on desktop. Top to bottom: graph and narrative overlay, timeline scale, composer, impact list. A narrow or short screen uses normal vertical flow with scrolling and keeps the list below the composer. |
| Timeline and settings | Begin with a **1980–2026** overview. A **“Start year”** box under the graph's bottom-left end and an **“End year”** box under its bottom-right end change the visible years. The year scale and chart share one time domain, and a range change pans/zooms the viewport. There is no time slider or playhead. The chart's hover box (dotted guide line plus values) shows full series names and values to two decimals; Plotly is given a concrete font so it sizes the box to fit. |
| Years, lines and intervals | Grey the specified year, or every included year for an interval, as a thin strip along the plot's bottom edge (there is no separate year row; the chart's own axis labels the years). For a single event draw one **pink** (`#f472b6`, 1.5 px) vertical dashed line through the chart with `Prompt (x+1)`,where x stands for the 0th indexed and the xth number of prompt, at its top. For an interval draw dashed start/end boundaries and a subtle grey band with one label anchored at the start. Preserve the semantic year even when the trading session is shifted. Every prompt line looks identical, selected or not; selection shows on its label instead. Each marker's label is a button, title yellow with brown text and a brown ring when selected. Supply an accessible button for each marker, stack overlapping labels, and include the full date/span in its tooltip. |
| Graph | Render backend-supplied observed history through the fork, followed by a visually distinct **simulated median** and shaded range. Label the target, units, observed/simulated boundary, and model used: these chart details sit in a small vertical legend (translucent brown, yellow text) pinned to the bottom-left corner of the screen (in flow under the chart below 1200 px wide). The 10–90% range is shaded pink for contrast with the blue median and the sea. On explicit reveal, overlay the actual subsequent path in a third style. Keep the reveal response out of forecasting inputs. |
| Animation | On the first successful run, animate the full visible available line left-to-right. On an add or replacement, retain all cached points strictly before `changed_from` and animate only the replacement suffix. Use the server's point order and existing points for the drawing effect. Keep the same y-axis during the animation, cancel older animations on a new revision, and allow skip/reduced motion. Planning defaults are 1.2 s for a full draw and 0.7 s for an edit. [Plotly animation reference](https://plotly.com/javascript/animations/) |
<<<<<<< HEAD
| Free-text prompts | The composer accepts any wording; the user may name any day, month, year or year range inside the sentence. Placeholder examples are **situational** (everyday events, no jargon or figures), e.g. “What if the U.S. bombed Iran in 2015?” or “What if the 2001 IMF crisis didn't happen?”. Ten are kept in `web/src/features/workspace/examples.ts` and swapped at random every 5 s while the box is empty. Wording with some figures (“6% inflation”) is intermediate; acronyms plus figures (“Set June 11 CPI to 0.4%”) is technical. All three must work. The browser sends the raw text only. On the server, scenario mode's two-call OpenAI research step turns it into a dated driver plan (there is no Qwen fallback in that mode). Research mode instead uses the CPI parser with a Qwen fallback, and accepts only the three 2025 release dates. **Dates:** the UI says events must fall between 1980 and 2026, but the real backend's data starts March 7, 2022. For a **historical event** named without a date (“What if Lehman Brothers had been rescued?”), the backend determines when it occurred from its own knowledge and evidence, and returns `needs_clarification` only if that is ambiguous. A **hypothetical event** must state its year; if it doesn't, return `needs_clarification` asking for one. The frontend does not resolve historical dates. Without `VITE_API=server`, the in-browser mock (`web/src/api/mockApi.ts`) guesses the dates and draws a labeled synthetic 1980–2026 path. |
| Selecting and replacing | Clicking a marker (or its note) selects its stable prompt ID, scrolls the composer into view, focuses/highlights it, loads the old text and labels the action “Replace prompt n”, where n is the prompt number. Submitting replaces that active prompt. Cancel/Escape, or a click on empty space that is not a button, link, input or the composer, returns to “Continue journey” and clears the selection. Keep unsent text on a failure; change the graph only on a successful commit. A keyboard user can perform the same sequence. |
| Deleting a prompt | Hovering a marker label, or focusing it from the keyboard, shows a small × at the label's top-right; on touch screens the × shows on the selected marker. Pressing × deletes that prompt through the delete endpoint (§5). Only the mock implements that endpoint so far. The other prompts keep their IDs and numbers. A new prompt takes the **lowest free number** (delete prompt 1 and the next prompt is prompt 1 again, with a new unique ID), and the composer label shows that number. The graph changes only on success and redraws from the deleted prompt's effective start. Deleting the selected prompt also clears the selection. |
| Prompt limit | `MAX_PROMPTS` (currently **7**) caps the journey length and the active prompts per timeline. The backend reports its own limit as `capabilities.max_prompts`, currently 3; the UI does not read it yet. The chosen length is the per-journey cap. At the cap, “Continue journey” explains that a prompt must be deleted or replaced, keeps the text and makes no API call. Replacing stays available. The composer label shows “prompt k of n”. |
=======
| Free-text prompts | The composer accepts any wording; the user may name any day, month, year or year range inside the sentence. Placeholder examples are **situational** (everyday events, no jargon or figures), e.g. “What if the U.S. bombed Iran in 2015?” or “What if the 2001 IMF crisis didn't happen?”. Ten are kept in `web/src/features/workspace/examples.ts` and swapped at random every 5 s while the box is empty. Wording with some figures (“6% inflation”) is intermediate; acronyms plus figures (“Set June 11 CPI to 0.4%”) is technical. All three must work. The browser sends the raw text only. The server-side OpenAI parser (Qwen fallback) translates it into the canonical instruction, including the dates. **Dates:** events must fall between 1980 and 2026. For a **historical event** named without a date (“What if Lehman Brothers had been rescued?”), the backend determines when it occurred from its own knowledge and evidence, and returns `needs_clarification` only if that is ambiguous. A **hypothetical event** must state its year; if it doesn't, return `needs_clarification` asking for one. The frontend does not resolve historical dates. Until that parser exists, a temporary in-browser mock (`web/src/api/mockApi.ts`) guesses dates and draws a labeled synthetic 1980–2026 path. |
| Selecting and replacing | Clicking a marker (or its note) selects its stable prompt ID, scrolls the composer into view, focuses/highlights it, loads the old text and labels the action “Replace prompt n”, where n is the prompt number. Submitting replaces that active prompt. Cancel/Escape, or a click on empty space that is not a button, link, input or the composer, returns to “Continue journey” and clears the selection. Keep unsent text on a failure; change the graph only on a successful commit. A keyboard user can perform the same sequence. |
| Deleting a prompt | Hovering a marker label, or focusing it from the keyboard, shows a small × at the label's top-right; on touch screens the × shows on the selected marker. Pressing × deletes that prompt through the delete endpoint (§5). The other prompts keep their IDs and numbers. A new prompt takes the **lowest free number** (delete prompt 1 and the next prompt is prompt 1 again, with a new unique ID), and the composer label shows that number. The graph changes only on success and redraws from the deleted prompt's effective start. Deleting the selected prompt also clears the selection. |
| Prompt limit | `MAX_PROMPTS` (currently **7**) caps the journey length and the active prompts per timeline; the backend reports it as `capabilities.max_prompts`. The chosen length is the per-journey cap. At the cap, “Continue journey” explains that a prompt must be deleted or replaced, keeps the text and makes no API call. Replacing stays available. The composer label shows “prompt k of n”. |
>>>>>>> origin/demo/teamrelay-final
| No repeated prompts | The browser keeps a record of every prompt submitted on the current journey, including ones later replaced or deleted. It is saved locally and cleared by “Sail again”. A prompt matching one in the record, ignoring case, spacing and trailing punctuation, is refused before any API call, with the text kept. Used examples drop out of the Tab suggestions. The backend may enforce the same rule. |
| Description notes | Styled as **pixel scrolls**: dithered parchment, a hard 4 px notched border, stepped wooden rods top and bottom, dark-brown ink in the bundled pixel font VT323 (`@fontsource/vt323`, OFL, works offline), centered lowercase title (“prompt n”) and a typed divider line (`=-=-`, `·x·x`, `.....`, `._.~`). **No prompt selected:** a centered row of small notes, one per prompt in timeline order, slightly tilted and overlapping, each with the prompt text, date and gain/loss; clicking a note selects that prompt. **A prompt selected:** one wide note centered above the graph with the market summary, direct and indirect markets/products, the resolved scope, and a labeled political-economic hypothesis with clickable dated sources. Notes sit in normal flow above the graph; the graph takes only the remaining height, so notes never cover markers, the plot or the composer. On mobile the row scrolls sideways inside itself. |
| Impact list | Directly **below the composer**, display 3–5 ranked bullets of the most affected industries when supported. Format signed quantified rows like `✈️ Airlines +1.2%`, with measure, reference and horizon visible in text or an accessible detail. Show fewer verified entries where necessary. Use a qualitative label for an exposure that has no defensible value. See §6. |
| Background | Workspace background is a pixel-art sea voyage (`web/src/features/workspace/PixelSea.tsx`) with a pirate ship. **Weather:** compare the shown prompt's forecast segment (selected, else last changed) terminal median with the level entering it. Any net gain is sunny; any net loss is stormy, with rain, a darker sky, spray and taller swells that roll slowly and smoothly: amplitude up to ~7×, speed down to 0.5×, the short choppy ripple faded out and a gentle ship roll, so storms swell rather than vibrate. Bigger moves give stronger weather. Flat or unknown is calm. **Voyage:** each prompt is one leg; the ship sails from the left dock toward the right dock as prompts are added (`prompts / chosen length`). **Sea level and ship size:** the water surface sits exactly on the chart's y = 2000 line (`SEA_LEVEL` in `Chart.tsx`, published as `data-sea-y`). The ship is scaled so its mast tip meets the y-axis maximum (the plot's top edge, `data-top-y`), and it floats on the water. The chart keeps its size; only its y scale adjusts, and the y-axis maximum is always at least 1.25 × `SEA_LEVEL` (2500), so the sea line and the ship always fit on the plot. The header shows “Voyage k / n · Sunny/Stormy/Calm”, and the scrolls keep a textual gain/loss and sign. Lightning flashes are capped at 25% white. Reduced motion draws a static frame with no lightning. A team-supplied local GIF can still replace the scene (`VITE_BACKGROUND_ASSET`). The start and end screens use the same scene, zoomed in on the docks. |
| Loading or unsupported | Keep the last committed graph visible and show a small pending state for the new request. For the very first prompt, show an empty graph frame and progress or a clarification. Explain a coverage gap, ambiguous prompt or unsupported intervention in place. Never animate invented history or a previously rejected edit. |

## 3. Timeline and replay rules

<<<<<<< HEAD
**Identity.** Each committed prompt has a stable `id` and a `display_number`. The number is permanent on the backend. In the frontend mock it is the lowest number free when the prompt was created, kept until the prompt is deleted. Each prompt also has its original text, date/span, canonical operation, units, evidence IDs and creation order. Every accepted write creates an immutable revision and atomically updates the active timeline. Replacing a prompt removes its old version from the active view. Its old version remains in the previous revision for comparison. Marker IDs/numbers survive date reordering.
=======
**Identity.** Each committed prompt has a stable `id`, a `display_number` (the lowest number free when it was created; kept until the prompt is deleted), original text, date/span, canonical operation, units, evidence IDs and creation order. Every accepted write creates an immutable revision and atomically updates the active timeline. Replacing a prompt removes its old version from the active view. Its old version remains in the previous revision for comparison. Marker IDs/numbers survive date reordering.
>>>>>>> origin/demo/teamrelay-final

**Dates and units.** Keep original requested dates, resolved trading sessions and timezone separately. US equities use America/New_York and the selected exchange calendar. Interpret a bare year as January 1–December 31 for lookup/highlighting. A single-year prompt produces one marker at the first relevant event/session, with the year grey. An explicit multi-date or multi-year interval includes both ends and uses two markers. A CPI reading applies on a release date. If a year/interval contains several eligible releases, require a choice of one release or an explicit recurring rule. If no date is given, offer the playhead or selected prompt date for confirmation. Resolve an after-close or non-trading effective instant to the next eligible session. Reject reversed dates and explain any span outside coverage.

**Order.** Execute by effective instant, then permanent creation order. Each operation has a typed meaning: `set` replaces an absolute value, `add_pp` applies a percentage-point delta to the value entering that step, and `carry` preserves it. Save relative instructions as relative expressions. Example: `0.4% + 0.1 percentage points = 0.5%`. For overlapping intervals on the same lever, the later-starting active instruction wins, with creation order breaking equal starts. Resolve the value of a delta once at activation. At an interval's expiry, resume the underlying still-active rule or the last persistent setting. Apply a repeated change only at explicitly specified releases. A point release updates the published scenario reading until the next applicable release. Tell the user which scope a draft will apply.

**Dirty boundary and atomicity.**

<<<<<<< HEAD
1. Adding a prompt sets `changed_from` to its effective start. Deleting a prompt (frontend mock only) sets it to the deleted prompt's effective start. Replacing in place keeps the same start. If the edit moves dates, use the **earliest of the old and new starts**. This removes obsolete effects when an event moves later. Changing an interval end uses the same conservative start rule.
=======
1. Adding a prompt sets `changed_from` to its effective start. Deleting a prompt sets it to the deleted prompt's effective start. Replacing in place keeps the same start. If the edit moves dates, use the **earliest of the old and new starts**. This removes obsolete effects when an event moves later. Changing an interval end uses the same conservative start rule.
>>>>>>> origin/demo/teamrelay-final
2. Retain every other prompt's text and ID. Restore the checkpoint strictly before the dirty boundary, including any still-active intervals and earlier simulated market state. Re-evaluate the affected instructions in time order. Earlier points and checkpoint values must compare exactly with the previous revision. A fixed instruction keeps its value; its market consequences may change with the inherited market state.
3. Later prompts become visible to the predictor only at their own activation point. Use observed data before the first fork and the scenario state after it. Preserve the original frozen evidence cutoff across downstream replay. A legally available future observation belongs to the reveal/score path.
4. A reference to a specific prompt that has moved into the future requires clarification. A reference to “the preceding reading” resolves against the updated chronological order. When an edit moves the first fork, rebuild from the common observed prefix. The interval between the former and new first fork becomes observed or simulated as appropriate. An invalid numeric input or a broken dependency returns a clarification and leaves the active revision intact. An explicitly qualitative scenario may be saved with an empty numeric suffix and a clear explanation.
5. Build candidate results outside the write transaction. Commit revision, cached run and timeline pointer together after comparing `expected_revision`. A duplicate request with the same ID and body returns the original result; reused ID with a different body or a stale revision returns `409`. Scope idempotency to the timeline and store a request-body hash. Look up a completed retry before checking its now-stale expected revision. The client ignores delayed responses for an obsolete edit. A refresh restores the last committed workspace.

**Shared acceptance example.** The three dates below are CPI **announcement dates**. Their reference months are May, June and July 2025 respectively. The values in the table are invented scenario inputs for testing. [June release](https://www.bls.gov/news.release/archives/cpi_06112025.htm) · [July release](https://www.bls.gov/news.release/archives/cpi_07152025.htm) · [August release](https://www.bls.gov/news.release/archives/cpi_08122025.htm)

| ID and instruction | Original branch | After replacing prompt [1] |
|---|---:|---:|
| `p1` · June 11 · Set reported monthly CPI to the entered value | 0.4% | 0.2% |
| `p2` · July 15 · Add 0.1 percentage points to the preceding reading | 0.5% | 0.3% |
| `p3` · August 12 · Keep July's simulated reading | 0.5% | 0.3% |

If only `p2` changes, every point before July 15, including June's simulated market path, must remain identical. If `p2` moves to July 18 in a generic daily fixture, repaint from July 15. The live CPI model must flag July 18 as a non-release date and ask for a valid release. Earlier prompts keep their definitions in both cases.

**Implemented replay (8 November).**

- **Research (CPI) mode** follows the rules above. It returns suffix responses and forecasts in five-session blocks anchored to each release, so appending a prompt and replaying the same prompts give identical paths (engine `…-cpu-cpi-v3`).
  - The verified journey is .35 / .275 / .275, rising to .6 / .525 / .525 after replacing `p1`. It runs 47 simulated sessions, ending August 18.
- **Scenario mode** recomputes the whole simulated run on every add or replace, and returns `series_mode: "full"` with `changed_from` at the frozen cutoff.
  - Because a block can see known future covariates, the simulated prefix before an edit is **not** guaranteed identical. Only the observed history before the cutoff is frozen.
  - The cutoff is the earliest prompt date. It can move earlier, never later.
  - Both modes keep stable IDs and a limit of three active prompts. Scenario mode also caps the total at 65 simulated sessions.
  - Add requests beyond three return `prompt_limit`. The backend has no delete route.

## 4. Backend services and models

**As implemented.** The table after this one is the original plan, kept for reference.

| Module (file) | What it does now |
|---|---|
| `ScenarioResearcher` (`api/scenario_research.py`) | Scenario mode only. Makes two OpenAI Responses calls with strict JSON schemas, `store=false`, a 5000-token cap and a 90 s timeout (`SCENARIO_TIMEOUT_SECONDS`). Call 1 must run web search (at most 3 tool calls). Call 2 must use only the available feature IDs and the accepted source URLs, both enforced as schema enums. There is no retry and no fallback; a failure saves nothing. |
| `ScenarioParserRouter` (`api/provider_parser.py`) | Research mode only. Presets are a zero-cost path. Otherwise one OpenAI attempt (20 s), then local Ollama `qwen3.5:9b` (12 s, thinking off). Output then passes several checks:<br>• a numeric "grounding" check, so the extracted number and units must appear in the text;<br>• basis-point conversion;<br>• rejection of alternatives;<br>• the shared domain policy in `api/cpi_domain.py`: release dates, −2% to 2%, references. |
| `ScenarioMarket` (`data/scenario_market.py`) | Builds one hashed snapshot (`scenario-<hash>`) from:<br>• SPY IEX minute bars (2022-03-07 to 2026-11-06), using each session's last minute as a daily close proxy, indexed to 100 on 2022-03-07;<br>• FRED `DFF`, `DCOILWTICO` and `VIXCLS` current vintages, lagged two calendar days with prior values carried at most 7 days;<br>• original BLS CPI releases, applied from publication.<br>Context is at most 252 sessions and needs at least 20 contiguous observed ones. A feature that is incomplete in the context is dropped, never filled. Also measures analogue windows: return, daily volatility, worst close and feature changes. |
| `EventArchive` (`data/scenario_events.py`) | Fetches and caches GDELT daily event exports on demand (12 s timeout, 30 MB cap). Rows must match the requested event date. This is context, not causal labels. |
| `ScenarioAdapter` (`training/scenario_adapter.py`) | Calls Chronos-2 `predict_df` on a session-ordinal clock with the SPY target plus covariates. The future frame holds covariates only; supplying a future target raises an error. Quantiles must be finite and ordered, with a positive median. `driver_path` ramps each feature from its preceding level to the endpoint, then optionally recovers. Engine `chronos-2-scenario-cpu`, version `chronos-2-2.3.2-29ec3766d36d-scenario-v1`. |
| `ChronosAdapter` (`training/chronos_adapter.py`) | Research mode, and the loader used by `ScenarioAdapter`. Uses `amazon/chronos-2` at pinned revision `29ec3766d36d6f73f0696f85560a422f50e8498c` with `chronos-forecasting==2.3.2`. Runs on CPU, offline (`local_files_only`), with 4 Torch threads and one locked, warmed pipeline. Takes CPI and release-indicator covariates. Bad output becomes an explicit `unsupported` result, never synthetic numbers. Version `…-cpu-cpi-v3`. |
| `EmpiricalBaseline` (`training/baseline.py`) | Reference and analogue modes over completed five-session windows after CPI releases. The floor is 8 distinct releases; the analogue tolerance is ±0.1 pp. Used by the standalone tools and evaluation only, not by HTTP. The scenario-mode "baseline" is a separate thing: Chronos with covariates held constant. |
| Evaluation (`training/evaluation.py`, `tools/evaluate_market.py`) | Chronological folds, each frozen one second before a CPI publication. Actual prices load only after forecasting. Scores mean absolute index error, q10–q90 coverage and interval width (§7). |
| Description relay (`api/descriptions.py`) | Frontend-initiated. Binds the submitted points to the saved revision (`409 forecast_mismatch` otherwise). One OpenAI call, 20 s timeout, 800-token cap, at most 6000 characters of output. |
| `DurableService` (`api/durable_service.py`, `api/sqlite_store.py`) | Handles drafts (300 s lifetime) and `expected_revision` checks. Parsing and inference run outside the write lock, and every check is repeated before the atomic write. Commits are idempotent by request ID and body hash. `sqlite3` errors become `503 storage_unavailable`. |

**Original plan:**

| Module | Contract and decisions |
|---|---|
| `ScenarioParser` | Primary `gpt-6-luna` through the **OpenAI Responses API**, subject to the event key's access and covered credit. Use only at app runtime to interpret scenarios and generate descriptions. Keep the key on the server. Use Structured Outputs with required fields, allowed operations, values, units, dates, explicit references and a `needs_clarification` state. Validate calendar, units, evidence IDs and supported numeric levers in Python. [OpenAI model](https://developers.openai.com/api/docs/models/gpt-6-luna) · [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) |
| `LocalParser` | Local `qwen3.5:9b` via Ollama, identical schema and validators. Pull once with `ollama pull qwen3.5:9b`. Fall back on timeout, unavailable model, exhausted event credit, rate limit or transport failure. Run the fallback only when needed. Begin with a 5-second interactive primary deadline and a 12-second warm local deadline, then tune on the demo host. Constrain each provider to one attempt per interactive request; handle an ambiguous prompt as a clarification. Use a checked preset if both providers are unavailable. Persist successful canonical instructions, so reapplying later instructions uses zero parser calls. Refresh affected descriptions separately for the committed revision. [Model and license](https://ollama.com/library/qwen3.5:9b) · [Schema support](https://docs.ollama.com/capabilities/structured-outputs) |
| `EvidenceStore` | SQLite FTS5 retrieves licensed passages by economic lever, exposure and publication date. Store source ID, publisher, passage location, version and release timestamp. Use passages available by the scenario cutoff; exclude later retrospective material from as-of explanations. Treat documents as evidence. A retrieved passage cannot change application rules, call tools or override a user assumption. |
| `Forecaster` | Use pretrained **`amazon/chronos-2`** as the primary numerical engine. Python package `chronos-forecasting`; use `Chronos2Pipeline.from_pretrained("amazon/chronos-2", device_map="cpu")` for a portable first run. Supply historical target and aligned covariates plus the assumed future covariates for the current segment via `predict_df`. Request quantiles 0.1, 0.5 and 0.9. Cache weights and warm the pipeline once per backend process. [Model card and Apache 2.0 license](https://huggingface.co/amazon/chronos-2) · [GitHub quickstart](https://github.com/amazon-science/chronos-forecasting/blob/main/notebooks/chronos-2-quickstart.ipynb) |
| `Baseline` | Reference = distribution of completed earlier CPI-release windows over the same five-session horizon. Also implement the original nearest-analogue estimate using the difference from the previously published CPI reading. Display dates, sample count and matching tolerance. Use a versioned threshold fixed before evaluation (initial analogue floor: eight distinct releases). Label the actual engine used. If Chronos fails, the analogue fallback may produce its supported five-session forecast; surface gaps beyond that horizon. |
| `Narrator` | **Current implementation:** frontend forwards saved forecast points to the backend description relay after commit; the relay calls OpenAI and returns plain prose to the frontend. Server credentials stay private. Basic panel text is the fallback; local narration and richer evidence are future work. **Longer-term design:** reuse the primary/fallback LLM pair in a separate call. Supply frozen passages, resolved assumptions, backend metrics and typed impacts. Ask for one plain market summary and one or two clearly labeled speculative mechanisms. Allow expressive prose here. Set temperature only on a provider/model that supports it for that call, otherwise vary wording through the instruction. Strict parsing is independent. A timeout returns a deterministic description from verified fields. No prose-generated number enters the chart or impact percentages. |
| `ReplayCoordinator` | Resolves the event log into segments, drives forecasting, computes `changed_from`, persists checkpoints, and assembles one versioned view. Use the same target, base and economic instructions whichever parser was selected. Quantitative LLM weight in this release is zero. |

**Numerical path.** Start with a single US-listed equity proxy such as SPY, one versioned eligible daily price feed, and seasonally adjusted headline month-on-month CPI-U. Record prices and CPI in separate units. Use one fixed base for the displayed index across the timeline and its edits, e.g. first eligible close in the pinned dataset = 100. Derive an indexed **level** series before inference so output quantiles correspond to displayed levels without compounding independent marginal return quantiles. Pass an explicit release indicator and latest as-released CPI reading on a regular trading-session index. Encode session numbers on a regular model grid and map them back to actual exchange sessions for display. Missing closes remain missing or exclude the affected window under the manifest's policy. Carry the latest known reading forward across non-release sessions with the release indicator set to zero. At a hypothetical release, change the reading exactly once and set the indicator to one. If a later release falls inside the horizon with no instruction, explicitly assume the previous reading carries forward and identify that assumption in the panel. Build the event calendar from information known at the fork or user-supplied dates. Never treat monthly CPI values as daily percentage shocks.

At each intervention use only the latest eligible historical or simulated state, plus inputs explicitly assumed through that segment. Project up to the next intervention or requested horizon, ending the segment immediately before the next intervention. For the final intervention use five trading sessions by default. Set a configurable **65-session total simulated horizon** for the demo, enough for the June–August example. Request confirmation for an incompatible interval; do not silently shorten it. Continue downstream from the previous segment's **simulated median trajectory**. Label downstream bands “conditional on the preceding simulated median”. These bands describe the local segment; a full joint multi-event uncertainty estimate would require propagating sampled trajectories. Keep validated historical five-session results separate from longer simulated bridges. Sparse historical support must be visible. Forecasts describe conditional associations. A political name alone does not identify a quantitative return.

**Implemented numerical path.**

- **Data.** SPY data starts March 7, 2022, so earlier years cannot be forecast. One SPY session is missing (December 23, 2024); context restarts after it.
- **Research mode** uses snapshot `spy-8c865e107520d2cdab66`, built from 28 extra original BLS release captures covering December 2022 to July 2025. It supplies 114 contiguous known-CPI sessions before the June 11, 2025 fork, which is frozen at 12:29:59 UTC.
- **Scenario mode** builds its own snapshot (verified as `scenario-969dbdff807fea8ccf36`). The fork is any session with at least 20 contiguous observed sessions before it.
- **Measured sensitivity.** With the same 114-session history and a 5-session horizon, CPI assumptions of .2%, .35% and .6% gave final medians of 143.78, 143.87 and 143.90. This is modest input sensitivity, not evidence of a causal sign.
- **Live scenario checks.** An Iran oil-export halt (June 11, 2025, 20 sessions) gave a final baseline median of 144.26 against a scenario median of 142.25. Removing all US import tariffs for 30 days (April 3, 2025, 10 sessions) gave 134.20 against 135.75.
- **Timing.** The first Chronos call takes about 2.2 s (loading cached weights); warm calls take about 0.24 s. An uncached scenario interpret can take minutes, because it makes two sequential web-research calls.

**What zero training means.** Chronos-2, the OpenAI model and Qwen run with fixed pretrained weights; nothing in this repository trains or fine-tunes a model. Reading historical data at inference time, indexing passages, backtesting, and cold startup still take time. Store the run, model and package versions, dataset hash, corpus hash, forecast settings and bounds for reproducibility. If model-pretraining overlap with a historical test is unknown, disclose it and show the as-of empirical baseline separately.

## 5. Frontend–backend wire contract

The executable handoff and conflict resolutions are in
[frontend-backend-contract.md](frontend-backend-contract.md). Generate OpenAPI, JSON
Schema and TypeScript from `api/contracts.py`. Use the fixture server only for synthetic
development; it does not establish live model or database readiness. A new read-only
`GET /api/timelines/{id}/revisions/{revision}` retrieves the preserved earlier snapshot.
Moving the first fork earlier must tighten the evidence cutoff if necessary; moving it
later or replaying downstream never advances that cutoff.

Type and validate the canonical schemas once in FastAPI/Pydantic. Chohan and Orion consume matching TypeScript types or generated OpenAPI types. Dates crossing the API are ISO 8601; session labels are US exchange dates. A numeric value of `0.4` with `unit="percent"` means 0.4%. A relative instruction uses `unit="percentage_points"`. Keep raw precision in the backend and round only for display.

| Endpoint | Request / response |
|---|---|
| `GET /api/capabilities` | Target IDs, units, dataset frequency, first/last usable sessions, supported event families, forecast cap, `max_prompts` (= `MAX_PROMPTS`), known gaps, available evidence and display rights. Include default viewport `1980–2026` separately from actual coverage. |
| `POST /api/timelines` and `GET /api/timelines/{id}` | Create an empty session or restore its active revision, stable prompt list, chart series, narrative and impacts. Empty session starts at revision 0. |
| `POST /api/timelines/{id}/interpret` | Send `text`, `mode` (add/replace), optional selected prompt ID and playhead, plus expected revision. Return a short-lived `draft_id` and canonical operation/date, or `needs_clarification` with specific choices. Bind draft to timeline, revision and selected ID. This call has no visible effect on history. |
| `POST /api/timelines/{id}/commit` | Send `draft_id`, `expected_revision`, `request_id`. A fully specified valid draft may auto-commit on Enter; ambiguities require the user's choice first. Return one atomic `revision`, `changed_from`, the complete active prompt metadata, chart data and per-prompt panels or clearly marked fallbacks. |
| `POST /api/timelines/{id}/delete` | Send `prompt_id`, `expected_revision`, `request_id`. Removes one active prompt and atomically returns the same response shape as commit: a suffix from the deleted prompt's effective start, the remaining prompts with unchanged IDs and display numbers, and their panels. Same idempotency, `409` and `422` rules as commit. **Pending:** the schema still needs adding to `api/contracts.py`; the browser client (`deletePrompt`) and the temporary mock already use this shape. |
| `GET /api/timelines/{id}/revisions/{revision}/summary` | End-screen journey summary for that revision: `headline`, `summary` (narrator prose from frozen passages, with a deterministic fallback; no prose-generated numbers), `net_change_percent` (level before the first prompt to the final point, from the backend run), and `legs[]` of `prompt_id, display_number, text, change_percent` in timeline order. Read-only. **Pending:** the schema still needs adding to `api/contracts.py`; the browser client (`summary`) and the temporary mock already use this shape. |
| `GET /api/timelines/{id}/revisions/{revision}/reveal` | Explicit user action. Return actual post-fork series with attribution and a distinct style within known coverage. This read cannot mutate a run. |
| `GET /api/timelines/{id}/revisions/{revision}` | **Implemented.** Read an immutable earlier revision. |
| `POST /api/timelines/{id}/delete` | **Frontend and mock only; no backend route.** Request `prompt_id, expected_revision, request_id`. Removes one active prompt and returns the commit response shape: a suffix from the deleted prompt's effective start, with the remaining prompts keeping their IDs and numbers. Follows the commit rules for idempotency, `409` and `422`. The frontend client (`deletePrompt`) uses hand-written types; the schema still needs adding to `api/contracts.py`. |
| `GET /api/timelines/{id}/revisions/{revision}/summary` | **Frontend and mock only; no backend route.** Returns the end-screen journey summary: `headline`, `summary`, `net_change_percent` (from the level before the first prompt to the final point) and `legs[]` (`prompt_id, display_number, text, change_percent`) in timeline order. Read-only. The frontend client (`summary`) uses hand-written types. |
| `POST /api/timelines/{id}/revisions/{revision}/description` | **Implemented.** Request `{prompt_id, forecast_points}`, where `forecast_points` is that prompt's complete unrounded simulated segment from the saved revision. Response `{timeline_id, revision, run_id, prompt_id, description, provider:"openai", model}`. Returns `409 forecast_mismatch` if the points differ from the saved revision, or `503 description_unavailable` / `description_not_configured`. |

**Implemented contract additions (still `contract_version: "1"`, all additive).**

- **`Instruction`** gains:
  - `scope: "event"`, `operation: "scenario"` and `unit: "scenario"`;
  - a `scenario` field holding the saved `ScenarioPlan`: requested/effective date, horizon, title, hypothesis, drivers, explanation, sources, measured analogues, limitations, research model/ID, dataset version and `web_search_used`.

  For scenario instructions, `value` and `reference` are null and `release_dates` is empty. Clients with exhaustive switches on operation or unit must handle the new members.
- **`RunResponse`** gains an optional `baseline` (same `Series` shape) and `scenario_warnings[]`.
- **`Capabilities` in scenario mode:**
  - `supported_event_families: ["open_ended_scenario"]` and no `fixture_presets`;
  - `default_viewport` taken from data coverage (2022–2026), not 1980–2026;
  - `default_horizon_sessions: 20`, `max_horizon_sessions: 65`, `max_prompts: 3`.
- **`Capabilities` in research mode:** `["headline_cpi_mom"]`, viewport 2025–2025, horizon 5.
- **Panels.** `impacts` is always `[]`. Scenario `support_count` is the number of measured analogue windows.
- **HTTP 200 results.** `needs_clarification` and `unsupported` come back as HTTP 200 `Problem` bodies, so check `status`. Codes include `scenario_clarification`, `data_coverage`, `horizon_coverage`, `prompt_limit`, `feature_unavailable` and `scenario_interpretation`.
- **Errors.** `503` covers research and forecast failures: `research_unavailable`, `research_sources_missing`, `scenario_forecast_failed`. `409` covers `timeline_configuration_mismatch`, when the data or model version changed and a new timeline is needed. `410` means `draft_expired`.
- **Not implemented:** delete-prompt, journey summary and impacts. The frontend's mock API simulates delete and summary. The real backend caps prompts at 3 and covers 2022 onward, so frontend settings that exceed this (more prompts, 1980–2021 dates) are unsupported against the server.

**Response fields relied on by the UI.**

| Field | Required content |
|---|---|
| `revision, parent_revision, changed_from, replace_through` | `changed_from` is inclusive. For a first commit or restore, return a full snapshot including the observed prefix. For later commits against a known parent, return a suffix. Set an explicit field named series_mode to full or suffix. On a suffix, drop the previous cached series from this date **through its former end**, then append the new suffix (even if empty or shorter). `replace_through` records the maximum of the former and new last affected dates. |
| `prompts[]` | `id, display_number, text, date_precision, requested_start, requested_end, effective_start, effective_end, scope, operation, value, unit, reference, status`. Preserve all stable IDs across a replacement. |
| `series` | `target_id, base_date, base_value, unit, frequency, points[]`. Each point has `date, kind` (`observed`/`simulated`/`gap`), `value, q10, q90, engine, segment_id`. Simulated `value` is the median; observed quantiles and gap values are null. |
| `panels[prompt_id]` | `summary, hypotheses[], evidence[], impacts[], horizon, comparison, engine, support_count, status`. Evidence has stable ID, title, URL, publication time and passage locator. Text, impacts and chart must share a revision. |
| `impact` | `name, emoji, exposure` (direct/indirect), `direction, metric_kind, magnitude, unit, comparator, horizon, method, source_ids[]`. Absolute magnitude and separate direction avoid a double minus. Unknown direction or unmeasured magnitude is nullable. |
| Errors | `422` for invalid units or dates, `409` for a stale write, `503` for an unavailable service with no supported fallback. An understood scenario with insufficient evidence is a domain result with `status="unsupported"` and its reason. |

**Contract fixture · replacement request and expected assertions.** Assume revision 3 contains the three June–August prompts in §3. The interpreted draft replaces `p1`. Save this as a shared test case; the count and dates below are acceptance values, not market observations.

```json
{
  "commit_request": {
    "draft_id": "draft-june-02",
    "expected_revision": 3,
    "request_id": "edit-june-001"
  },
  "assert_after_commit": {
    "revision": 4,
    "parent_revision": 3,
    "changed_from": "2025-06-11",
    "active_prompt_ids": ["p1", "p2", "p3"],
    "resolved_monthly_cpi_percent": [0.2, 0.3, 0.3],
    "prefix_unchanged_through": "2025-06-10"
  }
}
```

**Persistence.** SQLite tables hold timelines (active revision), revisions (parent and change date), versioned prompt definitions, per-segment results and checkpoints, idempotency records, sources, passages and exposure links. Store each checkpoint's preceding session, simulated target history required by Chronos, known feature state and active interval rules. Parquet holds observations and releases with both period and actual availability timestamps. Keep reveal data access in a separate reader. Debounce slider paints locally and commit only on explicit submission.

## 6. Evidence, impacts and data rights

**How to print a percentage.** A product can be affected by a scenario without contributing a measurable amount to SPY. The backend assigns a metric type to every row. The interface displays its meaning alongside the number. A curated exposure map links each product/market to a dated source and mechanism. Query enough candidates for 3–5 relevant bullets and rank quantified, supported entries ahead of qualitative ones. The text model can describe a link but cannot invent a measurement.

| Metric type | Calculation and example UI treatment |
|---|---|
| `proxy_change` | Forecast the eligible US sector/product proxy under the same scenario with the same fork and horizon. Report percentage change from **its own** starting level. Example format: `+ ✈️ Airlines 1.2% · sector proxy move, 5 sessions`. Illustrative number. |
| `index_contribution` | Only display when there is a documented, applicable decomposition with aligned constituents, weights, horizon and data rights. For a one-period fixed-weight basket, a 10% starting weight and a 2% component return give **+0.20 percentage points** of basket return. Identify the actual basket and basis. If using a multi-period methodology, validate it first. |
| `qualitative` | Example: `• 🚚 Freight · possible indirect exposure` with a source and mechanism. Show a sign only when the direction is supported. Do not show a made-up percentage, or interpret correlated sector moves as additive contributions. |

The initial supported quantitative target is SPY. Additional proxy models or a verified basket decomposition can populate numerical impact rows as rights and data allow. Until then, show grounded qualitative exposures. Keep speculative hypotheses under “Possible mechanism”; each carries an evidence link or an explicit “user assumption” label. Cite only passages actually supplied by the backend.

| Source | Release use and conditions |
|---|---|
| HF Data Library / IEX HIST | Candidate recent US equity data from March 2022 onward, varies by ticker. One exchange, split-adjusted prices. Compilation CC BY 4.0 plus provider academic/educational-use terms and required IEX linked notice. Confirm planned judging/public use, attribution and display scope before enabling. [Coverage](https://hfdatalibrary.com/) · [Terms](https://hfdatalibrary.com/pages/terms) · [IEX notice](https://www.iex.io/legal/hist-data-terms) |
| BLS | Use original archived CPI release times/values and original text; credit BLS. Exclude third-party copyrighted illustrations/photos. The change from the previous reading is CPI acceleration. A “consensus surprise” requires a separate permitted pre-release expectations series. [BLS rights](https://www.bls.gov/opub/copyright-information.htm) |
| **Implemented:** FRED (`DFF`, `DCOILWTICO`, `VIXCLS`) | Scenario-mode covariates, March 2022 to November 2026. These are current vintages, not ALFRED point-in-time vintages; the two-day lag and seven-day carry approximate availability and are disclosed in every run. |
| **Implemented:** GDELT 1.0 daily event exports | On-demand dated news-event context for at most two analogue dates, cached under `data/local/raw/gdelt/`. Not used as numerical input or as driver citations. |
| **Implemented:** OpenAI web search | Sources cited in the research step. A URL counts only if the search tool actually returned it. Only sources dated before the cutoff appear as panel evidence. Source dates and mechanisms are model interpretations and are not independently fact-checked. |
| Historical US macro/equity data | Optional JST US nominal equity total returns are annual. Separate annual mode and total-return basis; follow CC BY-NC-SA 4.0, required author citations and attribution. Annual points cannot support a daily 2008 path. [Database and terms](https://www.macrohistory.net/database/) |
| Political-economic literature | Use eligible original federal-author prose and individually licensed works. The 2008 Economic Report has contemporary credit-market material. The World Bank 2019/2020 banking report carries CC BY 3.0 IGO with third-party exceptions and is retrospective for 2008. Keep original publication date and component-level rights. [2008 report listing](https://georgewbush-whitehouse.archives.gov/cea/text/pubs.html) · [GovInfo rights](https://www.govinfo.gov/about/policies) · [World Bank report and rights](https://documents1.worldbank.org/curated/en/513831574784180010/pdf/Global-Financial-Development-Report-2019-2020-Bank-Regulation-and-Supervision-a-Decade-after-the-Global-Financial-Crisis.pdf) |

Persist owner, source URL, terms/version/date, attribution, allowed ingestion/indexing, external-model transmission, chart display and redistribution in a manifest. Keep restricted text local where required. Keep tool and model licenses with the submission. When the event credits are unavailable, select local Qwen for zero API charges. Simulated/test data uses a visible “synthetic example” label.

## 7. Backtest and failure behavior

Use dated chronological splits. For each past release, freeze prices, releases and evidence immediately before the event, enter its eventual release value **as the test scenario**, forecast, then reveal actual daily levels separately. Keep every look-back example's entire five-session outcome before the cutoff. Record event count, median forecast error at day five, empirical 10th–90th range coverage **and width**, and baseline results. A single realized path scores that factual scenario only. For branches spanning multiple events, label uncertainty conditional on earlier medians and test the chain separately.

**Implemented evaluation (CPI research mode, `tools/evaluate_market.py`, snapshot `spy-8c865e107520d2cdab66`).**

- **Folds.** 18 chronological CPI publication dates, January 2024 to June 2025. Each fold is frozen one second before publication and conditions on the subsequently published CPI as the scenario. Actual prices are loaded only for scoring.
- **Skipped fold.** January 2025 is unsupported, because the missing December 23 close leaves fewer than 20 contiguous sessions.
- **Results** (local `data/local/results/spy-8c865e107520d2cdab66/evaluation.json`):

| Engine | Scored / attempted | Mean absolute index error | q10–q90 coverage |
|---|---:|---:|---:|
| Chronos-2 | 17 / 18 | 1.6021 | 78.82% |
| Empirical reference | 17 / 18 | 1.4315 | 72.94% |
| Empirical analogue | 6 / 18 | 1.2062 | 76.67% |

How to read the results:
- The analogue engine was scored on a different subset of folds, so this is not a leaderboard.
- On these folds Chronos did **not** beat the simple reference distribution on error. Its bands covered slightly more of the actual outcomes.
- These are descriptive diagnostics, not a leakage-free backtest: the pretrained weights and current-vintage prices may contain later information.
- At the June 2025 cutoff the reference baseline has 29 windows. Analogue support is 10 for CPI 0.4% and 15 for CPI 0.2%.
- Scenario mode has no held-out evaluation yet. Sensitivity, calibration and analogue selection are open work.

| Failure | User-visible result |
|---|---|
| **Implemented:** OpenAI research unavailable, no verifiable sources, unknown feature or unverified citation (scenario mode) | `503` or a `needs_clarification` `Problem`, with no revision saved. There is no Ollama or CPI-parser fallback in scenario mode, so the user retries. |
| **Implemented:** Chronos failure or invalid quantiles | Scenario mode returns `503 scenario_forecast_failed`. Research mode returns an explicit unsupported result. There is no synthetic or empirical substitution over HTTP. |
| **Implemented:** date before data, not enough contiguous history, or horizon over 65 sessions | HTTP 200 `unsupported` with `data_coverage` or `horizon_coverage`. The chart is unchanged. |
| Missing rights, missing date or weak data support | Display the uncovered interval or ask for a supported date; keep the last successful run. An alternate-president prompt can ask for a specific policy and offer qualitative evidence. |
| OpenAI quota, network or invalid schema | Attempt Qwen locally; if both fail, use a confirmed preset or ask for clarification. Narrative failure uses a concise templated summary. |
| Chronos unavailable or exceeds its deadline | Use the separately labeled empirical forecast only within its supported strict range. The actual engine and any unavailable tail appear on the chart. |
| Two edits overlap or a response arrives late | Apply only the response for the current request/revision. Preserve the draft and offer reapply against the latest revision after a conflict. |
| Model loading, slow Wi-Fi or browser reload | One warm numerical model and one local LLM on the host. Cache by data/corpus/model version, cutoff, canonical event log and settings. Budget model calls server-side and measure warm and cold latency independently. |

## 8. Run and integrate

The M5 Max MacBook with 48 GB unified memory is the shared demo host. Windows and macOS teammates can use the browser against the same FastAPI URL. For standalone Windows use the same Python CPU model path and optional native Ollama. Keep the Ollama port internal to the backend; the browser uses only the app backend. Put credentials in server environment variables and package the frontend, licensed data slice, local weights and evidence snapshots ahead of time. One backend worker avoids redundant model memory. Bound concurrent jobs, record per-stage latency and run IDs, and retry an edit using its original request ID.

| Server configuration | Demo value or role |
|---|---|
| `OPENAI_API_KEY`, `OPENAI_MODEL` | Event runtime key and `gpt-6-luna` if enabled. Route to the local provider if credits are unavailable. No event-key coding use. |
| `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | `http://127.0.0.1:11434` and `qwen3.5:9b`. Pre-pull and make one valid schema call on the actual host. |
| `FORECAST_MODEL`, `FORECAST_DEVICE` | `amazon/chronos-2`, `cpu`. Pin package versions, weight revision and demo manifest; load once. |
<<<<<<< HEAD
| `DATA_DIR`, `SQLITE_PATH` | Approved local snapshots and persistent writable state. Keep credentials and restricted raw datasets out of the public repo. |
| **Frontend:** `MAX_PROMPTS` | `7` in `web/src/config.ts`. The backend limit is 3 (`capabilities.max_prompts`). Make them equal, or have the UI read the capability. |
| **Frontend:** `VITE_API`, `VITE_BACKGROUND_ASSET` | Set `VITE_API=server` to use the HTTP client instead of the in-browser mock. `VITE_BACKGROUND_ASSET=/file.gif` (in `web/public`) replaces the pixel sea. The planned `BACKGROUND_MODE` setting was not built. |
| **Implemented:** `APP_MODE` | `fixture` (default), `research` or `scenario`. |
| **Implemented:** `DATASET_VERSION` | Required in `research` mode, e.g. `spy-8c865e107520d2cdab66`. Scenario mode derives its snapshot from source hashes. |
| **Implemented:** `PARSER_PROVIDER` | `deterministic`, `auto` or `ollama`. Defaults to `auto` in research and scenario modes, `deterministic` in fixture mode. |
| **Implemented:** `OPENAI_MODEL` and timeouts | Verified with `gpt-5.6-sol`; set it to a model the project has access to. Timeouts: `OPENAI_TIMEOUT_SECONDS` (parser), `SCENARIO_TIMEOUT_SECONDS` (90, at most 180) and `OPENAI_DESCRIPTION_TIMEOUT_SECONDS` (20). `api.app` does not load `.env`. The launchers read an `--env-file` server-side; never put keys in `VITE_*`. |
| **Implemented:** launchers | `tools/serve_scenarios.py --env-file .env.local --model <model> --port 8772` and `tools/serve_research.py … --port 8771`. Each creates a new SQLite file unless `--database` is passed, and sets `HF_HUB_OFFLINE=1`. Frontend (`frontend` branch): `cd web && VITE_API=server npm run dev`. Its `vite.config.ts` proxies `/api` only to `127.0.0.1:8000`, so either run the backend launcher with `--port 8000` or change that proxy target. The `BACKEND_URL` variable in the handovers is not read yet. |
=======
| `MAX_PROMPTS` | `7`. Most active prompts per timeline and the longest journey; reported as `capabilities.max_prompts`. The frontend copy lives in `web/src/config.ts`; keep the two equal. |
| `DATA_DIR`, `SQLITE_PATH`, `BACKGROUND_MODE` | Approved local snapshots, persistent writable state and `pixel_sea`. Keep credentials and restricted raw datasets out of the public repo. |
>>>>>>> origin/demo/teamrelay-final

**Time boxes in Edinburgh time, 7–8 November.** These are team targets. The event lists **Sunday noon submission** and **12:30 judging**. Four owners can develop against the same contract in parallel. [Event itinerary](https://hacktheburgh.com/itinerary) · [Rules for AI and reused work](https://hacktheburgh.com/code-of-conduct)

| By | Handoff or decision |
|---|---|
| Saturday 22:15 | Aashna publishes schema and fixtures; Aditya validates a data license, two release windows and a Chronos smoke test; both frontend owners agree on one viewport and event-selection interface. |
| Sunday 00:30 | On the same host: one input, first full draw, primary/fallback parser, actual backend series, one dated source and an honest data status. |
| Sunday 03:00 | All three prompts replay through a replacement, including an earlier-date edit, with unchanged prefix checks. Verify both a quantitative and a qualitative impact display using labeled fixtures when necessary. |
| Sunday 09:30 | Finish held-out baseline comparison, accessible UI and coverage labels. Cut optional assets, extra instruments and elaborate narration first. Preserve core edits and evidence. |
| Sunday 10:30 | Freeze features. Rehearse on a Windows browser and the Mac host; exercise offline fallback, prepare disclosures and submit before noon. |

## 9. Definition of done

- **Screen and timeline:** A fresh desktop session has the centered black-screen composer. After submit the composer sits near 80%, impacts are beneath it, the date scale defaults to 1980–2026, settings change the viewport, and unavailable portions remain visibly empty. Check mobile scroll, keyboard selection and reduced motion.
- **Chart:** First success draws the full available path. A second prompt animates only its suffix. A past edit changes downstream points while a hash of all earlier points is identical. An interval greys every included year and displays both boundaries. Overlapping markers remain individually selectable.
<<<<<<< HEAD
- **Editor:** Click `prompt 2`, edit, cancel, then edit and submit. A successful replacement keeps three prompts and the original ID. Clicking empty space deselects. Hover a label and press ×: the prompt disappears, the others keep their IDs, and the earlier path is unchanged (mock only until a backend delete route exists). A prompt beyond the chosen journey length is refused with the text kept, and reaching the length shows "End journey". Test old/new dates in both directions, shortened bounds, same-date ordering, interval expiry, absolute versus relative inputs, and stale responses during animation.
=======
- **Editor:** Click `prompt 2`, edit, cancel, then edit and submit. A successful replacement keeps three prompts and the original ID. Clicking empty space deselects. Hover a label, press ×, and the prompt disappears while the others keep their IDs and the earlier path is unchanged. A prompt beyond the chosen journey length is refused with the text kept, and reaching the length shows the end screen. Test old/new dates in both directions, shortened bounds, same-date ordering, interval expiry, absolute versus relative inputs, and stale responses during animation.
>>>>>>> origin/demo/teamrelay-final
- **Numerics and prose:** All chart points and percentages trace to a versioned backend run; qualitative effects have source-backed explanations and no fabricated precision. Future-dated evidence is excluded. Changing only a politician's name with the same confirmed economic assumptions leaves model inputs identical.
- **Recovery and evaluation:** Try an offline provider, unsupported year, incomplete release window and duplicate commit. Show counts and held-out baseline alongside Chronos, including a case the model missed. Measure end-to-end time on the demo host; published throughput and prior synthetic timings do not establish it.
- **One judge walkthrough:** For **HRT**, compare the conditional forecast against the baseline and reveal an observed release. For **G-Research**, open a less obvious exposure and inspect its source or calculation. For **Metaview**, let the judge edit the first prompt and watch the second and third change. Credit team-built work, data, AI tools and dependencies in the submission.
