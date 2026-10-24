import { readFileSync, existsSync } from "node:fs";
import { createBot, makeNotifier } from "./bot.js";
import { LeadStore } from "./db.js";
import { buildServer } from "./server.js";

// Minimal .env loader, so the project has no extra dependency for it.
if (existsSync(".env")) {
  for (const line of readFileSync(".env", "utf8").split(/\r?\n/)) {
    const m = /^\s*([A-Z_]+)\s*=\s*(.*)\s*$/.exec(line);
    if (m && !(m[1] in process.env)) process.env[m[1]] = m[2];
  }
}

const need = (k: string): string => {
  const v = process.env[k];
  if (!v) throw new Error(`Missing ${k} in .env (see .env.example)`);
  return v;
};

const store = new LeadStore(process.env.DB_PATH ?? "leads.db");
const chatId = need("CHAT_ID");
const bot = createBot(need("BOT_TOKEN"), store, chatId);
const app = buildServer({ store, notify: makeNotifier(bot, chatId), secret: need("WEBHOOK_SECRET") });

const port = Number(process.env.PORT ?? 3000);
await app.listen({ port, host: "0.0.0.0" });
console.log(`API on :${port}  (POST /leads, GET /health)`);
bot.start({ onStart: (me) => console.log(`Bot @${me.username} is running`) });

const stop = async () => {
  await bot.stop();
  await app.close();
  store.close();
  process.exit(0);
};
process.once("SIGINT", stop);
process.once("SIGTERM", stop);
