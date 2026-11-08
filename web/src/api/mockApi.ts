import type { Capabilities, CommitRequest, CreateTimelineRequest, Instruction, InterpretRequest, Panel, Point,
  Problem, Prompt, ReadyDraft, RevealResponse, RunResponse } from "../generated/contracts.ts";
import { ApiError, createApi, type DeletePromptRequest, type JourneySummary } from "./client.ts";
import { segmentTrend } from "../features/workspace/format.ts";
import { MAX_PROMPTS } from "../config.ts";

// shortcut: temporary in-browser stand-in for the backend so any free-text prompt redraws a fake
// 1980–2026 graph. Delete once the OpenAI parser (free text → Instruction) and replay API are live.

const LABEL = "Synthetic mock — not market data or a real forecast";
const WEEK = 7 * 86_400_000;
const FIRST = Date.UTC(1980, 0, 7); // first Monday of 1980
// shortcut: weekly points instead of trading sessions keep 46 years light enough to animate.
const SESSIONS = Array.from({ length: Math.floor((Date.UTC(2026, 11, 31) - FIRST) / WEEK) + 1 },
  (_, i) => new Date(FIRST + i * WEEK).toISOString().slice(0, 10));
const LAST = SESSIONS[SESSIONS.length - 1];
const BASE_DRIFT = 0.0015;
const SHOCK_WEEKS = 52;

