import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { applyRun } from "../web/src/api/applyRun.ts";
import { clipPoints, domain, drawStart, markers, ms, pointAt, stackRows, yRange } from "../web/src/features/chart/geometry.ts";
import { formatImpact, rankImpacts, segmentTrend } from "../web/src/features/workspace/format.ts";
import { createMockApi, readDates } from "../web/src/api/mockApi.ts";
import { MAX_PROMPTS } from "../web/src/config.ts";
import { EXAMPLES, randomExample } from "../web/src/features/workspace/examples.ts";

test("mock date guess accepts free wording and any year", () => {
  assert.deepEqual(readDates("What if inflation spiked in 2008?"), { precision: "year", start: "2008-01-01", end: "2008-12-31" });
  assert.deepEqual(readDates("a crash on 19 October 1987"), { precision: "day", start: "1987-10-19", end: null });
  assert.deepEqual(readDates("Fed cuts rates March 3rd, 2020"), { precision: "day", start: "2020-03-03", end: null });
  assert.deepEqual(readDates("war from 1990 to 1991"), { precision: "interval", start: "1990-01-01", end: "1991-12-31" });
  assert.deepEqual(readDates("rates hike on 2015-12-16"), { precision: "day", start: "2015-12-16", end: null });
  assert.deepEqual(readDates("June 11: CPI jumps", "2025"), { precision: "day", start: "2025-06-11", end: null });
  assert.equal(readDates("CPI jumps"), null);
});

test("mock: free-text prompts redraw from changed_from and keep the earlier prefix", async () => {
  const api = createMockApi();
  let run = applyRun(null, await api.create({ target_id: "SPY", request_id: "c1" }));
  assert.ok(run.series.points.length > 2000 && run.series.points.every(p => p.kind === "observed"));
  const base = structuredClone(run.series.points);
  const send = async (text, selected = null) => {
    const draft = await api.interpret(run.timeline_id, { text, mode: selected ? "replace" : "add", selected_prompt_id: selected, expected_revision: run.revision });
    assert.equal(draft.status, "ready", draft.reason);
    const result = await api.commit(run.timeline_id, { draft_id: draft.draft_id, expected_revision: run.revision, request_id: `r${run.revision}` });
    const before = run;
    run = applyRun(run, result, `r${before.revision}`);
    assert.deepEqual(run.series.points.filter(p => p.date < result.changed_from), before.series.points.filter(p => p.date < result.changed_from));
    return result;
  };
  const first = await send("What if the 2008 crisis was worse?");
  assert.equal(first.series_mode, "full");
  assert.deepEqual(run.series.points.filter(p => p.date < "2008-01-01"), base.filter(p => p.date < "2008-01-01"));
  assert.equal((await send("A tech boom in 2015")).series_mode, "suffix");
  const edit = await send("Make it 2003 instead", "p1");
  assert.equal(edit.changed_from, "2003-01-06");
  assert.deepEqual(run.prompts.map(p => p.id), ["p1", "p2"]);
  const restored = await api.restore(run.timeline_id);
  assert.deepEqual(run.series.points, restored.series.points);
  const missing = await api.interpret(run.timeline_id, { text: "CPI jumps", mode: "add", expected_revision: run.revision });
  assert.equal(missing.status, "needs_clarification");

  // Delete p1: p2 keeps its ID and permanent number; history repaints from p1's start.
  const before = run;
  const del = await api.deletePrompt(run.timeline_id, { prompt_id: "p1", expected_revision: run.revision, request_id: "d1" });
  run = applyRun(run, del, "d1");
  assert.equal(del.changed_from, "2003-01-06");
  assert.deepEqual(run.prompts.map(p => [p.id, p.display_number]), [["p2", 2]]);
  assert.deepEqual(run.series.points.filter(p => p.date < "2003-01-06"), before.series.points.filter(p => p.date < "2003-01-06"));
  assert.ok(run.series.points.filter(p => p.date < "2015-01-01").every(p => p.kind === "observed"));

  // MAX_PROMPTS caps active prompts (p2 + MAX_PROMPTS - 1 more); one beyond is refused without a new revision.
  for (let i = 1; i < MAX_PROMPTS; i++) await send(`boom in ${1981 + i * 3}`);
  assert.equal(run.prompts.length, MAX_PROMPTS);
  const draft = await api.interpret(run.timeline_id, { text: "crash in 2010", mode: "add", expected_revision: run.revision });
  const refused = await api.commit(run.timeline_id, { draft_id: draft.draft_id, expected_revision: run.revision, request_id: "over" });
  assert.equal(refused.code, "prompt_limit");
  assert.equal((await api.restore(run.timeline_id)).revision, run.revision);

  // End-of-journey summary covers every leg, in timeline order, for the requested revision.
  const summary = await api.summary(run.timeline_id, run.revision);
  assert.equal(summary.revision, run.revision);
  assert.equal(summary.legs.length, MAX_PROMPTS);
  assert.deepEqual(summary.legs.map(l => l.prompt_id), [...run.prompts].sort((a, b) => a.effective_start.localeCompare(b.effective_start)).map(p => p.id));
  assert.equal(typeof summary.net_change_percent, "number");
  assert.match(summary.summary, /Synthetic mock/);
});

