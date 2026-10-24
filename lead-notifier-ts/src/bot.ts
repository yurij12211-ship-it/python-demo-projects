import { Bot } from "grammy";
import type { LeadStore } from "./db.js";
import { formatLead, formatStats, leadKeyboard, parseCallback } from "./format.js";
import type { Lead } from "./schema.js";

/** Pure status-change logic, separated from Telegram so it is unit-testable. */
export function applyStatusChange(store: LeadStore, data: string, by: string): { lead?: Lead; answer: string } {
  const cb = parseCallback(data);
  if (!cb) return { answer: "Unknown action" };
  const lead = store.get(cb.id);
  if (!lead) return { answer: "Lead not found" };
  if (!store.setStatus(cb.id, cb.status, by)) return { lead, answer: "Already set" };
  return { lead: store.get(cb.id), answer: "Updated" };
}

export function createBot(token: string, store: LeadStore, chatId: string): Bot {
  const bot = new Bot(token);

  // Only the configured team chat can use the bot.
  bot.use(async (ctx, next) => {
    if (String(ctx.chat?.id) === chatId) await next();
  });

  bot.command("start", (ctx) =>
    ctx.reply("I post new website leads here. Tap the buttons to change status. /stats shows the totals."),
  );
  bot.command("stats", (ctx) => ctx.reply(formatStats(store.stats()), { parse_mode: "HTML" }));

  bot.on("callback_query:data", async (ctx) => {
    const by = ctx.from.username ? `@${ctx.from.username}` : ctx.from.first_name;
    const { lead, answer } = applyStatusChange(store, ctx.callbackQuery.data, by);
    await ctx.answerCallbackQuery({ text: answer });
    if (lead && answer === "Updated") {
      await ctx.editMessageText(formatLead(lead), { parse_mode: "HTML", reply_markup: leadKeyboard(lead) });
    }
  });

  bot.catch((err) => console.error("bot error:", err.error));
  return bot;
}

export const makeNotifier =
  (bot: Bot, chatId: string) =>
  async (lead: Lead): Promise<void> => {
    await bot.api.sendMessage(chatId, formatLead(lead), { parse_mode: "HTML", reply_markup: leadKeyboard(lead) });
  };
