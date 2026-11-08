import { useRef } from "react";
import { MAX_PROMPTS } from "../../config.ts";

/** "How to play" button and its pop-up. A native modal <dialog> gives focus trapping, Escape and inert background for free. */
export function Instructions() {
  const dialog = useRef<HTMLDialogElement>(null);
  return (
    <>
      <button type="button" className="button button-quiet instructions-open" onClick={() => dialog.current?.showModal()}>
        How to play
      </button>
      <dialog ref={dialog} className="instructions" aria-labelledby="instructions-title"
        // A click on the dimmed area outside the scroll lands on the <dialog> itself: close.
        onClick={event => { if (event.target === dialog.current) dialog.current.close(); }}>
        <div className="note">
          <div className="note-scroll">
            <h2 id="instructions-title" className="note-title">how to play</h2>
            <div className="note-divider" aria-hidden="true">{"=-".repeat(40)}</div>
            <ol className="instructions-steps">
              <li>Choose how many prompts your journey has (1 to {MAX_PROMPTS}). Each prompt is one leg of the voyage.</li>
              <li>
                Ask <strong>what if</strong> an event had happened, anywhere between <strong>1980 and 2026</strong>:
                <ul>
                  <li><strong>A real historical event:</strong> just name it, e.g. “What if Lehman Brothers had been rescued?” We work out when it happened.</li>
                  <li><strong>A made-up event:</strong> include the year, e.g. “What if a huge hurricane hit New York in 2012?”</li>
                </ul>
              </li>
              <li>The chart redraws from your event onward. Gains bring sunshine; losses bring storms and rough seas.</li>
              <li>A short note appears above the chart for each prompt. Click a note to unroll its full description and more information.</li>
              <li>Clicking a prompt's label or note also lets you rewrite it. Hover the label and press × to delete it. Click empty space to deselect.</li>
              <li>Stuck for ideas? Press Tab in the empty box to use the suggested example.</li>
              <li>After your last prompt the ship docks, and the captain's log sums up your voyage.</li>
            </ol>
            <p className="scroll-label">For now the charts use a synthetic example, not real market data or a real forecast.</p>
            <div className="scroll-actions">
              <button type="button" className="button" autoFocus onClick={() => dialog.current?.close()}>Got it</button>
            </div>
          </div>
        </div>
      </dialog>
    </>
  );
}
