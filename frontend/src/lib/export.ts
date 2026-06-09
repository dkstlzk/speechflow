import type { ActionItem, Session, TranscriptSegment } from "@/types";
import { formatTranscriptTime } from "./transcript";

export interface SessionData {
  session: Session;
  transcript: TranscriptSegment[];
  summary?: string | null;
  mom?: string | null;
  actions?: ActionItem[];
}

function buildSpeakerMap(segments: TranscriptSegment[]): Record<string, string> {
  const map: Record<string, string> = {};
  let speakerIdx = 0;
  for (const seg of segments) {
    if (seg.speaker === "UNKNOWN" || !seg.speaker.startsWith("SPEAKER_")) continue;
    if (!map[seg.speaker]) {
      map[seg.speaker] = `Speaker ${String.fromCharCode(65 + speakerIdx)}`;
      speakerIdx++;
    }
  }
  return map;
}

function buildMarkdown(data: SessionData): string {
  const { session, transcript, summary, mom, actions } = data;
  const title = session.title || session.fileName || "Session";
  const date = session.createdAt ? new Date(session.createdAt).toLocaleString() : "Unknown Date";

  let md = `# ${title}\n\n`;
  md += `**Date:** ${date}\n`;
  md += `**ID:** ${session.id}\n\n`;
  md += `---\n\n`;

  if (summary) {
    md += `## Intelligence Summary\n\n${summary}\n\n---\n\n`;
  }

  if (mom) {
    md += `## Meeting Minutes\n\n${mom}\n\n---\n\n`;
  }

  if (actions && actions.length > 0) {
    md += `## Action Items\n\n`;
    actions.forEach((a) => {
      // If status exists on type, show it. Otherwise just print the text.
      const statusStr = (a as any).status === "completed" ? "x" : " ";
      md += `- [${statusStr}] ${a.text}\n`;
    });
    md += `\n---\n\n`;
  }

  md += `## Full Transcript\n\n`;
  const speakerMap = buildSpeakerMap(transcript);
  
  transcript.forEach((t) => {
    const time = `[${formatTranscriptTime(t.startSec)} -> ${formatTranscriptTime(t.endSec)}]`;
    const speakerName = speakerMap[t.speaker] || (t.speaker === "UNKNOWN" ? "Speaker" : t.speaker);
    md += `**${speakerName}** ${time}:\n${t.text}\n\n`;
  });

  return md;
}

function buildTxt(data: SessionData): string {
  const { session, transcript, summary, mom, actions } = data;
  const title = session.title || session.fileName || "Session";
  const date = session.createdAt ? new Date(session.createdAt).toLocaleString() : "Unknown Date";

  let txt = `=================================================\n`;
  txt += ` ${title.toUpperCase()}\n`;
  txt += ` Date: ${date}\n`;
  txt += ` ID: ${session.id}\n`;
  txt += `=================================================\n\n`;

  if (summary) {
    txt += `[ INTELLIGENCE SUMMARY ]\n\n${summary}\n\n`;
  }

  if (mom) {
    txt += `[ MEETING MINUTES ]\n\n${mom}\n\n`;
  }

  if (actions && actions.length > 0) {
    txt += `[ ACTION ITEMS ]\n\n`;
    actions.forEach((a) => {
      const status = (a as any).status || "open";
      txt += ` - ${a.text} (${status})\n`;
    });
    txt += `\n`;
  }

  txt += `[ FULL TRANSCRIPT ]\n\n`;
  const speakerMap = buildSpeakerMap(transcript);

  transcript.forEach((t) => {
    const time = `[${formatTranscriptTime(t.startSec)} -> ${formatTranscriptTime(t.endSec)}]`;
    const speakerName = speakerMap[t.speaker] || (t.speaker === "UNKNOWN" ? "Speaker" : t.speaker);
    txt += `${speakerName} ${time}:\n${t.text}\n\n`;
  });

  return txt;
}

function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function exportAsMarkdown(data: SessionData, filename: string = "export.md") {
  const md = buildMarkdown(data);
  downloadFile(md, filename, "text/markdown;charset=utf-8;");
}

export function exportAsTxt(data: SessionData, filename: string = "export.txt") {
  const txt = buildTxt(data);
  downloadFile(txt, filename, "text/plain;charset=utf-8;");
}

export function printAsPdf() {
  window.print();
}
