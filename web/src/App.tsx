import { useEffect, useState, useSyncExternalStore, type MouseEvent } from "react";
import { flushSync } from "react-dom";
import { Chart } from "./features/chart/Chart.tsx";
import { Timeline } from "./features/chart/Timeline.tsx";
import { Composer } from "./features/workspace/Composer.tsx";
import { EndScreen } from "./features/workspace/EndScreen.tsx";
import { Instructions } from "./features/workspace/Instructions.tsx";
import { ImpactList, NarrativePanel, NoteRow } from "./features/workspace/Panels.tsx";
import { nextDisplayNumber, segmentTrend } from "./features/workspace/format.ts";
import { useWorkspace } from "./features/workspace/useWorkspace.ts";
import { PixelSea, type SeaMode } from "./features/workspace/PixelSea.tsx";

const motionQuery = matchMedia("(prefers-reduced-motion: reduce)");
const useReducedMotion = () => useSyncExternalStore(
  notify => { motionQuery.addEventListener("change", notify); return () => motionQuery.removeEventListener("change", notify); },
  () => motionQuery.matches);

// Background layer config: set VITE_BACKGROUND_ASSET=/your.gif (in web/public) to replace the pixel sea.
const BACKGROUND_ASSET = import.meta.env.VITE_BACKGROUND_ASSET as string | undefined;

/** Any gain is sunny, any loss stormy; bigger moves make stronger weather. */
const moodOf = (change: number | null) =>
  change === null || Math.abs(change) < 0.05 ? 0 : Math.sign(change) * (0.4 + 0.6 * Math.min(Math.abs(change) / 10, 1));

export function App() {
  const ws = useWorkspace();
  const reducedMotion = useReducedMotion();
  const prompts = ws.run?.prompts ?? [];
  const shownId = ws.selectedId ?? ws.focusId;
  const shown = prompts.find(p => p.id === shownId);
  const points = ws.run?.series.points ?? [];
  const trend = segmentTrend(points, shown?.id ?? null);
  const replacing = prompts.find(p => p.id === ws.selectedId)?.display_number ?? null;
  const mood = moodOf(trend.direction === "flat" ? 0 : trend.change);
  const outlook = mood > 0 ? "☀ Sunny" : mood < 0 ? "⛈ Stormy" : "Calm";

  // Game phases: start screen → voyage (one prompt per leg) → end screen, only when the player chooses
  // "End journey" after every leg is written. Never forced: they may keep editing prompts first.
  const finished = ws.started && ws.legs !== null && prompts.length >= ws.legs;
  const [endRequested, setEndRequested] = useState(false);
  useEffect(() => { if (!finished) setEndRequested(false); }, [finished]); // a deleted leg reopens the voyage
  const ended = finished && endRequested;
  useEffect(() => { if (ended) ws.requestSummary(); }, [ended, ws.run?.revision]);

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

  const backdrop = (mode: SeaMode, seaMood: number, progress: number) => (
    <div className="backdrop" aria-hidden="true">
      {BACKGROUND_ASSET && !reducedMotion
        ? <img className="backdrop-asset" src={BACKGROUND_ASSET} alt="" />
        : <PixelSea mode={mode} mood={seaMood} progress={progress} reducedMotion={reducedMotion} />}
    </div>
  );

  const composer = (
    <Composer text={ws.text} replacing={replacing} count={ws.started ? prompts.length : null} legs={ws.legs}
      nextNumber={nextDisplayNumber(prompts)} used={ws.used}
      pending={ws.pending} notice={ws.notice} reducedMotion={reducedMotion}
      onChange={ws.setText} onLegsChange={ws.setLegs} onSubmit={submit} onCancel={ws.cancelSelection} />
  );

  if (!ws.started) {
    return (
      <main className="intro">
        {backdrop("start", 0.35, 0)}
        <h1 className="game-title game-title-start">US Market What If?</h1>
        <Instructions />
        {composer}
        {ws.capsFailed && <p className="intro-error">Couldn't reach the server. <button type="button" className="button button-quiet" onClick={ws.loadCaps}>Retry</button></p>}
      </main>
    );
  }

  if (ended) {
    const startLevel = points.findLast(p => p.kind === "observed")?.value ?? null;
    const endLevel = points.at(-1)?.value ?? null;
    const net = ws.summary?.net_change_percent ?? (startLevel && endLevel ? (endLevel / startLevel - 1) * 100 : null);
    return (
      <main className="endscreen">
        {backdrop("end", moodOf(net), 1)}
        <EndScreen summary={ws.summary} onRestart={ws.newJourney} onReview={() => setEndRequested(false)} />
      </main>
    );
  }

  return (
    <main className="workspace" data-trend={trend.direction} onClick={deselectOnBackground}>
      {/* Each prompt is one leg: the ship sails from the left dock to the right as prompts are added. */}
      {backdrop("voyage", mood, ws.legs ? Math.min(prompts.length / ws.legs, 1) : 0)}
      <header className="workspace-bar">
        <h1 className="game-title">US Market What If?</h1>
        <span className="data-label">{ws.run?.data_label ?? ws.caps?.data_label}</span>
        {ws.caps && <span>Data {ws.caps.coverage.first_session} to {ws.caps.coverage.last_session}</span>}
        <span className="voyage">Voyage {prompts.length} / {ws.legs} · {ws.pending ? `${ws.pending}…` : outlook}</span>
        <button type="button" className="button button-reveal" onClick={ws.toggleReveal} aria-pressed={ws.reveal !== null}
          disabled={!ws.reveal && !points.some(p => p.kind === "simulated")}>
          {ws.reveal ? "Hide actual history" : "Reveal actual history"}
        </button>
      </header>
      {finished && <button type="button" className="button end-journey" onClick={() => setEndRequested(true)}>End journey</button>}
      <section className="stage">
        {selected
          ? <NarrativePanel prompt={selected} panel={ws.run?.panels[selected.id]} trend={trends[selected.id]} description={ws.description?.prompt_id === selected.id ? ws.description.description : undefined} />
          : !!prompts.length && <NoteRow prompts={prompts} trends={trends} onSelect={ws.selectPrompt} />}
        <Chart run={ws.run} draw={ws.draw} viewport={ws.viewport} selectedId={ws.selectedId}
          canDelete={!ws.serverMode} reveal={ws.reveal} reducedMotion={reducedMotion} onSelectPrompt={ws.selectPrompt} onDeletePrompt={ws.deletePrompt} />
        <Timeline viewport={ws.viewport} onViewportChange={ws.setViewport} />
      </section>
      {composer}
      <ImpactList panel={shown && ws.run?.panels[shown.id]} />
    </main>
  );
}
