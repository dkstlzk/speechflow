import type { TranscriptSegment } from "@/types";
import { PanelShell } from "./PanelShell";

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
  return (
    <PanelShell
      title="Transcript"
      loading={loading}
      error={error}
      empty={!loading && !error && (!segments || segments.length === 0)}
      emptyMessage="No transcript available."
    >
      <div className="max-h-[480px] overflow-y-auto pr-2">
        <ul className="space-y-4">
          {segments?.map((seg, i) => (
            <li key={i} className="text-sm">
              <div className="mb-1 flex items-baseline gap-2">
                <span className="font-medium">{seg.speaker}</span>
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
