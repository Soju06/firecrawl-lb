import type { FirecrawlAccount } from "@/features/firecrawl/schemas";

const STATUS_STYLES: Record<FirecrawlAccount["status"], string> = {
  active: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  rate_limited: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  credit_exhausted: "border-destructive/30 bg-destructive/10 text-destructive",
  paused: "border-muted bg-muted text-muted-foreground",
  invalid: "border-destructive/30 bg-destructive/10 text-destructive",
};

export function accountStatusClass(status: FirecrawlAccount["status"]) {
  return STATUS_STYLES[status];
}

export function creditPercent(account: FirecrawlAccount) {
  const budget = account.monthly_budget_credits ?? account.plan_credits_live ?? 0;
  const remaining = account.remaining_credits_live ?? 0;
  if (budget <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round((remaining / budget) * 100)));
}
