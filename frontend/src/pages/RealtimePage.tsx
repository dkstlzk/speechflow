import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Link, useNavigate } from "@tanstack/react-router";
import { AppLayout } from "@/layouts/AppLayout";
import { Button } from "@/components/ui/button";
import { ConnectionStatusBadge } from "@/components/ConnectionStatusBadge";
import { RecordingTimer } from "@/components/RecordingTimer";
import { RealtimeControls } from "@/components/RealtimeControls";
import { LiveTranscriptPanel } from "@/components/LiveTranscriptPanel";
import { LiveCaptionStrip } from "@/components/LiveCaptionStrip";
import { StreamingEventLog } from "@/components/StreamingEventLog";
import { SummaryPanel } from "@/components/SummaryPanel";
import { MomPanel } from "@/components/MomPanel";
import { ActionItemsPanel } from "@/components/ActionItemsPanel";
import { AudioVisualizer } from "@/components/AudioVisualizer";
import { AiGeneratingSkeleton } from "@/components/AiGeneratingSkeleton";

import {
  socket,
  connect,
  disconnect,
  startRecording,
  stopRecording,
  pauseRecording,
  resumeRecording,
  subscribeToStatus,
  subscribeToTranscript,
  subscribeToCaptions,
} from "@/services/socket";
import {
  deleteRealtimeSession,
  finalizeRealtimeSession,
  getActions,
  getSummary,
  processSession,
  startRealtimeSession,
} from "@/services/api";
import { initAudioContext, startAudioCapture, stopAudioCapture } from "@/services/audio";
import type {
  ActionItem,
  CaptionUpdate,
  ConnectionStatus,
  RecordingStatus,
  StreamingEvent,
  SummaryResponse,
  TranscriptSegment,
  MicrophoneState,
} from "@/types";

