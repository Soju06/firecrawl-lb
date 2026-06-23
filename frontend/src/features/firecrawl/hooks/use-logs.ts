import { useQuery } from "@tanstack/react-query";

import { listFirecrawlLogs } from "@/features/firecrawl/api";
import type { SyncEndpoint } from "@/features/firecrawl/schemas";

export type LogFilters = {
  readonly endpoint: SyncEndpoint | "all";
  readonly status: string;
};

export function useFirecrawlLogs(filters: LogFilters) {
  return useQuery({
    queryKey: ["firecrawl", "logs", filters],
    queryFn: () => listFirecrawlLogs({ endpoint: filters.endpoint, status: filters.status, limit: 50, offset: 0 }),
    select: (data) => data.logs,
    refetchInterval: 20_000,
  });
}
