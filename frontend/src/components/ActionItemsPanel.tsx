import type { ActionItem } from "@/types";
import { PanelShell } from "./PanelShell";

interface Props {
  items?: ActionItem[];
  loading?: boolean;
  error?: string | null;
}

export function ActionItemsPanel({ items, loading, error }: Props) {
  return (
    <PanelShell
      title="Action Items"
      loading={loading}
      error={error}
      empty={!loading && !error && (!items || items.length === 0)}
      emptyMessage="No action items extracted."
    >
      <ul className="space-y-3">
        {items?.map((it) => (
          <li
            key={it.id}
            className="rounded-md border border-border bg-background px-3 py-2 text-sm"
          >
            <p className="font-medium">{it.text}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {it.owner ? `Owner: ${it.owner}` : "Unassigned"}
              {it.dueDate ? ` · Due ${it.dueDate}` : ""}
            </p>
          </li>
        ))}
      </ul>
    </PanelShell>
  );
}
