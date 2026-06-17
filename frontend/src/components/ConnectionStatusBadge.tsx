import type { ConnectionStatus } from "@/types";

const STYLES: Record<ConnectionStatus, string> = {
  connected: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  connecting: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  disconnected: "bg-muted text-muted-foreground",
  error: "bg-destructive/10 text-destructive dark:bg-destructive/20",
};

export function ConnectionStatusBadge({ status }: { status: ConnectionStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STYLES[status]}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          status === "connected"
            ? "bg-emerald-500"
            : status === "connecting"
              ? "bg-amber-500"
              : "bg-muted-foreground"
        }`}
      />
      {status}
    </span>
  );
}
