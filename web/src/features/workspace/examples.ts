import { promptKey } from "./format.ts";

/** Situational example prompts for the composer placeholder: everyday events, no jargon or figures to decode.
 * The server-side parser turns wording like this into canonical instructions. */
export const EXAMPLES = [
  "What if the U.S. bombed Iran in 2015?",
  "What if the 2001 IMF crisis didn't happen?",
  "What if Lehman Brothers had been rescued in 2008?",
  "What if the COVID lockdowns never happened in 2020?",
  "What if Britain had voted to stay in the EU in 2016?",
  "What if the Berlin Wall had stayed up in 1989?",
  "What if Apple had gone bankrupt in 1997?",
  "What if Russia never invaded Ukraine in 2022?",
  "What if a huge hurricane hit New York in 2012?",
  "What if the U.S. and China signed a trade peace deal in 2018?",
];

/** A random example: never the same one twice in a row, and never one already used this journey (while any remain). */
export const randomExample = (not?: string, used: string[] = []) => {
  const spent = new Set(used.map(promptKey));
  const fresh = EXAMPLES.filter(e => !spent.has(promptKey(e)));
  const pool = (fresh.length ? fresh : EXAMPLES).filter(e => e !== not);
  return pool[Math.floor(Math.random() * pool.length)] ?? EXAMPLES[0];
};
