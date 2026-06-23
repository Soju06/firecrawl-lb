import { useMemo, useState } from "react";
import { Boxes } from "lucide-react";

import { AlertMessage } from "@/components/alert-message";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { creditPercent } from "@/features/firecrawl/account-utils";
import { AccountCard, AccountStatusBadge } from "@/features/firecrawl/components/account-card";
import { AccountCreateDialog } from "@/features/firecrawl/components/account-create-dialog";
import { AccountDetailPanel } from "@/features/firecrawl/components/account-detail-panel";
import { useFirecrawlAccounts } from "@/features/firecrawl/hooks/use-accounts";
import type { FirecrawlAccount } from "@/features/firecrawl/schemas";
import { getErrorMessageOrNull } from "@/utils/errors";

export function FirecrawlAccountsPage() {
  const {
    accountsQuery,
    createAccountMutation,
    updateAccountMutation,
    addCredentialMutation,
    updateCredentialMutation,
  } = useFirecrawlAccounts();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const accounts = useMemo(() => accountsQuery.data ?? [], [accountsQuery.data]);
  const selectedAccount = useMemo(
    () => accounts.find((account) => account.id === selectedId) ?? null,
    [accounts, selectedId],
  );
  const busy =
    createAccountMutation.isPending ||
    updateAccountMutation.isPending ||
    addCredentialMutation.isPending ||
    updateCredentialMutation.isPending;
  const error =
    getErrorMessageOrNull(accountsQuery.error) ||
    getErrorMessageOrNull(createAccountMutation.error) ||
    getErrorMessageOrNull(updateAccountMutation.error) ||
    getErrorMessageOrNull(addCredentialMutation.error) ||
    getErrorMessageOrNull(updateCredentialMutation.error);
  return (
    <div className="animate-fade-in-up space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold">
            <Boxes className="h-5 w-5 text-primary" aria-hidden="true" />
            Accounts
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">Firecrawl teams, budgets, limits, and credentials.</p>
        </div>
        <AccountCreateDialog
          disabled={busy}
          onCreate={async (payload) => {
            await createAccountMutation.mutateAsync(payload);
          }}
        />
      </div>
      {error ? <AlertMessage variant="error">{error}</AlertMessage> : null}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {accounts.map((account) => (
          <button key={account.id} type="button" className="text-left" onClick={() => setSelectedId(account.id)}>
            <AccountCard account={account} />
          </button>
        ))}
      </div>
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Account</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Credits</TableHead>
                <TableHead>RPM</TableHead>
                <TableHead>Concurrency</TableHead>
                <TableHead>Cooldown</TableHead>
                <TableHead>Credentials</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {accounts.map((account) => (
                <AccountRow key={account.id} account={account} onSelect={() => setSelectedId(account.id)} />
              ))}
              {accounts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">
                    No Firecrawl accounts configured.
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      <AccountDetailPanel
        account={selectedAccount}
        open={selectedAccount !== null}
        busy={busy}
        onOpenChange={(open) => {
          if (!open) setSelectedId(null);
        }}
        onUpdateAccount={async (accountId, payload) => {
          await updateAccountMutation.mutateAsync({ accountId, payload });
        }}
        onAddCredential={async (accountId, payload) => {
          await addCredentialMutation.mutateAsync({ accountId, payload });
        }}
        onUpdateCredential={async (accountId, credentialId, payload) => {
          await updateCredentialMutation.mutateAsync({ accountId, credentialId, payload });
        }}
      />
    </div>
  );
}

function AccountRow({ account, onSelect }: { readonly account: FirecrawlAccount; readonly onSelect: () => void }) {
  const budget = account.monthly_budget_credits ?? account.plan_credits_live ?? 0;
  return (
    <TableRow>
      <TableCell>
        <div className="min-w-40">
          <p className="font-medium">{account.team_label}</p>
          <p className="text-xs text-muted-foreground">{account.id}</p>
        </div>
      </TableCell>
      <TableCell>
        <AccountStatusBadge status={account.status} />
      </TableCell>
      <TableCell>
        <div className="min-w-40 space-y-1">
          <div className="text-xs">
            {(account.remaining_credits_live ?? 0).toLocaleString()} / {budget.toLocaleString()}
          </div>
          <Progress value={creditPercent(account)} />
        </div>
      </TableCell>
      <TableCell>{account.rpm_limit ?? "None"}</TableCell>
      <TableCell>{account.max_concurrency ?? "None"}</TableCell>
      <TableCell>{account.cooldown_until ?? "None"}</TableCell>
      <TableCell>{account.credentials.length}</TableCell>
      <TableCell>
        <Button size="sm" variant="outline" onClick={onSelect}>
          Details
        </Button>
      </TableCell>
    </TableRow>
  );
}
