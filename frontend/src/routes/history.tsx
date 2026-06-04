import { createFileRoute } from "@tanstack/react-router";
import { HistoryPage } from "@/pages/HistoryPage";

export const Route = createFileRoute("/history")({
  head: () => ({
    meta: [
      { title: "SpeechFlow — Session History" },
      { name: "description", content: "Browse previously processed sessions." },
    ],
  }),
  component: HistoryPage,
});
