import { ScrollText } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { PanelShell } from "./PanelShell";

interface Props {
  mom?: string | null;
  loading?: boolean;
  error?: string | null;
  emptyMessage?: string;
  transcriptType?: string;
}

export function MomPanel({ mom, loading, error, emptyMessage, transcriptType }: Props) {
  const getTitle = (type?: string) => {
    switch (type) {
      case "lecture": return "Lecture Notes";
      case "interview": return "Interview Notes";
      case "presentation": return "Presentation Notes";
      case "voice_note": return "Voice Note Details";
      case "conversation": return "Conversation Details";
      case "meeting":
      default:
        return "Meeting Minutes";
    }
  };

  return (
    <PanelShell
      title={getTitle(transcriptType)}
      icon={<ScrollText className="h-3.5 w-3.5" />}
      loading={loading}
      error={error}
      empty={!loading && !error && !mom}
      emptyMessage={emptyMessage || "Not generated yet."}
    >
      <div className="prose prose-sm dark:prose-invert max-w-none text-foreground/90 prose-p:leading-relaxed prose-pre:bg-muted prose-pre:text-foreground prose-a:text-primary">
        <ReactMarkdown>{mom || ""}</ReactMarkdown>
      </div>
    </PanelShell>
  );
}
