import type { TranscriptSegment } from "@/types";
import { PanelShell } from "./PanelShell";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Download } from "lucide-react";
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
            <li
              key={i}
              className="text-sm flex flex-wrap items-baseline gap-2"
            >
              <Badge
                variant="secondary"
                className={`${getSpeakerColor(seg.speaker)} border-0 font-medium`}
              >
                {seg.speaker}
              </Badge>

              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground">
                  #{seg.chunk_index}
                  {" • "}
                  {formatTranscriptTime(seg.startSec)}
                  {" → "}
                  {formatTranscriptTime(seg.endSec)}
                </span>

                <span className="text-foreground/90">
                  {seg.text}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </PanelShell>
  );
}
