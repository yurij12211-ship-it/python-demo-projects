"""SQLite: цінові алерти і гаманці, за якими стежимо."""
import json
import sqlite3


class Storage:
    def __init__(self, path: str = "crypto_bot.db"):
        self.db = sqlite3.connect(path)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS alerts(
            id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, coin_id TEXT,
            symbol TEXT, direction TEXT CHECK(direction IN ('above','below')), target REAL);
        CREATE TABLE IF NOT EXISTS watches(
            chat_id INTEGER, network TEXT, address TEXT, last TEXT,
            PRIMARY KEY(chat_id, network, address));
        """)

    # --- алерти
    def add_alert(self, chat_id, coin_id, symbol, direction, target) -> int:
        with self.db:
            cur = self.db.execute(
                "INSERT INTO alerts(chat_id, coin_id, symbol, direction, target) VALUES(?,?,?,?,?)",
                (chat_id, coin_id, symbol, direction, target))
        return cur.lastrowid

    def alerts(self, chat_id=None):
        q = "SELECT id, chat_id, coin_id, symbol, direction, target FROM alerts"
        rows = self.db.execute(q + (" WHERE chat_id=?" if chat_id else "") + " ORDER BY id",
                               (chat_id,) if chat_id else ()).fetchall()
        return rows

    def delete_alert(self, chat_id, alert_id) -> bool:
        with self.db:
            return self.db.execute("DELETE FROM alerts WHERE id=? AND chat_id=?",
                                   (alert_id, chat_id)).rowcount > 0

    # --- гаманці
    def add_watch(self, chat_id, network, address, snapshot: dict) -> bool:
        with self.db:
            return self.db.execute(
                "INSERT OR IGNORE INTO watches VALUES(?,?,?,?)",
                (chat_id, network, address, json.dumps(snapshot))).rowcount > 0

    def watches(self, chat_id=None):
        q = "SELECT chat_id, network, address, last FROM watches"
        rows = self.db.execute(q + (" WHERE chat_id=?" if chat_id else ""),
                               (chat_id,) if chat_id else ()).fetchall()
        return [(c, n, a, json.loads(l)) for c, n, a, l in rows]

    def update_watch(self, chat_id, network, address, snapshot: dict):
        with self.db:
            self.db.execute("UPDATE watches SET last=? WHERE chat_id=? AND network=? AND address=?",
                            (json.dumps(snapshot), chat_id, network, address))

    def delete_watch(self, chat_id, address) -> int:
        with self.db:
            return self.db.execute("DELETE FROM watches WHERE chat_id=? AND address=?",
                                   (chat_id, address)).rowcount
