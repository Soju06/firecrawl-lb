import { Activity, Gauge, Layers, PieChart } from "lucide-react";

import { AlertMessage } from "@/components/alert-message";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { AccountCard } from "@/features/firecrawl/components/account-card";
import { useFirecrawlAccounts } from "@/features/firecrawl/hooks/use-accounts";
import { useFirecrawlOverview } from "@/features/firecrawl/hooks/use-overview";
import { getErrorMessageOrNull } from "@/utils/errors";

export function OverviewPage() {
  const overviewQuery = useFirecrawlOverview();
  const { accountsQuery } = useFirecrawlAccounts();
  const overview = overviewQuery.data;
  const accounts = accountsQuery.data ?? [];
  const error = getErrorMessageOrNull(overviewQuery.error) || getErrorMessageOrNull(accountsQuery.error);
  const creditPercent =
    overview && overview.total_budget_credits > 0
      ? Math.round((overview.total_remaining_credits / overview.total_budget_credits) * 100)
      : 0;
  const successPercent =
    overview && overview.recent_requests.total > 0
      ? Math.round((overview.recent_requests.success / overview.recent_requests.total) * 100)
      : 0;
  return (
    <div className="animate-fade-in-up space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <Activity className="h-5 w-5 text-primary" aria-hidden="true" />
          Overview
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">Firecrawl account capacity and proxy activity.</p>
      </div>
      {error ? <AlertMessage variant="error">{error}</AlertMessage> : null}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Credits"
          value={
            overview
              ? `${overview.total_remaining_credits.toLocaleString()} / ${overview.total_budget_credits.toLocaleString()}`
              : "Loading"
          }
          icon={<Gauge className="h-4 w-4" aria-hidden="true" />}
        >
          <Progress value={creditPercent} />
        </MetricCard>
        <MetricCard
          title="Accounts"
          value={overview ? `${overview.active_accounts} / ${overview.total_accounts} active` : "Loading"}
          icon={<Layers className="h-4 w-4" aria-hidden="true" />}
        >
          <div className="flex flex-wrap gap-1.5">
            {overview ? (
              Object.entries(overview.accounts_by_status).map(([status, count]) => (
                <Badge key={status} variant="outline" className="capitalize">
                  {status.replaceAll("_", " ")} {count}
                </Badge>
              ))
            ) : null}
          </div>
        </MetricCard>
        <MetricCard
          title="Active jobs"
          value={overview ? overview.active_jobs.toLocaleString() : "Loading"}
          icon={<Activity className="h-4 w-4" aria-hidden="true" />}
        />
        <MetricCard
          title="Recent requests"
          value={overview ? `${successPercent}% success` : "Loading"}
          icon={<PieChart className="h-4 w-4" aria-hidden="true" />}
        >
          <Progress value={successPercent} />
          {overview ? (
            <p className="text-xs text-muted-foreground">
              {overview.recent_requests.success} success, {overview.recent_requests.error} error
            </p>
          ) : null}
        </MetricCard>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Endpoint breakdown</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {overview
            ? Object.entries(overview.endpoint_breakdown).map(([endpoint, count]) => (
                <div key={endpoint} className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">{endpoint.replaceAll("_", " ")}</p>
                  <p className="mt-1 text-xl font-semibold">{count}</p>
                </div>
              ))
            : null}
        </CardContent>
      </Card>
      <div>
        <h2 className="mb-3 text-lg font-semibold">Account credits</h2>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {accounts.map((account) => (
            <AccountCard key={account.id} account={account} />
          ))}
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  title,
  value,
  icon,
  children,
}: {
  readonly title: string;
  readonly value: string;
  readonly icon: React.ReactNode;
  readonly children?: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3 pb-2">
        <CardTitle className="text-sm">{title}</CardTitle>
        <span className="text-muted-foreground">{icon}</span>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-2xl font-semibold">{value}</p>
        {children}
      </CardContent>
    </Card>
  );
}
