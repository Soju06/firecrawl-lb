import { ArrowUpCircle, Briefcase, CreditCard, Flame, Tag, Users } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { getFirecrawlOverview } from "@/features/firecrawl/api";
import { getRuntimeVersion } from "@/features/runtime/api";

const GITHUB_REPOSITORY_URL = "https://github.com/soju06/firecrawl-lb";

export function StatusBar() {
  const { data: overview } = useQuery({
    queryKey: ["firecrawl", "overview", "status-bar"],
    queryFn: getFirecrawlOverview,
    refetchInterval: 60_000,
  });
  const { data: runtimeVersion } = useQuery({
    queryKey: ["runtime", "version"],
    queryFn: getRuntimeVersion,
    retry: false,
    staleTime: 6 * 60 * 60 * 1000,
  });
  const currentVersion = runtimeVersion?.currentVersion ?? __APP_VERSION__;
  const latestVersion = runtimeVersion?.latestVersion ?? null;
  const showUpdateAvailable = runtimeVersion?.updateAvailable === true && latestVersion;
  const updateLabel = latestVersion
    ? `New version available: ${latestVersion}. Open release notes.`
    : "New version available. Open release notes.";
  return (
    <footer className="fixed bottom-0 left-0 right-0 z-50 border-t border-white/[0.08] bg-background/50 px-4 py-2 shadow-[0_-1px_12px_rgba(0,0,0,0.06)] backdrop-blur-xl backdrop-saturate-[1.8] supports-[backdrop-filter]:bg-background/40 dark:shadow-[0_-1px_12px_rgba(0,0,0,0.25)]">
      <div className="mx-auto flex w-full max-w-[1500px] items-center gap-4 text-xs text-muted-foreground">
        <div className="flex min-w-0 flex-wrap items-center gap-x-5 gap-y-1">
          <span className="inline-flex items-center gap-1.5">
            <Users className="h-3 w-3" aria-hidden="true" />
            <span className="font-medium">Accounts:</span> {overview?.total_accounts ?? "Loading"}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <CreditCard className="h-3 w-3" aria-hidden="true" />
            <span className="font-medium">Remaining:</span> {overview?.total_remaining_credits.toLocaleString() ?? "Loading"}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Briefcase className="h-3 w-3" aria-hidden="true" />
            <span className="font-medium">Active jobs:</span> {overview?.active_jobs ?? "Loading"}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Tag className="h-3 w-3" aria-hidden="true" />
            <span className="font-medium">Version:</span> {currentVersion}
            {showUpdateAvailable ? (
              <a
                aria-label={updateLabel}
                className="inline-flex h-4 w-4 items-center justify-center rounded-full text-amber-500 transition-colors hover:text-amber-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/60 focus-visible:ring-offset-2"
                href={runtimeVersion.releaseUrl}
                rel="noreferrer"
                target="_blank"
                title={updateLabel}
              >
                <ArrowUpCircle className="h-3.5 w-3.5" aria-hidden="true" />
              </a>
            ) : null}
          </span>
        </div>
        <a
          aria-label="Open official GitHub repository"
          className="ml-auto inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border/70 bg-background/70 text-muted-foreground transition-colors hover:bg-muted/70 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          href={GITHUB_REPOSITORY_URL}
          rel="noreferrer"
          target="_blank"
          title="GitHub"
        >
          <Flame className="h-3.5 w-3.5 text-orange-500" aria-hidden="true" />
        </a>
      </div>
    </footer>
  );
}
