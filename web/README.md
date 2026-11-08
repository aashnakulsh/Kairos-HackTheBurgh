# Chohan and Orion's handoff

Generated types live in `src/generated/contracts.ts`. Use shared fixtures while the
API is being implemented. Aashna coordinates one Vite/React scaffold and dependency
lockfile; do not create separate frontend applications.

- Orion: `src/features/workspace/`, composer, panels, API client, committed state,
  `App.tsx` and global layout. Own applying full/suffix updates and revision checks.
- Chohan: `src/features/chart/`, Plotly rendering, markers, viewport, playback.
- Chart receives a complete committed `RunResponse` (workspace has applied suffix),
  selected prompt ID, playhead, viewport and reduced-motion setting. It emits
  `onSelectPrompt(id)` and `onPlayheadChange(date)`. It does not fetch or commit.
- Agree CSS boundaries; chart styles stay scoped. Discuss package changes before
  modifying the shared package file or lockfile.

These are proposed collaboration boundaries, not access restrictions. Run the UI with
`cd web && npm install && npm run dev`, then open http://127.0.0.1:5173.

**Temporary mock (default):** `src/api/mockApi.ts` runs in the browser, draws a fake
1980–2026 baseline and accepts any free-text prompt. It guesses only a date, year or
year range from the text. The server-side OpenAI parser is meant to replace that guess
by translating free text into the canonical `Instruction`. The UI already sends raw
text to `/interpret`, so it needs no change when the parser lands. To use the HTTP
fixture/live API instead, start the server from the root README and run
`VITE_API=server npm run dev` (Vite forwards `/api` to port 8000). `npm run build` type-checks
and bundles. Optional `VITE_BACKGROUND_ASSET=/your.gif` (file in `web/public/`)
replaces the outcome gradient. `src/api/client.ts` now supplies typed calls and
`src/api/applyRun.ts` applies full/suffix cache updates. Use those in the workspace.
Start the local HTTP fixture API using the root README. Fixture mode must visibly say
synthetic example. Node tests exercise the client/cache without React dependencies.
