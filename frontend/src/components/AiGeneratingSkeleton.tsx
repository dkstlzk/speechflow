import { Skeleton } from "./ui/skeleton";
import { Sparkles } from "lucide-react";

export function AiGeneratingSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
        <Sparkles className="h-4 w-4 text-primary" />
        AI is generating intelligence…
      </div>
      <section className="rounded-lg border border-border bg-card p-5 shadow-sm space-y-3">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-32 w-full" />
      </section>
      <section className="rounded-lg border border-border bg-card p-5 shadow-sm space-y-3">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-3/4" />
      </section>
    </div>
  );
}
