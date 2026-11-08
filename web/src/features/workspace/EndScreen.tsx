import { useEffect, useRef } from "react";
import type { JourneySummary } from "../../api/client.ts";

const signed = (n: number | null) => (n === null ? "no forecast" : `${n >= 0 ? "▲ +" : "▼ −"}${Math.abs(n).toFixed(1)}%`);

/** Journey's end: a giant pixel scroll (left) with the backend's voyage summary; the ship docks behind it. */
export function EndScreen({ summary, onReview, onRestart }: { summary: JourneySummary | null; onReview: () => void; onRestart: () => void }) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), []); // new screen: move focus to its heading for keyboard and screen-reader users

  return (
    <section className="note scroll-giant" aria-labelledby="end-title" aria-busy={!summary}>
      <div className="note-scroll">
      <h1 id="end-title" className="note-title" ref={heading} tabIndex={-1}>
        {summary?.headline ?? "Docking…"}
      </h1>
      <div className="note-divider" aria-hidden="true">{"~=".repeat(40)}</div>
      {!summary ? <p>Unrolling the captain's log…</p> : <>
        <p className="scroll-net" data-trend={summary.net_change_percent === null ? "unknown" : summary.net_change_percent >= 0 ? "gain" : "loss"}>
          Voyage result: {signed(summary.net_change_percent)}
        </p>
        <p>{summary.summary}</p>
        <ol className="scroll-legs">
          {summary.legs.map(l => (
            <li key={l.prompt_id}>
              <span>prompt {l.display_number}: {l.text}</span>
              <span data-trend={l.change_percent === null ? "unknown" : l.change_percent >= 0 ? "gain" : "loss"}>{signed(l.change_percent)}</span>
            </li>
          ))}
        </ol>
        <p className="scroll-label">{summary.data_label}</p>
      </>}
      <div className="scroll-actions">
        <button type="button" className="button" onClick={onRestart}>Sail again</button>
        <button type="button" className="button button-quiet" onClick={onReview}>Review the chart</button>
      </div>
      </div>
    </section>
  );
}
