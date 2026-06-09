import { useState } from "react";
import { Link } from "@tanstack/react-router";
import type { TranscriptSegment } from "@/types";
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
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ReviewScreenProps {
  sessionId: string;
  segments: TranscriptSegment[];
  onSave: () => Promise<void>;
  onDelete: () => Promise<void>;
  saving: boolean;
  deleting: boolean;
  savedTitle?: string;
}

export function ReviewScreen({
  sessionId,
  segments,
  onSave,
  onDelete,
  saving,
  deleting,
  savedTitle,
}: ReviewScreenProps) {
  const [deleteOpen, setDeleteOpen] = useState(false);

  const totalWords = segments.reduce(
    (acc, seg) => acc + seg.text.split(/\s+/).filter(Boolean).length,
    0,
  );

  const duration =
    segments.length > 0
      ? (segments[segments.length - 1].endSec ?? 0) - (segments[0].startSec ?? 0)
      : 0;

  const formatDuration = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const previewLines = segments.slice(0, 5);

  return (
    <section className="rounded-lg border border-border bg-card p-6 shadow-sm">
      <h3 className="text-lg font-semibold tracking-tight">Recording Complete</h3>
      <p className="mt-1 text-sm text-muted-foreground">Review your recording before saving.</p>

      <div className="mt-4 grid grid-cols-3 gap-4">
        <div className="rounded-md bg-muted/50 p-3">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Duration</p>
          <p className="mt-1 text-xl font-semibold tabular-nums">{formatDuration(duration)}</p>
        </div>
        <div className="rounded-md bg-muted/50 p-3">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Segments</p>
          <p className="mt-1 text-xl font-semibold tabular-nums">{segments.length}</p>
        </div>
        <div className="rounded-md bg-muted/50 p-3">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Word Count</p>
          <p className="mt-1 text-xl font-semibold tabular-nums">{totalWords.toLocaleString()}</p>
        </div>
      </div>

      {previewLines.length > 0 && (
        <div className="mt-4 rounded-md border border-border bg-muted/30 p-3">
          <p className="text-xs uppercase tracking-wide text-muted-foreground mb-2">
            Transcript Preview
          </p>
          <div className="space-y-1 text-sm text-foreground/80">
            {previewLines.map((seg, i) => (
              <p key={i} className="line-clamp-1">
                <span className="text-muted-foreground">#{seg.chunk_index}</span> {seg.text}
              </p>
            ))}
            {segments.length > 5 && (
              <p className="text-muted-foreground italic">
                … and {segments.length - 5} more segments
              </p>
            )}
          </div>
        </div>
      )}

      {savedTitle && (
        <div className="mt-4 flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Saved as:</span>
          <span className="font-medium">{savedTitle}</span>
        </div>
      )}

      <div className="mt-5 flex flex-wrap items-center gap-3">
        {!savedTitle ? (
          <>
            <Button
              onClick={onSave}
              disabled={saving || deleting}
              className="bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {saving ? "Saving…" : "Save Recording"}
            </Button>

            <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" disabled={saving || deleting}>
                  {deleting ? "Deleting…" : "Delete Recording"}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete Recording?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This action cannot be undone. All transcript data for this recording will be
                    permanently deleted.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={(e) => {
                      e.preventDefault();
                      onDelete();
                    }}
                    disabled={deleting}
                    className={cn(buttonVariants({ variant: "destructive" }))}
                  >
                    {deleting ? "Deleting…" : "Delete"}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </>
        ) : (
          <Link
            to="/session/$id"
            params={{ id: sessionId }}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            View Session
          </Link>
        )}
      </div>
    </section>
  );
}
