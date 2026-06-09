import { createFileRoute } from "@tanstack/react-router";
import { UploadPage } from "@/pages/UploadPage";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "SpeechFlow — Upload" },
      {
        name: "description",
        content: "Upload audio/video recordings for transcription and intelligent processing.",
      },
    ],
  }),
  component: UploadPage,
});
