import type { CSSProperties } from "react";
import type { Panel, Prompt } from "../../generated/contracts.ts";
import { formatImpact, rankImpacts, type Trend } from "./format.ts";

const OPERATION = { set: "Set", add_pp: "Add", carry: "Carry forward" } as const;

/** What the backend resolved, so the user can see the scope the prompt applies to. */
function scope(p: Prompt) {
  const amount = p.value === null ? "" : ` ${p.value}${p.unit === "percent" ? "%" : " pp"}`;
  const resolved = p.resolved_value !== null && p.operation !== "set" ? ` → ${p.resolved_value}%` : "";
  const when = p.scope === "release" ? `release ${p.release_dates.join(", ")}`
    : p.scope === "recurring" ? `releases ${p.release_dates.join(", ")}`
    : `${p.effective_start} to ${p.effective_end}`;
  return `${OPERATION[p.operation]}${amount}${resolved} · ${when}`;
}

const TREND = { gain: "▲ Gain", loss: "▼ Loss", flat: "■ Flat", unknown: "No simulated move" } as const;
const trendText = (t: Trend) => `${TREND[t.direction]}${t.change === null ? "" : ` ${t.change > 0 ? "+" : ""}${t.change.toFixed(2)}%`}`;

// Typed dividers and tilts for the paper notes, picked by the permanent prompt number so a note never changes look.
const DIVIDERS = ["=-", "·x", "`·.·'·.", ".", "._.~", "-"];
const TILTS = [-1.6, 1.2, -0.4, 0.8, -1.1];
const divider = (n: number) => DIVIDERS[(n - 1) % DIVIDERS.length].repeat(40);

/** All prompts deselected: one small paper note per prompt, in timeline order. Clicking a note selects it. */
export function NoteRow({ prompts, trends, onSelect }: { prompts: Prompt[]; trends: Record<string, Trend>; onSelect: (id: string) => void }) {
  const ordered = [...prompts].sort((a, b) => a.effective_start.localeCompare(b.effective_start) || a.creation_order - b.creation_order);
  return (
    <ul className="notes" aria-label="Prompts">
      {ordered.map(p => (
        <li key={p.id} style={{ "--tilt": `${TILTS[(p.display_number - 1) % TILTS.length]}deg` } as CSSProperties}>
          <button type="button" className="note note-small" aria-label={`Prompt ${p.display_number}: ${p.text}. Select to replace.`}
            onClick={() => onSelect(p.id)}>
            <span className="note-title">prompt {p.display_number}</span>
            <span className="note-divider" aria-hidden="true">{divider(p.display_number)}</span>
            <span className="note-body">{p.text}</span>
            <span className="note-trend" data-trend={trends[p.id]?.direction}>{p.effective_start} · {trendText(trends[p.id] ?? { direction: "unknown", change: null })}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

/** Selected prompt: one wide, centred paper note with the full description. */
export function NarrativePanel({ prompt, panel, trend }: { prompt: Prompt; panel: Panel | undefined; trend: Trend }) {
  const evidence = new Map(panel?.evidence.map(e => [e.id, e]));
  const markets = (exposure: "direct" | "indirect") => panel?.impacts.filter(i => i.exposure === exposure).map(i => `${i.emoji} ${i.name}`) ?? [];
  const direct = markets("direct"), indirect = markets("indirect");
  return (
    <section className="note narrative" aria-label={`Prompt ${prompt.display_number} description`} key={prompt.id}>
      <h2 className="note-title">prompt {prompt.display_number}</h2>
      <div className="note-divider" aria-hidden="true">{divider(prompt.display_number)}</div>
      <p className="note-trend" data-trend={trend.direction}>{trendText(trend)}</p>
      <p className="narrative-scope">{scope(prompt)}</p>
      {prompt.status === "unsupported" && <p className="narrative-warning">Unsupported: no numeric forecast for this prompt.</p>}
      {!panel ? <p>No description returned; showing the resolved instruction only.</p> : <>
        <p>{panel.summary}</p>
        {!!direct.length && <p><strong>Direct:</strong> {direct.join(", ")}</p>}
        {!!indirect.length && <p><strong>Indirect:</strong> {indirect.join(", ")}</p>}
        {panel.hypotheses.map((h, i) => (
          <p key={i} className="narrative-hypothesis">
            <strong>Possible mechanism (hypothesis):</strong> {h.text}{" "}
            {h.user_assumption && <em>User assumption.</em>}
            {h.source_ids.map(id => evidence.get(id)).filter(e => e !== undefined).map(e => (
              <a key={e.id} href={e.url} target="_blank" rel="noreferrer">
                {e.title} ({e.publication_time.slice(0, 10)})
              </a>
            ))}
          </p>
        ))}
        <p className="narrative-meta">{panel.horizon} · engine {panel.engine} · {panel.support_count} supporting cases
          {panel.comparison && ` · ${panel.comparison}`}</p>
      </>}
    </section>
  );
}

/** 3–5 ranked bullets below the composer; fewer when fewer are verified. */
export function ImpactList({ panel }: { panel: Panel | undefined }) {
  const impacts = rankImpacts(panel?.impacts ?? []);
  if (!impacts.length) return <p className="impacts-empty">No supported industry impacts for this prompt yet.</p>;
  return (
    <ul className="impacts" aria-label="Most affected industries">
      {impacts.map(i => {
        const { text, detail } = formatImpact(i);
        return <li key={i.name}><span>{text}</span> <span className="impacts-detail">{detail}</span></li>;
      })}
    </ul>
  );
}
