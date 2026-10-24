import { timingSafeEqual } from "node:crypto";
import Fastify, { type FastifyInstance } from "fastify";
import type { LeadStore } from "./db.js";
import { LeadInput, type Lead } from "./schema.js";

export interface ServerDeps {
  store: LeadStore;
  /** Sends the lead to Telegram. Injected so tests run without network. */
  notify: (lead: Lead) => Promise<void>;
  secret: string;
}

const safeEqual = (a: string, b: string): boolean => {
  const x = Buffer.from(a);
  const y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
};

export function buildServer({ store, notify, secret }: ServerDeps): FastifyInstance {
  const app = Fastify({ logger: false, bodyLimit: 16 * 1024 });

  app.get("/health", async () => ({ ok: true }));

  app.post("/leads", async (req, reply) => {
    const given = String(req.headers["x-webhook-secret"] ?? "");
    if (!secret || !safeEqual(given, secret)) return reply.code(401).send({ error: "bad secret" });

    const parsed = LeadInput.safeParse(req.body);
    if (!parsed.success) {
      return reply.code(422).send({ error: "invalid lead", issues: parsed.error.issues.map((i) => i.message) });
    }
    if (store.isDuplicate(parsed.data)) return reply.code(200).send({ ok: true, duplicate: true });

    const lead = store.add(parsed.data);
    try {
      await notify(lead);
    } catch (err) {
      // The lead is saved anyway; Telegram outage must not lose data.
      req.log.error(err, "telegram notify failed");
      return reply.code(202).send({ ok: true, id: lead.id, notified: false });
    }
    return reply.code(201).send({ ok: true, id: lead.id, notified: true });
  });

  return app;
}
