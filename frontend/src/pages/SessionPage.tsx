import { useCallback, useEffect, useRef, useState } from "react";
import { Sparkles, RefreshCw } from "lucide-react";
import { AppLayout } from "@/layouts/AppLayout";
import { TranscriptViewer } from "@/components/TranscriptViewer";
import { SummaryPanel } from "@/components/SummaryPanel";
import { MomPanel } from "@/components/MomPanel";
import { ActionItemsPanel } from "@/components/ActionItemsPanel";
import { AiGeneratingSkeleton } from "@/components/AiGeneratingSkeleton";
import { StatusBadge } from "@/components/StatusBadge";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  ApiError,
  getActions,
  getSession,
  getSummary,
  getTranscript,
  processSession,
} from "@/services/api";
import type { ActionItem, Session, SummaryResponse, TranscriptResponse } from "@/types";

interface State<T> {
  data?: T;
  loading: boolean;
  error: string | null;
}

const initial = <T,>(): State<T> => ({ loading: true, error: null });

const POLL_INTERVAL_MS = 5000;

function formatDuration(sec?: number) {
  if (!sec || sec <= 0) return null;
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

export function SessionPage({ id }: { id: string }) {
  const [session, setSession] = useState<State<Session>>(initial());
  const [transcript, setTranscript] = useState<State<TranscriptResponse>>(initial());
  const [summary, setSummary] = useState<State<SummaryResponse>>(initial());
  const [actions, setActions] = useState<State<ActionItem[]>>(initial());
  const [processing, setProcessing] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchSession = useCallback(
    (showLoading: boolean) => {
      if (showLoading) setSession(initial());
      return getSession(id)
        .then((r) => {
          setSession({ data: r.data, loading: false, error: null });
          return r.data;
        })
        .catch((e: unknown) => {
          const msg = e instanceof Error ? e.message : "Failed to load session.";
          setSession({ loading: false, error: msg });
          return null;
        });
    },
    [id],
  );

  const fetchTranscript = useCallback(() => {
    setTranscript(initial());
    return getTranscript(id)
      .then((r) => setTranscript({ data: r.data, loading: false, error: null }))
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 404) {
          setTranscript({ data: undefined, loading: false, error: null });
        } else {
          setTranscript({ loading: false, error: "Failed to load transcript." });
        }
      });
  }, [id]);

  const fetchSummary = useCallback(() => {
    setSummary(initial());
    return getSummary(id)
      .then((r) => setSummary({ data: r.data, loading: false, error: null }))
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 404) {
          setSummary({ data: undefined, loading: false, error: null });
        } else {
          setSummary({ loading: false, error: "Failed to load summary." });
        }
      });
  }, [id]);

  const fetchActions = useCallback(() => {
    setActions(initial());
    return getActions(id)
      .then((r) => setActions({ data: r.data, loading: false, error: null }))
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 404) {
          setActions({ data: [], loading: false, error: null });
        } else {
          setActions({ loading: false, error: "Failed to load action items." });
        }
      });
  }, [id]);

  const load = useCallback(() => {
    fetchSession(true);
    fetchTranscript();
    fetchSummary();
    fetchActions();
  }, [fetchSession, fetchTranscript, fetchSummary, fetchActions]);

  useEffect(() => {
    load();
  }, [load]);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    const status = session.data?.status;
    if (status !== "processing") {
      stopPolling();
      return;
    }
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      const next = await fetchSession(false);
      if (!next) return;
      if (next.status === "completed") {
        stopPolling();
        fetchTranscript();
        fetchSummary();
        fetchActions();
      } else if (next.status === "failed") {
        stopPolling();
      }
    }, POLL_INTERVAL_MS);
    return () => stopPolling();
  }, [
    session.data?.status,
    fetchSession,
    fetchTranscript,
    fetchSummary,
    fetchActions,
    stopPolling,
  ]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  async function onProcess() {
    if (processing) return;
    setProcessing(true);
    try {
      await processSession(id);
      load();
    } catch (e) {
      setSummary({
        loading: false,
        error: e instanceof Error ? e.message : "Failed to process transcript.",
      });
    } finally {
      setProcessing(false);
    }
  }

  const duration = formatDuration(session.data?.durationSec);
  const title = session.data?.title || session.data?.fileName || "Session";
  const showSkeleton =
    processing || (session.data?.status === "processing" && !summary.data && !actions.data?.length);

  return (
    <AppLayout>
      {/* Session header */}
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4 border-b border-border/70 pb-6">
        <div className="min-w-0">
          <div className="mb-1.5 flex items-center gap-2">
            {session.data?.status && <StatusBadge status={session.data.status} />}
            {session.data?.transcriptType && (
              <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium capitalize text-muted-foreground">
                {session.data.transcriptType.replace("_", " ")}
              </span>
            )}
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-[28px]">
            {title}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <code className="rounded bg-muted px-1.5 py-0.5 font-mono">{id}</code>
            {session.data?.createdAt && (
              <span>{new Date(session.data.createdAt).toLocaleString()}</span>
            )}
            {duration && <span>· {duration}</span>}
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}>
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </Button>
          <Button size="sm" onClick={onProcess} disabled={processing}>
            {processing ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5" />
            )}
            {processing ? "Generating…" : "Generate Intelligence"}
          </Button>
        </div>
      </div>

      {showSkeleton ? (
        <div className="mb-8">
          <AiGeneratingSkeleton />
        </div>
      ) : null}

      {/* Two-column workspace: intelligence left (sticky), transcript right */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <aside className="space-y-6 lg:sticky lg:top-20 lg:self-start lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto lg:pr-1">
          <SummaryPanel
            summary={summary.data?.summary}
            loading={summary.loading}
            error={summary.error}
          />
          <MomPanel mom={summary.data?.mom} loading={summary.loading} error={summary.error} />
          <ActionItemsPanel items={actions.data} loading={actions.loading} error={actions.error} />
        </aside>

        <div>
          <TranscriptViewer
            segments={transcript.data?.segments}
            loading={transcript.loading}
            error={transcript.error}
          />
        </div>
      </div>
    </AppLayout>
  );
}
