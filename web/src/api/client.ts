import type { Capabilities, CommitRequest, CreateTimelineRequest, InterpretRequest,
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

/** Delete one active prompt (architecture §5). shortcut: hand-written until api/contracts.py defines it. */
export interface DeletePromptRequest {
  prompt_id: string;
  expected_revision: number;
  request_id: string;
}

/** End-of-journey summary (architecture §5). shortcut: hand-written until api/contracts.py defines it. */
export interface JourneySummary {
  timeline_id: string;
  revision: number;
  data_label: string;
  headline: string;
  summary: string;
  /** Percent change of the whole simulated voyage, from the level before the first prompt to the final point. */
  net_change_percent: number | null;
  legs: Array<{ prompt_id: string; display_number: number; text: string; change_percent: number | null }>;
}

/** Same-origin /api in production; http://127.0.0.1:8000 for local fixture mode.
 * No provider keys, OpenAI calls or automatic write retries belong in the browser.
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
    deletePrompt: (id: string, body: DeletePromptRequest, signal?: AbortSignal) => call<RunResponse | Problem>(`${timeline(id)}/delete`, body, signal),
    summary: (id: string, revision: number, signal?: AbortSignal) => call<JourneySummary>(`${timeline(id)}/revisions/${revision}/summary`, undefined, signal),
    reveal: (id: string, revision: number, signal?: AbortSignal) => call<RevealResponse>(`${timeline(id)}/revisions/${revision}/reveal`, undefined, signal),
  };
}
