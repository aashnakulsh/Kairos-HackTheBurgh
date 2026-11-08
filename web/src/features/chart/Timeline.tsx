import type { ChangeEvent } from "react";
import type { Point, Viewport } from "../../generated/contracts.ts";
import { MARGIN } from "./Chart.tsx";
import { domain, isoDay, ms, pointAt } from "./geometry.ts";

const DAY = 86_400_000;

export interface TimelineProps {
  viewport: Viewport;
  greyYears: Set<number>;
  points: Point[];
  playhead: string | null;
  onViewportChange: (viewport: Viewport) => void;
  onPlayheadChange: (day: string) => void;
}

/** Year scale, scrubber and viewport settings. Shares the chart's time domain and margins; never fetches. */
export function Timeline({ viewport, greyYears, points, playhead, onViewportChange, onPlayheadChange }: TimelineProps) {
  const [start, end] = domain(viewport);
  const years = Array.from({ length: viewport.end_year - viewport.start_year + 1 }, (_, i) => viewport.start_year + i);
  const step = years.length <= 15 ? 1 : years.length <= 30 ? 2 : years.length <= 60 ? 5 : 10;
  const days = Math.round((end - start) / DAY) - 1;
  const value = playhead ? Math.round((ms(playhead) - start) / DAY) : days;
  const cached = playhead ? pointAt(points, playhead) : null;
  const readout = !playhead ? "No playhead" : cached?.value != null
    ? `${playhead} · ${cached.value.toFixed(2)} (${cached.kind}, cached ${cached.date})`
    : `${playhead} · no data`;

  const setYear = (key: keyof Viewport) => (event: ChangeEvent<HTMLInputElement>) => {
    const next = { ...viewport, [key]: Number(event.target.value) };
    if (Number.isInteger(next[key]) && next.start_year >= 1900 && next.end_year <= 2100 && next.start_year <= next.end_year) {
      onViewportChange(next);
    }
  };

  return (
    <div className="timeline" style={{ paddingLeft: MARGIN.l, paddingRight: MARGIN.r }}>
      <div className="timeline-scale" aria-hidden="true">
        {years.map(year => (
          <span key={year} className="timeline-year" data-active={greyYears.has(year) || undefined}>
            {year % step === 0 ? year : ""}
          </span>
        ))}
      </div>
      <input className="timeline-scrubber" type="range" min={0} max={days} value={Math.min(Math.max(value, 0), days)}
        aria-label="Playhead date" aria-valuetext={readout}
        onChange={event => onPlayheadChange(isoDay(start + Number(event.target.value) * DAY))} />
      <div className="timeline-meta">
        <output className="timeline-readout" aria-live="polite">{readout}</output>
        <details className="timeline-settings">
          <summary>Visible years</summary>
          <label>From <input type="number" defaultValue={viewport.start_year}
            min={1900} max={viewport.end_year} onChange={setYear("start_year")} /></label>
          <label>To <input type="number" defaultValue={viewport.end_year}
            min={viewport.start_year} max={2100} onChange={setYear("end_year")} /></label>
        </details>
      </div>
    </div>
  );
}
