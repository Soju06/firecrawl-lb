import { FileText, RefreshCw } from "lucide-react";
import { useState } from "react";

import { AlertMessage } from "@/components/alert-message";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useFirecrawlLogs, type LogFilters } from "@/features/firecrawl/hooks/use-logs";
import type { FirecrawlRequestLog } from "@/features/firecrawl/schemas";
import { getErrorMessageOrNull } from "@/utils/errors";

const LOG_STATUSES = ["all", "success", "error"] as const;
const LOG_ENDPOINTS = ["all", "scrape", "map", "search"] as const;

export function LogsPage() {
  const [filters, setFilters] = useState<LogFilters>({ endpoint: "all", status: "all" });
  const logsQuery = useFirecrawlLogs(filters);
  const logs = logsQuery.data ?? [];
  const error = getErrorMessageOrNull(logsQuery.error);
  return (
    <div className="animate-fade-in-up space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold">
            <FileText className="h-5 w-5 text-primary" aria-hidden="true" />
            Logs
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">Sync scrape, map, and search request history.</p>
        </div>
        <Button variant="outline" onClick={() => void logsQuery.refetch()}>
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          Refresh
        </Button>
      </div>
      {error ? <AlertMessage variant="error">{error}</AlertMessage> : null}
      <div className="flex flex-wrap gap-3">
        <FilterSelect
          value={filters.endpoint}
          values={LOG_ENDPOINTS}
          onChange={(endpoint) => setFilters((current) => ({ ...current, endpoint }))}
        />
        <FilterSelect
          value={filters.status}
          values={LOG_STATUSES}
          onChange={(status) => setFilters((current) => ({ ...current, status }))}
        />
      </div>
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Endpoint</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Account</TableHead>
                <TableHead>HTTP</TableHead>
                <TableHead>Estimated</TableHead>
                <TableHead>Used</TableHead>
                <TableHead>Latency</TableHead>
                <TableHead>Error</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.map((log) => (
                <LogRow key={log.id} log={log} />
              ))}
              {logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="h-24 text-center text-muted-foreground">
                    No request logs match the current filters.
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
            {item}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function LogRow({ log }: { readonly log: FirecrawlRequestLog }) {
  return (
    <TableRow>
      <TableCell>{log.endpoint}</TableCell>
      <TableCell>
        <Badge variant="outline" className={log.status === "success" ? "border-emerald-500/30 bg-emerald-500/10" : ""}>
          {log.status}
        </Badge>
      </TableCell>
      <TableCell>{log.account_id ?? "None"}</TableCell>
      <TableCell>{log.upstream_status_code ?? "None"}</TableCell>
      <TableCell>{log.estimated_credits_pre ?? "None"}</TableCell>
      <TableCell>{log.credits_used_final ?? "None"}</TableCell>
      <TableCell>{formatLatency(log.latency_ms)}</TableCell>
      <TableCell>{log.error_message ? <ErrorTooltip log={log} /> : "None"}</TableCell>
      <TableCell>{new Date(log.created_at).toLocaleString()}</TableCell>
    </TableRow>
  );
}

function ErrorTooltip({ log }: { readonly log: FirecrawlRequestLog }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button type="button" className="max-w-36 truncate text-left text-destructive underline-offset-2 hover:underline">
          {log.error_code ?? "error"}
        </button>
      </TooltipTrigger>
      <TooltipContent className="max-w-80">
        <p>{log.error_message}</p>
      </TooltipContent>
    </Tooltip>
  );
}

function formatLatency(value: number | null) {
  if (value === null) return "None";
  if (value < 1000) return `${value} ms`;
  return `${(value / 1000).toFixed(2)} s`;
}
