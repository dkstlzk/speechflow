import { MessageSquareText, Download } from "lucide-react";
import type { TranscriptSegment } from "@/types";
import { PanelShell } from "./PanelShell";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { downloadTranscriptAsTxt, getSpeakerColor } from "@/lib/utils";
import { formatTranscriptTime } from "@/lib/transcript";

interface Props {
  segments?: TranscriptSegment[];
  loading?: boolean;
  error?: string | null;
}

export function TranscriptViewer({ segments, loading, error }: Props) {
  const hasSegments = !!segments && segments.length > 0;
  return (
    <PanelShell
      title="Transcript"
      icon={<MessageSquareText className="h-3.5 w-3.5" />}
      loading={loading}
      error={error}
      empty={!loading && !error && !hasSegments}
      emptyMessage="No transcript available yet."
      actions={
        hasSegments ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => downloadTranscriptAsTxt(segments!, "transcript.txt")}
          >
            <Download className="h-3.5 w-3.5" />
            Export
          </Button>
        ) : null
      }
    >
      <div className="max-h-[calc(100vh-12rem)] overflow-y-auto pr-1">
        <ul className="space-y-5">
          {segments?.map((seg, i) => (
            <li key={i} className="group">
              <div className="mb-1.5 flex flex-wrap items-center gap-2">
                <Badge
                  variant="secondary"
                  className={`${getSpeakerColor(seg.speaker)} border-0 font-medium`}
                >
                  {seg.speaker === "UNKNOWN" ? "Speaker" : seg.speaker}
                </Badge>
                <span className="text-[11px] font-mono text-muted-foreground/70">
                  #{i + 1} • {formatTranscriptTime(seg.startSec)} →{" "}
                  {formatTranscriptTime(seg.endSec)}
                </span>
              </div>
              <p
                className={`text-[14.5px] leading-7 ${
                  seg.is_partial ? "italic text-muted-foreground" : "text-foreground/90"
                }`}
              >
                {seg.text}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </PanelShell>
  );
}