export function RealtimePage() {
  const navigate = useNavigate();
  const [conn, setConn] = useState<ConnectionStatus>("disconnected");
  const [rec, setRec] = useState<RecordingStatus>("idle");
  const recRef = useRef<RecordingStatus>("idle");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);
  useEffect(() => {
    recRef.current = rec;
  }, [rec]);

  // Separated: captions are disposable, segments are committed
  const [caption, setCaption] = useState<string>("");
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);

  const [events, setEvents] = useState<StreamingEvent[]>([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const [resetKey, setResetKey] = useState(0);
  const [micState, setMicState] = useState<MicrophoneState>("initializing");
  const [isSystemAudio, setIsSystemAudio] = useState(false);

  const startInProgressRef = useRef(false);

  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [actions, setActions] = useState<ActionItem[] | null>(null);
  const [processing, setProcessing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [savedTitle, setSavedTitle] = useState<string | undefined>();
  
  const [title, setTitle] = useState("");
  const [hostName, setHostName] = useState("");
  const [participants, setParticipants] = useState("");
  useEffect(() => {
    // Subscribe to committed transcript chunks (persisted in DB)
    const off1 = subscribeToTranscript((seg) => {
      if (seg.sessionId && seg.sessionId !== sessionIdRef.current) return;
      setSegments((s) => [...s, seg]);
    });

    // Subscribe to live captions (disposable, UI only)
    const off2 = subscribeToCaptions((cap: CaptionUpdate) => {
      if (cap.sessionId && cap.sessionId !== sessionIdRef.current) return;
      setCaption(cap.text);
    });

    // Subscribe to status events for the event log
    const off3 = subscribeToStatus((ev: StreamingEvent) => {
      if (ev.sessionId && ev.sessionId !== sessionIdRef.current) return;
      setEvents((e) => [...e, ev]);

      if (ev.type === "connected") {
        setConn("connected");
      }
      if (ev.type === "connecting") {
        setConn("connecting");
      }
      if (ev.type === "disconnected" || ev.type === "error") {
        setConn(ev.type === "disconnected" ? "disconnected" : "error");
      }
    });

    // Connect to websocket after subscriptions are set up
    connect().catch((err) => {
      console.error("[RealtimePage] Initial connect failed", err);
    });

    return () => {
      off1();
      off2();
      off3();
      stopAudioCapture();
      disconnect();
    };
  }, []);

  // Safe declarative teardown: runs after state is fully committed
  useEffect(() => {
    if (
      (conn === "disconnected" || conn === "error") &&
      (rec === "recording" || rec === "paused")
    ) {
      stopAudioCapture();
      setRec("completed");
      setMicState("ready");
      toast.error(
        "Connection lost or error occurred. Recording was interrupted.",
        { duration: 10000 }
      );
    }
  }, [conn, rec]);

  useEffect(() => {
    let permissionStatus: PermissionStatus | null = null;

    const fallback = setTimeout(() => {
      setMicState((prev) => (prev === "initializing" ? "not_requested" : prev));
    }, 1000);

    async function checkMicrophonePermission() {
      try {
        if (!navigator.permissions || !navigator.permissions.query) {
          setMicState("not_requested");
          return;
        }
        const status = await navigator.permissions.query({ name: "microphone" as PermissionName });
        permissionStatus = status;

        const updateState = () => {
          if (status.state === "granted") {
            setMicState((prev) =>
              prev === "initializing" || prev === "not_requested" || prev === "denied"
                ? "ready"
                : prev,
            );
          } else if (status.state === "denied") {
            setMicState("denied");
          } else if (status.state === "prompt") {
            // only set not_requested if we aren't already ready/recording
            setMicState((prev) =>
              prev === "ready" || prev === "recording" || prev === "paused"
                ? prev
                : "not_requested",
            );
          }
        };

        updateState();
        status.onchange = updateState;
      } catch (err) {
        setMicState("not_requested");
      }
    }

    checkMicrophonePermission();

    return () => {
      clearTimeout(fallback);
      // Clean up the permission listener to prevent stale callbacks
      if (permissionStatus) {
        permissionStatus.onchange = null;
      }
    };
  }, []);

  async function requestMic() {
    if (!navigator.mediaDevices?.getUserMedia) {
      setMicState("denied");
      return false;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((t) => t.stop());
      setMicState("ready");
      return true;
    } catch {
      setMicState("denied");
      return false;
    }
  }

  async function onStart() {
    return _doStart(false);
  }

  async function onStartSystem() {
    return _doStart(true);
  }

  async function _doStart(captureSystem: boolean) {
    if (rec !== "idle" && rec !== "completed") {
      return;
    }

    if (startInProgressRef.current) return;
    startInProgressRef.current = true;

    if (!socket.connected) {
      toast.error("Cannot start recording: Server disconnected.");
      startInProgressRef.current = false;
      return;
    }

    try {
      const granted = await requestMic();
      if (!granted) {
        toast.error("Microphone access denied. Please allow microphone access to start recording.");
        return;
      }

      const res = await startRealtimeSession({
        title: title.trim() || undefined,
        host_name: hostName.trim() || undefined,
        participants: participants.trim() || undefined,
      });
      const newSessionId = String(res.data.sessionId);
      sessionIdRef.current = newSessionId;
      setSessionId(newSessionId);
      
      // Clear transcript state exactly once when starting a fresh recording
      setSegments([]);
      setCaption("");
      setEvents([]);
      setSummary(null);
      setActions(null);
      
      setRec("recording");
      setMicState("recording");
      setIsSystemAudio(captureSystem);

      try {
        const rate = initAudioContext();
        startRecording(newSessionId, rate);
        await startAudioCapture(captureSystem, () => {
          toast.info("Audio capture stopped externally.");
          onStop();
        });
      } catch (err: any) {
        await deleteRealtimeSession(newSessionId);
        stopAudioCapture();
        throw err;
      }
    } catch (err: any) {
      setConn("disconnected");
      setRec("idle");
      toast.error(err.message || "Failed to start session. Please try again.");
    } finally {
      startInProgressRef.current = false;
    }
  }

  function onPause() {
    pauseRecording();
    stopAudioCapture();
    setRec("paused");
    setMicState("paused");
  }

  async function onResume() {
    try {
      await startAudioCapture(isSystemAudio, () => {
        toast.info("Audio capture stopped externally.");
        onStop();
      });
      resumeRecording();
      setRec("recording");
      setMicState("recording");
    } catch (err: any) {
      toast.error("Failed to resume audio capture.");
    }
  }

  async function onStop() {
    stopRecording();
    stopAudioCapture();

    setRec("finalizing");
    if (micState === "recording" || micState === "paused") {
      setMicState("ready");
    }
    setCaption(""); // Clear disposable caption

    try {
      if (sessionId) {
        await finalizeRealtimeSession(sessionId);
        navigate({
          to: "/session/$id",
          params: { id: sessionId },
        });
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to finalize session. It may be partially saved.");
    } finally {
      setRec("completed");
    }
  }



  async function onDelete() {
    if (!sessionId) return;
    setDeleting(true);
    try {
      await deleteRealtimeSession(sessionId);
      // Reset to idle after delete
      onReset();
    } catch (err) {
      toast.error("Failed to delete session");
    } finally {
      setDeleting(false);
    }
  }

  function onReset() {
    stopRecording();
    stopAudioCapture();

    setRec("idle");
    if (micState === "recording" || micState === "paused" || micState === "ready") {
      setMicState("ready");
    }
    setSessionId(null);
    setSegments([]);
    setCaption("");
    setEvents([]);
    setSummary(null);
    setActions(null);
    setSavedTitle(undefined);
    setResetKey((k) => k + 1);
  }

  async function onGenerate() {
    if (!sessionId) return;
    setProcessing(true);
    try {
      await processSession(sessionId);
      const [s, a] = await Promise.all([getSummary(sessionId), getActions(sessionId)]);
      setSummary(s.data);
      setActions(a.data);
    } finally {
      setProcessing(false);
    }
  }

  return (
    <AppLayout>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Realtime Recording</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Live microphone transcription and session monitoring.
        </p>
      </div>

      <section className="mb-6 rounded-lg border border-border bg-card p-5 shadow-sm">
        <div className="grid gap-4 sm:grid-cols-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Connection</p>
            <div className="mt-1.5">
              <ConnectionStatusBadge status={conn} />
            </div>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Session State</p>
            <p className="mt-1.5 text-sm font-medium capitalize">{rec}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Session ID</p>
            <p className="mt-1.5 text-sm">
              {sessionId ? (
                <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{sessionId}</code>
              ) : (
                <span className="text-muted-foreground">—</span>
              )}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Duration</p>
            <div className="mt-1.5 flex items-center gap-3">
              <RecordingTimer running={rec === "recording"} resetKey={resetKey} />
              <AudioVisualizer isRecording={rec === "recording"} />
            </div>
          </div>
        </div>

        {rec === "idle" && (
          <div className="mt-5 border-t border-border pt-4">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">
              Meeting Details (Optional)
            </h3>
            <div className="grid gap-4 sm:grid-cols-3 mb-4">
              <div>
                <label className="text-xs font-medium text-foreground">Title</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Q3 Sync"
                  maxLength={255}
                  className="mt-1 flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-foreground">Host</label>
                <input
                  type="text"
                  value={hostName}
                  onChange={(e) => setHostName(e.target.value)}
                  placeholder="e.g. John Doe"
                  maxLength={255}
                  className="mt-1 flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-foreground">Participants</label>
                <input
                  type="text"
                  value={participants}
                  onChange={(e) => setParticipants(e.target.value)}
                  placeholder="e.g. Alice, Bob"
                  maxLength={255}
                  className="mt-1 flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </div>
            </div>
          </div>
        )}

        <div className="mt-5 border-t border-border pt-4">
          <RealtimeControls
            status={rec}
            micState={micState}
            onStart={onStart}
            onStartSystem={onStartSystem}
            onPause={onPause}
            onResume={onResume}
            onStop={onStop}
            onReset={onReset}
          />
        </div>
      </section>

      {/* Live caption — only shown during active recording */}
      {rec === "recording" && (
        <div className="mb-6">
          <LiveCaptionStrip caption={caption} />
        </div>
      )}

      {/* Committed transcript — always visible once segments exist */}
      <div className="mb-6">
        <LiveTranscriptPanel
          segments={segments}
          autoScroll={autoScroll}
          onToggleAutoScroll={setAutoScroll}
        />
      </div>

      {/* Post-recording actions */}
      {rec === "completed" && sessionId && (
        <div className="mb-6 flex gap-4">
          <Link
            to="/session/$id"
            params={{ id: sessionId }}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            View Full Session
          </Link>
          <Button variant="outline" onClick={onDelete} disabled={deleting}>
            {deleting ? "Deleting…" : "Delete Recording"}
          </Button>
        </div>
      )}

      {/* Intelligence generation */}
      {rec === "completed" && sessionId && (
        <section className="mb-6 rounded-lg border border-border bg-card p-5 shadow-sm">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Intelligence
          </h3>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              onClick={onGenerate}
              disabled={processing}
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {processing ? "Generating…" : "Generate Intelligence"}
            </button>
            <Link
              to="/session/$id"
              params={{ id: sessionId }}
              className="rounded-md border border-input bg-background px-3 py-1.5 text-sm hover:bg-accent"
            >
              View Session
            </Link>
          </div>
        </section>
      )}

      {processing && !summary && !actions && (
        <div className="mb-6">
          <AiGeneratingSkeleton />
        </div>
      )}

      {(summary || actions) && (
        <div className="mb-6 grid gap-6 lg:grid-cols-2">
          <SummaryPanel summary={summary?.summary} />
          <MomPanel mom={summary?.mom} />
          <div className="lg:col-span-2">
            <ActionItemsPanel items={actions ?? []} />
          </div>
        </div>
      )}

      {import.meta.env.DEV && (
        <>


          <StreamingEventLog events={events} />
        </>
      )}
    </AppLayout>
  );
}
