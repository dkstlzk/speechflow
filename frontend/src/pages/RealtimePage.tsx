import { useEffect, useRef, useState } from "react";
import { Link } from "@tanstack/react-router";
import { AppLayout } from "@/layouts/AppLayout";
import { ConnectionStatusBadge } from "@/components/ConnectionStatusBadge";
import { RecordingTimer } from "@/components/RecordingTimer";
import { RealtimeControls } from "@/components/RealtimeControls";
import { LiveTranscriptPanel } from "@/components/LiveTranscriptPanel";
import { LiveCaptionStrip } from "@/components/LiveCaptionStrip";
import { StreamingEventLog } from "@/components/StreamingEventLog";
import { SummaryPanel } from "@/components/SummaryPanel";
import { MomPanel } from "@/components/MomPanel";
import { ActionItemsPanel } from "@/components/ActionItemsPanel";
import {
  socket,
  connect,
  disconnect,
  startRecording,
  stopRecording,
  subscribeToStatus,
  subscribeToTranscript,
} from "@/services/socket";
import {
  finalizeRealtimeSession,
  getActions,
  getSummary,
  processSession,
  startRealtimeSession,
} from "@/services/api";
import { startAudioCapture, stopAudioCapture } from "@/services/audio";
import type {
  ActionItem,
  ConnectionStatus,
  RecordingStatus,
  StreamingEvent,
  SummaryResponse,
  TranscriptSegment,
} from "@/types";

export function RealtimePage() {
  const [conn, setConn] = useState<ConnectionStatus>("disconnected");
  const [rec, setRec] = useState<RecordingStatus>("idle");
  const [sessionId, setSessionId] = useState<string | null>(null);

  // PHASE 4B: Separate states
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [partial, setPartial] = useState<TranscriptSegment | null>(null);

  const [events, setEvents] = useState<StreamingEvent[]>([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const [resetKey, setResetKey] = useState(0);
  const [micGranted, setMicGranted] = useState<boolean | null>(null);

  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [actions, setActions] = useState<ActionItem[] | null>(null);
  const [processing, setProcessing] = useState(false);
  const [pingLogs, setPingLogs] = useState<string[]>([]);
  const pausedRef = useRef(false);

  useEffect(() => {
    const off1 = subscribeToTranscript((seg) => {
      if (pausedRef.current) return;

      // Route to the correct UI state
      if (seg.is_partial) {
        setPartial(seg);
      } else {
        setSegments((s) => [...s, seg]);
        setPartial(null); // Clear the live draft once committed
      }
    });

    const off2 = subscribeToStatus((ev) => {
      setEvents((e) => [...e, ev]);

      if (ev.type === "connected") {
        setConn("connected");
      }

      if (ev.type === "connecting") {
        setConn("connecting");
      }

      if (ev.type === "disconnected") {
        setConn("disconnected");
      }
    });

    const onPong = (data: any) => {
      const latency = data.echo_client_time
        ? Date.now() - data.echo_client_time
        : "N/A";

      setPingLogs((prev) =>
        [
          `PONG: ${data.message} | Latency: ${latency}ms | SID: ${data.sid}`,
          ...prev,
        ].slice(0, 3)
      );
    };

    socket.on("pong_test", onPong);

    return () => {
      off1();
      off2();
      socket.off("pong_test", onPong);
      disconnect();
    };
  }, []);

  async function requestMic() {
    if (!navigator.mediaDevices?.getUserMedia) {
      setMicGranted(false);
      return false;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((t) => t.stop());
      setMicGranted(true);
      return true;
    } catch {
      setMicGranted(false);
      return false;
    }
  }

  async function onStart() {
    const granted = await requestMic();
    if (!granted) return;
    setConn("connecting");
    await connect();
    const res = await startRealtimeSession();
    setSessionId(res.data.sessionId);
    setRec("recording");
    pausedRef.current = false;

    startRecording(res.data.sessionId);
    await startAudioCapture();
  }

  function onPause() {
    pausedRef.current = true;
    setRec("paused");
  }

  function onResume() {
    pausedRef.current = false;
    setRec("recording");
  }

  async function onStop() {
    stopRecording();
    stopAudioCapture();
    setRec("completed");
    if (sessionId) await finalizeRealtimeSession(sessionId);
  }

  function onReset() {
    stopRecording();
    stopAudioCapture();
    disconnect();
    setConn("disconnected");
    setRec("idle");
    setSessionId(null);
    setSegments([]);
    setPartial(null);
    setEvents([]);
    setSummary(null);
    setActions(null);
    setResetKey((k) => k + 1);
  }

  async function onGenerate() {
    if (!sessionId) return;
    setProcessing(true);
    try {
      await processSession(sessionId);
      const [s, a] = await Promise.all([
        getSummary(sessionId),
        getActions(sessionId),
      ]);
      setSummary(s.data);
      setActions(a.data);
    } finally {
      setProcessing(false);
    }
  }

  const latest = segments[segments.length - 1];

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
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Connection
            </p>
            <div className="mt-1.5">
              <ConnectionStatusBadge status={conn} />
            </div>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Recording
            </p>
            <p className="mt-1.5 text-sm font-medium capitalize">{rec}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Session ID
            </p>
            <p className="mt-1.5 text-sm">
              {sessionId ? (
                <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
                  {sessionId}
                </code>
              ) : (
                <span className="text-muted-foreground">—</span>
              )}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Duration
            </p>
            <p className="mt-1.5">
              <RecordingTimer
                running={rec === "recording"}
                resetKey={resetKey}
              />
            </p>
          </div>
        </div>
        <div className="mt-5 border-t border-border pt-4">
          <RealtimeControls
            status={rec}
            micGranted={micGranted}
            onStart={onStart}
            onPause={onPause}
            onResume={onResume}
            onStop={onStop}
            onReset={onReset}
          />
        </div>
      </section>

      <div className="mb-6">
        <LiveCaptionStrip latest={latest} />
      </div>

      <div className="mb-6">
        <LiveTranscriptPanel
          segments={segments}
          partial={partial}
          autoScroll={autoScroll}
          onToggleAutoScroll={setAutoScroll}
        />
      </div>

      {rec === "completed" && sessionId && (
        <section className="mb-6 rounded-lg border border-border bg-card p-5 shadow-sm">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Recording Complete
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

      {(summary || actions) && (
        <div className="mb-6 grid gap-6 lg:grid-cols-2">
          <SummaryPanel summary={summary?.summary} />
          <MomPanel mom={summary?.mom} />
          <div className="lg:col-span-2">
            <ActionItemsPanel items={actions ?? []} />
          </div>
        </div>
      )}

      <section className="mb-6 rounded-lg border border-border bg-card p-5 shadow-sm flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold uppercase text-muted-foreground mb-1">
            Transport Test
          </h3>

          <div className="font-mono text-xs text-muted-foreground h-4">
            {pingLogs[0] || "Click ping to test socket latency..."}
          </div>
        </div>

        <button
          onClick={() => {
            if (!socket.connected) return;

            socket.emit("ping_test", {
              client_time: Date.now(),
            });
          }}
          disabled={conn !== "connected"}
          className="rounded-md bg-secondary px-4 py-2 text-sm font-medium hover:bg-secondary/80 disabled:opacity-50"
        >
          Send Ping
        </button>
      </section>

      <StreamingEventLog events={events} />
    </AppLayout>
  );
}
