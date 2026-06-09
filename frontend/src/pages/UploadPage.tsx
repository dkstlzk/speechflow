import { Link } from "@tanstack/react-router";
import { ArrowRight, Mic, Upload } from "lucide-react";
import { AppLayout } from "@/layouts/AppLayout";
import { UploadCard } from "@/components/UploadCard";

export function UploadPage() {
  return (
    <AppLayout>
      <div className="mb-10 max-w-2xl">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
          AI meeting intelligence
        </span>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
          Turn conversations into structured insight.
        </h1>
        <p className="mt-3 text-[15px] leading-7 text-muted-foreground">
          Upload a recording or capture live audio. SpeechFlow transcribes, diarizes, and extracts
          summaries, meeting minutes, and action items — automatically.
        </p>
      </div>

      <div className="mb-10 grid gap-4 sm:grid-cols-2">
        <Link
          to="/"
          className="group relative flex flex-col gap-3 rounded-xl border border-border/70 bg-card p-6 transition-all hover:border-border-strong hover:shadow-[0_1px_2px_rgba(0,0,0,0.04),0_8px_24px_-12px_rgba(0,0,0,0.08)]"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Upload className="h-4 w-4" />
          </span>
          <div>
            <h2 className="text-base font-semibold tracking-tight">Upload Recording</h2>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              Drop in MP3, MP4, or WAV files for transcription and intelligence.
            </p>
          </div>
          <span className="mt-auto inline-flex items-center gap-1 text-xs font-medium text-primary">
            Open workflow
            <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
          </span>
        </Link>

        <Link
          to="/realtime"
          className="group relative flex flex-col gap-3 rounded-xl border border-border/70 bg-card p-6 transition-all hover:border-border-strong hover:shadow-[0_1px_2px_rgba(0,0,0,0.04),0_8px_24px_-12px_rgba(0,0,0,0.08)]"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Mic className="h-4 w-4" />
          </span>
          <div>
            <h2 className="text-base font-semibold tracking-tight">Realtime Recording</h2>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              Capture audio from the microphone and stream live transcript updates.
            </p>
          </div>
          <span className="mt-auto inline-flex items-center gap-1 text-xs font-medium text-primary">
            Open workflow
            <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
          </span>
        </Link>
      </div>

      <div id="upload">
        <UploadCard />
      </div>
    </AppLayout>
  );
}
