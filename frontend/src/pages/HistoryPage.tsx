import { useEffect, useMemo, useState } from "react";
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
    getSessions()
      .then((r) => setSessions(r.data))
      .catch(() => setError("Failed to load sessions."));
  }, []);

  const handleDelete = async (id: string) => {
    setError(null);
    try {
      await deleteSession(id);
      setSessions((prev) => (prev ? prev.filter((s) => s.id !== id) : prev));
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to delete session. Please try again.",
      );
      throw e;
    }
  };


  const filtered = useMemo(() => {
    if (!sessions) return [];
    return sessions.filter((s) => {
      const matchesQuery =
        !query ||
        s.id.toLowerCase().includes(query.toLowerCase()) ||
        s.fileName?.toLowerCase().includes(query.toLowerCase());
      const matchesFilter = filter === "all" || s.transcriptType === filter;
      return matchesQuery && matchesFilter;
    });
  }, [sessions, query, filter]);

  return (
    <AppLayout>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Session History</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Previously processed sessions.
        </p>
      </div>

      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by ID or file name"
          className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
        />
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as (typeof FILTERS)[number])}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm capitalize"
        >
          {FILTERS.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
      </div>

      {error ? (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-200">
          {error}
        </p>
      ) : sessions === null ? (
        <p className="text-sm text-muted-foreground">Loading sessions…</p>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-muted-foreground">No sessions found.</p>
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
