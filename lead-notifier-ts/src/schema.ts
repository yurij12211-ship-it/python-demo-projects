import { z } from "zod";

/** Normalizes phone numbers: keeps digits and a leading +. */
export function normalizePhone(raw: string): string {
  const trimmed = raw.trim();
  const digits = trimmed.replace(/\D/g, "");
  return trimmed.startsWith("+") ? `+${digits}` : digits;
}

const phone = z
  .string()
  .transform(normalizePhone)
  .refine((p) => p.replace("+", "").length >= 9 && p.replace("+", "").length <= 15, {
    message: "phone must have 9-15 digits",
  });

/** Payload a website form (or Tally, Typeform, Webflow, etc.) sends to POST /leads. */
export const LeadInput = z
  .object({
    name: z.string().trim().min(1).max(100),
    phone: phone.optional(),
    email: z.string().trim().toLowerCase().email().optional(),
    message: z.string().trim().max(2000).optional(),
    source: z.string().trim().max(50).default("website"),
  })
  .refine((l) => l.phone || l.email, { message: "phone or email is required" });

export type LeadInput = z.infer<typeof LeadInput>;

export const STATUSES = ["new", "in_progress", "done", "spam"] as const;
export type Status = (typeof STATUSES)[number];

export interface Lead extends LeadInput {
  id: number;
  status: Status;
  createdAt: string;
  updatedBy: string | null;
}
