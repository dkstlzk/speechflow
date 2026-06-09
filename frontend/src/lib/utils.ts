import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { TranscriptSegment } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function downloadTranscriptAsTxt(segments: TranscriptSegment[], filename: string) {
  const body = segments
    .filter((s) => !s.is_partial)
    .map((s) => `${s.speaker}: ${s.text}`)
    .join("\n");
  const blob = new Blob([body], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".txt") ? filename : `${filename}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

const SPEAKER_PALETTE = [
  "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200",
  "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-200",
  "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  "bg-pink-100 text-pink-800 dark:bg-pink-950 dark:text-pink-200",
  "bg-cyan-100 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-200",
  "bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-200",
  "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-200",
];

export function getSpeakerColor(speakerName: string): string {
  const name = (speakerName || "Unknown").trim();
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) | 0;
  }
  const idx = Math.abs(hash) % SPEAKER_PALETTE.length;
  return SPEAKER_PALETTE[idx];
}
