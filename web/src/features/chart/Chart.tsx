import { useEffect, useLayoutEffect, useRef, useState } from "react";
import Plotly, { type Data, type Shape } from "plotly.js-dist-min";
import type { Point, RevealResponse, RunResponse, Viewport } from "../../generated/contracts.ts";
import { clipPoints, domain, drawStart, fraction, isoDay, markers, ms, stackRows, yRange } from "./geometry.ts";
import "./chart.css";

/** Plot margins in px; Timeline uses the same left/right so the scale and scrubber line up. */
export const MARGIN = { l: 56, r: 24, b: 28 };
const LABEL_ROW = 24;
const LABEL_GAP = 84;
const FULL_DRAW_MS = 1200;
const EDIT_DRAW_MS = 700;

export interface ChartProps {
  run: RunResponse | null;
  /** Which committed revision to draw: `from` null = full draw, a date = suffix only. */
  draw: { revision: number; from: string | null; animate: boolean } | null;
  viewport: Viewport;
  selectedId: string | null;
  playhead: string | null;
  reveal: RevealResponse | null;
  reducedMotion: boolean;
  onSelectPrompt: (id: string) => void;
}

const only = (points: Point[], keep: (p: Point, next: Point | undefined) => boolean, field: "value" | "q10" | "q90" = "value") =>
  points.map((p, i) => (keep(p, points[i + 1]) ? p[field] : null));
// Simulated traces also include the observed point just before them, so the fork joins up.
const simulatedish = (p: Point, next: Point | undefined) =>
  p.kind === "simulated" || (p.kind === "observed" && next?.kind === "simulated");

