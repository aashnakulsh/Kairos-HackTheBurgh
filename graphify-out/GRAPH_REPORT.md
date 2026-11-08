# Graph Report - TeamRelay-Hackathon  (2026-11-08)

## Corpus Check
- 137 files · ~100,886 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: (none) 4, .patch 2, .css 2)

## Summary
- 1080 nodes · 2544 edges · 70 communities (58 shown, 12 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 237 edges (avg confidence: 0.91)
- Token cost: 407,217 input · 0 output

## Community Hubs (Navigation)
- OpenAI Handover Docs
- CPI Parser Router
- Frontend API Client
- App Factory & Launchers
- API Contracts & Routes
- Shared Fixtures
- App Shell & PixelSea
- Research HTTP Tests
- Test Suite Imports
- Market Data Prep
- Durable Service Core
- Durable Backend Tests
- Chronos Market Adapter
- Chart & Timeline
- Replay & Backends
- Market Evaluation
- Browser Mock API
- Forecast Engines
- Web Package Config
- Narrative Panels
- Contract Validators
- Scenario Backend
- Demo Scripts
- Scenario Research Tests
- Capabilities Endpoint
- TypeScript Config
- Architecture Modes
- Scenario Contracts
- Replay Rules Docs
- Journey Tests
- README Handoffs
- General Scenario Tests
- Schema Tests
- Preset Parser
- Fixture Service
- Research Mode Docs
- Composer & Prompt Limit
- Agent Workflow Rules
- Team Onboarding
- Chronos Model Docs
- Scenario Pipeline Docs
- General Scenario Design
- Docs Index
- CPI Acceptance Example
- Frontend-Backend Gaps
- Model Scope Findings
- CPI Whitelist Limits
- Frontend Research Check
- Data Input Audit
- Scenario Researcher
- Data Sources & Failures
- Wire Contract Docs
- Adapter Test Doubles
- Numerical Adapter Protocol
- Data Rights & Requirements
- Board & Handoff Review
- Fixture Path Docs
- Team Roles
- Scenario Integration Branches
- Snapshots & Baselines
- Scope Gap & Roadmap
- Market Alignment
- OpenAI Roadmap Stages
- Driver Path Interpolation
- Inbox Script
- Impact Metrics
- No Repeat Prompts
- Durable Verification

## God Nodes (most connected - your core abstractions)
1. `BackendError` - 45 edges
2. `create_app()` - 41 edges
3. `ResearchHTTPTests` - 35 edges
4. `UnsupportedInput` - 31 edges
5. `create_app()` - 29 edges
6. `DurableTests` - 29 edges
7. `Contract` - 27 edges
8. `RunResponse` - 27 edges
9. `Settings` - 27 edges
10. `DurableService` - 26 edges

## Surprising Connections (you probably didn't know these)
- `OpenAIDescriptionProvider` --references--> `OpenAIDescriptionProvider`  [INFERRED]
  docs/aditya-openai-frontend-handover.md → api/descriptions.py
- `ScenarioParser Protocol Seam` --references--> `ScenarioParser`  [INFERRED]
  docs/aditya-openai-frontend-handover.md → api/preset_parser.py
- `PresetParser (five exact preset strings)` --references--> `PresetParser`  [INFERRED]
  docs/aditya-openai-frontend-handover.md → api/preset_parser.py
- `Frontend-Initiated Descriptions (descriptions.py)` --semantically_similar_to--> `OpenAI Descriptions After Forecast`  [INFERRED] [semantically similar]
  api/README.md → docs/real-data-adapter.md
- `requirements-chronos-smoke.txt (chronos-forecasting==2.3.2)` --conceptually_related_to--> `Chronos-2 Pinned Offline CPU Model (chronos-2-2.3.2-29ec3766d36d-scenario-v1)`  [INFERRED]
  requirements-chronos-smoke.txt → docs/general-scenario-handover.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Forecast-to-Description Narration Pipeline** — docs_aditya_openai_frontend_handover_chronos2_forecasting, docs_aditya_openai_frontend_handover_applyrun_suffix_reconstruction, docs_aditya_openai_frontend_handover_descriptionrequest, docs_aditya_openai_frontend_handover_openai_description_provider, docs_aditya_openai_frontend_handover_openai_responses_api, docs_aditya_openai_frontend_handover_useworkspace_narration_effect [EXTRACTED 1.00]
- **ScenarioParser Implementations and Validation** — docs_aditya_openai_frontend_handover_scenarioparser_protocol, docs_aditya_openai_frontend_handover_presetparser, docs_aditya_openai_frontend_handover_nl_scenario_interpretation, docs_pr6_live_verification_provider_parser, docs_aditya_openai_frontend_handover_ollama_fallback, docs_aditya_openai_frontend_handover_parsedscenario_schema [INFERRED 0.85]
- **PR #6 Live-Verification Fixes** — docs_pr6_live_verification_fix_parser_instructions, docs_pr6_live_verification_fix_ollama_think_false, docs_pr6_live_verification_fix_reveal_yrange [EXTRACTED 1.00]
- **CPI five-case whitelist enforcement layers** — docs_model_scope_analysis_handover_presets_dictionary, docs_model_scope_analysis_handover_provider_parser, docs_model_scope_analysis_handover_grounded, docs_model_scope_analysis_handover_supported, docs_model_scope_analysis_handover_researchbackend_instruction [EXTRACTED 1.00]
- **Interpret -> forecast -> narrate research pipeline** — docs_model_scope_analysis_handover_openai_parser, docs_model_scope_analysis_handover_qwen_local_fallback, docs_model_scope_analysis_handover_chronos_adapter, docs_model_scope_analysis_handover_description_relay [EXTRACTED 1.00]
- **Prioritized staged next-work plan** — docs_model_scope_analysis_handover_stage1_continuous_cpi, docs_model_scope_analysis_handover_stage2_controlled_sensitivity, docs_model_scope_analysis_handover_stage3_economic_levers, docs_model_scope_analysis_handover_stage4_broaden_domain, docs_model_scope_analysis_handover_stage5_grounded_descriptions [EXTRACTED 1.00]
- **Scenario interpret -> commit -> describe -> reveal flow** — docs_architecture_scenarioresearcher, docs_architecture_scenarioadapter, docs_architecture_chronos_2, docs_architecture_description_relay, docs_architecture_reveal_actual_history, docs_architecture_durableservice [EXTRACTED 1.00]
- **Revision consistency: changed_from, idempotency, full/suffix apply** — docs_architecture_changed_from, docs_architecture_idempotent_commit, docs_durable_backend_request_hash_idempotency, docs_frontend_backend_contract_full_suffix_updates, docs_frontend_backend_contract_applyrun, docs_durable_backend_bridge_full_response [INFERRED 0.85]
- **Frontend/backend merge gaps** — docs_architecture_frontend_backend_gaps, docs_architecture_max_prompts, docs_architecture_sea_level, docs_architecture_delete_endpoint, docs_architecture_summary_endpoint, docs_architecture_unresolved_merge_conflict [INFERRED 0.85]
- **OpenAI research -> measured analogues -> Chronos -> narration pipeline** — docs_general_scenario_handover_openai_research_planning, docs_general_scenario_handover_historical_analogue_windows, docs_general_scenario_handover_driver_spec, docs_general_scenario_handover_chronos_2_model, docs_general_scenario_handover_narration_relay [EXTRACTED 1.00]
- **Layered Python requirements (contracts -> market -> forecast + chronos smoke)** — requirements_contracts, requirements_market, requirements_chronos_smoke, requirements_forecast [EXTRACTED 1.00]
- **Human-directed board coordination (policy, listener, hook, git workflow)** — agents_human_control_policy, agents_board_inbox_listener, claude_inbox_hook, agents_git_workflow [INFERRED 0.85]

## Communities (70 total, 12 thin omitted)

### Community 0 - "OpenAI Handover Docs"
Cohesion: 0.06
Nodes (38): Aditya Handover: OpenAI Implementation and Frontend Integration, Interpret/Commit/Describe/Restore/Reveal Architecture, Chronos-2 Offline CPU Numerical Forecasting, Headline CPI-U Monthly SA Lever, Pinned Dataset Versions (spy-99baca8c94f5871aff6b / spy-8c865e107520d2cdab66), 503 description_not_configured / description_unavailable, DescriptionRequest / DescriptionResponse, Environment Settings (APP_MODE, OPENAI_MODEL, etc.) (+30 more)

### Community 1 - "CPI Parser Router"
Cohesion: 0.09
Nodes (15): instruction_error(), PresetParser, _clarify(), _grounded(), OllamaParser, OpenAIParser, ParserUnavailable, _problem() (+7 more)

### Community 2 - "Frontend API Client"
Cohesion: 0.09
Nodes (36): applyRun(), ApiError, createApi(), call(), DeletePromptRequest, descriptionRequest(), JourneySummary, matchesDescription() (+28 more)

### Community 3 - "App Factory & Launchers"
Cohesion: 0.08
Nodes (10): create_app(), database_error(), validation_error(), OpenAIDescriptionProvider, Settings, DescriptionTests, SettingsTests, load_provider_env() (+2 more)

### Community 4 - "API Contracts & Routes"
Cohesion: 0.11
Nodes (14): Capabilities, CommitRequest, Contract, ContractBundle, CreateTimelineRequest, DescriptionRequest, DescriptionResponse, Evidence (+6 more)

### Community 5 - "Shared Fixtures"
Cohesion: 0.06
Nodes (34): capabilities.json, clarification.json, conflict.json, create-request.json, empty.json, empty-suffix.json, first-run-commit.json, first-run-draft.json (+26 more)

### Community 6 - "App Shell & PixelSea"
Cohesion: 0.10
Nodes (29): @fontsource/vt323, plotly.js-dist-min, react, react-dom, dependencies, @fontsource/vt323@^5.3.0, plotly.js-dist-min@^4.2.0, react@^19.3.1 (+21 more)

### Community 7 - "Research HTTP Tests"
Cohesion: 0.12
Nodes (7): ResearchHTTPTests, predict_df(), forecast_segment(), parse(), submit(), unsupported(), parse()

### Community 8 - "Test Suite Imports"
Cohesion: 0.12
Nodes (3): build(), ts(), main()

### Community 9 - "Market Data Prep"
Cohesion: 0.11
Nodes (6): digest(), instant(), parse_release(), validate_2025_calendar(), reveal_run(), main()

### Community 10 - "Durable Service Core"
Cohesion: 0.17
Nodes (7): BackendError, DurableService, ResearchBackend, body_hash(), encode(), SQLiteStore, empty()

### Community 11 - "Durable Backend Tests"
Cohesion: 0.19
Nodes (6): DurableTests, forecast_segment(), forecast_segment(), forecast_segment(), forecast_segment(), forecast_segment()

### Community 12 - "Chronos Market Adapter"
Cohesion: 0.14
Nodes (7): audit_prices(), sessions(), fake_inputs(), FakePipeline, MarketTests, ChronosAdapter, model_frames()

### Community 13 - "Chart & Timeline"
Cohesion: 0.19
Nodes (20): fixture(), journey(), Chart(), MARGIN, only(), simulatedish(), clipPoints(), domain() (+12 more)

### Community 14 - "Replay & Backends"
Cohesion: 0.16
Nodes (8): HistoryRow, Prompt, RunResponse, candidate(), forecast_points(), point(), save(), write()

### Community 15 - "Market Evaluation"
Cohesion: 0.17
Nodes (8): FutureRow, MarketInputs, UnsupportedInput, read_reveal(), main(), main(), EvaluationInputs, score()

### Community 16 - "Browser Mock API"
Cohesion: 0.11
Nodes (17): BASE, createMockApi(), snapshot(), DateReading, Draft, FIRST, MONTHS, noise() (+9 more)

### Community 17 - "Forecast Engines"
Cohesion: 0.20
Nodes (7): ForecastResult, Point, SyntheticAdapter, completed_windows(), EmpiricalBaseline, unsupported(), validate_request()

### Community 18 - "Web Package Config"
Cohesion: 0.13
Nodes (18): @types/react, @types/react-dom, typescript, vite, @vitejs/plugin-react, devDependencies, @types/react@^19.3.0, @types/react-dom@^19.3.0 (+10 more)

### Community 19 - "Narrative Panels"
Cohesion: 0.16
Nodes (18): formatImpact(), METRIC, quantified(), rankImpacts(), Trend, divider(), DIVIDERS, ImpactList() (+10 more)

### Community 20 - "Contract Validators"
Cohesion: 0.12
Nodes (5): Coverage, Hypothesis, Panel, Series, Viewport

### Community 21 - "Scenario Backend"
Cohesion: 0.17
Nodes (4): ScenarioBackend, infer(), ScenarioMarket, ScenarioAdapter

### Community 22 - "Demo Scripts"
Cohesion: 0.18
Nodes (3): main(), main(), main()

### Community 23 - "Scenario Research Tests"
Cohesion: 0.17
Nodes (3): strict_schema(), visit(), main()

### Community 24 - "Capabilities Endpoint"
Cohesion: 0.14
Nodes (4): create_app(), generate(), get_capabilities(), capabilities()

### Community 25 - "TypeScript Config"
Cohesion: 0.13
Nodes (14): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+6 more)

