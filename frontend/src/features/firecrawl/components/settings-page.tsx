import { useQuery } from "@tanstack/react-query";
import { Database, Folder, KeyRound, RefreshCw, Settings } from "lucide-react";

import { AlertMessage } from "@/components/alert-message";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getFirecrawlRuntimeSettings } from "@/features/firecrawl/api";
import { PasswordSettings } from "@/features/settings/components/password-settings";
import { getErrorMessageOrNull } from "@/utils/errors";

export function SettingsPage() {
  const runtimeQuery = useQuery({
    queryKey: ["firecrawl", "runtime-settings"],
    queryFn: getFirecrawlRuntimeSettings,
  });
  const runtime = runtimeQuery.data;
  const error = getErrorMessageOrNull(runtimeQuery.error);
  return (
    <div className="animate-fade-in-up space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <Settings className="h-5 w-5 text-primary" aria-hidden="true" />
          Settings
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">Firecrawl LB runtime and dashboard access.</p>
      </div>
      {error ? <AlertMessage variant="error">{error}</AlertMessage> : null}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Runtime</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3">
          <RuntimeRow
            icon={<RefreshCw className="h-4 w-4" aria-hidden="true" />}
            label="Refresh scheduler"
            value={
              <Badge variant="outline" className={runtime?.refresh_scheduler_enabled ? "border-emerald-500/30 bg-emerald-500/10" : ""}>
                {runtime?.refresh_scheduler_enabled ? "enabled" : "disabled"}
              </Badge>
            }
          />
          <RuntimeRow
            icon={<Folder className="h-4 w-4" aria-hidden="true" />}
            label="Data dir"
            value={runtime?.data_dir ?? "Loading"}
          />
          <RuntimeRow
            icon={<Database className="h-4 w-4" aria-hidden="true" />}
            label="Database URL"
            value={runtime?.database_url_masked ?? "Loading"}
          />
          <RuntimeRow
            icon={<KeyRound className="h-4 w-4" aria-hidden="true" />}
            label="Encryption key file"
            value={runtime?.encryption_key_file ?? "Loading"}
          />
        </CardContent>
      </Card>
      <PasswordSettings disabled={false} />
    </div>
  );
}

function RuntimeRow({
  icon,
  label,
  value,
}: {
  readonly icon: React.ReactNode;
  readonly label: string;
  readonly value: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border p-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-2 text-sm font-medium">
        <span className="text-muted-foreground">{icon}</span>
        {label}
      </div>
      <div className="break-all text-sm text-muted-foreground sm:text-right">{value}</div>
    </div>
  );
}
