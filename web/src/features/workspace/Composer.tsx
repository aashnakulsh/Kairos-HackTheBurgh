import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import type { Notice } from "./useWorkspace.ts";
import { MAX_PROMPTS } from "../../config.ts";
import { randomExample } from "./examples.ts";
import { promptKey } from "./format.ts";


export interface ComposerProps {
  text: string;
  replacing: number | null;
  /** Prompts so far, or null on the start screen (which shows the legs picker and "Start journey"). */
  count: number | null;
  /** Number the next new prompt will get (lowest free slot). */
  nextNumber: number;
  legs: number | null;
  /** Prompts already used this journey: examples skip them. */
  used: string[];
  pending: string | null;
  notice: Notice | null;
  reducedMotion: boolean;
  onChange: (text: string) => void;
  onLegsChange: (legs: number | null) => void;
  onSubmit: () => void;
  onCancel: () => void;
}

/** Enter submits, Shift+Enter adds a line, Escape cancels a replacement. */
export function Composer({ text, replacing, count, nextNumber, legs, used, pending, notice, reducedMotion, onChange, onLegsChange, onSubmit, onCancel }: ComposerProps) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const [example, setExample] = useState(() => randomExample(undefined, used));
  const starting = count === null;

  // Swap the placeholder example every few seconds while the box is empty (text only, no motion).
  useEffect(() => {
    if (text) return;
    setExample(e => used.some(u => promptKey(u) === promptKey(e)) ? randomExample(e, used) : e); // just used it: swap now
    const id = setInterval(() => setExample(e => randomExample(e, used)), 5000);
    return () => clearInterval(id);
  }, [text, used]);

  // Selecting a marker brings the composer into view with the old text ready to edit.
  useEffect(() => {
    const el = ref.current;
    if (replacing === null || !el) return;
    el.scrollIntoView({ block: "center", behavior: reducedMotion ? "auto" : "smooth" });
    el.focus({ preventScroll: true });
    el.setSelectionRange(el.value.length, el.value.length);
  }, [replacing]);

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    // Tab in an empty box takes the suggested example; with text, Tab moves focus as usual (no keyboard trap).
    if (event.key === "Tab" && !event.shiftKey && !text) {
      event.preventDefault();
      onChange(example);
    } else if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      onSubmit();
    } else if (event.key === "Escape") {
      onCancel();
    }
  };

  const action = starting ? "Start journey" : replacing === null ? "Continue journey" : `Replace prompt ${replacing}`;
  const label = starting ? "Describe your first what-if"
    : replacing !== null ? action
    : legs !== null && count >= legs ? `All ${legs} prompts sailed · select one to replace, or delete one`
    : `Describe a market what-if · prompt ${nextNumber} of ${legs ?? MAX_PROMPTS}`;

  return (
    <form className="composer" data-replacing={replacing !== null || undefined}
      onSubmit={event => { event.preventDefault(); onSubmit(); }}>
      <label htmlFor="composer-input" className="composer-label">{label}</label>
      <div className="composer-box">
        <textarea id="composer-input" ref={ref} className="composer-input" rows={1} autoFocus
          value={text} placeholder={`e.g. ${example} (Tab ⇥)`} aria-describedby="composer-tab-hint"
          onChange={event => onChange(event.target.value)} onKeyDown={onKeyDown} />
        {starting && (
          <label className="composer-legs">
            <span>Prompts</span>
            {/* Required: the journey length must be chosen, 1 to MAX_PROMPTS. */}
            <select required value={legs ?? ""} onChange={event => onLegsChange(Number(event.target.value) || null)}>
              <option value="" disabled>–</option>
              {Array.from({ length: MAX_PROMPTS }, (_, i) => i + 1).map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
        )}
        {replacing !== null && <button type="button" className="button button-quiet" onClick={onCancel}>Cancel</button>}
        <button type="submit" className="button" disabled={!text.trim() || (starting && !legs)}>{action}</button>
      </div>
      <span id="composer-tab-hint" className="visually-hidden">When the box is empty, press Tab to use the suggested example.</span>
      <div className="composer-status" aria-live="polite">
        {starting && !legs && !notice && <span>Choose how many prompts your journey has (1 to {MAX_PROMPTS}).</span>}
        {pending && <span className="composer-pending">{pending}…</span>}
        {notice && (
          <div className="notice" data-tone={notice.tone} role={notice.tone === "error" ? "alert" : undefined}>
            <p>{notice.reason}</p>
            {!!notice.choices?.length && (
              <div className="notice-choices">
                {notice.choices.map(choice => (
                  <button key={choice} type="button" className="button button-quiet"
                    onClick={() => { onChange(choice); ref.current?.focus(); }}>{choice}</button>
                ))}
              </div>
            )}
            {notice.retry && <button type="button" className="button button-quiet" onClick={notice.retry}>Retry</button>}
          </div>
        )}
      </div>
    </form>
  );
}