### Community 26 - "Architecture Modes"
Cohesion: 0.15
Nodes (14): APP_MODE (fixture / research / scenario), DurableService (api/durable_service.py, api/sqlite_store.py), EmpiricalBaseline (training/baseline.py), Evaluation (training/evaluation.py, tools/evaluate_market.py), Idempotent commit with expected_revision, Scenario mode (open-ended events), Server configuration (env vars, launchers), Expanded dataset snapshot spy-8c865e107520d2cdab66 (+6 more)

### Community 27 - "Scenario Contracts"
Cohesion: 0.24
Nodes (8): AnalogueCandidate, AnalogueMeasurement, FeatureChange, NumericalPlan, ResearchExtraction, ResearchSource, ScenarioDriver, Strict

### Community 28 - "Replay Rules Docs"
Cohesion: 0.18
Nodes (10): Dirty boundary changed_from, Frozen evidence cutoff, Prompt markers and interval shading, Stable prompt id and display_number, Suffix-only redraw animation, applyRun() cache update (web/src/api/applyRun.ts), Inventory and exact conflicts resolved, POST .../revisions/{revision}/description (DescriptionRequest/Response) (+2 more)

### Community 30 - "README Handoffs"
Cohesion: 0.18
Nodes (12): Team Roster (Aashna, Aditya, Chohan, Orion), Workspace Limits and Replay (3 prompts, 65 sessions, series_mode full), Fixture API Development Workflow, Shared Handoff v1 README, Contract Generation from api/contracts.py, Fixture Manifest and journey.json, Problem Response Body (409/422/503, clarification, unsupported), Suffix/Full Series Update Rule (parent_revision, changed_from) (+4 more)

