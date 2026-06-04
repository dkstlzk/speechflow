import type { RecordingStatus } from "@/types";

interface Props {
  status: RecordingStatus;
  micGranted: boolean | null;
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
  micGranted,
  onStart,
  onPause,
  onResume,
  onStop,
  onReset,
}: Props) {
  const recording = status === "recording";
  const paused = status === "paused";
  const idle = status === "idle";

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        onClick={onStart}
        disabled={!idle && status !== "completed"}
        className={`${btn} bg-primary text-primary-foreground hover:bg-primary/90`}
      >
        Start Recording
      </button>
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
        className={`${btn} border border-input bg-background hover:bg-accent`}
      >
        Reset Session
      </button>

      <span className="ml-auto text-xs text-muted-foreground">
        Microphone:{" "}
        {micGranted === null
          ? "not requested"
          : micGranted
            ? "granted"
            : "denied"}
      </span>
    </div>
  );
}
