import { Briefcase, RefreshCw, XCircle } from "lucide-react";
import { useState } from "react";

import { AlertMessage } from "@/components/alert-message";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useFirecrawlJobs, type JobFilters } from "@/features/firecrawl/hooks/use-jobs";
import type { FirecrawlJob } from "@/features/firecrawl/schemas";
import { getErrorMessageOrNull } from "@/utils/errors";

const JOB_STATUSES = ["all", "submitted", "completed", "failed", "cancelled"] as const;
const JOB_ENDPOINTS = ["all", "crawl", "batch_scrape"] as const;

export function JobsPage() {
  const [filters, setFilters] = useState<JobFilters>({ endpoint: "all", status: "all" });
  const { jobsQuery, cancelMutation } = useFirecrawlJobs(filters);
  const jobs = jobsQuery.data ?? [];
  const error = getErrorMessageOrNull(jobsQuery.error) || getErrorMessageOrNull(cancelMutation.error);
  return (
    <div className="animate-fade-in-up space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold">
            <Briefcase className="h-5 w-5 text-primary" aria-hidden="true" />
            Jobs
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">Crawl and batch scrape jobs routed through Firecrawl LB.</p>
        </div>
        <Button variant="outline" onClick={() => void jobsQuery.refetch()}>
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          Refresh
        </Button>
      </div>
      {error ? <AlertMessage variant="error">{error}</AlertMessage> : null}
      <div className="flex flex-wrap gap-3">
        <FilterSelect
          value={filters.endpoint}
          values={JOB_ENDPOINTS}
          onChange={(endpoint) => setFilters((current) => ({ ...current, endpoint }))}
        />
        <FilterSelect
          value={filters.status}
          values={JOB_STATUSES}
          onChange={(status) => setFilters((current) => ({ ...current, status }))}
        />
      </div>
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Upstream job</TableHead>
                <TableHead>Endpoint</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Account</TableHead>
                <TableHead>Reserved</TableHead>
                <TableHead>Used</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Completed</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.map((job) => (
                <JobRow
                  key={job.id}
                  job={job}
                  cancelling={cancelMutation.isPending}
                  onCancel={() => {
                    if (job.upstream_job_id) {
                      cancelMutation.mutate({ endpoint: job.endpoint, upstreamJobId: job.upstream_job_id });
                    }
                  }}
                />
              ))}
              {jobs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="h-24 text-center text-muted-foreground">
                    No jobs match the current filters.
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function FilterSelect<TValue extends string>({
  value,
  values,
  onChange,
}: {
  readonly value: TValue;
  readonly values: readonly TValue[];
  readonly onChange: (value: TValue) => void;
}) {
  return (
    <Select
      value={value}
      onValueChange={(next) => {
        const selected = values.find((item) => item === next);
        if (selected) onChange(selected);
      }}
    >
      <SelectTrigger className="w-44">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {values.map((item) => (
          <SelectItem key={item} value={item}>
            {item.replaceAll("_", " ")}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function JobRow({
  job,
  cancelling,
  onCancel,
}: {
  readonly job: FirecrawlJob;
  readonly cancelling: boolean;
  readonly onCancel: () => void;
}) {
  const canCancel = job.upstream_job_id !== null && job.status === "submitted";
  return (
    <TableRow>
      <TableCell className="font-medium">{job.upstream_job_id ?? "Pending"}</TableCell>
      <TableCell>{job.endpoint.replaceAll("_", " ")}</TableCell>
      <TableCell>
        <JobStatusBadge status={job.status} />
      </TableCell>
      <TableCell>{job.account_id ?? "None"}</TableCell>
      <TableCell>{job.estimated_credits_reserved ?? "None"}</TableCell>
      <TableCell>{job.credits_used_final ?? "None"}</TableCell>
      <TableCell>{formatDate(job.created_at)}</TableCell>
      <TableCell>{job.completed_at ? formatDate(job.completed_at) : "None"}</TableCell>
      <TableCell>
        <Button size="sm" variant="outline" disabled={!canCancel || cancelling} onClick={onCancel}>
          <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
          Cancel
        </Button>
      </TableCell>
    </TableRow>
  );
}

function JobStatusBadge({ status }: { readonly status: string }) {
  const style = status === "completed" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700" : "";
  return (
    <Badge variant="outline" className={style}>
      {status}
    </Badge>
  );
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}
