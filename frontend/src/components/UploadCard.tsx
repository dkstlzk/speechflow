import { useRef, useState, type DragEvent, type ChangeEvent } from "react";
import { useNavigate } from "@tanstack/react-router";
import { uploadFile } from "@/services/api";
import { StatusBadge } from "./StatusBadge";
import type { ProcessingStatus } from "@/types";

const ACCEPTED =
  ".mp3,.mp4,.wav,.m4a,.webm,audio/mpeg,audio/wav,audio/mp4,audio/webm,video/mp4,video/webm";

function formatBytes(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

export function UploadCard() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<ProcessingStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [title, setTitle] = useState("");
  const [hostName, setHostName] = useState("");
  const [participants, setParticipants] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    const f = files[0];
    const ok = /\.(mp3|mp4|wav|m4a|webm)$/i.test(f.name);
    if (!ok) {
      setError("Unsupported format. Use MP3, MP4, WAV, M4A, or WEBM.");
      return;
    }
    setError(null);
    setFile(f);
    setStatus("idle");
    setSessionId(null);
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  }

  function onSelect(e: ChangeEvent<HTMLInputElement>) {
    handleFiles(e.target.files);
  }

  async function onUpload() {
    if (!file) return;
    try {
      setStatus("uploading");
      const res = await uploadFile(file, {
        title: title.trim() || undefined,
        host_name: hostName.trim() || undefined,
        participants: participants.trim() || undefined,
      });
      setStatus("processing");
      setSessionId(res.data.sessionId);
      navigate({ to: "/session/$id", params: { id: res.data.sessionId } });
    } catch (e) {
      setStatus("failed");
      setError(e instanceof Error ? e.message : "Upload failed. Please try again.");
    }
  }

  function onClear() {
    setFile(null);
    setStatus("idle");
    setError(null);
    setSessionId(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
      <div className="mb-4">
        <h2 className="text-lg font-semibold">Upload Recording</h2>
        <p className="mt-1 text-sm text-muted-foreground">Supported formats: MP3, MP4, WAV</p>
      </div>

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <div>
          <label className="text-xs font-medium text-foreground">Title (Optional)</label>
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
          <label className="text-xs font-medium text-foreground">Host (Optional)</label>
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
          <label className="text-xs font-medium text-foreground">Participants (Optional)</label>
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

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed px-6 py-10 text-center transition-colors ${
          dragOver ? "border-primary bg-accent" : "border-border hover:bg-accent/50"
        }`}
      >
        <p className="text-sm font-medium">Drag & drop a file here</p>
        <p className="mt-1 text-xs text-muted-foreground">or click to select from your computer</p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          className="hidden"
          onChange={onSelect}
        />
      </div>

      {file && (
        <div className="mt-4 flex items-center justify-between rounded-md border border-border bg-background px-4 py-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{file.name}</p>
            <p className="text-xs text-muted-foreground">{formatBytes(file.size)}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClear}
              className="rounded-md border border-input bg-background px-3 py-1.5 text-sm hover:bg-accent"
            >
              Clear
            </button>
            <button
              onClick={onUpload}
              disabled={status === "uploading" || status === "processing"}
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              Upload
            </button>
          </div>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between text-sm">
        <span className="text-muted-foreground">Status</span>
        <StatusBadge status={status} />
      </div>

      {error && (
        <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-200">
          {error}
        </p>
      )}

      {sessionId && status === "completed" && (
        <div className="mt-4 rounded-md border border-border bg-background p-4">
          <p className="text-sm">
            Session ID: <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{sessionId}</code>
          </p>
          <button
            onClick={() => navigate({ to: "/session/$id", params: { id: sessionId } })}
            className="mt-3 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Open Session
          </button>
        </div>
      )}
    </div>
  );
}
