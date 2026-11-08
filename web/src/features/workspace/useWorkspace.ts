import { useEffect, useRef, useState } from "react";
import { applyRun } from "../../api/applyRun.ts";
import { ApiError, createApi } from "../../api/client.ts";
import { createMockApi } from "../../api/mockApi.ts";
import type { Capabilities, CommitRequest, RevealResponse, RunResponse, Viewport } from "../../generated/contracts.ts";
import type { ChartProps } from "../chart/Chart.tsx";

// shortcut: the in-browser mock is the default until the OpenAI parser lands; VITE_API=server uses the HTTP API.
const api = import.meta.env.VITE_API === "server" ? createApi() : createMockApi();
const STORAGE_KEY = "teamrelay.timeline_id";

export interface Notice {
  tone: "error" | "info";
  reason: string;
  /** Suggested replacement texts; picking one only fills the composer. */
  choices?: string[];
  retry?: () => void;
}

function remember(id: string | null) {
  try { id ? localStorage.setItem(STORAGE_KEY, id) : localStorage.removeItem(STORAGE_KEY); } catch { /* storage blocked: reload starts fresh */ }
}
function recalled() {
  try { return localStorage.getItem(STORAGE_KEY); } catch { return null; }
}

/** Committed workspace state and the interpret → commit flow. Only a successful commit changes the chart. */
export function useWorkspace() {
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [capsFailed, setCapsFailed] = useState(false);
  const [viewport, setViewport] = useState<Viewport>({ start_year: 1980, end_year: 2026 });
  const [run, setRun] = useState<RunResponse | null>(null);
  const [draw, setDraw] = useState<ChartProps["draw"]>(null);
  const [text, setText] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [focusId, setFocusId] = useState<string | null>(null);
  const [pending, setPending] = useState<"Interpreting" | "Simulating" | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [reveal, setReveal] = useState<RevealResponse | null>(null);
  const [playhead, setPlayhead] = useState<string | null>(null);
  const [started, setStarted] = useState(false);

  const runRef = useRef(run);
  const seq = useRef(0);
  const abort = useRef<AbortController | null>(null);
  const createId = useRef(crypto.randomUUID()); // reused until creation succeeds, so a blind retry is idempotent
  const stash = useRef(""); // unsent "Add prompt" text, restored when a selection is cancelled

  const install = (next: RunResponse, animate: boolean, from: string | null = null) => {
    runRef.current = next;
    setRun(next);
    setReveal(null);
    setDraw({ revision: next.revision, from, animate });
    if (next.prompts.length) setStarted(true);
  };

  const loadCaps = () => {
    setCapsFailed(false);
    api.capabilities().then(c => { setCaps(c); setViewport(c.default_viewport); }, () => setCapsFailed(true));
  };

  const restore = async (id: string) => {
    const full = await api.restore(id);
    install(applyRun(null, full), false);
    setFocusId(f => f && full.prompts.some(p => p.id === f) ? f : full.prompts.at(-1)?.id ?? null);
    setSelectedId(s => s && full.prompts.some(p => p.id === s) ? s : null);
  };

  useEffect(() => {
    loadCaps();
    const id = recalled();
    if (id) restore(id).catch(e => { if (e instanceof ApiError && e.httpStatus === 404) remember(null); });
  }, []);

  /** Shared failure handling: preserve text, keep the committed graph, explain in place. */
  const fail = async (error: unknown, retry?: () => void) => {
    const current = runRef.current;
    if (error instanceof ApiError && error.httpStatus === 409 && current) {
      await restore(current.timeline_id).catch(() => undefined);
      setNotice({ tone: "error", reason: `${error.problem.reason}. The timeline was refreshed and your text is kept — press Enter to reapply.` });
    } else if (error instanceof ApiError && error.httpStatus === 410) {
      setNotice({ tone: "error", reason: "That interpretation expired. Your text is kept — press Enter to interpret it again." });
    } else if (error instanceof ApiError) {
      setNotice({ tone: "error", reason: error.problem.reason, choices: error.problem.choices });
    } else if (error instanceof TypeError) {
      setNotice({ tone: "error", reason: "Can't reach the server. Your text and graph are kept.", retry });
    } else if (current) {
      // applyRun rejected the response (stale parent or basis change): resync from the server.
      await restore(current.timeline_id).catch(() => undefined);
      setNotice({ tone: "error", reason: "The graph was out of date and has been refreshed. Press Enter to reapply." });
    }
  };

  const commit = async (timelineId: string, body: CommitRequest, replacing: string | null, warnings: string[], mine: number, signal: AbortSignal) => {
    setPending("Simulating");
    const result = await api.commit(timelineId, body, signal);
    if (mine !== seq.current) return;
    if (!("revision" in result)) { setNotice({ tone: "error", reason: result.reason, choices: result.choices }); return; }
    const shownBefore = !!runRef.current?.series.points.length;
    const next = applyRun(runRef.current, result, body.request_id);
    // Redraw only from changed_from whenever a graph is already on screen; a full draw only from an empty frame.
    install(next, true, result.series_mode === "suffix" || shownBefore ? result.changed_from : null);
    const newest = next.prompts.reduce((a, b) => (b.creation_order > a.creation_order ? b : a));
    setFocusId(replacing ?? newest.id);
    setSelectedId(null);
    setText("");
    stash.current = "";
    if (warnings.length) setNotice({ tone: "info", reason: warnings.join(" ") });
  };

  /** One attempt; a newer submission aborts and supersedes it, and its late response is ignored. */
  const start = () => {
    abort.current?.abort();
    abort.current = new AbortController();
    setNotice(null);
    return { mine: ++seq.current, signal: abort.current.signal };
  };

  const finish = (mine: number) => { if (mine === seq.current) setPending(null); };

  const retryCommit = (timelineId: string, body: CommitRequest, replacing: string | null) => async () => {
    const { mine, signal } = start();
    try { await commit(timelineId, body, replacing, [], mine, signal); }
    catch (e) { if (mine === seq.current) await fail(e, retryCommit(timelineId, body, replacing)); }
    finally { finish(mine); }
  };

  const submit = async () => {
    const prompt = text.trim();
    if (!prompt) return;
    const { mine, signal } = start();
    const replacing = selectedId;
    setStarted(true);
    setPending("Interpreting");
    let body: CommitRequest | null = null;
    let timelineId = "";
    try {
      let base = runRef.current;
      if (!base) {
        base = await api.create({ target_id: "SPY", request_id: createId.current }, signal);
        if (mine !== seq.current) return;
        install(applyRun(null, base), false);
        remember(base.timeline_id);
      }
      timelineId = base.timeline_id;
      const draft = await api.interpret(timelineId, {
        text: prompt, mode: replacing ? "replace" : "add", selected_prompt_id: replacing,
        playhead, expected_revision: base.revision,
      }, signal);
      if (mine !== seq.current) return;
      if (draft.status !== "ready") { setNotice({ tone: "error", reason: draft.reason, choices: draft.choices }); return; }
      body = { draft_id: draft.draft_id, expected_revision: base.revision, request_id: crypto.randomUUID() };
      await commit(timelineId, body, replacing, draft.warnings, mine, signal);
    } catch (e) {
      if (mine !== seq.current || (e instanceof DOMException && e.name === "AbortError")) return;
      // Only a commit retry reuses its request ID; interpret/create failures retry via Enter.
      await fail(e, body ? retryCommit(timelineId, body, replacing) : undefined);
    } finally {
      finish(mine);
    }
  };

  const selectPrompt = (id: string) => {
    const prompt = runRef.current?.prompts.find(p => p.id === id);
    if (!prompt) return;
    if (!selectedId) stash.current = text;
    setSelectedId(id);
    setText(prompt.text);
    setNotice(null);
  };

  const cancelSelection = () => {
    if (!selectedId) return;
    setSelectedId(null);
    setText(stash.current);
  };

  const requestReveal = () => {
    const current = runRef.current;
    if (!current) return;
    api.reveal(current.timeline_id, current.revision).then(
      r => { if (runRef.current?.revision === r.revision) setReveal(r); },
      e => fail(e));
  };

  return {
    caps, capsFailed, loadCaps, viewport, setViewport, run, draw, text, setText, selectedId, focusId,
    pending, notice, reveal, playhead, setPlayhead, started, submit, selectPrompt, cancelSelection, requestReveal,
  };
}
