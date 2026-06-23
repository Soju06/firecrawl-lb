import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { AccountStatusBadge } from "@/features/firecrawl/components/account-card";
import { CredentialAddDialog } from "@/features/firecrawl/components/credential-add-dialog";
import type {
  FirecrawlAccount,
  FirecrawlAccountUpdateRequest,
  FirecrawlCredentialCreateRequest,
  FirecrawlCredentialUpdateRequest,
} from "@/features/firecrawl/schemas";

const ACCOUNT_STATUSES = ["active", "rate_limited", "credit_exhausted", "paused"] as const;
const CREDENTIAL_STATUSES = ["active", "paused", "invalid"] as const;

function accountStatusFromValue(value: string): FirecrawlAccount["status"] | null {
  return ACCOUNT_STATUSES.find((status) => status === value) ?? null;
}

function credentialStatusFromValue(value: string): FirecrawlCredentialUpdateRequest["status"] | null {
  return CREDENTIAL_STATUSES.find((status) => status === value) ?? null;
}

function nullableNumber(form: FormData, key: string): number | null {
  const value = String(form.get(key) ?? "").trim();
  return value ? Number(value) : null;
}

export function AccountDetailPanel({
  account,
  open,
  busy,
  onOpenChange,
  onUpdateAccount,
  onAddCredential,
  onUpdateCredential,
}: {
  readonly account: FirecrawlAccount | null;
  readonly open: boolean;
  readonly busy?: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly onUpdateAccount: (accountId: string, payload: FirecrawlAccountUpdateRequest) => Promise<void>;
  readonly onAddCredential: (accountId: string, payload: FirecrawlCredentialCreateRequest) => Promise<void>;
  readonly onUpdateCredential: (
    accountId: string,
    credentialId: string,
    payload: FirecrawlCredentialUpdateRequest,
  ) => Promise<void>;
}) {
  const [status, setStatus] = useState<FirecrawlAccount["status"]>("active");
  if (!account) return null;
  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const cooldown = String(form.get("cooldown_until") ?? "").trim();
    void onUpdateAccount(account.id, {
      status,
      monthly_budget_credits: nullableNumber(form, "monthly_budget_credits"),
      remaining_credits_live: nullableNumber(form, "remaining_credits_live"),
      plan_credits_live: nullableNumber(form, "plan_credits_live"),
      rpm_limit: nullableNumber(form, "rpm_limit"),
      max_concurrency: nullableNumber(form, "max_concurrency"),
      cooldown_until: cooldown ? new Date(cooldown).toISOString() : null,
    });
  };
  return (
    <Sheet
      open={open}
      onOpenChange={(nextOpen) => {
        if (nextOpen) setStatus(account.status);
        onOpenChange(nextOpen);
      }}
    >
      <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
        <SheetHeader>
          <SheetTitle className="flex items-center justify-between gap-3">
            <span className="truncate">{account.team_label}</span>
            <AccountStatusBadge status={account.status} />
          </SheetTitle>
        </SheetHeader>
        <div className="space-y-6 px-4 pb-6">
          <div className="grid gap-2 text-sm">
            <Info label="Account ID" value={account.id} />
            <Info label="Plan" value={account.plan_type} />
            <Info label="Cooldown" value={account.cooldown_until ?? "None"} />
          </div>
          <Separator />
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Status</Label>
                <Select
                  value={status}
                  onValueChange={(value) => {
                    const nextStatus = accountStatusFromValue(value);
                    if (nextStatus) setStatus(nextStatus);
                  }}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ACCOUNT_STATUSES.map((item) => (
                      <SelectItem key={item} value={item}>
                        {item.replaceAll("_", " ")}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Field name="monthly_budget_credits" label="Monthly budget" defaultValue={account.monthly_budget_credits ?? ""} />
              <Field name="remaining_credits_live" label="Remaining credits" defaultValue={account.remaining_credits_live ?? ""} />
              <Field name="plan_credits_live" label="Plan credits live" defaultValue={account.plan_credits_live ?? ""} />
              <Field name="rpm_limit" label="RPM limit" defaultValue={account.rpm_limit ?? ""} />
              <Field name="max_concurrency" label="Max concurrency" defaultValue={account.max_concurrency ?? ""} />
              <Field name="cooldown_until" label="Cooldown until" type="datetime-local" />
            </div>
            <Button type="submit" disabled={busy}>
              Save changes
            </Button>
          </form>
          <Separator />
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold">Credentials</h3>
            <CredentialAddDialog disabled={busy} onCreate={(payload) => onAddCredential(account.id, payload)} />
          </div>
          <div className="space-y-2">
            {account.credentials.map((credential) => (
              <div key={credential.id} className="flex items-center justify-between gap-3 rounded-lg border p-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{credential.name ?? credential.id}</p>
                  <p className="truncate text-xs text-muted-foreground">{credential.id}</p>
                </div>
                <Select
                  value={credential.status}
                  onValueChange={(value) => {
                    const nextStatus = credentialStatusFromValue(value);
                    if (nextStatus) void onUpdateCredential(account.id, credential.id, { status: nextStatus });
                  }}
                >
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CREDENTIAL_STATUSES.map((item) => (
                      <SelectItem key={item} value={item}>
                        {item}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ))}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function Info({ label, value }: { readonly label: string; readonly value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className="truncate font-medium">{value}</span>
    </div>
  );
}

function Field(props: React.ComponentProps<typeof Input> & { readonly label: string; readonly name: string }) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={`account-${props.name}`}>{props.label}</Label>
      <Input id={`account-${props.name}`} type="number" min="0" {...props} />
    </div>
  );
}
