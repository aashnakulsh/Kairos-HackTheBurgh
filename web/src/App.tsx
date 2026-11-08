import { useSyncExternalStore, type MouseEvent } from "react";
import { flushSync } from "react-dom";
import { Chart } from "./features/chart/Chart.tsx";
import { Timeline } from "./features/chart/Timeline.tsx";
import { markers } from "./features/chart/geometry.ts";
import { Composer } from "./features/workspace/Composer.tsx";
import { ImpactList, NarrativePanel, NoteRow } from "./features/workspace/Panels.tsx";
import { segmentTrend } from "./features/workspace/format.ts";
import { useWorkspace } from "./features/workspace/useWorkspace.ts";

const motionQuery = matchMedia("(prefers-reduced-motion: reduce)");
const useReducedMotion = () => useSyncExternalStore(
  notify => { motionQuery.addEventListener("change", notify); return () => motionQuery.removeEventListener("change", notify); },
  () => motionQuery.matches);

// Background layer config: set VITE_BACKGROUND_ASSET=/your.gif (in web/public) to replace the gradient.
const BACKGROUND_ASSET = import.meta.env.VITE_BACKGROUND_ASSET as string | undefined;

export function App() {
  const ws = useWorkspace();
  const reducedMotion = useReducedMotion();
  const prompts = ws.run?.prompts ?? [];
  const shownId = ws.selectedId ?? ws.focusId;
  const shown = prompts.find(p => p.id === shownId);
  const points = ws.run?.series.points ?? [];
  const trend = segmentTrend(points, shown?.id ?? null);
  const replacing = prompts.find(p => p.id === ws.selectedId)?.display_number ?? null;
  const greyYears = new Set(markers(prompts).flatMap(m => m.years));

  // The first submit morphs the centred composer into its workspace slot (a one-time transition).
  const submit = () => {
    if (ws.started || reducedMotion || !document.startViewTransition) return void ws.submit();
    document.startViewTransition(() => flushSync(() => void ws.submit()));
  };

  const selected = prompts.find(p => p.id === ws.selectedId);
  const trends = Object.fromEntries(prompts.map(p => [p.id, segmentTrend(points, p.id)]));

  // Clicking empty space (not a control, link, input or the composer) clears the selection.
  const deselectOnBackground = (event: MouseEvent<HTMLElement>) => {
    if (!(event.target as Element).closest("button, a, input, textarea, select, summary, label, form")) ws.cancelSelection();
  };

  const composer = (
    <Composer text={ws.text} replacing={replacing} count={ws.started ? prompts.length : null} pending={ws.pending} notice={ws.notice} reducedMotion={reducedMotion}
      onChange={ws.setText} onSubmit={submit} onCancel={ws.cancelSelection} />
  );

  if (!ws.started) {
    return (
      <main className="intro">
        <h1 className="visually-hidden">US Market What If?</h1>
        {composer}
        {ws.capsFailed && <p className="intro-error">Couldn't reach the server. <button type="button" className="button button-quiet" onClick={ws.loadCaps}>Retry</button></p>}
      </main>
    );
  }

  return (
    <main className="workspace" data-trend={trend.direction} onClick={deselectOnBackground}>
      <div className="backdrop" aria-hidden="true">
        {(["gain", "loss", "flat"] as const).map(tone => <div key={tone} className={`backdrop-${tone}`} />)}
        {BACKGROUND_ASSET && !reducedMotion && <img className="backdrop-asset" src={BACKGROUND_ASSET} alt="" />}
      </div>
      <header className="workspace-bar">
        <h1>US Market What If?</h1>
        <span className="data-label">{ws.run?.data_label ?? ws.caps?.data_label}</span>
        {ws.caps && <span>Data {ws.caps.coverage.first_session} to {ws.caps.coverage.last_session}</span>}
        <button type="button" className="button button-quiet" onClick={ws.toggleReveal} aria-pressed={ws.reveal !== null}
          disabled={!ws.reveal && !points.some(p => p.kind === "simulated")}>
          {ws.reveal ? "Hide actual history" : "Reveal actual history"}
        </button>
      </header>
      <section className="stage">
        {selected
          ? <NarrativePanel prompt={selected} panel={ws.run?.panels[selected.id]} trend={trends[selected.id]} />
          : !!prompts.length && <NoteRow prompts={prompts} trends={trends} onSelect={ws.selectPrompt} />}
        <Chart run={ws.run} draw={ws.draw} viewport={ws.viewport} selectedId={ws.selectedId} playhead={ws.playhead}
          reveal={ws.reveal} reducedMotion={reducedMotion} onSelectPrompt={ws.selectPrompt} onDeletePrompt={ws.deletePrompt} />
        <Timeline viewport={ws.viewport} greyYears={greyYears} points={points} playhead={ws.playhead}
          onViewportChange={ws.setViewport} onPlayheadChange={ws.setPlayhead} />
      </section>
      {composer}
      <ImpactList panel={shown && ws.run?.panels[shown.id]} />
    </main>
  );
}
