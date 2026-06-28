import { useCallback, useEffect, useRef, useState } from "react";
import {
  Sparkles,
  RefreshCw,
  Music,
  Download,
  Pencil,
  Check,
  X,
  Languages,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  ApiError,
  getActions,
  getSession,
  getSummary,
  getTranscript,
  processSession,
  processQuickDiarization,
  updateSpeaker,
  getSupportedLanguages,
  translateSession,
  getTranslations,
  processAccurateDiarization,
  updateSessionTitle,
  retrySession,
  cancelSessionJob,
} from "@/services/api";
import type { TranslationResponse } from "@/services/api";
import type { ActionItem, Session, SummaryResponse, TranscriptResponse } from "@/types";
import {
  exportAsMarkdown,
  exportAsTxt,
  exportAsDocx,
  exportTranslatedAsDocx,
  exportTranslatedAsTxt,
  printAsPdf,
} from "@/lib/export";
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
  const [activeIteration, setActiveIteration] = useState<number>(1);
  const [processing, setProcessing] = useState(false);
  const [diarizing, setDiarizing] = useState(false);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editTitleValue, setEditTitleValue] = useState("");
  const [isSavingTitle, setIsSavingTitle] = useState(false);
  const [translations, setTranslations] = useState<TranslationResponse[]>([]);
  const [supportedLanguages, setSupportedLanguages] = useState<Record<string, string>>({});
  const [selectedLanguage, setSelectedLanguage] = useState<string>("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isPolling = useRef(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  // Load supported languages on mount
  useEffect(() => {
    getSupportedLanguages()
      .then((r) => {
        setSupportedLanguages(r.data);
        // Default to hi (Hindi) if available
        if (r.data.hi) setSelectedLanguage("hi");
        else {
          const first = Object.keys(r.data)[0];
          if (first) setSelectedLanguage(first);
        }
      })
      .catch(() => {});
  }, []);

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
              seg.speaker === speaker ? { ...seg, displayName: newName } : seg,
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

  const fetchTranscript = useCallback(
    (signal?: AbortSignal) => {
      setTranscript((prev) => ({ ...prev, loading: true, error: null }));
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
    },
    [id],
  );

  const fetchSummary = useCallback(
    (signal?: AbortSignal) => {
      setSummary((prev) => ({ ...prev, loading: true, error: null }));
      return getSummary(id, signal)
        .then((r) => {
          setSummary({ data: r.data, loading: false, error: null });
          if (r.data?.history && r.data.history.length > 0) {
            const maxIter = Math.max(...r.data.history.map((h) => h.iteration));
            setActiveIteration(maxIter);
          }
        })
        .catch((e: unknown) => {
          if (e instanceof Error && (e.name === "AbortError" || e.message.includes("aborted")))
            return;
          if (e instanceof ApiError && e.status === 404) {
            setSummary({ data: undefined, loading: false, error: null });
          } else {
            setSummary({ loading: false, error: "Failed to load summary." });
          }
        });
    },
    [id],
  );

  const fetchActions = useCallback(
    (signal?: AbortSignal) => {
      setActions((prev) => ({ ...prev, loading: true, error: null }));
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
    },
    [id],
  );

  const fetchTranslations = useCallback(
    (signal?: AbortSignal) => {
      return getTranslations(id, signal)
        .then((r) => setTranslations(r.data))
        .catch((e: unknown) => {
          if (e instanceof Error && (e.name === "AbortError" || e.message.includes("aborted")))
            return;
        });
    },
    [id],
  );

  const load = useCallback(
    (signal?: AbortSignal) => {
      fetchSession(true, signal);
      fetchTranscript(signal);
      fetchSummary(signal);
      fetchActions(signal);
      fetchTranslations(signal);
    },
    [fetchSession, fetchTranscript, fetchSummary, fetchActions, fetchTranslations],
  );

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
    const isProcessingSession = [
      "pending",
      "uploaded",
      "preprocessing",
      "transcribing",
      "diarizing",
      "processing",
      "finalizing",
    ].includes(status || "");
    const hasActiveTranslation = translations.some((t) => t.status === "translating");

    if (!isProcessingSession && !hasActiveTranslation) {
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
        await fetchTranslations(controller.signal);

        if (!next) return;
        if (next.status === "completed" && isProcessingSession) {
          fetchTranscript();
          fetchSummary();
          fetchActions();
        } else if (next.status === "failed") {
          // If session failed, we might still have active translations,
          // but usually it means we stop polling.
          // The effect dependencies will clean up next render if hasActiveTranslation becomes false.
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
    translations,
    fetchSession,
    fetchTranscript,
    fetchSummary,
    fetchActions,
    fetchTranslations,
    stopPolling,
  ]);

  async function onProcess() {
    if (processing) return;
    setProcessing(true);
    try {
      await processSession(id);
      toast.success(
        "Intelligence generation started. Refresh the session after processing completes.",
      );
      fetchSession(false); // F-1: Immediately reflect PROCESSING status
    } catch (e: any) {
      toast.error(e.message || "Failed to process transcript.");
      setSummary({
        loading: false,
        error: e instanceof Error ? e.message : "Failed to process transcript.",
      });
    } finally {
      setProcessing(false);
    }
  }

  async function onRetry() {
    if (processing) return;
    setProcessing(true);
    try {
      await retrySession(id);
      toast.success("Retry started. Refresh the session after processing completes.");
      fetchSession(false);
    } catch (e: any) {
      toast.error(e.message || "Failed to retry session.");
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

    let curSummary = summary.data?.summary;
    let curMom = summary.data?.mom;

    if (summary.data?.history && summary.data.history.length > 0) {
      const hist = summary.data.history.find((h) => h.iteration === activeIteration);
      if (hist) {
        curSummary = hist.summary;
        curMom = hist.mom;
      }
    }

    const curActions = actions.data?.filter((a) => a.iteration === activeIteration) || actions.data;

    const data = {
      session: session.data!,
      transcript: transcript.data.segments,
      summary: curSummary,
      mom: curMom,
      actions: curActions || [],
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
        setTimeout(() => {
          printAsPdf();
        }, 100);
        break;
    }
  }

  async function handleTranslate() {
    if (!selectedLanguage) return;
    try {
      await translateSession(id, selectedLanguage);
      toast.success(
        `Translation started for ${supportedLanguages[selectedLanguage] || selectedLanguage}`,
      );
      fetchTranslations();
    } catch (e: any) {
      toast.error(e.message || "Translation failed to start");
    }
  }

  const activeTranslation = translations.find((t) => t.target_language === selectedLanguage);
  const isTranslating = activeTranslation?.status === "translating";

  async function handleCancelJob(jobType: string) {
    try {
      await cancelSessionJob(id, jobType);
      toast.success("Cancellation requested");
      if (jobType.startsWith("translation_")) {
        fetchTranslations();
      } else {
        setProcessing(false);
        setDiarizing(false);
        fetchSession(false);
      }
    } catch (e: any) {
      toast.error(e.message || "Failed to cancel process");
    }
  }

  async function handleExportTranslated(format: string) {
    if (!session.data || !activeTranslation || activeTranslation.status !== "completed") return;
    const langLabel =
      supportedLanguages[activeTranslation.target_language] || activeTranslation.target_language;
    try {
      if (format === "docx") {
        await exportTranslatedAsDocx({
          session: session.data,
          translatedTranscript: activeTranslation.translated_transcript || "",
          translatedSummary: activeTranslation.translated_summary,
          translatedMom: activeTranslation.translated_mom,
          targetLanguage: langLabel,
        });
      } else {
        exportTranslatedAsTxt({
          session: session.data,
          translatedTranscript: activeTranslation.translated_transcript || "",
          translatedSummary: activeTranslation.translated_summary,
          translatedMom: activeTranslation.translated_mom,
          targetLanguage: langLabel,
        });
      }
      toast.success(`Exported translated ${format.toUpperCase()}`);
    } catch (err) {
      toast.error("Failed to export translated document");
      console.error(err);
    }
  }

  const duration = formatDuration(session.data?.durationSec);
  const title = session.data?.title || session.data?.fileName || "Session";
  const showSkeleton =
    processing ||
    session.data?.status === "finalizing" ||
    session.data?.status === "processing";

  const progressMode =
    diarizing || session.data?.status === "diarizing"
      ? "diarization"
      : session.data?.status === "finalizing"
        ? "finalizing"
        : processing || session.data?.status === "processing"
          ? "intelligence"
          : !transcript.data?.segments?.length
            ? "transcript"
            : "intelligence";

  return (
    <AppLayout>
      {/* Session header */}
      <div className="sticky top-14 z-30 -mx-4 mb-8 flex flex-wrap items-start justify-between gap-4 border-b border-border/70 bg-background/85 px-4 pb-6 pt-4 backdrop-blur supports-[backdrop-filter]:bg-background/65 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
        <div className="min-w-0">
          <div className="mb-1.5 flex items-center gap-2">
            {session.data?.status && <StatusBadge status={session.data.status} />}
            {session.data?.transcriptType && (
              <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium capitalize text-muted-foreground">
                {session.data.transcriptType.replace("_", " ")}
              </span>
            )}
            {session.data?.detected_languages &&
            session.data.detected_languages.length > 0 &&
            session.data.transcriptType !== ("upload" as any) ? (
              <span className="rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 px-2 py-0.5 text-[11px] font-medium">
                🌐{" "}
                {session.data.detected_languages
                  .map((l) => `${l.code.toUpperCase()} ${l.percentage}%`)
                  .join(" • ")}
              </span>
            ) : session.data?.detected_language ? (
              <span className="rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 px-2 py-0.5 text-[11px] font-medium">
                🌐 Primary Language:{" "}
                {(() => {
                  const langMap: Record<string, string> = {
                    en: "English",
                    hi: "Hindi",
                    ta: "Tamil",
                    te: "Telugu",
                    mr: "Marathi",
                    or: "Odia",
                    es: "Spanish",
                    nl: "Dutch",
                    fr: "French",
                    de: "German",
                    ja: "Japanese",
                    zh: "Chinese",
                    ko: "Korean",
                    ar: "Arabic",
                    pt: "Portuguese",
                    ru: "Russian",
                  };
                  return (
                    langMap[session.data.detected_language] ||
                    session.data.detected_language.toUpperCase()
                  );
                })()}
              </span>
            ) : null}
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
          {(session.data?.host_name || session.data?.participants) && (
            <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-sm">
              {session.data.host_name && (
                <div>
                  <span className="font-semibold text-foreground">Host: </span>
                  <span className="text-muted-foreground">{session.data.host_name}</span>
                </div>
              )}
              {session.data.participants && (
                <div>
                  <span className="font-semibold text-foreground">Participants: </span>
                  <span className="text-muted-foreground">{session.data.participants}</span>
                </div>
              )}
            </div>
          )}
          {session.data?.diarization_mode && session.data?.diarized_at && (
            <div className="mt-3 flex items-center gap-2 text-xs">
              <span className="font-medium text-muted-foreground">Diarization:</span>
              <span className="rounded-md bg-secondary px-2 py-1 font-medium capitalize text-secondary-foreground">
                {session.data.diarization_mode.replace("_", " ")}
              </span>
              <span className="text-muted-foreground">
                Completed:{" "}
                {new Date(session.data.diarized_at).toLocaleString(undefined, {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            </div>
          )}
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
          {/* Translation controls */}
          {session.data &&
            transcript.data?.segments &&
            Object.keys(supportedLanguages).length > 0 && (
              <div className="flex items-center gap-1.5">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="min-w-[100px]">
                      {supportedLanguages[selectedLanguage] || "Language"}
                      <ChevronDown className="h-3 w-3 ml-1" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {Object.entries(supportedLanguages).map(([key, label]) => (
                      <DropdownMenuItem
                        key={key}
                        onClick={() => setSelectedLanguage(key)}
                        className={selectedLanguage === key ? "bg-accent" : ""}
                      >
                        {label}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleTranslate}
                  disabled={isTranslating || !selectedLanguage}
                >
                  {isTranslating ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />
                  ) : (
                    <Languages className="h-3.5 w-3.5 mr-1" />
                  )}
                  {isTranslating ? "Translating…" : "Translate"}
                </Button>
              </div>
            )}
          <Button
            variant="outline"
            size="sm"
            onClick={onQuickDiarization}
            disabled={
              diarizing ||
              session.data?.status === "diarizing" ||
              session.data?.status === "processing"
            }
          >
            ⚡ Quick Labels
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                disabled={
                  diarizing ||
                  session.data?.status === "diarizing" ||
                  session.data?.status === "processing"
                }
              >
                🎯 Accurate Diarization
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Run Accurate Diarization?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will run a full Whisper + Pyannote rebuild. Your existing transcript will be
                  permanently overwritten. Proceed?
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={onAccurateDiarization}>Proceed</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
          <Button variant="outline" size="sm" onClick={() => load()}>
            <RefreshCw className="h-3.5 w-3.5 mr-1" />
            Refresh
          </Button>
          {session.data?.status === "failed" ? (
            <Button size="sm" onClick={onRetry} disabled={processing} variant="destructive">
              {processing ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5 mr-1" />
              )}
              {processing ? "Retrying…" : "Retry Processing"}
            </Button>
          ) : (
            <Button size="sm" onClick={onProcess} disabled={processing}>
              {processing ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />
              ) : (
                <Sparkles className="h-3.5 w-3.5 mr-1" />
              )}
              {processing ? "Generating…" : "Generate Intelligence"}
            </Button>
          )}
        </div>
      </div>

      {showSkeleton ? (
        <div className="mb-8">
          <IntelligenceProgress
            mode={progressMode}
            processingStage={session.data?.processing_stage}
            onCancel={() => handleCancelJob(progressMode === "diarization" ? "accurate_diarization" : "intelligence")}
          />
        </div>
      ) : null}

      {/* Two-column workspace: intelligence left (sticky), transcript right */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <aside className="space-y-6 lg:sticky lg:top-20 lg:self-start lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto lg:pr-1">
          {session.data?.has_audio && session.data?.audio_url && (
            <PanelShell title="Recording" icon={<Music className="h-4 w-4" />} bare>
              <audio
                ref={audioRef}
                controls
                src={session.data.audio_url}
                className="w-full"
              />
            </PanelShell>
          )}

          {summary.data?.history && summary.data.history.length > 1 && (
            <div className="flex items-center justify-between bg-muted/30 px-4 py-2 rounded-lg border border-border/50">
              <span className="text-sm font-medium text-muted-foreground">
                Intelligence Version
              </span>
              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  size="icon"
                  className="h-7 w-7"
                  disabled={activeIteration <= 1}
                  onClick={() => setActiveIteration((i) => Math.max(1, i - 1))}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-xs font-semibold tabular-nums">
                  {activeIteration} of {Math.max(...summary.data.history.map((h) => h.iteration))}
                </span>
                <Button
                  variant="outline"
                  size="icon"
                  className="h-7 w-7"
                  disabled={
                    activeIteration >= Math.max(...summary.data.history.map((h) => h.iteration))
                  }
                  onClick={() =>
                    setActiveIteration((i) =>
                      Math.min(Math.max(...summary.data!.history!.map((h) => h.iteration)), i + 1),
                    )
                  }
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          <SummaryPanel
            summary={
              summary.data?.history?.find((h) => h.iteration === activeIteration)?.summary ||
              summary.data?.summary
            }
            loading={summary.loading}
            error={summary.error}
            emptyMessage={
              session.data?.status === "failed" ? "Generation failed." : "Not generated yet."
            }
          />
          <MomPanel
            mom={
              summary.data?.history?.find((h) => h.iteration === activeIteration)?.mom ||
              summary.data?.mom
            }
            loading={summary.loading}
            error={summary.error}
            emptyMessage={
              session.data?.status === "failed" ? "Generation failed." : "Not generated yet."
            }
            transcriptType={session.data?.transcriptType}
          />
          <ActionItemsPanel
            items={actions.data?.filter((a) => a.iteration === activeIteration || !a.iteration)}
            loading={actions.loading}
            error={actions.error}
            emptyMessage={
              session.data?.status === "failed" ? "Generation failed." : "Not generated yet."
            }
          />
        </aside>

        <div className="flex flex-col gap-6">
          {(diarizing || session.data?.status === "diarizing") && (
            <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-lg flex items-center gap-3 shadow-sm mb-2">
              <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
              <div className="text-sm">
                <p className="font-medium">Transcript is ready!</p>
                <p className="text-blue-700/80">
                  We are running background AI to identify individual speakers. Speaker labels will update automatically soon.
                </p>
              </div>
            </div>
          )}
          <TranscriptViewer
            segments={transcript.data?.segments}
            loading={transcript.loading}
            error={transcript.error}
            session={session.data ?? undefined}
            onRenameSpeaker={handleRenameSpeaker}
            searchQuery={initialSearch}
            onSeek={onSeek}
            isDiarizing={diarizing || session.data?.status === "diarizing"}
          />

          {/* Translation Results */}
          {isTranslating ? (
            <PanelShell title="Translation" icon={<Languages className="h-4 w-4" />}>
              <div className="flex flex-col items-center justify-center p-8 border rounded-lg bg-muted/20">
                <Loader2 className="h-6 w-6 animate-spin mb-4 text-primary" />
                <p className="text-sm text-muted-foreground font-medium mb-4">
                  Translating to {supportedLanguages[selectedLanguage] || selectedLanguage}...
                </p>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="text-destructive hover:bg-destructive/10"
                  onClick={() => handleCancelJob(`translation_${selectedLanguage}`)}
                >
                  Cancel Translation
                </Button>
              </div>
            </PanelShell>
          ) : activeTranslation?.status === "failed" ? (
            <PanelShell title="Translation Failed" icon={<Languages className="h-4 w-4" />}>
              <div className="text-sm text-destructive">
                Failed to translate to {supportedLanguages[selectedLanguage]}.{" "}
                {activeTranslation.error_message}
              </div>
            </PanelShell>
          ) : null}
          {activeTranslation?.status === "invalidated" && (
            <PanelShell title="Translation Invalidated" icon={<Languages className="h-4 w-4" />}>
              <div className="text-sm text-amber-600 bg-amber-50 p-3 rounded-md border border-amber-200">
                ⚠ Translation is outdated because the transcript changed.{" "}
                {activeTranslation.error_message}
              </div>
            </PanelShell>
          )}
          {activeTranslation?.status === "completed" && (
            <PanelShell
              title={`Translation (${supportedLanguages[activeTranslation.target_language] || activeTranslation.target_language})`}
              icon={<Languages className="h-4 w-4" />}
            >
              <div className="space-y-4">
                {activeTranslation.error_message && (
                  <div className="text-sm text-amber-700 bg-amber-50 p-3 rounded-md border border-amber-200 mb-3 whitespace-pre-wrap">
                    ⚠ {activeTranslation.error_message}
                  </div>
                )}
                <div className="flex gap-2 mb-3">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleExportTranslated("docx")}
                  >
                    <Download className="h-3 w-3 mr-1" /> Export DOCX
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleExportTranslated("txt")}>
                    <Download className="h-3 w-3 mr-1" /> Export TXT
                  </Button>
                </div>

                {activeTranslation.translated_summary && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-1.5">
                      Translated Summary
                    </h4>
                    <div className="whitespace-pre-wrap text-sm leading-relaxed bg-muted/30 rounded-md p-3">
                      {activeTranslation.translated_summary}
                    </div>
                  </div>
                )}

                {activeTranslation.translated_mom && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-1.5">
                      Translated Meeting Minutes
                    </h4>
                    <div className="whitespace-pre-wrap text-sm leading-relaxed bg-muted/30 rounded-md p-3">
                      {activeTranslation.translated_mom}
                    </div>
                  </div>
                )}

                {activeTranslation.translated_transcript && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-1.5">
                      Translated Transcript
                    </h4>
                    <div className="whitespace-pre-wrap text-sm leading-relaxed bg-muted/30 rounded-md p-3 max-h-[400px] overflow-y-auto">
                      {activeTranslation.translated_transcript}
                    </div>
                  </div>
                )}
              </div>
            </PanelShell>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
