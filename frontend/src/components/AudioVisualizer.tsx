interface Props {
  isRecording: boolean;
}

const BARS = 5;

export function AudioVisualizer({ isRecording }: Props) {
  return (
    <div
      className="flex h-6 items-end gap-0.5"
      aria-label={isRecording ? "Recording audio" : "Microphone idle"}
    >
      {Array.from({ length: BARS }).map((_, i) => (
        <span
          key={i}
          className={
            isRecording
              ? "w-1 rounded-sm bg-primary animate-[audiobar_900ms_ease-in-out_infinite]"
              : "w-1 h-1 rounded-sm bg-muted-foreground/40"
          }
          style={isRecording ? { animationDelay: `${i * 120}ms`, height: "100%" } : undefined}
        />
      ))}
    </div>
  );
}
