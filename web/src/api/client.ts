import type { Capabilities, CommitRequest, CreateTimelineRequest, DescriptionRequest, DescriptionResponse, InterpretRequest,
  Problem, ReadyDraft, RevealResponse, RunResponse } from "../generated/contracts.ts";

export class ApiError extends Error {
  httpStatus: number;
  problem: Problem;
  constructor(httpStatus: number, problem: Problem) {
    super(problem.reason);
    this.httpStatus = httpStatus;
    this.problem = problem;
  }
}

/** Call only after applyRun has reconstructed a full revision, never with rounded chart values. */
export function descriptionRequest(run: RunResponse, promptId: string): DescriptionRequest {
  if (run.series_mode !== "full") throw new Error("Apply the forecast suffix before requesting a description");
  const forecast_points = run.series.points.filter(p => p.kind === "simulated" && p.segment_id === promptId);
  if (!forecast_points.length) throw new Error("No forecast segment for this prompt");
  return { prompt_id: promptId, forecast_points: structuredClone(forecast_points) };
}

export function matchesDescription(run: RunResponse, promptId: string, response: DescriptionResponse): boolean {
  return response.timeline_id === run.timeline_id && response.revision === run.revision &&
    response.run_id === run.run_id && response.prompt_id === promptId;
}

/** Same-origin /api in production; http://127.0.0.1:8000 for local fixture mode.
 * The browser forwards forecast numbers to the description relay; provider keys stay on the server.
 * No direct OpenAI calls or automatic write retries belong in the browser.
 * Types are compile-time only; HTTP response conformance is checked by the server.
 */
export function createApi(baseUrl = "", fetcher: typeof fetch = fetch) {
  async function call<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
    const response = await fetcher(`${baseUrl}${path}`, {
      method: body === undefined ? "GET" : "POST",
      ...(body === undefined ? {} : { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
      signal,
    });
    const data = await response.json();
    if (!response.ok) throw new ApiError(response.status, data as Problem);
    return data as T;
  }
  const timeline = (id: string) => `/api/timelines/${encodeURIComponent(id)}`;
  return {
    capabilities: (signal?: AbortSignal) => call<Capabilities>("/api/capabilities", undefined, signal),
    create: (body: CreateTimelineRequest, signal?: AbortSignal) => call<RunResponse>("/api/timelines", body, signal),
    restore: (id: string, signal?: AbortSignal) => call<RunResponse>(timeline(id), undefined, signal),
    revision: (id: string, revision: number) => call<RunResponse>(`${timeline(id)}/revisions/${revision}`),
    interpret: (id: string, body: InterpretRequest, signal?: AbortSignal) => call<ReadyDraft | Problem>(`${timeline(id)}/interpret`, body, signal),
    commit: (id: string, body: CommitRequest, signal?: AbortSignal) => call<RunResponse | Problem>(`${timeline(id)}/commit`, body, signal),
    describe: (id: string, revision: number, body: DescriptionRequest, signal?: AbortSignal) =>
      call<DescriptionResponse>(`${timeline(id)}/revisions/${revision}/description`, body, signal),
    reveal: (id: string, revision: number, signal?: AbortSignal) => call<RevealResponse>(`${timeline(id)}/revisions/${revision}/reveal`, undefined, signal),
  };
}
