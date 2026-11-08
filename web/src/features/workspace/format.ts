import type { Impact, Point } from "../../generated/contracts.ts";

/** Pure display helpers for the workspace. No React, so Node tests can import them. */

const quantified = (i: Impact) => i.magnitude !== null && i.unit !== null;

/** Quantified rows first, backend order otherwise, at most five. Never pads the list. */
export const rankImpacts = (impacts: Impact[]) =>
  [...impacts].sort((a, b) => Number(quantified(b)) - Number(quantified(a))).slice(0, 5);

const METRIC = { proxy_change: "sector proxy move", index_contribution: "index contribution", qualitative: "" } as const;

/** `✈️ Airlines +1.2%` plus the measure/comparator/horizon that give the number its meaning. */
export function formatImpact(i: Impact): { text: string; detail: string } {
  if (!quantified(i)) {
    const lean = i.direction && i.direction !== "neutral" ? `, likely ${i.direction}` : "";
    return { text: `${i.emoji} ${i.name}`, detail: `possible ${i.exposure} exposure${lean}` };
  }
  // Absolute magnitude plus direction: the backend never sends a double minus.
  const sign = i.direction === "positive" ? "+" : i.direction === "negative" ? "−" : "";
  const amount = i.unit === "percent" ? `${i.magnitude!.toFixed(1)}%` : `${i.magnitude!.toFixed(2)} pp`;
  const comparator = i.comparator ? ` vs ${i.comparator}` : "";
  return { text: `${i.emoji} ${i.name} ${sign}${amount}`, detail: `${METRIC[i.metric_kind]}${comparator}, ${i.horizon}` };
}

export type Trend = { direction: "gain" | "loss" | "flat" | "unknown"; change: number | null };

/** Terminal median of a prompt's simulated segment vs the market level entering it. */
export function segmentTrend(points: Point[], promptId: string | null): Trend {
  const first = points.findIndex(p => p.segment_id === promptId && p.kind === "simulated" && p.value !== null);
  const last = points.findLastIndex(p => p.segment_id === promptId && p.kind === "simulated" && p.value !== null);
  const entry = points.slice(0, Math.max(first, 0)).findLast(p => p.value !== null);
  if (first === -1 || !entry) return { direction: "unknown", change: null };
  const change = (points[last].value! / entry.value! - 1) * 100;
  return { direction: Math.abs(change) < 0.05 ? "flat" : change > 0 ? "gain" : "loss", change };
}
