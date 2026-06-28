import type { ProcessingStatus } from "@/types";

const STYLES: Record<ProcessingStatus, { wrap: string; dot: string }> = {
  idle: { wrap: "bg-muted text-muted-foreground", dot: "bg-muted-foreground/60" },
  pending: { wrap: "bg-muted text-muted-foreground", dot: "bg-muted-foreground/60" },
  uploading: { wrap: "bg-blue-500/10 text-blue-700 dark:text-blue-300", dot: "bg-blue-500 animate-pulse" },
  preprocessing: { wrap: "bg-indigo-500/10 text-indigo-700 dark:text-indigo-300", dot: "bg-indigo-500 animate-pulse" },
  transcribing: { wrap: "bg-indigo-500/10 text-indigo-700 dark:text-indigo-300", dot: "bg-indigo-500 animate-pulse" },
  processing: {
    wrap: "bg-amber-500/10 text-amber-700 dark:text-amber-300",
    dot: "bg-amber-500 animate-pulse",
  },
  completed: {
    wrap: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
    dot: "bg-emerald-500",
  },
  failed: { wrap: "bg-red-500/10 text-red-700 dark:text-red-300", dot: "bg-red-500" },
  recording: {
    wrap: "bg-red-500/10 text-red-700 dark:text-red-300",
    dot: "bg-red-500 animate-pulse",
  },
  finalizing: {
    wrap: "bg-amber-500/10 text-amber-700 dark:text-amber-300",
    dot: "bg-amber-500 animate-pulse",
  },
  diarizing: {
    wrap: "bg-purple-500/10 text-purple-700 dark:text-purple-300",
    dot: "bg-purple-500 animate-pulse",
  },
};

export function StatusBadge({ status }: { status: ProcessingStatus }) {
  const s = STYLES[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ring-1 ring-inset ring-current/10 ${s.wrap}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {status}
    </span>
  );
}
