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
      loading={loading}
      error={error}
      empty={!loading && !error && !summary}
      emptyMessage="No summary generated."
    >
      <p className="whitespace-pre-line text-sm leading-relaxed">{summary}</p>
    </PanelShell>
  );
}
