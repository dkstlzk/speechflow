import { CheckCircle2, ListTodo } from "lucide-react";
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
      icon={<ListTodo className="h-3.5 w-3.5" />}
      loading={loading}
      error={error}
      empty={!loading && !error && (!items || items.length === 0)}
      emptyMessage="Action items unavailable or generation failed."
    >
      <ul className="divide-y divide-border/70">
        {items?.map((it) => (
          <li key={it.id} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
            <CheckCircle2
              className={`mt-0.5 h-4 w-4 shrink-0 ${
                it.completed ? "text-emerald-500" : "text-muted-foreground/50"
              }`}
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm leading-6 text-foreground">{it.text}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {it.owner ? `Owner: ${it.owner}` : "Unassigned"}
                {it.dueDate ? ` · Due ${it.dueDate}` : ""}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </PanelShell>
  );
}
