import { useCallback, useEffect, useRef, useState } from "react";
import { AppLayout } from "@/layouts/AppLayout";
import { TranscriptViewer } from "@/components/TranscriptViewer";
import { SummaryPanel } from "@/components/SummaryPanel";
import { MomPanel } from "@/components/MomPanel";
import { ActionItemsPanel } from "@/components/ActionItemsPanel";
import { AiGeneratingSkeleton } from "@/components/AiGeneratingSkeleton";
import { StatusBadge } from "@/components/StatusBadge";
import {
  ApiError,
  getActions,
  getSession,
  getSummary,
  getTranscript,
  processSession,
} from "@/services/api";
import type {
  ActionItem,
  Session,
  SummaryResponse,
  TranscriptResponse,
} from "@/types";

interface State<T> {
  data?: T;
  loading: boolean;
  error: string | null;
}

const initial = <T,>(): State<T> => ({ loading: true, error: null });

const POLL_INTERVAL_MS = 5000;

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
          // Summary not yet generated — empty panel, not an error.
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

  // Poll session status every 5s while processing; refresh data on completion.
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
    setProcessing(true);
    try {
      await processSession(id);
      load();
    } catch (e) {
      setSummary({
        loading: false,
        error:
          e instanceof Error ? e.message : "Failed to process transcript.",
      });
    } finally {
      setProcessing(false);
    }
  }

  return (
    <AppLayout>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">Session</h1>
            <code className="rounded bg-muted px-1.5 py-0.5 text-sm">{id}</code>
            {session.data && (
              <>
                <span className="rounded-full border border-border px-2 py-0.5 text-xs capitalize text-muted-foreground">
                  {session.data.transcriptType}
                </span>
                <StatusBadge status={session.data.status} />
              </>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onProcess}
            disabled={processing}
            className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {processing ? "Processing…" : "Process Transcript"}
          </button>
          <button
            onClick={load}
            className="rounded-md border border-input bg-background px-3 py-1.5 text-sm hover:bg-accent"
          >
            Refresh
          </button>
        </div>
      </div>

      {processing || (session.data?.status === "processing" && !summary.data && !actions.data?.length) ? (
        <div className="mb-6">
          <AiGeneratingSkeleton />
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="lg:col-span-2">
          <TranscriptViewer
            segments={transcript.data?.segments}
            loading={transcript.loading}
            error={transcript.error}
          />
        </div>
        <SummaryPanel
          summary={summary.data?.summary}
          loading={summary.loading}
          error={summary.error}
        />
        <MomPanel
          mom={summary.data?.mom}
          loading={summary.loading}
          error={summary.error}
        />
        <div className="lg:col-span-2">
          <ActionItemsPanel
            items={actions.data}
            loading={actions.loading}
            error={actions.error}
          />
        </div>
      </div>
    </AppLayout>
  );
}
