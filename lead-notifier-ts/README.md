# Lead Notifier (TypeScript)

Website form leads go straight to your team's Telegram chat, with buttons to take them into work.

```
Website form / Tally / Webflow ──POST /leads──▶ Fastify API ──▶ SQLite
                                                    │
                                                    ▼
                                    Telegram group: "Lead #12 · 🆕 New"
                                    [⏳ In progress] [🚫 Spam]
```

**What it does**

- `POST /leads` accepts a lead (name, phone or email, message, source), validates it with zod and normalizes the phone and email.
- The lead is saved to SQLite first and then posted to Telegram, so a Telegram outage never loses a lead (the API answers `202`).
- Each lead gets status buttons: New → In progress → Done, or Spam. The message updates in place and shows who took it.
- `/stats` in the chat shows totals by status.
- Duplicate protection: the same phone or email within 10 minutes is ignored (double clicks on the submit button).
- Security: shared secret in the `X-Webhook-Secret` header (timing-safe check), HTML escaping of user input, 16 KB body limit, the bot answers only in the configured chat.

**Stack:** Node.js 20+, TypeScript, Fastify 5, grammY, zod, better-sqlite3, Vitest.

## Run

```bash
npm install
cp .env.example .env   # fill BOT_TOKEN, CHAT_ID, WEBHOOK_SECRET
npm start
```

Send a test lead:

```bash
curl -X POST http://localhost:3000/leads \
  -H "Content-Type: application/json" -H "X-Webhook-Secret: change-me" \
  -d '{"name":"Anna","phone":"+380 93 123 45 67","message":"Need a quote","source":"landing"}'
```

From a plain HTML form:

```html
<script>
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    await fetch("https://your-server/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Webhook-Secret": "change-me" },
      body: JSON.stringify(Object.fromEntries(new FormData(form))),
    });
  });
</script>
```

For a public site, put the call behind your own backend or a serverless function so the secret is not exposed in the browser.

## Tests

```bash
npm test        # 8 tests: validation, API, duplicates, Telegram outage, HTML escaping, status flow
npm run typecheck
```

| Response | Meaning |
|---|---|
| `201` | saved and posted to Telegram |
| `202` | saved, Telegram unavailable |
| `200 {duplicate:true}` | same contact within 10 minutes, ignored |
| `401` / `422` | wrong secret / invalid data |
