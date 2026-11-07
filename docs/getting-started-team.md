# Start building together

This foundation provides schemas, generated TypeScript and synthetic response files.
It is not yet a runnable frontend/backend. It reduces interface drift; it cannot
guarantee conflict-free merges. Do not wait for four finished branches to integrate.

## 1. Establish one shared starting point

Have Aashna review this foundation alongside architecture.md. Foundation task:
[issue #3](https://github.com/aashnakulsh/TeamRelay-Hackathon/issues/3), branch
`3-foundation-contract-placeholders`. Merge only after explicit human authorization.
Everyone then updates their own clean clone
from main and creates a separate task branch. One editing agent per working folder.

Agree contract changes with Aashna, especially the remaining capabilities, draft and
reveal payloads. Add those to api/contracts.py and regenerate; never edit generated
TypeScript independently. Agree the typed forecast segment adapter before wiring it.

## 2. Start these tasks in parallel

| Person | Start now | First handoff |
|---|---|---|
| Aashna | Scaffold one FastAPI app and coordinate one Vite app; pin dependencies; finish endpoint schemas | Browser can call a fixture-backed route; startup instructions and matching types |
| Aditya | Verify data rights/coverage, build manifest and session mapping; smoke-test pretrained inference | Two eligible release windows, typed supported/unsupported forecast result and reproducible command |
| Chohan | Build chart/timeline components against shared fixtures after the common Vite scaffold | Observed/simulated styles, marker selection and suffix redraw |
| Orion | Build shell/composer/panels, API client and committed state after that scaffold | Submit/select/edit/cancel flows and preserved state on failure |

Aashna owns replay, transactions and idempotency; Aditya supplies numerical segments.
Do not both implement the coordinator. Orion owns App.tsx, layout and workspace state;
Chohan owns scoped chart components. Coordinate shared dependency/CSS edits first.
These are working boundaries, not exclusive ownership restrictions.

Aditya can investigate data/model feasibility while Aashna scaffolds. Frontend owners
can agree props/layout meanwhile; neither needs to wait for the real model to render
synthetic fixtures. Keep synthetic labels visible.

## 3. Test from the first handoff

Before implementing, Chohan and Orion should create one shared Google Doc listing what
they need from Aashna and Aditya and share its link on board issue #1. For each need,
record the UI action, endpoint/field or callback, example payload, loading/error/null
behavior, units/dates, acceptance check, priority and backend owner. Mark open decisions
explicitly. Aashna and Aditya respond with agreed behavior or constraints. The Doc is
for discussion; accepted decisions must enter the repository contracts/fixtures/docs
through a PR so it does not become a competing source of truth. Do not put secrets or
restricted data in it. No Google Doc has been created by this foundation change.

Run now with Python and Pydantic v2:

```sh
python tools/export_contracts.py --check
python tools/check_fixtures.py
```

These check schema drift and fixture consistency, not a running application.
Aashna adds these to CI with backend tests and frontend typecheck/build once scaffolded.

First integration: browser -> FastAPI -> synthetic result -> chart. Merge this small
vertical slice early. Next swap in Aditya's real adapter without changing the UI shape.
Then add persistence, three-prompt replay, and parser/narrator providers. Keep a
deterministic fixture path for UI development; never disguise it as model output.

Backend checks: stale revision, duplicate request, replacement stable IDs, atomic
failure, restore, earlier/later date moves and unchanged prefix. Shared three-prompt
acceptance: 0.4/0.5/0.5 becomes 0.2/0.3/0.3 after replacing the first input. The current
fixtures only cover a single prompt and suffix behavior; add this full replay test
when the coordinator exists.

Aditya checks session alignment, units, missing data, cutoff leakage, quantile ordering,
unsupported ranges and chronological baseline evaluation. Frontend owners check empty,
loading, clarification, conflict, shorter/empty suffix, stale response, edit/cancel,
keyboard and reduced motion. Final team rehearsal checks real host/browser operation,
reload, provider failure, actual-outcome reveal and three-prompt edits.

## 4. Commit, push, review and merge repeatedly

Each person gets a task issue and uses this sequence from a clean working tree:

```sh
git checkout main
git pull --ff-only
git checkout -b <issue-number>-<slug>
```

1. Implement a small coherent part; inspect diff and run relevant checks.
2. When authorized, stage only intended files and commit locally. A commit is a saved
   checkpoint, not a change to main. Never stage .board, credentials or local data.
3. Before first push, fetch origin; rebase the unpublished branch on origin/main if
   needed. Stop on ambiguous conflicts. Rerun checks affected by updates.
4. When authorized, push the task branch and open a PR with `Closes #TASK_NUMBER`.
   A draft PR can share an incomplete handoff. Push does not mean merge.
5. Aashna reviews, checks CI and integration behavior, and merges with explicit human
   authorization. Announce changed contracts only when posting is authorized.
6. Others bring updated main into their task branches regularly. On already shared
   branches, merge origin/main without force-pushing/replacing shared history.

Merge foundation first, then small compatible frontend/backend slices, real data/model
adapter, replay and recovery. Integrate after each useful handoff, not only at the end.
If two branches change a contract, settle the shared shape before merging either.

## 5. Suggested first instructions to your agents

Aditya: "Read AGENTS.md and the team guide. Implement the data manifest and two-window
loader on my task branch; agree the forecast adapter with Aashna. Test timestamps,
units and missing coverage. Do not commit, push, post or merge without my instruction."

Aashna: "Read AGENTS.md and the team guide. Finish the shared API contracts, coordinate
the common scaffold, and implement the first fixture-backed browser/API flow. Keep
Aditya's model behind the agreed segment interface. Test and report before publishing."

Chohan: "Build the chart components against shared fixtures and the agreed workspace
props. Coordinate with Orion before editing shared layout or dependencies. Test marker
selection, empty/short suffix rendering and reduced motion."

Orion: "Build the shell, composer and committed workspace state using generated types.
Coordinate chart props with Chohan. Preserve state on failed/stale responses; test
submit, select, edit and cancel against the shared fixtures."
