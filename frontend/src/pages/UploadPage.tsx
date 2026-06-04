import { Link } from "@tanstack/react-router";
import { AppLayout } from "@/layouts/AppLayout";
import { UploadCard } from "@/components/UploadCard";

export function UploadPage() {
  return (
    <AppLayout>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">SpeechFlow</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Choose a workflow to get started.
        </p>
      </div>

      <div className="mb-8 grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
          <h2 className="text-base font-semibold">Upload Recording</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Upload MP3, MP4, or WAV files for transcription and intelligent
            processing.
          </p>
          <a
            href="#upload"
            className="mt-4 inline-flex items-center rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Open Upload Workflow
          </a>
        </div>
        <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
          <h2 className="text-base font-semibold">Realtime Recording</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Record audio directly from the microphone and receive live
            transcript updates.
          </p>
          <Link
            to="/realtime"
            className="mt-4 inline-flex items-center rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Open Realtime Workflow
          </Link>
        </div>
      </div>

      <div id="upload">
        <UploadCard />
      </div>
    </AppLayout>
  );
}
