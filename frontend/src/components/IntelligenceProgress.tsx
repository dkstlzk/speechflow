import React, { useEffect, useState } from "react";
import { CheckCircle2, Loader2, Circle } from "lucide-react";

interface Stage {
  label: string;
  delayMs: number;
}

interface Props {
  mode?: "transcript" | "intelligence";
}

export function IntelligenceProgress({ mode = "intelligence" }: Props) {
  const STAGES: Stage[] =
    mode === "transcript"
      ? [
          { label: "Processing Audio...", delayMs: 0 },
          { label: "Running Transcription...", delayMs: 1000 },
        ]
      : [
          { label: "Transcript Loaded", delayMs: 0 },
          { label: "Classification", delayMs: 1000 },
          { label: "Generating Intelligence...", delayMs: 3000 },
        ];

  const title = mode === "transcript" ? "Transcribing Audio" : "Processing Intelligence";

  const [currentStage, setCurrentStage] = useState<number>(0);

  useEffect(() => {
    const timers = STAGES.map((stage, index) => {
      if (index === 0) return null;
      return setTimeout(() => {
        setCurrentStage((prev) => Math.max(prev, index));
      }, stage.delayMs);
    });

    return () => {
      timers.forEach((t) => t && clearTimeout(t));
    };
  }, []);

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center border rounded-xl bg-card shadow-sm">
      <h3 className="text-lg font-semibold mb-6">{title}</h3>
      <div className="flex flex-col space-y-4 max-w-sm w-full mx-auto">
        {STAGES.map((stage, index) => {
          const isComplete = index < currentStage;
          const isCurrent = index === currentStage;
          const isPending = index > currentStage;

          return (
            <div key={index} className="flex items-center text-sm font-medium">
              <div className="w-8 flex justify-center mr-3">
                {isComplete ? (
                  <CheckCircle2 className="h-5 w-5 text-primary" />
                ) : isCurrent ? (
                  <Loader2 className="h-5 w-5 text-primary animate-spin" />
                ) : (
                  <Circle className="h-5 w-5 text-muted-foreground/30" />
                )}
              </div>
              <span
                className={
                  isComplete
                    ? "text-foreground"
                    : isCurrent
                      ? "text-primary font-semibold"
                      : "text-muted-foreground"
                }
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
