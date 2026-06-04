import type { TranscriptSegment } from "@/types";

export function LiveCaptionStrip({ latest }: { latest?: TranscriptSegment }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">
        Current Caption
      </p>
      <p className="mt-2 text-lg font-medium">
        {latest ? `"${latest.text}"` : "—"}
      </p>
    </div>
  );
}
