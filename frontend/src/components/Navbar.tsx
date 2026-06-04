import { Link } from "@tanstack/react-router";

const linkBase =
  "rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground";

export function Navbar() {
  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" className="text-base font-semibold tracking-tight">
          SpeechFlow
        </Link>
        <nav className="flex items-center gap-1">
          <Link
            to="/"
            activeOptions={{ exact: true }}
            className={linkBase}
            activeProps={{ className: "bg-accent text-foreground" }}
          >
            Upload
          </Link>
          <Link
            to="/realtime"
            className={linkBase}
            activeProps={{ className: "bg-accent text-foreground" }}
          >
            Realtime
          </Link>
          <Link
            to="/history"
            className={linkBase}
            activeProps={{ className: "bg-accent text-foreground" }}
          >
            History
          </Link>
        </nav>
      </div>
    </header>
  );
}
