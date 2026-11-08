import { useEffect, useRef, type KeyboardEvent } from "react";
import type { Notice } from "./useWorkspace.ts";
import { MAX_PROMPTS } from "../../config.ts";

export interface ComposerProps {
  text: string;
  replacing: number | null;
  /** Active prompts, or null before the workspace opens. */
  count: number | null;
  pending: string | null;
  notice: Notice | null;
  reducedMotion: boolean;
  onChange: (text: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
}

/** Enter submits, Shift+Enter adds a line, Escape cancels a replacement. */
export function Composer({ text, replacing, count, pending, notice, reducedMotion, onChange, onSubmit, onCancel }: ComposerProps) {
  const ref = useRef<HTMLTextAreaElement>(null);

  // Selecting a marker brings the composer into view with the old text ready to edit.
  useEffect(() => {
    const el = ref.current;
    if (replacing === null || !el) return;
    el.scrollIntoView({ block: "center", behavior: reducedMotion ? "auto" : "smooth" });
    el.focus({ preventScroll: true });
    el.setSelectionRange(el.value.length, el.value.length);
  }, [replacing]);

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      onSubmit();
    } else if (event.key === "Escape") {
      onCancel();
    }
  };

  const action = replacing === null ? "Add prompt" : `Replace prompt ${replacing}`;

  return (
    <form className="composer" data-replacing={replacing !== null || undefined}
      onSubmit={event => { event.preventDefault(); onSubmit(); }}>
      <label htmlFor="composer-input" className="composer-label">
        {replacing === null ? `Describe a market what-if${count === null ? "" : ` · ${count} of ${MAX_PROMPTS} prompts`}` : action}
      </label>
      <div className="composer-box">
        <textarea id="composer-input" ref={ref} className="composer-input" rows={1} autoFocus
          value={text} placeholder="e.g. What if inflation spiked to 6% in 2008?"
          onChange={event => onChange(event.target.value)} onKeyDown={onKeyDown} />
        {replacing !== null && <button type="button" className="button button-quiet" onClick={onCancel}>Cancel</button>}
        <button type="submit" className="button" disabled={!text.trim()}>{action}</button>
      </div>
      <div className="composer-status" aria-live="polite">
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
