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

These are proposed collaboration boundaries, not access restrictions. There is no
runnable frontend yet. Fixture mode must visibly say synthetic example.
