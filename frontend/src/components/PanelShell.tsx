import type { ReactNode } from "react";
import { Inbox } from "lucide-react";

interface Props {
  title: string;
  icon?: ReactNode;
  description?: string;
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyMessage?: string;
  actions?: ReactNode;
  children?: ReactNode;
  bare?: boolean;
}

export function PanelShell({
  title,
  icon,
  description,
  loading,
  error,
  empty,
  emptyMessage = "Nothing to show.",
  actions,
  children,
  bare,
}: Props) {
  return (
    <section
      className={bare ? "space-y-4" : "rounded-xl border border-border/70 bg-card p-5 sm:p-6"}
    >
      <header className="mb-4 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h3 className="flex items-center gap-2 text-[13px] font-semibold tracking-tight text-foreground">
            {icon && <span className="text-muted-foreground">{icon}</span>}
            {title}
          </h3>
          {description && <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>}
        </div>
        {actions}
      </header>

      {loading ? (
        <div className="space-y-2">
          <div className="h-3 w-2/3 animate-pulse rounded bg-muted" />
          <div className="h-3 w-1/2 animate-pulse rounded bg-muted" />
          <div className="h-3 w-3/4 animate-pulse rounded bg-muted" />
        </div>
      ) : error ? (
        <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
      ) : empty ? (
        <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <Inbox className="h-4 w-4" />
          </span>
          <p className="text-sm text-muted-foreground">{emptyMessage}</p>
        </div>
      ) : (
        children
      )}
    </section>
  );
}
