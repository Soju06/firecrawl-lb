import { useQuery } from "@tanstack/react-query";

import { getFirecrawlOverview } from "@/features/firecrawl/api";

export function useFirecrawlOverview() {
  return useQuery({
    queryKey: ["firecrawl", "overview"],
    queryFn: getFirecrawlOverview,
    refetchInterval: 30_000,
  });
}
