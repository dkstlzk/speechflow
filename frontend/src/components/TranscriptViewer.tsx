import { MessageSquareText, Download } from "lucide-react";
import type { TranscriptSegment, Session } from "@/types";
import { PanelShell } from "./PanelShell";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { downloadTranscriptAsTxt, getSpeakerColor } from "@/lib/utils";
import { formatTranscriptTime } from "@/lib/transcript";
import { generateExportFilename } from "@/lib/export";

import { useState, useMemo, useRef, useEffect } from "react";

function SpeakerBadge({
  seg,
  speakerMapping,
  onRenameSpeaker,
}: {
  seg: TranscriptSegment;
  speakerMapping: Record<string, string>;
  onRenameSpeaker?: (speaker: string, newName: string) => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const currentName =
    seg.displayName ||
    speakerMapping[seg.speaker] ||
    (seg.speaker === "UNKNOWN" ? "Speaker" : seg.speaker);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isEditing]);

  const isSaving = useRef(false);

  const handleSave = () => {
    if (isSaving.current) return;
    isSaving.current = true;

    const trimmed = editValue.trim();
    if (trimmed !== currentName) {
      onRenameSpeaker?.(seg.speaker, trimmed);
    }
    setIsEditing(false);

    // Reset after a short delay to prevent double-firing from onBlur
    setTimeout(() => {
      isSaving.current = false;
    }, 100);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSave();
    if (e.key === "Escape") setIsEditing(false);
  };

  if (isEditing) {
    return (
      <input
        ref={inputRef}
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        className={`h-6 rounded bg-background px-2 py-0 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-ring ${getSpeakerColor(seg.speaker)}`}
        style={{ width: `${Math.max(editValue.length, 5) + 2}ch` }}
      />
    );
  }

  return (
    <Badge
      variant="secondary"
      className={`${getSpeakerColor(seg.speaker)} cursor-pointer border-0 font-medium hover:opacity-80 transition-opacity`}
      onClick={() => {
        if (onRenameSpeaker) {
          setEditValue(currentName);
          setIsEditing(true);
        }
      }}
    >
      {currentName}
    </Badge>
  );
}

interface Props {
  segments?: TranscriptSegment[];
  loading?: boolean;
  error?: string | null;
  session?: Session;
  onRenameSpeaker?: (speaker: string, newName: string) => void;
  searchQuery?: string;
  onSeek?: (time: number) => void;
  activeTranslation?: import("@/services/api").TranslationResponse | null;
}

export function TranscriptViewer({
  segments,
  loading,
  error,
  session,
  onRenameSpeaker,
  searchQuery,
  onSeek,
  activeTranslation,
}: Props) {
  const hasSegments = !!segments && segments.length > 0;

  const highlightText = (text: string, query?: string): React.ReactNode => {
    if (!query || query.trim() === "") return text;
    const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const parts = text.split(new RegExp(`(${escaped})`, "gi"));
    return (
      <>
        {parts.map((part, i) =>
          part.toLowerCase() === query.toLowerCase() ? (
            <mark
              key={i}
              className="bg-yellow-200/80 text-foreground rounded-sm px-0.5 font-medium dark:bg-yellow-500/40"
            >
              {part}
            </mark>
          ) : (
            part
          ),
        )}
      </>
    );
  };

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
          {segments?.map((seg, i) => {
            let translatedText = null;
            if (activeTranslation?.translated_chunks && seg.id) {
              const tc = activeTranslation.translated_chunks.find((c) => c.chunk_id === seg.id);
              if (tc) translatedText = tc.text;
            }

            return (
              <li key={i} className="group">
                <div className="mb-1.5 flex flex-wrap items-center gap-2">
                  <SpeakerBadge
                    seg={seg}
                    speakerMapping={speakerMapping}
                    onRenameSpeaker={onRenameSpeaker}
                  />
                  {seg.language && (
                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 bg-muted px-1.5 py-0.5 rounded-sm">
                      {seg.language}
                    </span>
                  )}
                  <button
                    onClick={() => {
                      if (onSeek && seg.startSec !== undefined) {
                        onSeek(seg.startSec);
                      }
                    }}
                    disabled={!onSeek || seg.startSec === undefined}
                    aria-label={`Jump to ${formatTranscriptTime(seg.startSec)}`}
                    className={`text-[11px] font-mono text-muted-foreground/70 transition-colors ${onSeek && seg.startSec !== undefined ? "cursor-pointer hover:text-primary" : ""}`}
                  >
                    #{i + 1} • {formatTranscriptTime(seg.startSec)} →{" "}
                    {formatTranscriptTime(seg.endSec)}
                  </button>
                </div>
                <div className={`${translatedText ? "grid grid-cols-2 gap-4" : ""}`}>
                  <p
                    className={`text-[14.5px] leading-7 ${
                      seg.is_partial ? "italic text-muted-foreground" : "text-foreground/90"
                    }`}
                  >
                    {highlightText(seg.text, searchQuery)}
                  </p>
                  {translatedText && (
                    <p className="text-[14.5px] leading-7 text-primary/90 border-l border-primary/20 pl-4">
                      {highlightText(translatedText, searchQuery)}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </PanelShell>
  );
}
