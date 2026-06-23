import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { FirecrawlAccountCreateRequest } from "@/features/firecrawl/schemas";

function nullableNumber(form: FormData, key: string): number | null {
  const value = String(form.get(key) ?? "").trim();
  return value ? Number(value) : null;
}

export function AccountCreateDialog({
  disabled,
  onCreate,
}: {
  readonly disabled?: boolean;
  readonly onCreate: (payload: FirecrawlAccountCreateRequest) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload: FirecrawlAccountCreateRequest = {
      id: String(form.get("id") ?? "").trim(),
      team_label: String(form.get("team_label") ?? "").trim(),
      plan_type: String(form.get("plan_type") ?? "unknown").trim(),
      monthly_budget_credits: nullableNumber(form, "monthly_budget_credits"),
      remaining_credits_live: nullableNumber(form, "remaining_credits_live"),
      plan_credits_live: nullableNumber(form, "plan_credits_live"),
      rpm_limit: nullableNumber(form, "rpm_limit"),
      max_concurrency: nullableNumber(form, "max_concurrency"),
    };
    setSubmitting(true);
    void onCreate(payload)
      .then(() => setOpen(false))
      .finally(() => setSubmitting(false));
  };
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button disabled={disabled}>Create account</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Firecrawl account</DialogTitle>
        </DialogHeader>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field name="id" label="Account ID" required />
            <Field name="team_label" label="Team label" required />
            <Field name="plan_type" label="Plan type" defaultValue="unknown" required />
            <Field name="monthly_budget_credits" label="Monthly budget" type="number" min="0" />
            <Field name="remaining_credits_live" label="Remaining credits" type="number" min="0" />
            <Field name="plan_credits_live" label="Plan credits live" type="number" min="0" />
            <Field name="rpm_limit" label="RPM limit" type="number" min="1" />
            <Field name="max_concurrency" label="Max concurrency" type="number" min="1" />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              Save account
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function Field(props: React.ComponentProps<typeof Input> & { readonly label: string; readonly name: string }) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={props.name}>{props.label}</Label>
      <Input id={props.name} {...props} />
    </div>
  );
}
