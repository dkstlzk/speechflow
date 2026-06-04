import { createFileRoute } from "@tanstack/react-router";
import { RealtimePage } from "@/pages/RealtimePage";

export const Route = createFileRoute("/realtime")({
  head: () => ({
    meta: [
      { title: "SpeechFlow — Realtime Recording" },
      {
        name: "description",
        content: "Live microphone transcription and session monitoring.",
      },
    ],
  }),
  component: RealtimePage,
});
