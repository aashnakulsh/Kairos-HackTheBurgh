import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { applyRun } from "../web/src/api/applyRun.ts";
import { createApi, ApiError } from "../web/src/api/client.ts";

const fixture = name => JSON.parse(readFileSync(new URL(`../shared/fixtures/${name}.json`, import.meta.url), "utf8"));

test("complete frontend cache journey preserves IDs and prefix", () => {
  let state = applyRun(null, fixture("empty"));
  for (const name of ["first-run", "second-run", "third-run"]) state = applyRun(state, fixture(name));
  const before = structuredClone(state);
  const edited = applyRun(state, fixture("replace-first"), "commit-004");
  assert.deepEqual(edited.prompts.map(p => p.id), ["p1", "p2", "p3"]);
  assert.deepEqual(edited.prompts.map(p => p.resolved_value), [0.2, 0.3, 0.3]);
  assert.deepEqual(edited.series.points.filter(p => p.date < "2025-06-11"), before.series.points.filter(p => p.date < "2025-06-11"));
  assert.deepEqual(state, before);
  assert.deepEqual(edited.series.points, fixture("restore").series.points);
});

test("shorter and empty suffixes remove obsolete tail", () => {
  for (const name of ["shorter-suffix", "empty-suffix"]) {
    const result = applyRun(fixture("first-run"), fixture(name));
    assert.equal(result.series.points.some(p => p.date > "2025-06-11"), false);
    assert.equal(result.series.points[0].date, "2025-06-10");
  }
});

test("stale parent, request, timeline and base are rejected", () => {
  assert.throws(() => applyRun(fixture("first-run"), fixture("replace-first")));
  assert.throws(() => applyRun(fixture("previous-branch"), fixture("replace-first"), "obsolete"));
  const bad = fixture("shorter-suffix");
  bad.timeline_id = "different";
  assert.throws(() => applyRun(fixture("first-run"), bad));
  bad.timeline_id = fixture("first-run").timeline_id;
  bad.series.base_value = 200;
  assert.throws(() => applyRun(fixture("first-run"), bad));
});

test("client methods/paths/bodies and error handling match journey", async () => {
  const steps = JSON.parse(readFileSync(new URL("../shared/journey.json", import.meta.url), "utf8"));
  const pending = [...steps];
  const api = createApi("http://fixture", async (url, options) => {
    const step = pending.shift();
    assert.equal(url, `http://fixture${step.path}`);
    assert.equal(options.method, step.method);
    assert.deepEqual(options.body ? JSON.parse(options.body) : null, step.request ? fixture(step.request.slice(0, -5)) : null);
    return new Response(JSON.stringify(fixture(step.response.slice(0, -5))), { status: step.http });
  });
  await api.capabilities();
  const run = await api.create(fixture("create-request"));
  for (const name of ["first-run", "second-run", "third-run", "replace-first"]) {
    await api.interpret(run.timeline_id, fixture(`${name}-interpret`));
    await api.commit(run.timeline_id, fixture(`${name}-commit`));
  }
  await api.reveal(run.timeline_id, 4);
  assert.equal(pending.length, 0);
  const failure = createApi("", async () => new Response(JSON.stringify(fixture("conflict")), { status: 409 }));
  await assert.rejects(failure.commit("fixture-1", fixture("replace-first-commit")), ApiError);
});
