import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { applyStatusChange } from "../src/bot.js";
import { LeadStore } from "../src/db.js";
import { formatLead, leadKeyboard, parseCallback } from "../src/format.js";
import { LeadInput, normalizePhone, type Lead } from "../src/schema.js";
import { buildServer } from "../src/server.js";

const SECRET = "s3cret";
let store: LeadStore;
let sent: Lead[];
let failNotify: boolean;

beforeEach(() => {
  store = new LeadStore(":memory:");
  sent = [];
  failNotify = false;
});
afterEach(() => store.close());

const app = () =>
  buildServer({
    store,
    secret: SECRET,
    notify: async (l) => {
      if (failNotify) throw new Error("telegram down");
      sent.push(l);
    },
  });

const post = (body: unknown, secret = SECRET) =>
  app().inject({ method: "POST", url: "/leads", headers: { "x-webhook-secret": secret }, payload: body as object });

describe("schema", () => {
  it("normalizes phone and email", () => {
    expect(normalizePhone(" +38 (093) 123-45-67 ")).toBe("+380931234567");
    const l = LeadInput.parse({ name: " Anna ", email: "Anna@Mail.COM " });
    expect(l).toMatchObject({ name: "Anna", email: "anna@mail.com", source: "website" });
  });

  it("requires phone or email and rejects short phones", () => {
    expect(LeadInput.safeParse({ name: "A" }).success).toBe(false);
    expect(LeadInput.safeParse({ name: "A", phone: "123" }).success).toBe(false);
  });
});

describe("POST /leads", () => {
  it("saves a lead and notifies Telegram", async () => {
    const res = await post({ name: "Ivan", phone: "+380 93 111 22 33", message: "Need a quote" });
    expect(res.statusCode).toBe(201);
    expect(res.json()).toMatchObject({ ok: true, id: 1, notified: true });
    expect(sent[0]).toMatchObject({ name: "Ivan", phone: "+380931112233", status: "new" });
  });

  it("rejects a wrong secret and invalid payloads", async () => {
    expect((await post({ name: "X", phone: "+380931112233" }, "nope")).statusCode).toBe(401);
    const bad = await post({ name: "" });
    expect(bad.statusCode).toBe(422);
    expect(sent).toHaveLength(0);
  });

  it("ignores a duplicate sent twice in a row", async () => {
    await post({ name: "Ivan", email: "i@x.com" });
    const again = await post({ name: "Ivan", email: "I@X.com" });
    expect(again.json()).toMatchObject({ duplicate: true });
    expect(sent).toHaveLength(1);
  });

  it("keeps the lead when Telegram is down", async () => {
    failNotify = true;
    const res = await post({ name: "Olha", email: "o@x.com" });
    expect(res.statusCode).toBe(202);
    expect(store.get(1)?.name).toBe("Olha");
  });
});

describe("telegram formatting and buttons", () => {
  it("escapes HTML from user input", () => {
    const lead = store.add(LeadInput.parse({ name: "<b>Hacker</b>", email: "h@x.com" }));
    expect(formatLead(lead)).toContain("&lt;b&gt;Hacker&lt;/b&gt;");
  });

  it("moves a lead through statuses", () => {
    const lead = store.add(LeadInput.parse({ name: "Ivan", email: "i@x.com" }));
    const buttons = leadKeyboard(lead).inline_keyboard.flat().map((b) => ("callback_data" in b ? b.callback_data : ""));
    expect(buttons).toEqual(["st:1:in_progress", "st:1:spam"]);

    const r = applyStatusChange(store, "st:1:in_progress", "@manager");
    expect(r.answer).toBe("Updated");
    expect(r.lead).toMatchObject({ status: "in_progress", updatedBy: "@manager" });
    expect(applyStatusChange(store, "st:1:in_progress", "@other").answer).toBe("Already set");
    expect(applyStatusChange(store, "st:99:done", "@m").answer).toBe("Lead not found");
    expect(parseCallback("st:1:hack")).toBeNull();
    expect(store.stats()).toMatchObject({ in_progress: 1, new: 0 });
  });
});
