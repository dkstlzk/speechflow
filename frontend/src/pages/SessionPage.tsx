import { useCallback, useEffect, useRef, useState } from "react";
import { Sparkles, RefreshCw, Music, Download, Pencil, Check, X } from "lucide-react";
import { AppLayout } from "@/layouts/AppLayout";
import { TranscriptViewer } from "@/components/TranscriptViewer";
import { SummaryPanel } from "@/components/SummaryPanel";
import { MomPanel } from "@/components/MomPanel";
import { ActionItemsPanel } from "@/components/ActionItemsPanel";
import { IntelligenceProgress } from "@/components/IntelligenceProgress";
import { StatusBadge } from "@/components/StatusBadge";
import { PanelShell } from "@/components/PanelShell";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  ApiError,
  getActions,
  getSession,
  getSummary,
  getTranscript,
  processSession,
  processQuickDiarization,
  processAccurateDiarization,
  updateSessionTitle,
  updateSpeaker,
} from "@/services/api";
import type { ActionItem, Session, SummaryResponse, TranscriptResponse } from "@/types";
import { exportAsMarkdown, exportAsTxt, exportAsDocx, printAsPdf } from "@/lib/export";
import { toast } from "sonner";

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

export function SessionPage({ id, initialSearch }: { id: string; initialSearch?: string }) {
  const [session, setSession] = useState<State<Session>>(initial());
  const [transcript, setTranscript] = useState<State<TranscriptResponse>>(initial());
  const [summary, setSummary] = useState<State<SummaryResponse>>(initial());
  const [actions, setActions] = useState<State<ActionItem[]>>(initial());
  const [processing, setProcessing] = useState(false);
  const [diarizing, setDiarizing] = useState(false);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editTitleValue, setEditTitleValue] = useState("");
  const [isSavingTitle, setIsSavingTitle] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isPolling = useRef(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  const onSeek = (time: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      audioRef.current.play();
    }
  };

  const handleSaveTitle = async () => {
    if (!editTitleValue.trim() || editTitleValue === session.data?.title) {
      setIsEditingTitle(false);
      return;
    }
    setIsSavingTitle(true);
    try {
      await updateSessionTitle(id, editTitleValue.trim());
      setSession((prev) =>
        prev.data ? { ...prev, data: { ...prev.data, title: editTitleValue.trim() } } : prev,
      );
      toast.success("Session title updated");
      setIsEditingTitle(false);
    } catch (err) {
      toast.error("Failed to update session title.");
    } finally {
      setIsSavingTitle(false);
    }
  };


  const handleRenameSpeaker = async (speaker: string, newName: string) => {
    try {
      await updateSpeaker(id, speaker, newName);
      setTranscript((prev) => {
        if (!prev.data) return prev;
        return {
          ...prev,
          data: {
            ...prev.data,
            segments: prev.data.segments.map((seg) =>
              seg.speaker === speaker ? { ...seg, displayName: newName } : seg
            ),
          },
        };
      });
      toast.success("Speaker renamed");
    } catch (err) {
      toast.error("Failed to rename speaker.");
    }
  };

  const fetchSession = useCallback(
    (showLoading: boolean, signal?: AbortSignal) => {
      if (showLoading) setSession(initial());
      return getSession(id, signal)
        .then((r) => {
          setSession({ data: r.data, loading: false, error: null });
          return r.data;
        })
        .catch((e: unknown) => {
          if (e instanceof Error && (e.name === "AbortError" || e.message.includes("aborted")))
            return null;
          const msg = e instanceof Error ? e.message : "Failed to load session.";
          setSession({ loading: false, error: msg });
          return null;
        });
    },
    [id],
  );

  const fetchTranscript = useCallback((signal?: AbortSignal) => {
    setTranscript(prev => ({ ...prev, loading: true, error: null }));
    return getTranscript(id, signal)
      .then((r) => setTranscript({ data: r.data, loading: false, error: null }))
      .catch((e: unknown) => {
        if (e instanceof Error && (e.name === "AbortError" || e.message.includes("aborted")))
          return;
        if (e instanceof ApiError && e.status === 404) {
          setTranscript({ data: undefined, loading: false, error: null });
        } else {
          setTranscript({ loading: false, error: "Failed to load transcript." });
        }
      });
  }, [id]);

  const fetchSummary = useCallback((signal?: AbortSignal) => {
    setSummary(prev => ({ ...prev, loading: true, error: null }));
    return getSummary(id, signal)
      .then((r) => setSummary({ data: r.data, loading: false, error: null }))
      .catch((e: unknown) => {
        if (e instanceof Error && (e.name === "AbortError" || e.message.includes("aborted")))
          return;
        if (e instanceof ApiError && e.status === 404) {
          setSummary({ data: undefined, loading: false, error: null });
        } else {
          setSummary({ loading: false, error: "Failed to load summary." });
        }
      });
  }, [id]);

  const fetchActions = useCallback((signal?: AbortSignal) => {
    setActions(prev => ({ ...prev, loading: true, error: null }));
    return getActions(id, signal)
      .then((r) => setActions({ data: r.data, loading: false, error: null }))
      .catch((e: unknown) => {
        if (e instanceof Error && (e.name === "AbortError" || e.message.includes("aborted")))
          return;
        if (e instanceof ApiError && e.status === 404) {
          setActions({ data: [], loading: false, error: null });
        } else {
          setActions({ loading: false, error: "Failed to load action items." });
        }
      });
  }, [id]);

  const load = useCallback((signal?: AbortSignal) => {
    fetchSession(true, signal);
    fetchTranscript(signal);
    fetchSummary(signal);
    fetchActions(signal);
  }, [fetchSession, fetchTranscript, fetchSummary, fetchActions]);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    isPolling.current = false;
  }, []);

  useEffect(() => {
    const status = session.data?.status;
    if (status !== "processing" && status !== "diarizing" && status !== "finalizing") {
      stopPolling();
      return;
    }
    if (pollRef.current) return;
    const controller = new AbortController();

    pollRef.current = setInterval(async () => {
      if (isPolling.current) return;
      isPolling.current = true;
      try {
        const next = await fetchSession(false, controller.signal);
        if (!next) return;
        if (next.status === "completed") {
          stopPolling();
          fetchTranscript();
          fetchSummary();
          fetchActions();
        } else if (next.status === "failed") {
          stopPolling();
        }
      } finally {
        isPolling.current = false;
      }
    }, POLL_INTERVAL_MS);
    return () => {
      stopPolling();
      controller.abort();
    };
  }, [
    session.data?.status,
    fetchSession,
    fetchTranscript,
    fetchSummary,
    fetchActions,
    stopPolling,
  ]);


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

  async function onQuickDiarization() {
    setDiarizing(true);
    try {
      await processQuickDiarization(id);
      toast.success("Quick diarization started. Refresh the session after processing completes.");
      fetchSession(false); // F-1: Immediately reflect DIARIZING status
    } catch (err: any) {
      toast.error(err.message || "Failed to apply quick labels");
    } finally {
      setDiarizing(false);
    }
  }

  async function onAccurateDiarization() {
    setDiarizing(true);
    try {
      await processAccurateDiarization(id);
      toast.success("Accurate diarization started. Processing may take several minutes.");
      fetchSession(false); // F-1: Immediately reflect DIARIZING status
    } catch (err: any) {
      toast.error(err.message || "Failed to start accurate diarization");
    } finally {
      setDiarizing(false);
    }
  }

  async function handleExport(format: string) {
    if (!session.data || !transcript.data?.segments) return;
    const data = {
      session: session.data!,
      transcript: transcript.data.segments,
      summary: summary.data?.summary,
      mom: summary.data?.mom,
      actions: actions.data || [],
    };
    switch (format) {
      case "txt":
        exportAsTxt(data);
        break;
      case "md":
        exportAsMarkdown(data);
        break;
      case "docx":
        try {
          await exportAsDocx(data);
        } catch (err) {
          toast.error("Failed to generate DOCX export");
          console.error(err);
        }
        break;
      case "pdf":
        printAsPdf();
        break;
    }
  }

  const duration = formatDuration(session.data?.durationSec);
  const title = session.data?.title || session.data?.fileName || "Session";
  const showSkeleton =
    processing || diarizing || 
    session.data?.status === "diarizing" || 
    session.data?.status === "finalizing" ||
    (session.data?.status === "processing" && !summary.data && !actions.data?.length);
  const progressMode = !transcript.data?.segments?.length ? "transcript" : "intelligence";

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
          <div className="flex items-center gap-2 group min-h-[40px]">
            {isEditingTitle ? (
              <div className="flex items-center gap-2 w-full max-w-md">
                <input
                  type="text"
                  className="text-2xl font-semibold tracking-tight text-foreground sm:text-[28px] bg-transparent border-b border-primary/50 focus:border-primary focus:outline-none w-full disabled:opacity-50"
                  value={editTitleValue}
                  onChange={(e) => setEditTitleValue(e.target.value)}
                  disabled={isSavingTitle}
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleSaveTitle();
                    if (e.key === "Escape") setIsEditingTitle(false);
                  }}
                />
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleSaveTitle}
                  disabled={isSavingTitle}
                  className="h-8 px-2 text-green-600 hover:text-green-700 hover:bg-green-50"
                >
                  Save
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setIsEditingTitle(false)}
                  disabled={isSavingTitle}
                  className="h-8 px-2 text-muted-foreground hover:bg-muted"
                >
                  Cancel
                </Button>
              </div>
            ) : (
              <>
                <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-[28px]">
                  {title}
                </h1>
                <button
                  onClick={() => {
                    setEditTitleValue(title);
                    setIsEditingTitle(true);
                  }}
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 text-muted-foreground hover:text-foreground rounded hover:bg-muted"
                  title="Rename Session"
                >
                  <Pencil className="h-4 w-4" />
                </button>
              </>
            )}
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <code className="rounded bg-muted px-1.5 py-0.5 font-mono">{id}</code>
            {session.data?.createdAt && (
              <span>{new Date(session.data.createdAt).toLocaleString()}</span>
            )}
            {duration && <span>· {duration}</span>}
          </div>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          {session.data && transcript.data?.segments && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <Download className="h-3.5 w-3.5 mr-2" />
                  Export
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => handleExport("txt")}>
                  Export as TXT
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport("md")}>
                  Export as Markdown
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport("docx")}>
                  Export as DOCX (Meeting Report)
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleExport("pdf")}>
                  Export as PDF
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
          <Button variant="outline" size="sm" onClick={onQuickDiarization} disabled={diarizing || session.data?.status === "diarizing" || session.data?.status === "processing"}>
            ⚡ Quick Labels
          </Button>
          <Button variant="outline" size="sm" onClick={onAccurateDiarization} disabled={diarizing || session.data?.status === "diarizing" || session.data?.status === "processing"}>
            🎯 Accurate Diarization
          </Button>
          <Button variant="outline" size="sm" onClick={() => load()}>
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
          <IntelligenceProgress mode={progressMode} />
        </div>
      ) : null}

      {/* Two-column workspace: intelligence left (sticky), transcript right */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <aside className="space-y-6 lg:sticky lg:top-20 lg:self-start lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto lg:pr-1">
          {session.data?.has_audio && session.data?.audio_url && (
            <PanelShell title="Recording" icon={<Music className="h-4 w-4" />} bare>
              <audio ref={audioRef} controls src={`${session.data.audio_url}?t=${session.data.createdAt || Date.now()}`} className="w-full" />
            </PanelShell>
          )}
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
            session={session.data ?? undefined}
            onRenameSpeaker={handleRenameSpeaker}
            searchQuery={initialSearch}
            onSeek={onSeek}
          />
        </div>
      </div>
    </AppLayout>
  );
}
