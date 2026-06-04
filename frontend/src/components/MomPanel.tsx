import { PanelShell } from "./PanelShell";

interface Props {
  mom?: string | null;
  loading?: boolean;
  error?: string | null;
}

export function MomPanel({ mom, loading, error }: Props) {
  return (
    <PanelShell
      title="Meeting Minutes"
      loading={loading}
      error={error}
      empty={!loading && !error && !mom}
      emptyMessage="No meeting minutes generated."
    >
      <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
        {mom}
      </pre>
    </PanelShell>
  );
}
