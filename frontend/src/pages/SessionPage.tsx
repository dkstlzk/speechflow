import { useCallback, useEffect, useState } from "react";
import { AppLayout } from "@/layouts/AppLayout";
import { TranscriptViewer } from "@/components/TranscriptViewer";
import { SummaryPanel } from "@/components/SummaryPanel";
import { MomPanel } from "@/components/MomPanel";
import { ActionItemsPanel } from "@/components/ActionItemsPanel";
import { StatusBadge } from "@/components/StatusBadge";
import {
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

export function SessionPage({ id }: { id: string }) {
  const [session, setSession] = useState<State<Session>>(initial());
  const [transcript, setTranscript] = useState<State<TranscriptResponse>>(initial());
  const [summary, setSummary] = useState<State<SummaryResponse>>(initial());
  const [actions, setActions] = useState<State<ActionItem[]>>(initial());
  const [processing, setProcessing] = useState(false);

  const load = useCallback(() => {
    setSession(initial());
    setTranscript(initial());
    setSummary(initial());
    setActions(initial());

    getSession(id)
      .then((r) => setSession({ data: r.data, loading: false, error: null }))
      .catch(() =>
        setSession({ loading: false, error: "Failed to load session." }),
      );
    getTranscript(id)
      .then((r) => setTranscript({ data: r.data, loading: false, error: null }))
      .catch(() =>
        setTranscript({ loading: false, error: "Failed to load transcript." }),
      );
    getSummary(id)
      .then((r) => setSummary({ data: r.data, loading: false, error: null }))
      .catch(() =>
        setSummary({ loading: false, error: "Failed to load summary." }),
      );
    getActions(id)
      .then((r) => setActions({ data: r.data, loading: false, error: null }))
      .catch(() =>
        setActions({ loading: false, error: "Failed to load action items." }),
      );
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  async function onProcess() {
    setProcessing(true);
    try {
      await processSession(id);
      load();
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