### Community 32 - "Schema Tests"
Cohesion: 0.29
Nodes (4): Impact, Instruction, fixture(), SchemaTests

### Community 33 - "Preset Parser"
Cohesion: 0.25
Nodes (3): InterpretRequest, ParsedScenario, ScenarioParser

### Community 34 - "Fixture Service"
Cohesion: 0.31
Nodes (3): ReadyDraft, FixtureError, FixtureService

### Community 35 - "Research Mode Docs"
Cohesion: 0.22
Nodes (11): Durable Backend and Numerical Interface README, Frontend-Initiated Descriptions (descriptions.py), ForecastRequest/ForecastResult Numerical Boundary, ChronosAdapter.forecast_segment (NumericalAdapter), Chronological Market Evaluation (tools/evaluate_market.py), Replay Model Identity Versioning (cpu-cpi-v2), APP_MODE=research CPI Research API, Actual-History Reveal Endpoint (+3 more)

### Community 37 - "Composer & Prompt Limit"
Cohesion: 0.33
Nodes (7): MAX_PROMPTS, Composer(), ComposerProps, EXAMPLES, randomExample(), promptKey(), Notice

### Community 38 - "Agent Workflow Rules"
Cohesion: 0.27
Nodes (9): AGENTS.md Shared Agent Instructions, Board Listener and Local Inbox (tools/board), Git Issue-Branch/PR Workflow, Security and Compatibility Rules, CLAUDE.md Project Instructions, Claude Local Inbox Notification Hook, TeamRelay-Hackathon README, Selected Stack (React/TypeScript/Vite, Plotly, FastAPI, SQLite, Parquet) (+1 more)

