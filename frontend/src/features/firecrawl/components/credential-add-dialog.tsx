import { KeyRound } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { FirecrawlCredentialCreateRequest } from "@/features/firecrawl/schemas";

export function CredentialAddDialog({
  disabled,
  onCreate,
}: {
  readonly disabled?: boolean;
  readonly onCreate: (payload: FirecrawlCredentialCreateRequest) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") ?? "").trim();
    const payload: FirecrawlCredentialCreateRequest = {
      id: String(form.get("id") ?? "").trim(),
      name: name || null,
      api_key: String(form.get("api_key") ?? ""),
    };
    setSubmitting(true);
    void onCreate(payload)
      .then(() => setOpen(false))
      .finally(() => setSubmitting(false));
  };
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline" disabled={disabled}>
          <KeyRound className="h-3.5 w-3.5" aria-hidden="true" />
          Add credential
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add credential</DialogTitle>
        </DialogHeader>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="credential-id">Credential ID</Label>
              <Input id="credential-id" name="id" required />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="credential-name">Name</Label>
              <Input id="credential-name" name="name" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="credential-api-key">API key</Label>
              <Input id="credential-api-key" name="api_key" type="password" required autoComplete="off" />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              Save credential
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
