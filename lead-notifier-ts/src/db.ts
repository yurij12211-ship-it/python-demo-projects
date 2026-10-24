import Database from "better-sqlite3";
import type { Lead, LeadInput, Status } from "./schema.js";

interface Row {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  message: string | null;
  source: string;
  status: Status;
  created_at: string;
  updated_by: string | null;
}

const toLead = (r: Row): Lead => ({
  id: r.id,
  name: r.name,
  phone: r.phone ?? undefined,
  email: r.email ?? undefined,
  message: r.message ?? undefined,
  source: r.source,
  status: r.status,
  createdAt: r.created_at,
  updatedBy: r.updated_by,
});

export class LeadStore {
  private db: Database.Database;

  constructor(path = "leads.db") {
    this.db = new Database(path);
    this.db.pragma("journal_mode = WAL");
    this.db.exec(`CREATE TABLE IF NOT EXISTS leads (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      phone TEXT,
      email TEXT,
      message TEXT,
      source TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'new',
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      updated_by TEXT
    )`);
  }

  add(l: LeadInput): Lead {
    const info = this.db
      .prepare("INSERT INTO leads (name, phone, email, message, source) VALUES (?, ?, ?, ?, ?)")
      .run(l.name, l.phone ?? null, l.email ?? null, l.message ?? null, l.source);
    return this.get(Number(info.lastInsertRowid))!;
  }

  get(id: number): Lead | undefined {
    const row = this.db.prepare("SELECT * FROM leads WHERE id = ?").get(id) as Row | undefined;
    return row && toLead(row);
  }

  /** Returns true if the status actually changed. */
  setStatus(id: number, status: Status, by: string): boolean {
    const info = this.db
      .prepare("UPDATE leads SET status = ?, updated_by = ? WHERE id = ? AND status != ?")
      .run(status, by, id, status);
    return info.changes > 0;
  }

  /** Duplicate guard: same phone or email within the last N minutes. */
  isDuplicate(l: LeadInput, minutes = 10): boolean {
    const row = this.db
      .prepare(
        `SELECT 1 FROM leads WHERE ((phone IS NOT NULL AND phone = ?) OR (email IS NOT NULL AND email = ?))
         AND created_at >= datetime('now', ?) LIMIT 1`,
      )
      .get(l.phone ?? null, l.email ?? null, `-${minutes} minutes`);
    return Boolean(row);
  }

  stats(): Record<Status, number> {
    const out: Record<Status, number> = { new: 0, in_progress: 0, done: 0, spam: 0 };
    const rows = this.db.prepare("SELECT status, COUNT(*) AS n FROM leads GROUP BY status").all() as {
      status: Status;
      n: number;
    }[];
    for (const r of rows) out[r.status] = r.n;
    return out;
  }

  close(): void {
    this.db.close();
  }
}
