import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowUpRight, Clock, FileAudio, Trash2, Music } from "lucide-react";
import type { Session } from "@/types";
import { StatusBadge } from "./StatusBadge";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";

interface SessionCardProps {
  session: Session;
  onDelete?: (id: string) => void | Promise<void>;
}

function formatDuration(sec?: number) {
  if (!sec || sec <= 0) return null;
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

function formatRelative(iso?: string) {
  if (!iso) return "Just now";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "Just now";
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return d.toLocaleDateString();
}

export function SessionCard({ session, onDelete }: SessionCardProps) {
  const [deleting, setDeleting] = useState(false);
  const [open, setOpen] = useState(false);

  const handleConfirmDelete = async () => {
    if (!onDelete) return;
    try {
      setDeleting(true);
      await onDelete(session.id);
      setOpen(false);
    } finally {
      setDeleting(false);
    }
  };

  const duration = formatDuration(session.durationSec);
  const title =
    session.title || session.fileName || `Session ${session.id?.toString().slice(0, 8)}`;

  return (
    <div className="group relative flex flex-col gap-4 rounded-xl border border-border/70 bg-card p-5 transition-all hover:border-border-strong hover:shadow-[0_1px_2px_rgba(0,0,0,0.04),0_8px_24px_-12px_rgba(0,0,0,0.08)] sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 items-start gap-3">
        <div className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary sm:flex">
          <FileAudio className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate text-sm font-semibold text-foreground">{title}</h3>
            <StatusBadge status={session.status} />
            {session.transcriptType && (
              <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium capitalize text-muted-foreground">
                {session.transcriptType.replace("_", " ")}
              </span>
            )}
            {session.has_audio && (
              <span className="flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                <Music className="h-3 w-3" />
                Recording Available
              </span>
            )}
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatRelative(session.createdAt)}
            </span>
            {duration && <span>· {duration}</span>}
            <code className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground/80">
              {session.id.slice(0, 12)}
            </code>
          </div>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        {onDelete && (
          <AlertDialog open={open} onOpenChange={setOpen}>
            <AlertDialogTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                aria-label="Delete session"
                className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete this session?</AlertDialogTitle>
                <AlertDialogDescription>
                  This permanently removes the transcript, summary, action items, and all related
                  records. This action can't be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={(e) => {
                    e.preventDefault();
                    handleConfirmDelete();
                  }}
                  disabled={deleting}
                  className={cn(buttonVariants({ variant: "destructive" }))}
                >
                  {deleting ? "Deleting…" : "Delete"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        )}
        <Link
          to="/session/$id"
          params={{ id: session.id }}
          className="inline-flex items-center gap-1 rounded-md border border-border bg-surface px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-accent"
        >
          Open
          <ArrowUpRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
        </Link>
      </div>
    </div>
  );
}
