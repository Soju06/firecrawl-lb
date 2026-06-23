import { z } from "zod";

export const AccountStatusSchema = z.enum(["active", "rate_limited", "credit_exhausted", "paused", "invalid"]);
export const CredentialStatusSchema = z.enum(["active", "paused", "invalid"]);
export const JobEndpointSchema = z.enum(["crawl", "batch_scrape"]);
export const SyncEndpointSchema = z.enum(["scrape", "map", "search"]);

export const FirecrawlCredentialSchema = z.object({
  id: z.string(),
  name: z.string().nullable(),
  status: CredentialStatusSchema,
});

export const FirecrawlAccountSchema = z.object({
  id: z.string(),
  team_label: z.string(),
  plan_type: z.string(),
  status: AccountStatusSchema,
  monthly_budget_credits: z.number().int().nullable(),
  remaining_credits_live: z.number().int().nullable(),
  plan_credits_live: z.number().int().nullable(),
  rpm_limit: z.number().int().nullable(),
  max_concurrency: z.number().int().nullable(),
  cooldown_until: z.string().nullable(),
  credentials: z.array(FirecrawlCredentialSchema),
});

export const FirecrawlAccountsResponseSchema = z.object({
  accounts: z.array(FirecrawlAccountSchema),
});

export const FirecrawlAccountCreateRequestSchema = z.object({
  id: z.string().trim().min(1),
  team_label: z.string().trim().min(1),
  plan_type: z.string().trim().min(1),
  monthly_budget_credits: z.number().int().min(0).nullable(),
  remaining_credits_live: z.number().int().min(0).nullable(),
  plan_credits_live: z.number().int().min(0).nullable(),
  rpm_limit: z.number().int().min(1).nullable(),
  max_concurrency: z.number().int().min(1).nullable(),
});

export const FirecrawlAccountUpdateRequestSchema = z.object({
  status: AccountStatusSchema.optional(),
  monthly_budget_credits: z.number().int().min(0).nullable().optional(),
  remaining_credits_live: z.number().int().min(0).nullable().optional(),
  plan_credits_live: z.number().int().min(0).nullable().optional(),
  rpm_limit: z.number().int().min(1).nullable().optional(),
  max_concurrency: z.number().int().min(1).nullable().optional(),
  cooldown_until: z.string().nullable().optional(),
});

export const FirecrawlCredentialCreateRequestSchema = z.object({
  id: z.string().trim().min(1),
  name: z.string().trim().min(1).nullable(),
  api_key: z.string().min(1),
});

export const FirecrawlCredentialUpdateRequestSchema = z.object({
  status: CredentialStatusSchema,
});

export const FirecrawlJobSchema = z.object({
  id: z.number().int(),
  account_id: z.string().nullable(),
  credential_id: z.string().nullable(),
  endpoint: JobEndpointSchema,
  upstream_job_id: z.string().nullable(),
  status: z.string(),
  estimated_credits_reserved: z.number().int().nullable(),
  credits_used_final: z.number().int().nullable(),
  created_at: z.string(),
  completed_at: z.string().nullable(),
  last_polled_at: z.string().nullable(),
});

export const FirecrawlJobsResponseSchema = z.object({
  jobs: z.array(FirecrawlJobSchema),
});

export const FirecrawlRequestLogSchema = z.object({
  id: z.number().int(),
  account_id: z.string().nullable(),
  credential_id: z.string().nullable(),
  endpoint: SyncEndpointSchema,
  upstream_job_id: z.string().nullable(),
  status: z.string(),
  upstream_status_code: z.number().int().nullable(),
  estimated_credits_pre: z.number().int().nullable(),
  credits_used_final: z.number().int().nullable(),
  latency_ms: z.number().int().nullable(),
  error_code: z.string().nullable(),
  error_message: z.string().nullable(),
  created_at: z.string(),
});

export const FirecrawlRequestLogsResponseSchema = z.object({
  logs: z.array(FirecrawlRequestLogSchema),
});

export const FirecrawlOverviewSchema = z.object({
  total_accounts: z.number().int(),
  active_accounts: z.number().int(),
  total_remaining_credits: z.number().int(),
  total_budget_credits: z.number().int(),
  accounts_by_status: z.object({
    active: z.number().int(),
    rate_limited: z.number().int(),
    credit_exhausted: z.number().int(),
    paused: z.number().int(),
  }),
  active_jobs: z.number().int(),
  recent_requests: z.object({
    total: z.number().int(),
    success: z.number().int(),
    error: z.number().int(),
  }),
  endpoint_breakdown: z.object({
    scrape: z.number().int(),
    map: z.number().int(),
    search: z.number().int(),
    crawl: z.number().int(),
    batch_scrape: z.number().int(),
  }),
});

export const FirecrawlRuntimeSettingsSchema = z.object({
  refresh_scheduler_enabled: z.boolean(),
  data_dir: z.string(),
  database_url_masked: z.string(),
  encryption_key_file: z.string(),
});

export type FirecrawlAccount = z.infer<typeof FirecrawlAccountSchema>;
export type FirecrawlAccountCreateRequest = z.infer<typeof FirecrawlAccountCreateRequestSchema>;
export type FirecrawlAccountUpdateRequest = z.infer<typeof FirecrawlAccountUpdateRequestSchema>;
export type FirecrawlCredential = z.infer<typeof FirecrawlCredentialSchema>;
export type FirecrawlCredentialCreateRequest = z.infer<typeof FirecrawlCredentialCreateRequestSchema>;
export type FirecrawlCredentialUpdateRequest = z.infer<typeof FirecrawlCredentialUpdateRequestSchema>;
export type FirecrawlJob = z.infer<typeof FirecrawlJobSchema>;
export type FirecrawlOverview = z.infer<typeof FirecrawlOverviewSchema>;
export type FirecrawlRequestLog = z.infer<typeof FirecrawlRequestLogSchema>;
export type FirecrawlRuntimeSettings = z.infer<typeof FirecrawlRuntimeSettingsSchema>;
export type JobEndpoint = z.infer<typeof JobEndpointSchema>;
export type SyncEndpoint = z.infer<typeof SyncEndpointSchema>;
