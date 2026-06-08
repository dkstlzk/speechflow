/**
 * LiveCaptionStrip — Displays the current disposable caption text.
 *
 * This is ephemeral UI — like Google Meet captions or YouTube auto-captions.
 * The text here is NEVER persisted. It's purely for live user feedback.
 */

export function LiveCaptionStrip({ caption }: { caption?: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">
        Live Caption
      </p>
      <p className="mt-2 text-lg font-medium min-h-[1.75rem]">
        {caption ? `"${caption}"` : "—"}
      </p>
    </div>
  );
}
