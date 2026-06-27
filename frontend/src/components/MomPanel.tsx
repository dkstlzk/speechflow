import { ScrollText } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { PanelShell } from "./PanelShell";

interface Props {
  mom?: string | null;
  loading?: boolean;
  error?: string | null;
  emptyMessage?: string;
}

export function MomPanel({ mom, loading, error, emptyMessage }: Props) {
  return (
    <PanelShell
      title="Meeting Minutes"
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
