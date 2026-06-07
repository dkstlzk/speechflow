import { useEffect, useRef } from "react";
import type { TranscriptSegment } from "@/types";
import { PanelShell } from "./PanelShell";

interface Props {
  segments: TranscriptSegment[];
  partial?: TranscriptSegment | null; // Accept the new prop
  autoScroll: boolean;
  onToggleAutoScroll: (v: boolean) => void;
}

export function LiveTranscriptPanel({
  segments,
  partial,
  autoScroll,
  onToggleAutoScroll,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight;
    }
  }, [segments, partial, autoScroll]); // Add partial to dependency array

  return (
    <PanelShell
      title="Live Transcript"
      empty={segments.length === 0 && !partial}
      emptyMessage="Waiting for transcript chunks…"
      actions={
        <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => onToggleAutoScroll(e.target.checked)}
          />
          Auto-scroll
        </label>
      }
    >
      <div ref={ref} className="max-h-[420px] overflow-y-auto pr-2">
        <ul className="space-y-3">
          {segments.map((seg, i) => (
            <li key={i} className="text-sm">
              <span className="font-medium">{seg.speaker}: </span>
              <span className="text-foreground/90">{seg.text}</span>
            </li>
          ))}

          {/* Render the tentative draft in gray/italics */}
          {partial && partial.text && (
            <li className="text-sm opacity-60 italic animate-pulse">
              <span className="font-medium">{partial.speaker}: </span>
              <span>{partial.text}</span>
            </li>
          )}
        </ul>
      </div>
    </PanelShell>
  );
}
