import { useEffect, useLayoutEffect, useRef, useState } from "react";
import Plotly, { type Data, type Shape } from "plotly.js-dist-min";
import type { Point, RevealResponse, RunResponse, Viewport } from "../../generated/contracts.ts";
import { clipPoints, domain, drawStart, fraction, isoDay, markers, ms, stackRows, yRange } from "./geometry.ts";
import "./chart.css";

/** Plot margins in px; Timeline uses the same left/right so the scale and scrubber line up. */
export const MARGIN = { l: 56, r: 24, b: 28 };
const LABEL_ROW = 24;
const LABEL_GAP = 84;
const CHART_FONT = "Helvetica Neue, Helvetica, Arial, sans-serif";
/** y-axis value where the background sea's surface sits. */
const SEA_LEVEL = 2000;
const TOOLTIP_HALF = 130; // half of .chart-tooltip's 240px max-width, plus a little air
const FULL_DRAW_MS = 1200;
const EDIT_DRAW_MS = 700;

export interface ChartProps {
  run: RunResponse | null;
  /** Which committed revision to draw: `from` null = full draw, a date = suffix only. */
  draw: { revision: number; from: string | null; animate: boolean } | null;
  viewport: Viewport;
  selectedId: string | null;
  reveal: RevealResponse | null;
  reducedMotion: boolean;
  onSelectPrompt: (id: string) => void;
  onDeletePrompt: (id: string) => void;
}

const only = (points: Point[], keep: (p: Point, next: Point | undefined) => boolean, field: "value" | "q10" | "q90" = "value") =>
  points.map((p, i) => (keep(p, points[i + 1]) ? p[field] : null));
// Simulated traces also include the observed point just before them, so the fork joins up.
const simulatedish = (p: Point, next: Point | undefined) =>
  p.kind === "simulated" || (p.kind === "observed" && next?.kind === "simulated");

