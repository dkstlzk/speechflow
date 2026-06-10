import { MessageSquareText, Download } from "lucide-react";
import type { TranscriptSegment, Session } from "@/types";
import { PanelShell } from "./PanelShell";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { downloadTranscriptAsTxt, getSpeakerColor } from "@/lib/utils";
import { formatTranscriptTime } from "@/lib/transcript";
import { generateExportFilename } from "@/lib/export";

import { useMemo } from "react";

interface Props {
  segments?: TranscriptSegment[];
  loading?: boolean;
  error?: string | null;
  session?: Session;
}

export function TranscriptViewer({ segments, loading, error, session }: Props) {
  const hasSegments = !!segments && segments.length > 0;

  const speakerMapping = useMemo(() => {
    const map: Record<string, string> = {};
    if (!segments) return map;

    let speakerIdx = 0;
    for (const seg of segments) {
      if (seg.speaker === "UNKNOWN" || !seg.speaker.startsWith("SPEAKER_")) {
        continue;
      }
      if (!map[seg.speaker]) {
        map[seg.speaker] = `Speaker ${String.fromCharCode(65 + speakerIdx)}`;
        speakerIdx++;
      }
    }
    return map;
  }, [segments]);

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
            onClick={() => {
              const filename = session
                ? generateExportFilename(session, "txt", "transcript")
                : "transcript.txt";
              downloadTranscriptAsTxt(segments!, filename);
            }}
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
                  {speakerMapping[seg.speaker] ||
                    (seg.speaker === "UNKNOWN" ? "Speaker" : seg.speaker)}
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
