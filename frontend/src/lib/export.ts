import type { ActionItem, Session, TranscriptSegment } from "@/types";
import { formatTranscriptTime } from "./transcript";
import { Document, Packer, Paragraph, TextRun, HeadingLevel } from "docx";

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
    if (seg.displayName) {
      map[seg.speaker] = seg.displayName;
    } else if (!map[seg.speaker]) {
      map[seg.speaker] = `Speaker ${String.fromCharCode(65 + speakerIdx)}`;
      speakerIdx++;
    }
  }
  return map;
}

function escapeMarkdown(text: string): string {
  if (!text) return text;
  // Escape markdown control characters to prevent layout breakage
  return text.replace(/([\\`*_{}[\]()#+|<>~])/g, '\\$1');
}

function buildMarkdown(data: SessionData): string {
  const { session, transcript, summary, mom, actions } = data;
  const title = session.title || session.fileName || "Session";
  const date = session.createdAt ? new Date(session.createdAt).toLocaleString() : "Unknown Date";

  let md = `# ${escapeMarkdown(title)}\n\n`;
  md += `**Date:** ${date}\n`;
  if (session.host_name) md += `**Host:** ${escapeMarkdown(session.host_name)}\n`;
  if (session.participants) md += `**Participants:** ${escapeMarkdown(session.participants)}\n`;
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
  if (session.host_name) txt += ` Host: ${session.host_name}\n`;
  if (session.participants) txt += ` Participants: ${session.participants}\n`;
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

export async function exportAsDocx(data: SessionData) {
  const { session, transcript, summary, mom, actions } = data;
  const title = session.title || session.fileName || "Session";
  const date = session.createdAt ? new Date(session.createdAt).toLocaleString() : "Unknown Date";

  const children: Paragraph[] = [
    new Paragraph({
      text: title,
      heading: HeadingLevel.HEADING_1,
    }),
    new Paragraph({
      children: [
        new TextRun({ text: "Date: ", bold: true }),
        new TextRun(date),
      ],
    }),
  ];

  if (session.host_name) {
    children.push(
      new Paragraph({
        children: [
          new TextRun({ text: "Host: ", bold: true }),
          new TextRun(session.host_name),
        ],
      })
    );
  }

  if (session.participants) {
    children.push(
      new Paragraph({
        children: [
          new TextRun({ text: "Participants: ", bold: true }),
          new TextRun(session.participants),
        ],
      })
    );
  }

  children.push(
    new Paragraph({
      children: [
        new TextRun({ text: "ID: ", bold: true }),
        new TextRun(session.id),
      ],
      spacing: { after: 400 },
    }),
  );

  if (summary) {
    children.push(
      new Paragraph({ text: "Intelligence Summary", heading: HeadingLevel.HEADING_2 }),
      new Paragraph({ text: summary, spacing: { after: 400 } })
    );
  }

  if (mom) {
    children.push(
      new Paragraph({ text: "Meeting Minutes", heading: HeadingLevel.HEADING_2 }),
      new Paragraph({ text: mom, spacing: { after: 400 } })
    );
  }

  if (actions && actions.length > 0) {
    children.push(new Paragraph({ text: "Action Items", heading: HeadingLevel.HEADING_2 }));
    actions.forEach((a) => {
      children.push(new Paragraph({ text: a.text, bullet: { level: 0 } }));
    });
    children.push(new Paragraph({ text: "", spacing: { after: 400 } }));
  }

  children.push(new Paragraph({ text: "Full Transcript", heading: HeadingLevel.HEADING_2 }));
  const speakerMap = buildSpeakerMap(transcript);

  transcript.forEach((t) => {
    const time = `[${formatTranscriptTime(t.startSec)} -> ${formatTranscriptTime(t.endSec)}]`;
    const speakerName = speakerMap[t.speaker] || (t.speaker === "UNKNOWN" ? "Speaker" : t.speaker);
    children.push(
      new Paragraph({
        children: [
          new TextRun({ text: `${speakerName} `, bold: true }),
          new TextRun({ text: time, color: "666666" }),
        ],
      }),
      new Paragraph({ text: t.text, spacing: { after: 200 } })
    );
  });

  const doc = new Document({
    sections: [{ children }],
  });

  const blob = await Packer.toBlob(doc);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = generateExportFilename(data.session, "docx");
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}


// ─── Translated Export Functions ─────────────────────────────────────

export interface TranslatedExportData {
  session: Session;
  translatedTranscript: string;
  translatedSummary?: string | null;
  translatedMom?: string | null;
  targetLanguage: string;
}

export async function exportTranslatedAsDocx(data: TranslatedExportData) {
  const { session, translatedTranscript, translatedSummary, translatedMom, targetLanguage } = data;
  const title = session.title || session.fileName || "Session";
  const date = session.createdAt ? new Date(session.createdAt).toLocaleString() : "Unknown Date";

  const children: Paragraph[] = [
    new Paragraph({
      text: `${title} — ${targetLanguage} Translation`,
      heading: HeadingLevel.HEADING_1,
    }),
    new Paragraph({
      children: [
        new TextRun({ text: "Date: ", bold: true }),
        new TextRun(date),
      ],
    }),
    new Paragraph({
      children: [
        new TextRun({ text: "Language: ", bold: true }),
        new TextRun(targetLanguage),
      ],
    }),
  ];

  if (session.host_name) {
    children.push(
      new Paragraph({
        children: [
          new TextRun({ text: "Host: ", bold: true }),
          new TextRun(session.host_name),
        ],
      })
    );
  }

  if (session.participants) {
    children.push(
      new Paragraph({
        children: [
          new TextRun({ text: "Participants: ", bold: true }),
          new TextRun(session.participants),
        ],
      })
    );
  }

  children.push(
    new Paragraph({
      children: [
        new TextRun({ text: "ID: ", bold: true }),
        new TextRun(session.id),
      ],
      spacing: { after: 400 },
    }),
  );

  if (translatedSummary) {
    children.push(
      new Paragraph({ text: "Translated Summary", heading: HeadingLevel.HEADING_2 }),
      ...translatedSummary.split("\n").map(
        (line) => new Paragraph({ text: line, spacing: { after: 100 } }),
      ),
      new Paragraph({ text: "", spacing: { after: 400 } }),
    );
  }

  if (translatedMom) {
    children.push(
      new Paragraph({ text: "Translated Meeting Minutes", heading: HeadingLevel.HEADING_2 }),
      ...translatedMom.split("\n").map(
        (line) => new Paragraph({ text: line, spacing: { after: 100 } }),
      ),
      new Paragraph({ text: "", spacing: { after: 400 } }),
    );
  }

  children.push(
    new Paragraph({ text: "Translated Transcript", heading: HeadingLevel.HEADING_2 }),
    ...translatedTranscript.split("\n").map(
      (line) => new Paragraph({ text: line, spacing: { after: 100 } }),
    ),
  );

  const doc = new Document({
    sections: [{ children }],
  });

  const blob = await Packer.toBlob(doc);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = generateExportFilename(data.session, "docx", targetLanguage);
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function exportTranslatedAsTxt(data: TranslatedExportData) {
  const { session, translatedTranscript, translatedSummary, translatedMom, targetLanguage } = data;
  const title = session.title || session.fileName || "Session";
  const date = session.createdAt ? new Date(session.createdAt).toLocaleString() : "Unknown Date";

  let txt = `=================================================\n`;
  txt += ` ${title.toUpperCase()} — ${targetLanguage.toUpperCase()} TRANSLATION\n`;
  txt += ` Date: ${date}\n`;
  if (session.host_name) txt += ` Host: ${session.host_name}\n`;
  if (session.participants) txt += ` Participants: ${session.participants}\n`;
  txt += ` Language: ${targetLanguage}\n`;
  txt += ` ID: ${session.id}\n`;
  txt += `=================================================\n\n`;

  if (translatedSummary) {
    txt += `[ TRANSLATED SUMMARY ]\n\n${translatedSummary}\n\n`;
  }

  if (translatedMom) {
    txt += `[ TRANSLATED MEETING MINUTES ]\n\n${translatedMom}\n\n`;
  }

  txt += `[ TRANSLATED TRANSCRIPT ]\n\n${translatedTranscript}\n`;

  downloadFile(
    txt,
    generateExportFilename(session, "txt", targetLanguage),
    "text/plain;charset=utf-8;",
  );
}

