import type { ChangeEvent } from "react";
import type { Viewport } from "../../generated/contracts.ts";
import { MARGIN } from "./Chart.tsx";

export interface TimelineProps {
  viewport: Viewport;
  onViewportChange: (viewport: Viewport) => void;
}

/** Start/End year boxes under the graph's two ends. Shares the chart's time domain and margins; never fetches. */
export function Timeline({ viewport, onViewportChange }: TimelineProps) {
  const setYear = (key: keyof Viewport) => (event: ChangeEvent<HTMLInputElement>) => {
    const next = { ...viewport, [key]: Number(event.target.value) };
    if (Number.isInteger(next[key]) && next.start_year >= 1900 && next.end_year <= 2100 && next.start_year <= next.end_year) {
      onViewportChange(next);
    }
  };

  return (
    <div className="timeline" style={{ paddingLeft: MARGIN.l, paddingRight: MARGIN.r }}>
      <div className="timeline-range">
        <label className="timeline-box">Start year
          <input type="number" defaultValue={viewport.start_year} min={1900} max={viewport.end_year} onChange={setYear("start_year")} />
        </label>
        <label className="timeline-box">End year
          <input type="number" defaultValue={viewport.end_year} min={viewport.start_year} max={2100} onChange={setYear("end_year")} />
        </label>
      </div>
    </div>
  );
}
