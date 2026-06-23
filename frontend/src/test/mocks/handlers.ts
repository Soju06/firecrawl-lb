import { HttpResponse, http } from "msw";

const now = "2026-06-23T12:00:00Z";

const authSession = {
  authenticated: true,
  passwordRequired: false,
  totpRequiredOnLogin: false,
  totpConfigured: false,
  bootstrapRequired: false,
  bootstrapTokenConfigured: false,
  authMode: "standard",
  passwordManagementEnabled: true,
  passwordSessionActive: false,
};

const primaryFirecrawlAccount = {
  id: "team-primary",
  team_label: "Primary Firecrawl",
  plan_type: "growth",
  status: "active",
  monthly_budget_credits: 100_000,
  remaining_credits_live: 72_500,
  plan_credits_live: 100_000,
  rpm_limit: 120,
  max_concurrency: 8,
  cooldown_until: null,
  credentials: [{ id: "cred-primary", name: "Primary key", status: "active" }],
};

const firecrawlAccounts = [
  primaryFirecrawlAccount,
  {
    id: "team-secondary",
    team_label: "Secondary Firecrawl",
    plan_type: "starter",
    status: "paused",
    monthly_budget_credits: 25_000,
    remaining_credits_live: 18_000,
    plan_credits_live: 25_000,
    rpm_limit: 60,
    max_concurrency: 4,
    cooldown_until: null,
    credentials: [{ id: "cred-secondary", name: "Backup key", status: "paused" }],
  },
] as const;

export function resetMockState(): void {}

export const handlers = [
  http.get("/api/dashboard-auth/session", () => HttpResponse.json(authSession)),
  http.post("/api/dashboard-auth/password/setup", () =>
    HttpResponse.json({ ...authSession, authenticated: true, passwordRequired: true, passwordSessionActive: true }),
  ),
  http.post("/api/dashboard-auth/password/login", () =>
    HttpResponse.json({ ...authSession, authenticated: true, passwordRequired: true, passwordSessionActive: true }),
  ),
  http.post("/api/dashboard-auth/password/change", () => HttpResponse.json({ status: "ok" })),
  http.delete("/api/dashboard-auth/password", () => HttpResponse.json({ status: "ok" })),
  http.post("/api/dashboard-auth/totp/setup/start", () =>
    HttpResponse.json({
      secret: "JBSWY3DPEHPK3PXP",
      otpauthUri: "otpauth://totp/firecrawl-lb?secret=JBSWY3DPEHPK3PXP",
      qrSvgDataUri: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'/%3E",
    }),
  ),
  http.post("/api/dashboard-auth/totp/setup/confirm", () => HttpResponse.json({ status: "ok" })),
  http.post("/api/dashboard-auth/totp/verify", () =>
    HttpResponse.json({ ...authSession, authenticated: true, passwordRequired: true, passwordSessionActive: true }),
  ),
  http.post("/api/dashboard-auth/totp/disable", () => HttpResponse.json({ status: "ok" })),
  http.post("/api/dashboard-auth/logout", () => HttpResponse.json({ status: "ok" })),

  http.get("/api/runtime/version", () =>
    HttpResponse.json({
      currentVersion: "0.1.0",
      latestVersion: null,
      updateAvailable: false,
      checkedAt: now,
      source: "mock",
      releaseUrl: "https://github.com/Soju06/firecrawl-lb/releases/latest",
    }),
  ),
  http.get("/api/settings/firecrawl-runtime", () =>
    HttpResponse.json({
      refresh_scheduler_enabled: true,
      data_dir: "/tmp/firecrawl-lb",
      database_url_masked: "sqlite+aiosqlite:////tmp/firecrawl-lb/store.db",
      encryption_key_file: "/tmp/firecrawl-lb/encryption.key",
    }),
  ),

  http.get("/v2/admin/firecrawl/accounts", () => HttpResponse.json({ accounts: firecrawlAccounts })),
  http.post("/v2/admin/firecrawl/accounts", () =>
    HttpResponse.json({
      id: "team-new",
      team_label: "New Firecrawl",
      plan_type: "starter",
      status: "active",
      monthly_budget_credits: null,
      remaining_credits_live: null,
      plan_credits_live: null,
      rpm_limit: null,
      max_concurrency: null,
      cooldown_until: null,
      credentials: [],
    }),
  ),
  http.patch("/v2/admin/firecrawl/accounts/:accountId", ({ params }) =>
    HttpResponse.json({ ...primaryFirecrawlAccount, id: String(params.accountId) }),
  ),
  http.post("/v2/admin/firecrawl/accounts/:accountId/credentials", ({ params }) =>
    HttpResponse.json({ id: `${String(params.accountId)}-credential`, name: "New key", status: "active" }),
  ),
  http.patch("/v2/admin/firecrawl/accounts/:accountId/credentials/:credentialId", ({ params }) =>
    HttpResponse.json({ id: String(params.credentialId), name: "Updated key", status: "active" }),
  ),
  http.get("/v2/admin/firecrawl/overview", () =>
    HttpResponse.json({
      total_accounts: 2,
      active_accounts: 1,
      total_remaining_credits: 90_500,
      total_budget_credits: 125_000,
      accounts_by_status: { active: 1, rate_limited: 0, credit_exhausted: 0, paused: 1 },
      active_jobs: 1,
      recent_requests: { total: 12, success: 10, error: 2 },
      endpoint_breakdown: { scrape: 7, map: 3, search: 2, crawl: 1, batch_scrape: 0 },
    }),
  ),
  http.get("/v2/admin/firecrawl/jobs", () =>
    HttpResponse.json({
      jobs: [
        {
          id: 1,
          account_id: "team-primary",
          credential_id: "cred-primary",
          endpoint: "crawl",
          upstream_job_id: "crawl-123",
          status: "running",
          estimated_credits_reserved: 25,
          credits_used_final: null,
          created_at: now,
          completed_at: null,
          last_polled_at: now,
        },
      ],
    }),
  ),
  http.post("/v2/admin/firecrawl/jobs/:endpoint/:upstreamJobId/cancel", () => HttpResponse.json({ status: "cancelled" })),
  http.get("/v2/admin/firecrawl/logs", () =>
    HttpResponse.json({
      logs: [
        {
          id: 1,
          account_id: "team-primary",
          credential_id: "cred-primary",
          endpoint: "scrape",
          upstream_job_id: null,
          status: "success",
          upstream_status_code: 200,
          estimated_credits_pre: 1,
          credits_used_final: 1,
          latency_ms: 420,
          error_code: null,
          error_message: null,
          created_at: now,
        },
      ],
    }),
  ),
];
