import type { RecordingStatus, MicrophoneState } from "@/types";

interface Props {
  status: RecordingStatus;
  micState: MicrophoneState;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onReset: () => void;
}

const btn =
  "rounded-md px-3 py-1.5 text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed";

export function RealtimeControls({
  status,
  micState,
  onStart,
  onPause,
  onResume,
  onStop,
  onReset,
}: Props) {
  const recording = status === "recording";
  const paused = status === "paused";
  const idle = status === "idle";
  const canStart = idle || status === "completed";

  const micTextMap: Record<MicrophoneState, string> = {
    initializing: "Checking...",
    not_requested: "Permission not requested",
    ready: "Ready",
    recording: "Recording",
    paused: "Paused",
    denied: "Permission denied",
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      {status !== "completed" && (
        <button
          onClick={onStart}
          disabled={!idle}
          className={`${btn} bg-primary text-primary-foreground hover:bg-primary/90`}
        >
          Start Recording
        </button>
      )}
      <button
        onClick={onPause}
        disabled={!recording}
        className={`${btn} border border-input bg-background hover:bg-accent`}
      >
        Pause
      </button>
      <button
        onClick={onResume}
        disabled={!paused}
        className={`${btn} border border-input bg-background hover:bg-accent`}
      >
        Resume
      </button>
      <button
        onClick={onStop}
        disabled={!recording && !paused}
        className={`${btn} bg-red-600 text-white hover:bg-red-700`}
      >
        Stop
      </button>
      <button
        onClick={onReset}
        disabled={idle}
        className={`${btn} border border-input bg-background hover:bg-accent flex flex-col items-center`}
      >
        <span className="leading-tight">New Recording</span>
        <span className="text-[10px] font-normal leading-tight text-muted-foreground">
          (Auto-saved)
        </span>
      </button>

      <span className="ml-auto text-xs text-muted-foreground">
        Microphone: {micTextMap[micState]}
      </span>
    </div>
  );
}
