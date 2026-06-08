import type { ProcessingStatus } from "@/types";

const STYLES: Record<ProcessingStatus, string> = {
  idle: "bg-muted text-muted-foreground",
  uploading: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200",
  processing: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  completed: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  failed: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200",
  recording: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200",
  finalizing: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  review: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200",
  saved: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
};

export function StatusBadge({ status }: { status: ProcessingStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STYLES[status]}`}
    >
      {status}
    </span>
  );
}
