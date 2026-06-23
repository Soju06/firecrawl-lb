import { CreditCard } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { accountStatusClass, creditPercent } from "@/features/firecrawl/account-utils";
import type { FirecrawlAccount } from "@/features/firecrawl/schemas";
import { cn } from "@/lib/utils";

export function AccountStatusBadge({ status }: { readonly status: FirecrawlAccount["status"] }) {
  return (
    <Badge variant="outline" className={cn("capitalize", accountStatusClass(status))}>
      {status.replaceAll("_", " ")}
    </Badge>
  );
}

export function AccountCard({ account }: { readonly account: FirecrawlAccount }) {
  const percent = creditPercent(account);
  const budget = account.monthly_budget_credits ?? account.plan_credits_live ?? 0;
  return (
    <Card className="card-hover">
      <CardHeader className="flex flex-row items-start justify-between gap-3 pb-2">
        <div className="min-w-0">
          <CardTitle className="truncate text-sm">{account.team_label}</CardTitle>
          <p className="truncate text-xs text-muted-foreground">{account.id}</p>
        </div>
        <AccountStatusBadge status={account.status} />
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <CreditCard className="h-3.5 w-3.5" aria-hidden="true" />
            Credits
          </span>
          <span className="font-medium text-foreground">
            {(account.remaining_credits_live ?? 0).toLocaleString()} / {budget.toLocaleString()}
          </span>
        </div>
        <Progress value={percent} />
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div>
            <p className="text-muted-foreground">Plan</p>
            <p className="font-medium">{account.plan_type}</p>
          </div>
          <div>
            <p className="text-muted-foreground">RPM</p>
            <p className="font-medium">{account.rpm_limit ?? "None"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Creds</p>
            <p className="font-medium">{account.credentials.length}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
