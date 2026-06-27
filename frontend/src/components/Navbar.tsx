import { Link } from "@tanstack/react-router";
import { AudioLines } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";

const linkBase =
  "rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40";

export function Navbar() {
  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-14 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2" aria-label="SpeechFlow home">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground shadow-sm">
            <AudioLines className="h-4 w-4" aria-hidden="true" />
          </span>
          <span className="text-[15px] font-semibold tracking-tight">SpeechFlow</span>
        </Link>
        <nav className="flex items-center gap-1" aria-label="Primary">
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
          <span className="mx-1 hidden h-5 w-px bg-border sm:inline-block" aria-hidden="true" />
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