function rand(seed: number) { // mulberry32: same seed, same number, so unchanged prefixes stay identical
  let t = (seed + 0x6d2b79f5) | 0;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
const noise = (i: number) => (rand(i * 3) + rand(i * 3 + 1) + rand(i * 3 + 2) - 1.5) * 0.04;

const BASE: number[] = [100];
for (let i = 1; i < SESSIONS.length; i++) BASE.push(BASE[i - 1] * (1 + BASE_DRIFT + noise(i)));

const hash = (text: string) => [...text].reduce((h, c) => Math.imul(h ^ c.charCodeAt(0), 16777619) >>> 0, 2166136261);
// Checked first: averted disasters ("never invaded", "crisis didn't happen", "rescued") read as good news.
const AVERTED = /never|didn'?t|did not|rescue|saved|stay|deal|peace/;
const NEGATIVE = /crash|recession|war|default|collapse|crisis|panic|pandemic|shutdown|lockdown|bankrupt|hike|tariff|fall|drop|bear|inflation|spike|bomb|invad|attack|hurricane/;
const POSITIVE = /boom|rally|cut|stimulus|growth|bull|rise|surge|recover|bail/;
/** Weekly drift added while the prompt is active. Keyword sign so demos look plausible; magnitude from the text hash. */
function shock(text: string) {
  const t = text.toLowerCase();
  const sign = AVERTED.test(t) || POSITIVE.test(t) ? 1 : NEGATIVE.test(t) ? -1 : hash(t) & 1 ? 1 : -1;
  return sign * (0.004 + ((hash(t) >>> 1) % 1000) / 1000 * 0.004); // strong enough that the window's net sign follows the wording
}

const MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
const MONTH = "(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\\.?";
const pad = (n: number) => String(n).padStart(2, "0");

export type DateReading = { precision: "day" | "year" | "interval"; start: string; end: string | null };

/** Crude date guess from free text. The OpenAI parser replaces this; it only exists so the mock accepts any wording. */
export function readDates(text: string, fallbackYear?: string): DateReading | null {
  const t = text.toLowerCase();
  const iso = t.match(/\b(\d{4})-(\d{2})-(\d{2})\b/);
  if (iso) return { precision: "day", start: iso[0], end: null };
  const years = [...new Set([...t.matchAll(/\b(19\d\d|20\d\d)\b/g)].map(m => Number(m[1])))].sort();
  if (years.length >= 2) return { precision: "interval", start: `${years[0]}-01-01`, end: `${years.at(-1)}-12-31` };
  const year = years[0] ?? (fallbackYear ? Number(fallbackYear) : null);
  // "19 October" first, else "October 19" would read as plain "October" when a year follows.
  const monthDay = t.match(new RegExp(`\\b(\\d{1,2})(?:st|nd|rd|th)?\\s+${MONTH}`))
    ?? t.match(new RegExp(`\\b${MONTH}(?:\\s+(\\d{1,2})(?:st|nd|rd|th)?\\b)?`));
  if (year === null) return null;
  if (!monthDay) return years.length ? { precision: "year", start: `${year}-01-01`, end: `${year}-12-31` } : null;
  const [month, day] = /\d/.test(monthDay[1]) ? [monthDay[2], monthDay[1]] : [monthDay[1], monthDay[2]];
  return { precision: "day", start: `${year}-${pad(MONTHS.indexOf(month.slice(0, 3)) + 1)}-${pad(Number(day ?? 1))}`, end: null };
}

const sessionOnOrAfter = (day: string) => SESSIONS.find(s => s >= day) ?? null;
const sessionOnOrBefore = (day: string) => SESSIONS.findLast(s => s <= day) ?? null;

/** Observed baseline until the first prompt, then a deterministic path tilted by whichever prompt is active. */
function seriesFor(prompts: Prompt[]): Point[] {
  const ordered = [...prompts].sort((a, b) => a.effective_start.localeCompare(b.effective_start) || a.creation_order - b.creation_order);
  const fork = ordered.length ? SESSIONS.indexOf(ordered[0].effective_start) : SESSIONS.length;
  let value = BASE[Math.max(fork - 1, 0)];
  return SESSIONS.map((date, i) => {
    if (i < fork) return { date, kind: "observed", value: BASE[i], q10: null, q90: null, engine: null, segment_id: null };
    const segment = ordered.findLast(p => p.effective_start <= date)!;
    // Latest-started prompt still inside its window wins; after it expires the base drift resumes.
    const active = ordered.findLast(p => p.effective_start <= date &&
      date <= (p.effective_end ?? SESSIONS[Math.min(SESSIONS.indexOf(p.effective_start) + SHOCK_WEEKS, SESSIONS.length - 1)]));
    value *= 1 + BASE_DRIFT + (active ? shock(active.text) : 0) + noise(i) * 0.5;
    const spread = Math.min(0.012 * Math.sqrt(i - fork + 1), 0.3);
    return { date, kind: "simulated", value, q10: value * (1 - spread), q90: value * (1 + spread), engine: "mock",
      // A prompt's segment is only its active window, like the real short horizons; the drift after it is a separate segment.
      segment_id: active ? active.id : `${segment.id}-drift` };
  });
}

interface Timeline { id: string; revisions: RunResponse[]; next: number }
interface Draft { timelineId: string; revision: number; selected: string | null; text: string; instruction: Instruction }

const problem = (status: Problem["status"], code: string, reason: string, current_revision: number | null = null): Problem =>
  ({ status, code, reason, choices: [], current_revision, retryable: false });
const sleep = () => new Promise(resolve => setTimeout(resolve, 250)); // visible pending state, like a real round trip
const suffix = (run: RunResponse): RunResponse => ({ ...structuredClone(run), series_mode: "suffix",
  series: { ...run.series, points: run.series.points.filter(p => p.date >= run.changed_from!) } });

export function createMockApi(): ReturnType<typeof createApi> {
  const timelines = new Map<string, Timeline>();
  const created = new Map<string, string>();
  const drafts = new Map<string, Draft>();

  const timeline = (id: string) => {
    const tl = timelines.get(id);
    if (!tl) throw new ApiError(404, problem("not_found", "timeline_not_found", "Unknown timeline"));
    return tl;
  };
  const latest = (tl: Timeline) => tl.revisions[tl.revisions.length - 1];

  function snapshot(tl: Timeline, prompts: Prompt[], requestId: string | null, changedFrom: string | null): RunResponse {
    const revision = tl.revisions.length;
    const panels: Record<string, Panel> = Object.fromEntries(prompts.map(p => [p.id, {
      summary: `${LABEL}. Read “${p.text}” as starting ${p.effective_start}${p.effective_end ? ` until ${p.effective_end}` : ""}.`,
      hypotheses: [], evidence: [], impacts: [], horizon: "Mock path to the end of the timeline", comparison: null,
      engine: "mock", support_count: 0, status: "supported",
    } satisfies Panel]));
    return {
      contract_version: "1", data_label: LABEL, timeline_id: tl.id, run_id: `${tl.id}-run-${revision}`,
      dataset_version: "mock-v1", model_version: "mock-v1", corpus_version: "none", request_id: requestId,
      revision, parent_revision: revision ? revision - 1 : null, changed_from: changedFrom,
      replace_through: changedFrom ? LAST : null, series_mode: "full", evidence_cutoff: null, prompts,
      series: { target_id: "SPY", base_date: SESSIONS[0], base_value: 100, unit: "index", frequency: "trading_session", points: seriesFor(prompts) },
      panels,
    };
  }

  return {
    async capabilities(): Promise<Capabilities> {
      return {
        contract_version: "1", mode: "fixture", data_label: LABEL, targets: ["SPY"], unit: "index", frequency: "trading_session",
        default_viewport: { start_year: 1980, end_year: 2026 }, coverage: { first_session: SESSIONS[0], last_session: LAST, gaps: [] },
        supported_event_families: ["free_text_mock"], default_horizon_sessions: 5, max_horizon_sessions: 65, max_prompts: MAX_PROMPTS,
        evidence_available: false, display_rights: "Synthetic mock only", fixture_presets: [],
      };
    },

    async create(body: CreateTimelineRequest) {
      await sleep();
      const known = created.get(body.request_id);
      if (known) return structuredClone(latest(timeline(known)));
      const tl: Timeline = { id: `mock-${crypto.randomUUID().slice(0, 8)}`, revisions: [], next: 1 };
      tl.revisions.push(snapshot(tl, [], body.request_id, null));
      timelines.set(tl.id, tl);
      created.set(body.request_id, tl.id);
      return structuredClone(latest(tl));
    },

    async restore(id: string) { return structuredClone(latest(timeline(id))); },

    async revision(id: string, revision: number) {
      const run = timeline(id).revisions[revision];
      if (!run) throw new ApiError(404, problem("not_found", "revision_not_found", "Unknown revision"));
      return structuredClone(run);
    },

    async interpret(id: string, body: InterpretRequest): Promise<ReadyDraft | Problem> {
      await sleep();
      const tl = timeline(id), run = latest(tl);
      if (body.expected_revision !== run.revision) throw new ApiError(409, problem("conflict", "stale_revision", "Restore before reinterpreting", run.revision));
      const selected = run.prompts.find(p => p.id === body.selected_prompt_id) ?? null;
      if (body.mode === "replace" && !selected) throw new ApiError(422, problem("invalid", "unknown_prompt", "Unknown selected prompt", run.revision));
      // No year in the text: borrow it from the prompt being replaced, then the playhead (architecture §3).
      const reading = readDates(body.text, (selected?.requested_start ?? body.playhead ?? undefined)?.slice(0, 4))
        ?? (selected ? { precision: selected.date_precision, start: selected.requested_start, end: selected.requested_end } : null)
        ?? (body.playhead ? { precision: "day" as const, start: body.playhead, end: null } : null);
      if (!reading) return problem("needs_clarification", "date_missing",
        "When should this happen? Add a year (for example “in 2008”). Made-up events always need one. The real backend will work out the dates of historical events by itself; this temporary mock cannot.", run.revision);
      if (reading.end && reading.end < reading.start) return problem("invalid", "reversed_dates", "The end date is before the start date.", run.revision);
      const start = sessionOnOrAfter(reading.start);
      const end = reading.end ? sessionOnOrBefore(reading.end) : null;
      if (!start || reading.start < SESSIONS[0] || (reading.end && !end)) return problem("unsupported", "outside_coverage",
        `That date is outside the mock timeline (${SESSIONS[0]} to ${LAST}).`, run.revision);
      const instruction: Instruction = {
        date_precision: reading.precision, requested_start: reading.start, requested_end: reading.end,
        effective_start: start, effective_end: end, effective_at: `${start}T09:30:00-05:00`, timezone: "America/New_York",
        scope: reading.precision === "interval" ? "interval" : "release", release_dates: [start],
        operation: "set", value: null, unit: "percent", reference: null,
      };
      const draft_id = `draft-${crypto.randomUUID().slice(0, 8)}`;
      drafts.set(draft_id, { timelineId: id, revision: run.revision, selected: selected?.id ?? null, text: body.text, instruction });
      const span = reading.end ? `${reading.start} to ${reading.end}` : reading.start;
      return {
        status: "ready", draft_id, timeline_id: id, expected_revision: run.revision, mode: body.mode,
        selected_prompt_id: selected?.id ?? null, text: body.text, expires_at: new Date(Date.now() + 300_000).toISOString(),
        instruction, warnings: [`Mock read this as ${reading.precision} ${span}. The OpenAI parser will replace this guess.`],
      };
    },

    async commit(id: string, body: CommitRequest): Promise<RunResponse | Problem> {
      await sleep();
      const tl = timeline(id), run = latest(tl);
      const draft = drafts.get(body.draft_id);
      if (!draft || draft.timelineId !== id) throw new ApiError(404, problem("not_found", "draft_not_found", "Unknown draft", run.revision));
      if (body.expected_revision !== run.revision || draft.revision !== run.revision) {
        throw new ApiError(409, problem("conflict", "stale_revision", "The timeline changed", run.revision));
      }
      const old = run.prompts.find(p => p.id === draft.selected);
      if (!old && run.prompts.length >= MAX_PROMPTS) {
        return problem("unsupported", "prompt_limit", `A timeline holds up to ${MAX_PROMPTS} prompts. Delete or replace one.`, run.revision);
      }
      const prompt: Prompt = {
        ...draft.instruction, id: old?.id ?? `p${tl.next}`, display_number: old?.display_number ?? tl.next,
        creation_order: old?.creation_order ?? tl.next, text: draft.text, evidence_ids: [], resolved_value: null, status: "supported",
      };
      if (!old) tl.next++;
      const prompts = old ? run.prompts.map(p => (p.id === old.id ? prompt : p)) : [...run.prompts, prompt];
      // Replacing uses the earlier of the old and new starts, so a moved prompt's old effects are removed.
      const changedFrom = old && old.effective_start < prompt.effective_start ? old.effective_start : prompt.effective_start;
      const next = snapshot(tl, prompts, body.request_id, changedFrom);
      tl.revisions.push(next);
      drafts.delete(body.draft_id);
      if (run.revision === 0) return structuredClone(next); // contract: first commit is a full snapshot
      return suffix(next);
    },

    async deletePrompt(id: string, body: DeletePromptRequest): Promise<RunResponse | Problem> {
      await sleep();
      const tl = timeline(id), run = latest(tl);
      if (body.expected_revision !== run.revision) throw new ApiError(409, problem("conflict", "stale_revision", "The timeline changed", run.revision));
      const gone = run.prompts.find(p => p.id === body.prompt_id);
      if (!gone) throw new ApiError(422, problem("invalid", "unknown_prompt", "Unknown prompt", run.revision));
      // Other prompts keep their IDs and permanent numbers; history repaints from the deleted prompt's start.
      const next = snapshot(tl, run.prompts.filter(p => p !== gone), body.request_id, gone.effective_start);
      tl.revisions.push(next);
      return suffix(next);
    },

    async summary(id: string, revision: number): Promise<JourneySummary> {
      await sleep();
      const run = timeline(id).revisions[revision];
      if (!run) throw new ApiError(404, problem("not_found", "revision_not_found", "Unknown revision"));
      const points = run.series.points;
      const start = points.findLast(p => p.kind === "observed")?.value ?? null;
      const end = points.at(-1)?.value ?? null;
      const net = start && end ? (end / start - 1) * 100 : null;
      const legs = [...run.prompts].sort((a, b) => a.effective_start.localeCompare(b.effective_start))
        .map(p => ({ prompt_id: p.id, display_number: p.display_number, text: p.text, change_percent: segmentTrend(points, p.id).change }));
      const worst = legs.reduce<(typeof legs)[number] | null>((w, l) => (l.change_percent ?? 0) < (w?.change_percent ?? 0) ? l : w, null);
      const best = legs.reduce<(typeof legs)[number] | null>((b, l) => (l.change_percent ?? 0) > (b?.change_percent ?? 0) ? l : b, null);
      const direction = net === null ? "drifted" : net >= 0 ? `ended up ${net.toFixed(1)}%` : `ended down ${Math.abs(net).toFixed(1)}%`;
      return {
        timeline_id: id, revision, data_label: LABEL, net_change_percent: net, legs,
        headline: net === null ? "The voyage is over" : net >= 0 ? "Fair winds: you reached port ahead" : "Battered but home: you reached port behind",
        summary: `${LABEL}. Across ${legs.length} leg${legs.length === 1 ? "" : "s"}, your alternate market ${direction}. `
          + (best ? `The kindest wind was “${best.text}”. ` : "") + (worst ? `The roughest storm was “${worst.text}”. ` : "")
          + "The backend narrator will replace this mock with a sourced story of the whole journey.",
      };
    },

    async reveal(id: string, revision: number): Promise<RevealResponse> {
      timeline(id);
      return {
        timeline_id: id, revision, data_label: LABEL, sources: [], attribution: "Unmodified mock baseline, not real history",
        series: { target_id: "SPY", base_date: SESSIONS[0], base_value: 100, unit: "index", frequency: "trading_session",
          points: SESSIONS.map((date, i) => ({ date, kind: "observed", value: BASE[i], q10: null, q90: null, engine: null, segment_id: null })) },
      };
    },
  };
}
