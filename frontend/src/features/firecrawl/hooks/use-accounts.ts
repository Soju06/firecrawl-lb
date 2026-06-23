import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  addFirecrawlCredential,
  createFirecrawlAccount,
  listFirecrawlAccounts,
  updateFirecrawlAccount,
  updateFirecrawlCredential,
} from "@/features/firecrawl/api";
import type {
  FirecrawlAccountCreateRequest,
  FirecrawlAccountUpdateRequest,
  FirecrawlCredentialCreateRequest,
  FirecrawlCredentialUpdateRequest,
} from "@/features/firecrawl/schemas";

export function useFirecrawlAccounts() {
  const queryClient = useQueryClient();
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["firecrawl", "accounts"] });
    void queryClient.invalidateQueries({ queryKey: ["firecrawl", "overview"] });
  };
  const accountsQuery = useQuery({
    queryKey: ["firecrawl", "accounts"],
    queryFn: listFirecrawlAccounts,
    select: (data) => data.accounts,
  });
  const createAccountMutation = useMutation({
    mutationFn: (payload: FirecrawlAccountCreateRequest) => createFirecrawlAccount(payload),
    onSuccess: () => {
      toast.success("Account created");
      invalidate();
    },
  });
  const updateAccountMutation = useMutation({
    mutationFn: ({ accountId, payload }: { readonly accountId: string; readonly payload: FirecrawlAccountUpdateRequest }) =>
      updateFirecrawlAccount(accountId, payload),
    onSuccess: () => {
      toast.success("Account updated");
      invalidate();
    },
  });
  const addCredentialMutation = useMutation({
    mutationFn: ({ accountId, payload }: { readonly accountId: string; readonly payload: FirecrawlCredentialCreateRequest }) =>
      addFirecrawlCredential(accountId, payload),
    onSuccess: () => {
      toast.success("Credential added");
      invalidate();
    },
  });
  const updateCredentialMutation = useMutation({
    mutationFn: ({
      accountId,
      credentialId,
      payload,
    }: {
      readonly accountId: string;
      readonly credentialId: string;
      readonly payload: FirecrawlCredentialUpdateRequest;
    }) => updateFirecrawlCredential(accountId, credentialId, payload),
    onSuccess: () => {
      toast.success("Credential updated");
      invalidate();
    },
  });
  return {
    accountsQuery,
    createAccountMutation,
    updateAccountMutation,
    addCredentialMutation,
    updateCredentialMutation,
  };
}
