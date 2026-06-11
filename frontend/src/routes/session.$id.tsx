import { createFileRoute } from "@tanstack/react-router";
import { SessionPage } from "@/pages/SessionPage";

import { z } from "zod";

export const Route = createFileRoute("/session/$id")({
  validateSearch: z.object({
    q: z.string().optional(),
  }),
  head: () => ({
    meta: [
      { title: "SpeechFlow — Session" },
      { name: "description", content: "Session transcript, summary, MoM and action items." },
    ],
  }),
  component: RouteComponent,
});

function RouteComponent() {
  const { id } = Route.useParams();
  const search = Route.useSearch();
  return <SessionPage id={id} initialSearch={search.q} />;
}
