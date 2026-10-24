import { InlineKeyboard } from "grammy";
import type { Lead, Status } from "./schema.js";

const LABEL: Record<Status, string> = {
  new: "🆕 New",
  in_progress: "⏳ In progress",
  done: "✅ Done",
  spam: "🚫 Spam",
};

export const escapeHtml = (s: string): string =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

/** Telegram message text (HTML parse mode) for a lead. */
export function formatLead(l: Lead): string {
  const lines = [`<b>Lead #${l.id}</b> · ${LABEL[l.status]}`, `👤 ${escapeHtml(l.name)}`];
  if (l.phone) lines.push(`📞 <code>${escapeHtml(l.phone)}</code>`);
  if (l.email) lines.push(`✉️ ${escapeHtml(l.email)}`);
  if (l.message) lines.push(`💬 ${escapeHtml(l.message)}`);
  lines.push(`🔗 ${escapeHtml(l.source)} · ${l.createdAt} UTC`);
  if (l.updatedBy && l.status !== "new") lines.push(`👷 ${escapeHtml(l.updatedBy)}`);
  return lines.join("\n");
}

/** Buttons for the next possible statuses. Callback data: "st:<id>:<status>". */
export function leadKeyboard(l: Lead): InlineKeyboard {
  const kb = new InlineKeyboard();
  const next: Status[] =
    l.status === "new" ? ["in_progress", "spam"] : l.status === "in_progress" ? ["done", "new"] : ["new"];
  for (const s of next) kb.text(LABEL[s], `st:${l.id}:${s}`);
  return kb;
}

export function parseCallback(data: string): { id: number; status: Status } | null {
  const m = /^st:(\d+):(new|in_progress|done|spam)$/.exec(data);
  return m ? { id: Number(m[1]), status: m[2] as Status } : null;
}

export function formatStats(s: Record<Status, number>): string {
  const total = Object.values(s).reduce((a, b) => a + b, 0);
  return [`<b>Leads: ${total}</b>`, ...Object.entries(s).map(([k, n]) => `${LABEL[k as Status]}: ${n}`)].join("\n");
}
