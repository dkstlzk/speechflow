import type { TranscriptSegment } from "@/types";
import { PanelShell } from "./PanelShell";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Download } from "lucide-react";
import { downloadTranscriptAsTxt, getSpeakerColor } from "@/lib/utils";

interface Props {
  segments?: TranscriptSegment[];
  loading?: boolean;
  error?: string | null;
}

function formatTime(s?: number) {
  if (s === undefined) return "";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

export function TranscriptViewer({ segments, loading, error }: Props) {
  const hasSegments = !!segments && segments.length > 0;
  return (
    <PanelShell
      title="Transcript"
      loading={loading}
      error={error}
      empty={!loading && !error && !hasSegments}
      emptyMessage="No transcript available."
      actions={
        hasSegments ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => downloadTranscriptAsTxt(segments!, "transcript.txt")}
          >
            <Download className="h-4 w-4" />
            Download TXT
          </Button>
        ) : null
      }
    >
      <div className="max-h-[480px] overflow-y-auto pr-2">
        <ul className="space-y-4">
          {segments?.map((seg, i) => (
            <li key={i} className="text-sm">
              <div className="mb-1 flex items-baseline gap-2">
                <Badge
                  variant="secondary"
                  className={`${getSpeakerColor(seg.speaker)} border-0 font-medium`}
                >
                  {seg.speaker}
                </Badge>
                {seg.startSec !== undefined && (
                  <span className="text-xs text-muted-foreground">
                    {formatTime(seg.startSec)}
                  </span>
                )}
              </div>
              <p className="text-foreground/90">{seg.text}</p>
            </li>
          ))}
        </ul>
      </div>
    </PanelShell>
  );
}
