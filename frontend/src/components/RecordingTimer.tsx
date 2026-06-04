import { useEffect, useState } from "react";

interface Props {
  running: boolean;
  resetKey?: number;
}

export function RecordingTimer({ running, resetKey = 0 }: Props) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    setSeconds(0);
  }, [resetKey]);

  useEffect(() => {
    if (!running) return;
    const i = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(i);
  }, [running]);

  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return (
    <span className="font-mono text-sm tabular-nums">
      {m.toString().padStart(2, "0")}:{s.toString().padStart(2, "0")}
    </span>
  );
}