### Community 39 - "Team Onboarding"
Cohesion: 0.20
Nodes (10): API contracts (api/contracts.py), tools/export_contracts.py --check, Local fixture HTTP routes (api/fixture_app.py), Three-prompt HTTP journey test (0.4/0.5/0.5 -> 0.2/0.3/0.3), Typed frontend client and cache (web/src/api/client.ts, applyRun.ts), Start Building Together (team guide), Backend checks (stale revision, idempotency, atomic failure, prefix), Foundation task issue #3 (3-foundation-contract-placeholders) (+2 more)

### Community 40 - "Chronos Model Docs"
Cohesion: 0.22
Nodes (7): Chronos-2 (amazon/chronos-2, pinned, offline CPU), ChronosAdapter (training/chronos_adapter.py), Research mode (bounded CPI demo), ScenarioAdapter (training/scenario_adapter.py), Engine chronos-2-2.3.2-29ec3766d36d-cpu-cpi-v3, Verified journey .35/.275/.275 then .6/.525/.525 (47 sessions), tools/chronos_smoke.py (download, load --offline, forecast)

### Community 41 - "Scenario Pipeline Docs"
Cohesion: 0.22
Nodes (9): Description relay (api/descriptions.py), Local Qwen qwen3.5:9b via Ollama (fallback), OpenAI Responses API, Pixel scroll description notes (Panels.tsx), Reveal actual history (separate from forecast inputs), ScenarioParserRouter (api/provider_parser.py), Numeric grounding and basis-point normalization, PresetParser and Ollama check (tools/check_ollama.py) (+1 more)

