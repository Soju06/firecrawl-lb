import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { cancelFirecrawlJob, listFirecrawlJobs } from "@/features/firecrawl/api";
import type { JobEndpoint } from "@/features/firecrawl/schemas";

export type JobFilters = {
  readonly endpoint: JobEndpoint | "all";
  readonly status: string;
};

export function useFirecrawlJobs(filters: JobFilters) {
  const queryClient = useQueryClient();
  const jobsQuery = useQuery({
    queryKey: ["firecrawl", "jobs", filters],
    queryFn: () => listFirecrawlJobs({ endpoint: filters.endpoint, status: filters.status, limit: 50, offset: 0 }),
    select: (data) => data.jobs,
    refetchInterval: 20_000,
  });
  const cancelMutation = useMutation({
    mutationFn: ({ endpoint, upstreamJobId }: { readonly endpoint: JobEndpoint; readonly upstreamJobId: string }) =>
      cancelFirecrawlJob(endpoint, upstreamJobId),
    onSuccess: () => {
      toast.success("Job cancellation requested");
      void queryClient.invalidateQueries({ queryKey: ["firecrawl", "jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["firecrawl", "overview"] });
    },
  });
  return { jobsQuery, cancelMutation };
}
