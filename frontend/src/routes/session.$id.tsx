import { createFileRoute } from "@tanstack/react-router";
import { SessionPage } from "@/pages/SessionPage";

export const Route = createFileRoute("/session/$id")({
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
  return <SessionPage id={id} />;
}