### Community 42 - "General Scenario Design"
Cohesion: 0.22
Nodes (8): General Scenario Implementation and Frontend Handover, Baseline vs Scenario Five-Session Block Inference, Chronos-2 Pinned Offline CPU Model (chronos-2-2.3.2-29ec3766d36d-scenario-v1), Covariate Channels (oil, VIX, effective rate, monthly CPI), Scenario Driver Specification (feature/operation/transition/duration/recovery/basis), Live Verification Runs (Iran export halt, US tariff removal), OpenAI Research and Numerical Planning (two Responses calls), Scenario Research Cache (data/local/cache/scenario-research)

### Community 43 - "Docs Index"
Cohesion: 0.28
Nodes (9): US Market What If? Architecture (architecture.md), Team ownership split (Aashna, Aditya, Chohan, Orion), Continuous CPI demo handover, integration/frontend-research.patch, Live LLM/browser journey not yet verified, scenario_interpretation problem code (replaces choose_preset), Durable backend milestone and host handoff, Frontend/backend handoff contract v1 (+1 more)

### Community 44 - "CPI Acceptance Example"
Cohesion: 0.22
Nodes (8): Operations set / add_pp / carry, Definition of done (judge walkthrough HRT, G-Research, Metaview), Shared acceptance example (June/July/August 2025 CPI p1-p3), useWorkspace.ts (frontend state and API calls), Shared CPI domain policy (api/cpi_domain.py, [-2%, 2%]), Browser journey and endpoints table, createApi() typed browser client (web/src/api/client.ts), shared/journey.json fixture journey

