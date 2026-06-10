import type { ActionItem, Session, TranscriptSegment } from "@/types";
import { formatTranscriptTime } from "./transcript";

export function generateExportFilename(
  session: Session,
  extension: string,
  suffix?: string,
): string {
  const rawTitle = session.title || session.fileName || "SpeechFlow_Session";

  const safeTitle = rawTitle
    .replace(/\.[^/.]+$/, "")
    .replace(/[<>:"/\\|?*#]/g, "")
    .trim()
    .replace(/\s+/g, "_");

  const date = session.createdAt
    ? new Date(session.createdAt).toISOString().split("T")[0]
    : new Date().toISOString().split("T")[0];

  const artifact = suffix ? `_${suffix}` : "";

  return `${safeTitle}_${date}${artifact}.${extension}`;
}

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
      md += `- ${a.text}\n`;
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
      txt += ` - ${a.text}\n`;
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

export function exportAsMarkdown(data: SessionData) {
  const md = buildMarkdown(data);

  downloadFile(md, generateExportFilename(data.session, "md"), "text/markdown;charset=utf-8;");
}

export function exportAsTxt(data: SessionData) {
  const txt = buildTxt(data);

  downloadFile(txt, generateExportFilename(data.session, "txt"), "text/plain;charset=utf-8;");
}

export function printAsPdf() {
  window.print();
}
