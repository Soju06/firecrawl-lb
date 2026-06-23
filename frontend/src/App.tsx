import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { AppHeader } from "@/components/layout/app-header";
import { StatusBar } from "@/components/layout/status-bar";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthGate } from "@/features/auth/components/auth-gate";
import { useAuthStore } from "@/features/auth/hooks/use-auth";
import { FirecrawlAccountsPage } from "@/features/firecrawl/components/accounts-page";
import { JobsPage } from "@/features/firecrawl/components/jobs-page";
import { LogsPage } from "@/features/firecrawl/components/logs-page";
import { OverviewPage } from "@/features/firecrawl/components/overview-page";
import { SettingsPage } from "@/features/firecrawl/components/settings-page";
import { useTimeFormatStore } from "@/hooks/use-time-format";

function AppLayout() {
  const logout = useAuthStore((state) => state.logout);
  const passwordRequired = useAuthStore((state) => state.passwordRequired);
  const timeFormat = useTimeFormatStore((state) => state.timeFormat);

  return (
    <div className="flex min-h-screen flex-col bg-background pb-10" data-time-format={timeFormat}>
      <AppHeader
        onLogout={() => {
          void logout();
        }}
        showLogout={passwordRequired}
      />
      <main className="mx-auto w-full max-w-[1500px] flex-1 px-4 py-8 sm:px-6">
        <Outlet />
      </main>
      <StatusBar />
    </div>
  );
}

export default function App() {
  return (
    <TooltipProvider>
      <Toaster richColors />
      <AuthGate>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/overview" replace />} />
            <Route path="/overview" element={<OverviewPage />} />
            <Route path="/accounts" element={<FirecrawlAccountsPage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </AuthGate>
    </TooltipProvider>
  );
}