### Community 45 - "Frontend-Backend Gaps"
Cohesion: 0.33
Nodes (9): POST /api/timelines/{id}/delete (frontend/mock only), Frontend vs backend integration gaps, MAX_PROMPTS / capabilities.max_prompts, In-browser mock API (web/src/api/mockApi.ts), PixelSea pirate-ship background (PixelSea.tsx), SEA_LEVEL chart scale (Chart.tsx), GET .../revisions/{revision}/summary (frontend/mock only), Unresolved merge conflict markers (HEAD vs origin/demo/teamrelay-final) (+1 more)

### Community 46 - "Model Scope Findings"
Cohesion: 0.25
Nodes (8): Chronos-2 pretrained time-series model (amazon/chronos-2), ChronosAdapter (training/chronos_adapter.py), Data bottleneck: constant CPI context, Saved live results (.4/.5/.5 vs .2/.3/.3 revisions), Real market loader restrictions (data/real_market.py), Replay/inference chunking confounder (api/replay.py), Snapshot spy-8c865e107520d2cdab66 (114 sessions, expanded), Snapshot spy-99baca8c94f5871aff6b (20 sessions, live verification)

### Community 47 - "CPI Whitelist Limits"
Cohesion: 0.31
Nodes (8): integration/frontend-research.patch, _grounded handwritten grounding checks, PR #6 CPI parser frontend patch, PRESETS dictionary (shared/fixture_service.py), Provider parser (api/provider_parser.py), Local Qwen fallback parser (qwen3.5:9b via Ollama), ResearchBackend.instruction second whitelist (api/research_backend.py), _supported parser tuple whitelist

### Community 48 - "Frontend Research Check"
Cohesion: 0.22
Nodes (5): api, observed, run, snapshots, web

### Community 49 - "Data Input Audit"
Cohesion: 0.25
Nodes (7): Hashed Scenario Snapshot scenario-969dbdff807fea8ccf36, Bounded GDELT Daily Archive Retrieval, Local Data Inputs Policy (SPY IEX, FRED, BLS, GDELT under data/local), SPY IEX Minute-Bar Input Audit, XNYS Exchange Calendar (exchange-calendars 4.13.2), requirements-contracts.txt (pydantic, fastapi, httpx, jsonschema, uvicorn), requirements-market.txt (pandas, numpy, pyarrow, exchange-calendars, bs4, pypdf)

### Community 50 - "Scenario Researcher"
Cohesion: 0.48
Nodes (3): ScenarioPlan, ScenarioResearcher, plan()

### Community 51 - "Data Sources & Failures"
Cohesion: 0.33
Nodes (6): Data sources and rights (HF/IEX, BLS, FRED, GDELT, web search), EventArchive (data/scenario_events.py, GDELT), Failure behavior table, ScenarioMarket (data/scenario_market.py), ScenarioResearcher (api/scenario_research.py), Real input sources (HF SPY, BLS CPI, NYSE sessions, reveal)

### Community 52 - "Wire Contract Docs"
Cohesion: 0.33
Nodes (7): Fixture mode (SyntheticAdapter), Scenario contract additions (operation/unit 'scenario', baseline, scenario_warnings), Frontend-backend wire contract (section 5), NumericalAdapter.forecast_segment (ForecastRequest -> ForecastResult), SyntheticAdapter (arithmetic, labelled synthetic), api/contracts.py canonical schema and generated copies, api/fixture_app.py synthetic in-memory server

### Community 55 - "Data Rights & Requirements"
Cohesion: 0.33
Nodes (6): Local Market Inputs README, Data Source Manifest Policy, Real-Data Adapter and Research API Guide, Data Rights and Publication (HF/IEX, BLS, NYSE), requirements-chronos-smoke.txt (chronos-forecasting==2.3.2), requirements-forecast.txt (torch, transformers, accelerate, huggingface-hub)