export function Chart({ run, draw, viewport, selectedId, reveal, reducedMotion, onSelectPrompt, onDeletePrompt }: ChartProps) {
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
  // Same plot size, adjusted y scale: the top always clears the sea line, so the ship (sea → y max) always has room.
  const [yLo, dataHi] = yRange(points);
  const yHi = Math.max(dataHi, SEA_LEVEL * 1.25);
  // Pixel y of SEA_LEVEL inside the plot, clamped to the plot area; the background sea reads it from data-sea-y.
  const seaY = Math.min(Math.max(top + ((yHi - SEA_LEVEL) / (yHi - yLo)) * (height - MARGIN.b - top), top), height - MARGIN.b);
  const forkDate = points.find(p => p.kind === "simulated")?.date;
  const segments = new Set(points.map(p => p.segment_id).filter(Boolean));

  useEffect(() => {
    const shown = clipPoints(points, head);
    const x = shown.map(p => p.date);
    const traces: Data[] = [
      { x, y: only(shown, simulatedish, "q90"), mode: "lines", line: { width: 0 }, hoverinfo: "skip", name: "90th percentile" },
      { x, y: only(shown, simulatedish, "q10"), mode: "lines", line: { width: 0 }, fill: "tonexty",
        fillcolor: "rgba(244, 114, 182, 0.28)", hoverinfo: "skip", name: "10th percentile" }, // pink: contrasts with the blue median and the sea
      { x, y: only(shown, p => p.kind === "observed"), mode: "lines", name: "Observed",
        line: { color: "#e5e5e5", width: 2 } },
      { x, y: only(shown, simulatedish), mode: "lines", name: "Simulated median",
        line: { color: "#7dd3fc", width: 2.5, dash: "dot" } },
    ];
    if (reveal) traces.push({ x: reveal.series.points.map(p => p.date), y: reveal.series.points.map(p => p.value),
      mode: "lines", name: "Actual (revealed)", line: { color: "#fbbf24", width: 1.5 } });

    // Every prompt line is the same pink dash, selected or not (the yellow label shows selection).
    const line = { color: "#f472b6", width: 1.5, dash: "dash" as const };
    const shapes: Partial<Shape>[] = marks.flatMap(m => {
      const edge = (day: string) => ({ type: "line" as const, xref: "x" as const, yref: "paper" as const, x0: day, x1: day, y0: 0, y1: 1, line });
      // The prompt's semantic year(s), greyed as a thin strip along the plot's bottom edge.
      const years = m.years.map(y => ({ type: "rect" as const, xref: "x" as const, yref: "paper" as const, layer: "below" as const,
        x0: `${y}-01-01`, x1: `${y + 1}-01-01`, y0: 0, y1: 0.03, fillcolor: "rgba(163, 163, 163, 0.55)", line: { width: 0 } }));
      if (!m.end) return [...years, edge(m.start)];
      return [...years, { type: "rect" as const, xref: "x" as const, yref: "paper" as const, x0: m.start, x1: m.end, y0: 0, y1: 1,
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
      // A concrete family, not "inherit": Plotly measures label text with it, so boxes fit their values.
      font: { color: "#d4d4d4", family: CHART_FONT, size: 12 },
      showlegend: false,
      hovermode: "x unified",
      // namelength -1: never truncate "Simulated median" / "Observed"; larger text so the whole value shows.
      hoverlabel: { bgcolor: "#4a2a10", bordercolor: "#7a4a22", namelength: -1, font: { family: CHART_FONT, size: 14, color: "#fbbf24" } },
      xaxis: { type: "date", range: [isoDay(range[0]), isoDay(range[1])], fixedrange: true, gridcolor: "rgba(255,255,255,0.06)" },
      yaxis: { range: [yLo, yHi], hoverformat: ",.2f", fixedrange: true, gridcolor: "rgba(255,255,255,0.06)", zeroline: false },
      shapes,
      annotations: forkDate ? [{ x: forkDate, xref: "x", yref: "paper", y: 0, yanchor: "bottom", xanchor: "left",
        text: "simulated →", showarrow: false, font: { color: "#7dd3fc", size: 11 } }] : [],
    }, { displayModeBar: false });
  }, [run, head, range[0], range[1], selectedId, reveal, top, width, height]);

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
      {/* Small vertical legend pinned to the screen's bottom-left corner (in flow on narrow screens). */}
      <figcaption className="chart-legend">
        {caption}
        {segments.size > 1 && <span>Later bands are conditional on the preceding simulated median.</span>}
      </figcaption>
      <div className="chart-caption">
        {animating && <button type="button" className="chart-skip" onClick={() => setHead(Infinity)}>Skip animation</button>}
      </div>
      {/* The background ship floats on data-sea-y and its mast tip reaches data-top-y (the y-axis maximum). */}
      <div className="chart-plot" data-sea-y={height ? Math.round(seaY) : undefined} data-top-y={height ? top : undefined}>
        <div ref={plotRef} className="chart-canvas" />
        {visibleMarks.map((m, i) => (
          // Wrapper, not a button: the delete × is a sibling button (buttons cannot nest).
          <div key={m.id} className="chart-marker" data-selected={m.id === selectedId || undefined}
            // Tooltips near an edge open inward so they never widen the page.
            data-align={xOf(m.start) > width - TOOLTIP_HALF ? "end" : xOf(m.start) < TOOLTIP_HALF ? "start" : undefined}
            style={{ left: xOf(m.start), top: rows[i] * LABEL_ROW + 4 }}>
            <button type="button" className="chart-marker-select" aria-pressed={m.id === selectedId}
              aria-label={`${m.title}. Select to replace.`} onClick={() => onSelectPrompt(m.id)}>
              {m.label}
              <span className="chart-tooltip" aria-hidden="true">{m.title}</span>
            </button>
            <button type="button" className="chart-marker-delete" aria-label={`Delete ${m.label}`}
              onClick={() => onDeletePrompt(m.id)}>×</button>
          </div>
        ))}
      </div>
    </figure>
  );
}
