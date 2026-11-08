/** Exercise the actual frontend client/cache against a research HTTP server (Node 22.18+).
 * This verifies data integration, not browser rendering. Creates one local test timeline.
 */
import assert from "node:assert/strict";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const web = resolve(process.argv[2] ?? "web");
const base = process.argv[3] ?? "http://127.0.0.1:8000";
const { createApi } = await import(pathToFileURL(resolve(web, "src/api/client.ts")));
const { applyRun } = await import(pathToFileURL(resolve(web, "src/api/applyRun.ts")));
const api = createApi(base);
assert.equal((await api.capabilities()).max_prompts, 3);
let run = applyRun(null, await api.create({target_id: "SPY", request_id: crypto.randomUUID()}));
const observed = structuredClone(run.series.points);
const snapshots = [];
for (const [revision, text] of ["Set June 11 CPI to 0.4%",
  "July 15: add 0.1 percentage points to preceding reading",
  "August 12: keep July simulated reading", "Set June 11 CPI to 0.2%"].entries()) {
  const draft = await api.interpret(run.timeline_id, {text, mode: revision === 3 ? "replace" : "add",
    selected_prompt_id: revision === 3 ? "p1" : null, playhead: null, expected_revision: revision});
  assert.equal(draft.status, "ready", JSON.stringify(draft));
  const request_id = crypto.randomUUID();
  const response = await api.commit(run.timeline_id, {draft_id: draft.draft_id, expected_revision: revision, request_id});
  assert.ok("revision" in response, JSON.stringify(response));
  run = applyRun(run, response, request_id);
  snapshots.push(structuredClone(run));
}
assert.deepEqual(run.prompts.map(p => p.resolved_value), [.2, .3, .3]);
assert.deepEqual(run.prompts.map(p => p.id), ["p1", "p2", "p3"]);
assert.deepEqual(run.series.points.slice(0, observed.length), observed);
assert.deepEqual(await api.restore(run.timeline_id), run);
const previous = await api.revision(run.timeline_id, 3);
assert.deepEqual(previous, snapshots[2]);
const revealed = await api.reveal(run.timeline_id, run.revision);
assert.ok("series" in revealed, JSON.stringify(revealed));
assert.deepEqual(revealed.series.points.map(p => p.date), run.series.points.filter(p => p.kind === "simulated").map(p => p.date));
assert.equal(revealed.series.base_date, run.series.base_date);
assert.deepEqual(await api.restore(run.timeline_id), run);
const unsupported = await api.interpret(run.timeline_id, {text: "Invent unsupported 2008 scenario",
  mode: "replace", selected_prompt_id: "p1", playhead: null, expected_revision: run.revision});
assert.notEqual(unsupported.status, "ready");
assert.deepEqual(await api.restore(run.timeline_id), run);
console.log(`PASS: real frontend client/cache, three prompts, replace, restore, previous revision, reveal and unsupported preservation. ${run.timeline_id}`);