### Community 56 - "Board & Handoff Review"
Cohesion: 0.33
Nodes (6): API Handoff Review, GO WITH CONDITIONS verdict, Board Issue (shared coordination board), 60-second notification-only listener, [Name's Codex]/[Name's Claude] post convention, Shared frontend-needs Google Doc

### Community 57 - "Fixture Path Docs"
Cohesion: 0.33
Nodes (4): tools/check_fixtures.py (34 fixtures), Deterministic in-memory fixture service, Browser mockApi.ts synthetic path generator, Backend SyntheticAdapter test arithmetic

### Community 58 - "Team Roles"
Cohesion: 0.33
Nodes (6): Remaining owner tasks / live blockers, Aashna (@aashnakulsh), team lead, Aditya (@ADI-GHH), Orion (@wthoreo), Chohan (@yimchohan), Parallel starting tasks per person

### Community 59 - "Scenario Integration Branches"
Cohesion: 0.40
Nodes (6): integration/frontend-scenario.patch (full diff from f272c22), Frontend-Initiated OpenAI Narration Relay, Scenario HTTP API Flow (capabilities, timelines, interpret, commit, description, reveal), tools/serve_scenarios.py Local Launcher, integration/frontend-research.patch, OpenAI Descriptions After Forecast

### Community 60 - "Snapshots & Baselines"
Cohesion: 0.33
Nodes (6): Frozen Evidence Cutoff and Context Rules (20-252 sessions), Measured Historical Analogue Windows, Original BLS CPI Release Vintages, Empirical Reference/Analogue Baseline (eight-release floor), Expanded Snapshot spy-8c865e107520d2cdab66 (BLS Dec 2022-Jul 2025), Original Snapshot spy-99baca8c94f5871aff6b

### Community 61 - "Scope Gap & Roadmap"
Cohesion: 0.47
Nodes (3): Model Scope Analysis and Next-Chat Handover, APP_MODE=scenario general scenario mode, Product/Modeling Scope Gap (restricted CPI demo vs general scenario engine)

### Community 63 - "OpenAI Roadmap Stages"
Cohesion: 0.50
Nodes (3): OpenAI description/narration relay (api/descriptions.py), OpenAI text interpreter (gpt-5.6-sol), Timeline API endpoints (capabilities/interpret/commit/description/reveal)

## Knowledge Gaps
- **57 isolated node(s):** `SPY Fixed-Base Index Target`, `Headline CPI-U Monthly SA Lever`, `OpenAI Responses API (POST /v1/responses)`, `OpenAI Structured Outputs (text.format json_schema)`, `Real market loader restrictions (data/real_market.py)` (+52 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 319 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_app()` connect `App Factory & Launchers` to `Preset Parser`, `Fixture Service`, `CPI Parser Router`, `API Contracts & Routes`, `Research HTTP Tests`, `Test Suite Imports`, `Durable Service Core`, `Durable Backend Tests`, `Replay & Backends`, `Adapter Test Doubles`, `Scenario Research Tests`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `BackendError` (e.g. with `create_app()` and `Problem`) actually correct?**
  _`BackendError` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `SPY Fixed-Base Index Target`, `Headline CPI-U Monthly SA Lever`, `OpenAI Responses API (POST /v1/responses)` to the rest of the system?**
  _57 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `OpenAI Handover Docs` be split into smaller, more focused modules?**
  _Cohesion score 0.05714285714285714 - nodes in this community are weakly interconnected._
- **Why does `ResearchHTTPTests` connect `Research HTTP Tests` to `Preset Parser`, `CPI Parser Router`, `App Factory & Launchers`, `API Contracts & Routes`, `Test Suite Imports`, `Chronos Market Adapter`, `Replay & Backends`, `Market Evaluation`, `Forecast Engines`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `create_app()` (e.g. with `BackendError` and `Capabilities`) actually correct?**
  _`create_app()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Should `CPI Parser Router` be split into smaller, more focused modules?**
  _Cohesion score 0.0935374149659864 - nodes in this community are weakly interconnected._