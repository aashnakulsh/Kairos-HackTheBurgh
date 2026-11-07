import type { RunResponse } from "../generated/contracts.ts";

/** Pure cache update. Keep pending text and actual-history overlays outside this state. */
export function applyRun(current: RunResponse | null, next: RunResponse, expectedRequestId?: string): RunResponse {
  if (expectedRequestId !== undefined && next.request_id !== expectedRequestId) {
    throw new Error("Obsolete response: request ID mismatch");
  }
  if (current && (next.timeline_id !== current.timeline_id || next.revision < current.revision)) {
    throw new Error("Obsolete response: timeline/revision mismatch");
  }
  if (next.series_mode === "full") return structuredClone(next);
  if (!current || current.revision !== next.parent_revision || !next.changed_from) {
    throw new Error("Restore a full snapshot before applying this suffix");
  }
  const { points: oldPoints, ...oldMeta } = current.series;
  const { points: newPoints, ...newMeta } = next.series;
  if (Object.keys(oldMeta).some(key => oldMeta[key as keyof typeof oldMeta] !== newMeta[key as keyof typeof newMeta])) {
    throw new Error("Series basis changed: restore a full snapshot");
  }
  if (newPoints.some(point => point.date < next.changed_from!)) {
    throw new Error("Suffix precedes changed_from");
  }
  const result = structuredClone(next);
  result.series.points = structuredClone([
    ...oldPoints.filter(point => point.date < next.changed_from!), ...newPoints,
  ]);
  result.series_mode = "full";
  return result;
}
