import type { ReactNode } from "react";

interface Props {
  title: string;
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyMessage?: string;
  actions?: ReactNode;
  children?: ReactNode;
}

export function PanelShell({
  title,
  loading,
  error,
  empty,
  emptyMessage = "Nothing to show.",
  actions,
  children,
}: Props) {
  return (
    <section className="rounded-lg border border-border bg-card p-5 shadow-sm">
      <header className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
        </h3>
        {actions}
      </header>
      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : error ? (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-200">
          {error}
        </p>
      ) : empty ? (
        <p className="text-sm text-muted-foreground">{emptyMessage}</p>
      ) : (
        children
      )}
    </section>
  );
}
