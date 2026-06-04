import { Link } from "@tanstack/react-router";
import type { Session } from "@/types";
import { StatusBadge } from "./StatusBadge";

export function SessionCard({ session }: { session: Session }) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{session.id}</code>
          <span className="rounded-full border border-border px-2 py-0.5 text-xs capitalize text-muted-foreground">
            {session.transcriptType}
          </span>
          <StatusBadge status={session.status} />
        </div>
        <p className="mt-1.5 text-xs text-muted-foreground">
          Created {new Date(session.createdAt).toLocaleString()}
          {session.fileName ? ` · ${session.fileName}` : ""}
        </p>
      </div>
      <Link
        to="/session/$id"
        params={{ id: session.id }}
        className="inline-flex shrink-0 items-center justify-center rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
      >
        Open Session
      </Link>
    </div>
  );
}
