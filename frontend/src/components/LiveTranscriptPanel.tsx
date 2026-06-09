import { useEffect, useRef } from "react";
import type { TranscriptSegment } from "@/types";
import { PanelShell } from "./PanelShell";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Download } from "lucide-react";
import { downloadTranscriptAsTxt, getSpeakerColor } from "@/lib/utils";

import { formatTranscriptTime } from "@/lib/transcript";

interface Props {
  segments: TranscriptSegment[];
  autoScroll: boolean;
  onToggleAutoScroll: (v: boolean) => void;
}

/**
 * LiveTranscriptPanel — Displays committed transcript chunks only.
 *
 * Every entry here has already been persisted to the database.
 * No partial/draft segments are shown — those are handled by LiveCaptionStrip.
 */
export function LiveTranscriptPanel({ segments, autoScroll, onToggleAutoScroll }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight;
    }
  }, [segments, autoScroll]);

  return (
    <PanelShell
      title="Live Transcript"
      empty={segments.length === 0}
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
              onClick={() => downloadTranscriptAsTxt(segments, "live-transcript.txt")}
            >
              <Download className="h-4 w-4" />
              Download TXT
            </Button>
          )}
        </div>
      }
    >
      <div ref={ref} className="max-h-[420px] overflow-y-auto pr-2">
        <ul className="space-y-6">
          {segments.map((seg, i) => (
            <li key={i} className="text-sm flex flex-wrap items-baseline gap-2">
              <Badge
                variant="secondary"
                className={`${getSpeakerColor(seg.speaker)} border-0 font-medium`}
              >
                {seg.speaker === "UNKNOWN" ? "Speaker" : seg.speaker}
              </Badge>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">
                  #{i + 1}
                  {" • "}
                  {formatTranscriptTime(seg.startSec)}
                  {" → "}
                  {formatTranscriptTime(seg.endSec)}
                </span>

                <span className="text-foreground/90 leading-relaxed mt-1">{seg.text}</span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </PanelShell>
  );
}
