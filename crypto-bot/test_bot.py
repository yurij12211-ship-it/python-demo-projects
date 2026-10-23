"""Перевірка команд і фонового циклу з фейковими API (без мережі і без Telegram)."""
import asyncio
import os
from decimal import Decimal
from types import SimpleNamespace

import pytest

os.environ.setdefault("BOT_TOKEN", "123:TEST")
os.environ["DB_PATH"] = ":memory:"
import bot  # noqa: E402
from chain import Chain  # noqa: E402

ADDR = "0xdAC17F958D2ee523a2206206994597C13D831ec7"


class FakeCG:
    def __init__(self):
        self.p = {"bitcoin": {"usd": 71000.0, "usd_24h_change": 2.1},
                  "ethereum": {"usd": 2400.0, "usd_24h_change": -1.3}}

    async def resolve(self, s):
        m = {"btc": "bitcoin", "eth": "ethereum"}
        if s.lower() not in m:
            raise bot.PriceError(f"Монету «{s}» не знайдено")
        return m[s.lower()]

    async def prices(self, ids):
        return {i: self.p[i] for i in ids if i in self.p}


class FakeChain:
    def __init__(self):
        self.bal = {"ETH": Decimal("1.5"), "USDT": Decimal("100")}

    async def balances(self, net, addr):
        return dict(self.bal)


class Msg:
    def __init__(self):
        self.chat = SimpleNamespace(id=42)
        self.out = []

    async def answer(self, text, **kw):
        self.out.append(text)


def cmd(args):
    return SimpleNamespace(args=args)


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    monkeypatch.setattr(bot, "cg", FakeCG(), raising=False)
    monkeypatch.setattr(bot, "chain", FakeChain())
    monkeypatch.setattr(bot, "store", bot.Storage(":memory:"))


def run(coro):
    return asyncio.run(coro)


def test_price():
    m = Msg(); run(bot.price(m, cmd("btc eth")))
    assert "BTC: $71,000  🟢 +2.10%" in m.out[0] and "ETH: $2,400  🔴 -1.30%" in m.out[0]
    m = Msg(); run(bot.price(m, cmd("xyz")))
    assert "не знайдено" in m.out[0]


def test_alert_flow_and_loop():
    m = Msg()
    run(bot.alert(m, cmd("btc above 70000")))
    run(bot.alert(m, cmd("eth below 2000")))
    run(bot.alerts(m))
    assert "Алерт №1" in m.out[0] and "№1: BTC ≥ $70,000" in m.out[2]

    sent = []

    class FakeBot:
        async def send_message(self, chat_id, text):
            sent.append((chat_id, text))

    async def one_iteration():
        bot.CHECK_EVERY = 0
        task = asyncio.create_task(bot.check_loop(FakeBot()))
        await asyncio.sleep(0.05)
        task.cancel()

    run(one_iteration())
    assert len(sent) == 1 and "BTC зараз $71,000" in sent[0][1]
    assert [r[0] for r in bot.store.alerts(42)] == [2]  # спрацьований видалено, ETH лишився


def test_watch_detects_change():
    m = Msg()
    run(bot.watch(m, cmd(f"eth {ADDR.lower()}")))
    assert "Стежу" in m.out[0] and "USDT: 100" in m.out[0]
    run(bot.watch(m, cmd(f"eth {ADDR}")))
    assert "Вже стежу" in m.out[1]

    bot.chain.bal["USDT"] = Decimal("350.25")
    sent = []

    class FakeBot:
        async def send_message(self, chat_id, text):
            sent.append(text)

    async def one_iteration():
        bot.CHECK_EVERY = 0
        t = asyncio.create_task(bot.check_loop(FakeBot()))
        await asyncio.sleep(0.05)
        t.cancel()

    run(one_iteration())
    assert len(sent) == 1 and "USDT: 100 → 350.25 (+250.25)" in sent[0]


def test_balance_bad_address():
    m = Msg(); run(bot.balance(m, cmd("eth 0x123")))
    assert "не схоже на адресу" in m.out[0]


def test_chain_balances_with_mocked_rpc(monkeypatch):
    c = Chain()
    w3 = c.w3["eth"]

    async def get_balance(addr):
        return 2 * 10**18

    class Fn:
        def __init__(self, v): self.v = v
        def balanceOf(self, a): return self
        async def call(self): return self.v

    monkeypatch.setattr(w3.eth, "get_balance", get_balance)
    monkeypatch.setattr(w3.eth, "contract",
                        lambda address, abi: SimpleNamespace(functions=Fn(12_500_000)))
    bal = asyncio.run(c.balances("eth", ADDR))
    assert bal == {"ETH": Decimal(2), "USDT": Decimal("12.5"), "USDC": Decimal("12.5")}
