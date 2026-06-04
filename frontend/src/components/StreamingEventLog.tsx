import { useState } from "react";
import type { StreamingEvent } from "@/types";

export function StreamingEventLog({ events }: { events: StreamingEvent[] }) {
  const [open, setOpen] = useState(false);
  return (
    <section className="rounded-lg border border-border bg-card shadow-sm">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-5 py-3 text-left"
      >
        <span className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Streaming Events ({events.length})
        </span>
        <span className="text-xs text-muted-foreground">{open ? "Hide" : "Show"}</span>
      </button>
      {open && (
        <div className="max-h-64 overflow-y-auto border-t border-border px-5 py-3">
          {events.length === 0 ? (
            <p className="text-sm text-muted-foreground">No events yet.</p>
          ) : (
            <ul className="space-y-1 font-mono text-xs">
              {events.map((e) => (
                <li key={e.id} className="text-muted-foreground">
                  <span className="text-foreground">
                    [{new Date(e.timestamp).toLocaleTimeString()}]
                  </span>{" "}
                  <span className="font-semibold">{e.type}</span> — {e.message}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
