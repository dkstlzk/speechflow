import { ScrollText } from "lucide-react";
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
      icon={<ScrollText className="h-3.5 w-3.5" />}
      loading={loading}
      error={error}
      empty={!loading && !error && !mom}
      emptyMessage="No meeting minutes available."
    >
      <pre className="whitespace-pre-wrap font-sans text-[14px] leading-7 text-foreground/90">
        {mom}
      </pre>
    </PanelShell>
  );
}
