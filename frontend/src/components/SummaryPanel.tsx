import { Sparkles } from "lucide-react";
import { PanelShell } from "./PanelShell";

interface Props {
  summary?: string;
  loading?: boolean;
  error?: string | null;
}

export function SummaryPanel({ summary, loading, error }: Props) {
  return (
    <PanelShell
      title="Summary"
      icon={<Sparkles className="h-3.5 w-3.5" />}
      loading={loading}
      error={error}
      empty={!loading && !error && !summary}
      emptyMessage="No intelligence generated yet."
    >
      <p className="whitespace-pre-line text-[14px] leading-7 text-foreground/90">{summary}</p>
    </PanelShell>
  );
}
