import type { Point, Prompt, Viewport } from "../../generated/contracts.ts";

/** Pure chart/timeline math. No React or Plotly, so Node tests can import it. */

/** "YYYY-MM-DD" (or a longer ISO string) → UTC milliseconds. Session labels have no time zone. */
export const ms = (iso: string) => Date.parse(iso.slice(0, 10));

/** One time domain shared by the chart, the year scale and the scrubber. */
export function domain(viewport: Viewport): [number, number] {
  return [Date.UTC(viewport.start_year, 0, 1), Date.UTC(viewport.end_year + 1, 0, 1)];
}

export const fraction = (t: number, [a, b]: [number, number]) => (t - a) / (b - a);

export const isoDay = (t: number) => new Date(t).toISOString().slice(0, 10);

export interface Marker {
  id: string;
  label: string;
  start: string;
  end: string | null;
  years: number[];
  title: string;
}

/** A dashed line at the resolved session; intervals add an end line and band. Years stay semantic. */
export function markers(prompts: Prompt[]): Marker[] {
  return prompts.map(p => {
    const first = Number(p.requested_start.slice(0, 4));
    const last = Number((p.requested_end ?? p.requested_start).slice(0, 4));
    const span = p.requested_end ? `${p.requested_start} to ${p.requested_end}` : p.requested_start;
    const session = p.effective_start === p.requested_start ? "" : `, session ${p.effective_start}`;
    return {
      id: p.id,
      label: `Prompt ${p.display_number}`,
      start: p.effective_start,
      end: p.date_precision === "interval" ? (p.effective_end ?? p.requested_end) : null,
      years: Array.from({ length: last - first + 1 }, (_, i) => first + i),
      title: `Prompt ${p.display_number}: ${span}${session}`,
    };
  });
}

/** Greedy label stacking: returns a row per input x so labels closer than minGap never overlap. */
export function stackRows(xs: number[], minGap: number): number[] {
  const rows: number[] = new Array(xs.length);
  const rowEnds: number[] = [];
  [...xs.keys()].sort((a, b) => xs[a] - xs[b]).forEach(i => {
    let row = rowEnds.findIndex(end => xs[i] - end >= minGap);
    if (row === -1) row = rowEnds.length;
    rowEnds[row] = xs[i];
    rows[i] = row;
  });
  return rows;
}

const lerp = (a: number | null, b: number | null, t: number) => (a === null || b === null ? null : a + (b - a) * t);

/** Points up to `head`, plus one interpolated point so the line grows smoothly between sessions. */
export function clipPoints(points: Point[], head: number): Point[] {
  const kept = points.filter(p => ms(p.date) <= head);
  const prev = kept.at(-1);
  const next = points[kept.length];
  if (!prev || !next || prev.value === null || next.value === null) return kept;
  const t = (head - ms(prev.date)) / (ms(next.date) - ms(prev.date));
  if (t <= 0) return kept;
  return [...kept, {
    ...next,
    date: new Date(head).toISOString().replace("T", " ").slice(0, 19),
    value: lerp(prev.value, next.value, t),
    q10: lerp(next.kind === prev.kind ? prev.q10 : prev.value, next.q10, t),
    q90: lerp(next.kind === prev.kind ? prev.q90 : prev.value, next.q90, t),
  }];
}

/** Where the draw starts: the first point for a full draw, else the last retained point before changed_from. */
export function drawStart(points: Point[], changedFrom: string | null): number {
  if (!changedFrom) return points.length ? ms(points[0].date) : 0;
  const before = points.filter(p => p.date < changedFrom).at(-1);
  return ms(before?.date ?? changedFrom);
}

/** Fixed y-axis for the whole series so an animation never rescales it. */
export function yRange(points: Point[]): [number, number] {
  const values = points.flatMap(p => [p.value, p.q10, p.q90]).filter((v): v is number => v !== null);
  if (!values.length) return [90, 110];
  const lo = Math.min(...values), hi = Math.max(...values);
  const pad = Math.max((hi - lo) * 0.08, 0.5);
  return [lo - pad, hi + pad];
}

/** Cached value at the playhead: the last point on or before it. Never interpolates or fetches. */
export function pointAt(points: Point[], day: string): Point | null {
  return points.filter(p => p.date <= day).at(-1) ?? null;
}
