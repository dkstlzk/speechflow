import React, { useEffect, useState } from "react";
import { CheckCircle2, Loader2, Circle } from "lucide-react";

interface Stage {
  label: string;
  delayMs: number;
}

interface Props {
  mode?: "transcript" | "intelligence" | "diarization" | "finalizing";
  processingStage?: string;
}

export function IntelligenceProgress({ mode = "intelligence", processingStage }: Props) {
  let STAGES: Stage[] = [];

  if (mode === "transcript") {
    STAGES = [
      { label: "Processing Audio...", delayMs: 0 },
      { label: "Running Transcription...", delayMs: 1000 },
    ];
  } else if (mode === "diarization") {
    STAGES = [
      { label: "Loading Audio...", delayMs: 0 },
      { label: "Running Pyannote Inference...", delayMs: 1000 },
      { label: "Aligning Speaker Segments...", delayMs: 3000 },
    ];
  } else if (mode === "finalizing") {
    STAGES = [
      { label: "Saving Audio Stream...", delayMs: 0 },
      { label: "Finalizing Session...", delayMs: 1000 },
    ];
  } else {
    if (processingStage) {
      const knownStages = [
        "Transcript Loaded",
        "Classifying Transcript...",
        "Generating Summary...",
        "Generating Meeting Minutes...",
        "Generating Action Items...",
        "Saving Outputs...",
      ];

      const currentIndex = knownStages.indexOf(processingStage);
      if (currentIndex >= 0) {
        for (let i = 0; i <= currentIndex; i++) {
          let label = knownStages[i];
          if (i < currentIndex) {
            if (label === "Classifying Transcript...") label = "Classified Transcript";
            if (label === "Generating Summary...") label = "Summary Generated";
            if (label === "Generating Meeting Minutes...") label = "Meeting Minutes Generated";
            if (label === "Generating Action Items...") label = "Action Items Generated";
            if (label === "Saving Outputs...") label = "Outputs Saved";
          }
          STAGES.push({ label, delayMs: 0 });
        }
      } else {
        STAGES = [{ label: processingStage, delayMs: 0 }];
      }
    } else {
      STAGES = [
        { label: "Transcript Loaded", delayMs: 0 },
        { label: "Generating Intelligence...", delayMs: 1000 },
      ];
    }
  }

  const title =
    mode === "transcript"
      ? "Transcribing Audio"
      : mode === "diarization"
        ? "Identifying Speakers"
        : mode === "finalizing"
          ? "Finalizing Recording"
          : "Processing Intelligence";

  const isDynamicIntelligence = mode === "intelligence" && processingStage;
  const initialStage = isDynamicIntelligence ? STAGES.length - 1 : 0;

  const [currentStage, setCurrentStage] = useState<number>(initialStage);

  useEffect(() => {
    if (isDynamicIntelligence) {
      setCurrentStage(STAGES.length - 1);
      return;
    }

    const timers = STAGES.map((stage, index) => {
      if (index === 0) return null;
      return setTimeout(() => {
        setCurrentStage((prev) => Math.max(prev, index));
      }, stage.delayMs);
    });

    return () => {
      timers.forEach((t) => t && clearTimeout(t));
    };
  }, [mode, processingStage, STAGES.length, isDynamicIntelligence]);

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
