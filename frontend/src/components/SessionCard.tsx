import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Trash2 } from "lucide-react";
import type { Session } from "@/types";
import { StatusBadge } from "./StatusBadge";
import { Button } from "@/components/ui/button";
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
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SessionCardProps {
  session: Session;
  onDelete?: (id: string) => void | Promise<void>;
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
      <div className="flex shrink-0 items-center gap-2">
        <Link
          to="/session/$id"
          params={{ id: session.id }}
          className="inline-flex items-center justify-center rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Open Session
        </Link>
        {onDelete && (
          <AlertDialog open={open} onOpenChange={setOpen}>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" size="sm" aria-label="Delete session">
                <Trash2 className="h-4 w-4" />
                Delete
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete Session?</AlertDialogTitle>
                <AlertDialogDescription>
                  This action cannot be undone. All transcript data, summaries, action
                  items, and related records will be permanently removed.
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
                  className={cn(
                    buttonVariants({ variant: "destructive" }),
                  )}
                >
                  {deleting ? "Deleting…" : "Delete"}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        )}
      </div>
    </div>
  );
}