test("ten distinct situational examples; the mock reads a date from each and rotation never repeats", () => {
  assert.equal(new Set(EXAMPLES).size, 10);
  for (const e of EXAMPLES) {
    assert.ok(readDates(e), `no date read from: ${e}`);
    assert.doesNotMatch(e, /%|\bCPI\b|\bpp\b|percentage point/i, `technical wording in: ${e}`);
  }
  for (let i = 0; i < 50; i++) assert.notEqual(randomExample(EXAMPLES[0]), EXAMPLES[0]);
});

const fixture = name => JSON.parse(readFileSync(new URL(`../shared/fixtures/${name}.json`, import.meta.url), "utf8"));
const journey = () => ["first-run", "second-run", "third-run"].reduce((s, n) => applyRun(s, fixture(n)), applyRun(null, fixture("empty")));

test("viewport domain covers whole years and markers keep stable IDs and semantic years", () => {
  assert.deepEqual(domain({ start_year: 1980, end_year: 2026 }).map(t => new Date(t).toISOString().slice(0, 10)), ["1980-01-01", "2027-01-01"]);
  const marks = markers(journey().prompts);
  assert.deepEqual(marks.map(m => [m.id, m.label, m.start, m.end]), [
    ["p1", "Prompt 1", "2025-06-11", null], ["p2", "Prompt 2", "2025-07-15", null], ["p3", "Prompt 3", "2025-08-12", null]]);
  const interval = markers([{ ...journey().prompts[0], date_precision: "interval", requested_start: "2020-01-01",
    requested_end: "2022-12-31", effective_start: "2020-01-02", effective_end: "2022-12-30" }])[0];
  assert.deepEqual(interval.years, [2020, 2021, 2022]);
  assert.equal(interval.end, "2022-12-30");
  assert.match(interval.title, /2020-01-01 to 2022-12-31, session 2020-01-02/);
});

test("overlapping labels stack into separate rows, distant ones share a row", () => {
  assert.deepEqual(stackRows([100, 120, 300, 130], 80), [0, 1, 0, 2]);
  assert.deepEqual(stackRows([], 80), []);
});

test("suffix draw starts at the last retained point and never rescales y", () => {
  const before = journey();
  const edited = applyRun(before, fixture("replace-first"), "commit-004");
  const points = edited.series.points;
  assert.equal(drawStart(points, "2025-06-11"), ms("2025-06-10"));
  assert.equal(drawStart(points, null), ms(points[0].date));
  // Clipping at the start shows exactly the unchanged prefix.
  assert.deepEqual(clipPoints(points, drawStart(points, "2025-06-11")), before.series.points.filter(p => p.date < "2025-06-11"));
  const [lo, hi] = yRange(points);
  for (const p of points) for (const v of [p.value, p.q10, p.q90]) if (v !== null) assert.ok(v >= lo && v <= hi);
});

test("clipping interpolates one head point between sessions, from observed into simulated", () => {
  const points = fixture("first-run").series.points;
  const half = (ms("2025-06-10") + ms("2025-06-11")) / 2;
  const clipped = clipPoints(points, half);
  assert.equal(clipped.length, 2);
  const headPoint = clipped[1];
  assert.equal(headPoint.kind, "simulated");
  assert.equal(headPoint.value, (points[0].value + points[1].value) / 2);
  assert.ok(headPoint.q10 <= headPoint.value && headPoint.value <= headPoint.q90);
  assert.deepEqual(clipPoints(points, Infinity), points);
});

test("playhead reads cached points only", () => {
  const points = journey().series.points;
  assert.equal(pointAt(points, "2025-06-14").date, "2025-06-13");
  assert.equal(pointAt(points, "2000-01-01"), null);
});

test("segment trend compares terminal median to the level entering the segment", () => {
  const points = journey().series.points;
  const trend = segmentTrend(points, "p1");
  assert.ok(["gain", "loss", "flat"].includes(trend.direction));
  const seg = points.filter(p => p.segment_id === "p1");
  const entry = points[points.indexOf(seg[0]) - 1];
  assert.equal(trend.change, (seg.at(-1).value / entry.value - 1) * 100);
  assert.deepEqual(segmentTrend(points, "missing"), { direction: "unknown", change: null });
  assert.deepEqual(segmentTrend(fixture("empty-suffix").series.points, "p1").direction, "unknown");
});

test("impacts: quantified first, max five, signed magnitude without double minus", () => {
  const panel = fixture("panel-example");
  const ranked = rankImpacts([...panel.impacts, ...panel.impacts, ...panel.impacts]);
  assert.ok(ranked.length <= 5);
  const firstQualitative = ranked.findIndex(i => i.magnitude === null);
  if (firstQualitative !== -1) assert.ok(ranked.slice(firstQualitative).every(i => i.magnitude === null));
  const base = { name: "Airlines", emoji: "✈️", exposure: "direct", metric_kind: "proxy_change", unit: "percent",
    comparator: null, horizon: "5 sessions", method: "m", source_ids: [] };
  assert.equal(formatImpact({ ...base, direction: "positive", magnitude: 1.2 }).text, "✈️ Airlines +1.2%");
  assert.equal(formatImpact({ ...base, direction: "negative", magnitude: 0.2, unit: "percentage_points",
    metric_kind: "index_contribution" }).text, "✈️ Airlines −0.20 pp");
  const qualitative = formatImpact({ ...base, name: "Freight", emoji: "🚚", exposure: "indirect", direction: null,
    magnitude: null, unit: null, metric_kind: "qualitative" });
  assert.deepEqual(qualitative, { text: "🚚 Freight", detail: "possible indirect exposure" });
});
