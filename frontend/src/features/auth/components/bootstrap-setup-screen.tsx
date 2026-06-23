import { Flame } from "lucide-react";

import { AlertMessage } from "@/components/alert-message";
import { PasswordSettings } from "@/features/settings/components/password-settings";
import { useAuthStore } from "@/features/auth/hooks/use-auth";

export function BootstrapSetupScreen() {
  const bootstrapTokenConfigured = useAuthStore((state) => state.bootstrapTokenConfigured);

  return (
    <div className="relative flex min-h-screen items-center justify-center p-4">
      <div className="relative w-full max-w-2xl space-y-6 animate-fade-in-up">
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-lg bg-primary/10 shadow-sm ring-2 ring-primary/10 ring-offset-2 ring-offset-background">
            <Flame className="h-7 w-7 text-orange-500" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Complete Remote Setup</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Remote dashboard access stays locked until an admin password is configured.
            </p>
          </div>
        </div>

        <div className="rounded-2xl border bg-card p-6 shadow-[var(--shadow-md)]">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Use the password setup flow below to bootstrap dashboard access before loading the rest of the admin UI.
            </p>
            <AlertMessage variant="error">
              {bootstrapTokenConfigured
                ? "Enter the configured bootstrap token below with your new password. Depending on your setup, it may come from your server logs or FIRECRAWL_LB_DASHBOARD_BOOTSTRAP_TOKEN."
                : "Remote setup is blocked. Set FIRECRAWL_LB_DASHBOARD_BOOTSTRAP_TOKEN on the server or restart without a password to auto-generate one."}
            </AlertMessage>
          </div>
        </div>

        <PasswordSettings />
      </div>
    </div>
  );
}
