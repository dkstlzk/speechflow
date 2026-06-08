import { useEffect, useRef } from "react";
import type { TranscriptSegment } from "@/types";
import { PanelShell } from "./PanelShell";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Download } from "lucide-react";
import { downloadTranscriptAsTxt, getSpeakerColor } from "@/lib/utils";

interface Props {
  segments: TranscriptSegment[];
  partial?: TranscriptSegment | null;
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
  }, [segments, partial, autoScroll]);

  return (
    <PanelShell
      title="Live Transcript"
      empty={segments.length === 0 && !partial}
      emptyMessage="Waiting for transcript chunks…"
      actions={
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => onToggleAutoScroll(e.target.checked)}
            />
            Auto-scroll
          </label>
          {segments.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                downloadTranscriptAsTxt(segments, "live-transcript.txt")
              }
            >
              <Download className="h-4 w-4" />
              Download TXT
            </Button>
          )}
        </div>
      }
    >
      <div ref={ref} className="max-h-[420px] overflow-y-auto pr-2">
        <ul className="space-y-3">
          {segments.map((seg, i) => (
            <li key={i} className="text-sm flex flex-wrap items-baseline gap-2">
              <Badge
                variant="secondary"
                className={`${getSpeakerColor(seg.speaker)} border-0 font-medium`}
              >
                {seg.speaker}
              </Badge>
              <span className="text-foreground/90">{seg.text}</span>
            </li>
          ))}

          {partial && partial.text && (
            <li className="text-sm flex flex-wrap items-baseline gap-2 opacity-60 italic animate-pulse">
              <Badge
                variant="outline"
                className="border-dashed font-medium text-muted-foreground"
              >
                {partial.speaker}
              </Badge>
              <span>{partial.text}</span>
            </li>
          )}
        </ul>
      </div>
    </PanelShell>
  );
}