export function Chart({ run, draw, viewport, selectedId, playhead, reveal, reducedMotion, onSelectPrompt }: ChartProps) {
  const plotRef = useRef<HTMLDivElement>(null);
  const [{ width, height }, setSize] = useState({ width: 0, height: 0 });
  const [head, setHead] = useState(Infinity);
  const points = run?.series.points ?? [];
  const animating = head !== Infinity;

  useEffect(() => {
    const el = plotRef.current!;
    // Plotly's own `responsive` only follows the window; this follows the box (e.g. the panel above growing).
    const observer = new ResizeObserver(([entry]) => setSize({ width: entry.contentRect.width, height: entry.contentRect.height }));
    observer.observe(el);
    return () => { observer.disconnect(); Plotly.purge(el); };
  }, []);

  // A new revision cancels the previous draw and animates only what changed.
  // Layout effect: the clipped start is set before paint, so the full new line never flashes.
  useLayoutEffect(() => {
    if (!draw?.animate || reducedMotion || !points.length) { setHead(Infinity); return; }
    const start = drawStart(points, draw.from);
    const end = ms(points[points.length - 1].date);
    if (end <= start) { setHead(Infinity); return; }
    const duration = draw.from ? EDIT_DRAW_MS : FULL_DRAW_MS;
    const began = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min((now - began) / duration, 1);
      const eased = 1 - (1 - t) ** 3; // ease-out: the line starts moving the moment the commit lands
      setHead(t === 1 ? Infinity : start + (end - start) * eased);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    setHead(start);
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [draw?.revision, reducedMotion]); // keyed on revision only: its points arrive with it

  const marks = markers(run?.prompts ?? []);
  const range = domain(viewport);
  const plotWidth = Math.max(width - MARGIN.l - MARGIN.r, 1);
  const xOf = (day: string) => MARGIN.l + fraction(ms(day), range) * plotWidth;
  const visibleMarks = marks.filter(m => ms(m.start) >= range[0] && ms(m.start) < range[1]);
  const rows = stackRows(visibleMarks.map(m => xOf(m.start)), LABEL_GAP);
  const top = (Math.max(-1, ...rows) + 1) * LABEL_ROW + 12;
  const forkDate = points.find(p => p.kind === "simulated")?.date;
  const segments = new Set(points.map(p => p.segment_id).filter(Boolean));

  useEffect(() => {
    const shown = clipPoints(points, head);
    const x = shown.map(p => p.date);
    const grey = "rgba(163, 163, 163, 0.55)";
    const traces: Data[] = [
      { x, y: only(shown, simulatedish, "q90"), mode: "lines", line: { width: 0 }, hoverinfo: "skip", name: "90th percentile" },
      { x, y: only(shown, simulatedish, "q10"), mode: "lines", line: { width: 0 }, fill: "tonexty",
        fillcolor: "rgba(125, 211, 252, 0.18)", hoverinfo: "skip", name: "10th percentile" },
      { x, y: only(shown, p => p.kind === "observed"), mode: "lines", name: "Observed",
        line: { color: "#e5e5e5", width: 2 } },
      { x, y: only(shown, simulatedish), mode: "lines", name: "Simulated median",
        line: { color: "#7dd3fc", width: 2.5, dash: "dot" } },
    ];
    if (reveal) traces.push({ x: reveal.series.points.map(p => p.date), y: reveal.series.points.map(p => p.value),
      mode: "lines", name: "Actual (revealed)", line: { color: "#fbbf24", width: 1.5 } });

    const shapes: Partial<Shape>[] = marks.flatMap(m => {
      const line = { color: m.id === selectedId ? "rgba(255,255,255,0.9)" : grey, width: m.id === selectedId ? 2 : 1, dash: "dash" as const };
      const edge = (day: string) => ({ type: "line" as const, xref: "x" as const, yref: "paper" as const, x0: day, x1: day, y0: 0, y1: 1, line });
      if (!m.end) return [edge(m.start)];
      return [{ type: "rect" as const, xref: "x" as const, yref: "paper" as const, x0: m.start, x1: m.end, y0: 0, y1: 1,
        fillcolor: "rgba(163, 163, 163, 0.10)", line: { width: 0 } }, edge(m.start), edge(m.end)];
    });
    if (forkDate) shapes.push({ type: "line", xref: "x", yref: "paper", x0: forkDate, x1: forkDate, y0: 0, y1: 1,
      line: { color: "rgba(125, 211, 252, 0.5)", width: 1, dash: "dot" } });

    if (!width || !height) return;
    Plotly.react(plotRef.current!, traces, {
      width, height,
      margin: { ...MARGIN, t: top },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0.25)",
      font: { color: "#d4d4d4", family: "inherit", size: 12 },
      showlegend: false,
      hovermode: "x unified",
      hoverlabel: { bgcolor: "#171717", bordercolor: "#404040" },
      xaxis: { type: "date", range: [isoDay(range[0]), isoDay(range[1])], fixedrange: true, gridcolor: "rgba(255,255,255,0.06)" },
      yaxis: { range: yRange(points), fixedrange: true, gridcolor: "rgba(255,255,255,0.06)", zeroline: false },
      shapes,
      annotations: forkDate ? [{ x: forkDate, xref: "x", yref: "paper", y: 0, yanchor: "bottom", xanchor: "left",
        text: "simulated →", showarrow: false, font: { color: "#7dd3fc", size: 11 } }] : [],
    }, { displayModeBar: false });
  }, [run, head, range[0], range[1], selectedId, reveal, top, width, height]); // the playhead is an HTML overlay: scrubbing never repaints Plotly

  const caption = run && <>
    <span>{run.series.target_id} · indexed level ({run.series.base_date} = {run.series.base_value})</span>
    <span className="chart-key"><i className="key-observed" />observed</span>
    <span className="chart-key"><i className="key-simulated" />simulated median</span>
    <span className="chart-key"><i className="key-band" />10–90% range</span>
    {reveal && <span className="chart-key"><i className="key-reveal" />actual</span>}
    <span>model: {[...new Set(points.map(p => p.engine).filter(Boolean))].join(", ") || "none yet"}</span>
  </>;

  return (
    <figure className="chart" aria-label="Forecast chart">
      <figcaption className="chart-caption">
        {caption}
        {segments.size > 1 && <span>Later bands are conditional on the preceding simulated median.</span>}
        {animating && <button type="button" className="chart-skip" onClick={() => setHead(Infinity)}>Skip animation</button>}
      </figcaption>
      <div className="chart-plot">
        <div ref={plotRef} className="chart-canvas" />
        {visibleMarks.map((m, i) => (
          <button key={m.id} type="button" className="chart-marker" aria-pressed={m.id === selectedId}
            aria-label={`${m.title}. Select to replace.`}
            style={{ left: xOf(m.start), top: rows[i] * LABEL_ROW + 4 }}
            onClick={() => onSelectPrompt(m.id)}>
            {m.label}
            <span className="chart-tooltip" aria-hidden="true">{m.title}</span>
          </button>
        ))}
        {playhead && ms(playhead) >= range[0] && ms(playhead) < range[1] &&
          <div className="chart-playhead" style={{ left: xOf(playhead), top }} aria-hidden="true" />}
      </div>
    </figure>
  );
}
