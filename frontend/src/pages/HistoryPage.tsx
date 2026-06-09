import { useEffect, useMemo, useState } from "react";
import { History, Search } from "lucide-react";
import { AppLayout } from "@/layouts/AppLayout";
import { SessionCard } from "@/components/SessionCard";
import { deleteSession, getSessions } from "@/services/api";
import type { Session, TranscriptType } from "@/types";

const FILTERS: ("all" | TranscriptType)[] = [
  "all",
  "meeting",
  "conversation",
  "interview",
  "lecture",
  "presentation",
];

export function HistoryPage() {
  const [sessions, setSessions] = useState<Session[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");

  useEffect(() => {
    // mounted
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    const timer = setTimeout(() => {
      setSessions(null); // Show loading skeleton on new search
      setError(null);    // Clear previous errors

      getSessions(query, controller.signal)
        .then((r) => {
          if (!controller.signal.aborted) {
            setSessions(r.data);
          }
        })
        .catch((e) => {
          if (!controller.signal.aborted) {
            setError("Failed to load sessions.");
            setSessions([]); // Prevent staying stuck in loading skeleton
          }
        });
    }, 300);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  const handleDelete = async (id: string) => {
    setError(null);
    try {
      await deleteSession(id);
      setSessions((prev) => (prev ? prev.filter((s) => s.id !== id) : prev));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete session. Please try again.");
      throw e;
    }
  };

  const filtered = useMemo(() => {
    if (!sessions) return [];
    return sessions.filter((s) => {
      // Local filtering is still applied for 'filter' dropdown (TranscriptType)
      const matchesFilter = filter === "all" || s.transcriptType === filter;
      return matchesFilter;
    });
  }, [sessions, filter]);

  return (
    <AppLayout>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-[28px]">Session History</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            {sessions
              ? `${sessions.length} session${sessions.length === 1 ? "" : "s"}`
              : "Loading sessions…"}{" "}
            · Previously processed recordings.
          </p>
        </div>
      </div>

      <div className="mb-6 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by title, file name, ID, or transcript content..."
            className="w-full rounded-md border border-input bg-surface py-2 pl-9 pr-3 text-sm placeholder:text-muted-foreground/70 focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/20"
          />
        </div>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as (typeof FILTERS)[number])}
          className="rounded-md border border-input bg-surface px-3 py-2 text-sm capitalize focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/20"
        >
          {FILTERS.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
      </div>

      {error ? (
        <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
      ) : sessions === null ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-[88px] animate-pulse rounded-xl border border-border/70 bg-card"
            />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border bg-card/50 py-16 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <History className="h-5 w-5" />
          </span>
          <div>
            <p className="text-sm font-medium text-foreground">No sessions found</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {query || filter !== "all"
                ? "Try adjusting your filters."
                : "Upload a recording or start a realtime session to see it here."}
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((s) => (
            <SessionCard key={s.id} session={s} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </AppLayout>
  );
}
