import { del, get, patch, post } from "@/lib/api-client";
import {
  FirecrawlAccountCreateRequestSchema,
  FirecrawlAccountSchema,
  FirecrawlAccountsResponseSchema,
  FirecrawlAccountUpdateRequestSchema,
  FirecrawlCredentialCreateRequestSchema,
  FirecrawlCredentialSchema,
  FirecrawlCredentialUpdateRequestSchema,
  FirecrawlJobsResponseSchema,
  FirecrawlOverviewSchema,
  FirecrawlRequestLogsResponseSchema,
  FirecrawlRuntimeSettingsSchema,
  type FirecrawlAccountCreateRequest,
  type FirecrawlAccountUpdateRequest,
  type FirecrawlCredentialCreateRequest,
  type FirecrawlCredentialUpdateRequest,
  type JobEndpoint,
  type SyncEndpoint,
} from "@/features/firecrawl/schemas";

const ADMIN_PATH = "/v2/admin/firecrawl";

type ListQuery<TEndpoint extends string> = {
  readonly endpoint?: TEndpoint | "all";
  readonly status?: string;
  readonly limit?: number;
  readonly offset?: number;
};

function queryString<TEndpoint extends string>(query: ListQuery<TEndpoint>): string {
  const params = new URLSearchParams();
  if (query.endpoint && query.endpoint !== "all") params.set("endpoint", query.endpoint);
  if (query.status && query.status !== "all") params.set("status", query.status);
  if (query.limit !== undefined) params.set("limit", String(query.limit));
  if (query.offset !== undefined) params.set("offset", String(query.offset));
  const serialized = params.toString();
  return serialized ? `?${serialized}` : "";
}

export function getFirecrawlOverview() {
  return get(`${ADMIN_PATH}/overview`, FirecrawlOverviewSchema);
}

export function listFirecrawlAccounts() {
  return get(`${ADMIN_PATH}/accounts`, FirecrawlAccountsResponseSchema);
}

export function createFirecrawlAccount(payload: FirecrawlAccountCreateRequest) {
  const validated = FirecrawlAccountCreateRequestSchema.parse(payload);
  return post(`${ADMIN_PATH}/accounts`, FirecrawlAccountSchema, { body: validated });
}

export function updateFirecrawlAccount(accountId: string, payload: FirecrawlAccountUpdateRequest) {
  const validated = FirecrawlAccountUpdateRequestSchema.parse(payload);
  return patch(`${ADMIN_PATH}/accounts/${encodeURIComponent(accountId)}`, FirecrawlAccountSchema, {
    body: validated,
  });
}

export function addFirecrawlCredential(accountId: string, payload: FirecrawlCredentialCreateRequest) {
  const validated = FirecrawlCredentialCreateRequestSchema.parse(payload);
  return post(`${ADMIN_PATH}/accounts/${encodeURIComponent(accountId)}/credentials`, FirecrawlCredentialSchema, {
    body: validated,
  });
}

export function updateFirecrawlCredential(
  accountId: string,
  credentialId: string,
  payload: FirecrawlCredentialUpdateRequest,
) {
  const validated = FirecrawlCredentialUpdateRequestSchema.parse(payload);
  return patch(
    `${ADMIN_PATH}/accounts/${encodeURIComponent(accountId)}/credentials/${encodeURIComponent(credentialId)}`,
    FirecrawlCredentialSchema,
    { body: validated },
  );
}

export function listFirecrawlJobs(query: ListQuery<JobEndpoint>) {
  return get(`${ADMIN_PATH}/jobs${queryString(query)}`, FirecrawlJobsResponseSchema);
}

export function listFirecrawlLogs(query: ListQuery<SyncEndpoint>) {
  return get(`${ADMIN_PATH}/logs${queryString(query)}`, FirecrawlRequestLogsResponseSchema);
}

export function cancelFirecrawlJob(endpoint: JobEndpoint, upstreamJobId: string) {
  const path = endpoint === "crawl" ? "/v2/crawl" : "/v2/batch/scrape";
  return del(`${path}/${encodeURIComponent(upstreamJobId)}`);
}

export function getFirecrawlRuntimeSettings() {
  return get("/api/settings/firecrawl-runtime", FirecrawlRuntimeSettingsSchema);
}
