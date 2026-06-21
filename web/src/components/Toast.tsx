import { useEffect } from "react";
import { Check } from "../icons";

// A calm, dimensional toast that settles in from below and auto-dismisses. Used to confirm a finished run
// ("Optimization complete") — plain, specific copy, never hype.
export function Toast({ msg, onDone, ms = 3200 }: { msg: string | null; onDone: () => void; ms?: number }) {
  useEffect(() => {
    if (!msg) return;
    const t = setTimeout(onDone, ms);
    return () => clearTimeout(t);
  }, [msg, ms, onDone]);
  if (!msg) return null;
  return (
    <div className="toast" role="status" aria-live="polite">
      <span className="toast-ic"><Check /></span>
      {msg}
    </div>
  );
}
