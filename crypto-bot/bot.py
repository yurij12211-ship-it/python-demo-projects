"""
Crypto Alert Bot: ціни, цінові алерти і стеження за гаманцями (Ethereum, BNB Chain, Base).

Команди:
  /price btc eth sol        поточні ціни і зміна за 24 год
  /alert btc above 70000    повідомити, коли ціна перетне рівень (above/below)
  /alerts                   мої алерти,  /del 3  видалити алерт №3
  /balance eth 0x…          баланс гаманця (нативна монета + USDT/USDC)
  /watch eth 0x…            стежити за гаманцем і писати про кожну зміну балансу
  /watches, /unwatch 0x…    список і видалення

Запуск:  pip install -r requirements.txt
         заповнити .env (див. .env.example), python bot.py
"""
import asyncio
import logging
import os

import aiohttp
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from chain import NETWORKS, Chain, ChainError, normalize
from logic import diff, fmt_amount, fmt_price, parse_alert, snapshot, triggered
from prices import CoinGecko, PriceError
from storage import Storage


def load_env(path=".env"):
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHECK_EVERY = int(os.environ.get("CHECK_EVERY_SEC", "60"))
log = logging.getLogger("crypto-bot")
router = Router()
store = Storage(os.environ.get("DB_PATH", "crypto_bot.db"))
chain = Chain({k: os.environ.get(f"RPC_{k.upper()}") for k in NETWORKS})
cg: CoinGecko  # створюється в main(), бо потрібна aiohttp-сесія

HELP = ("Я стежу за криптою замість вас.\n\n"
        "/price btc eth — ціни зараз\n"
        "/alert btc above 70000 — сповіщення по ціні\n"
        "/alerts — мої алерти, /del 3 — видалити\n"
        f"/balance eth 0x… — баланс гаманця ({', '.join(NETWORKS)})\n"
        "/watch eth 0x… — повідомляти про зміни балансу\n"
        "/watches, /unwatch 0x…")


@router.message(CommandStart())
@router.message(Command("help"))
async def start(m: Message):
    await m.answer(HELP)


@router.message(Command("price"))
async def price(m: Message, command: CommandObject):
    symbols = (command.args or "btc eth").split()[:10]
    try:
        ids = {s: await cg.resolve(s) for s in symbols}
        data = await cg.prices(list(ids.values()))
    except PriceError as e:
        return await m.answer(str(e))
    lines = []
    for s, cid in ids.items():
        p = data.get(cid, {})
        if "usd" in p:
            ch = p.get("usd_24h_change") or 0
            lines.append(f"{s.upper()}: {fmt_price(p['usd'])}  {'🟢' if ch >= 0 else '🔴'} {ch:+.2f}% за 24 год")
    await m.answer("\n".join(lines) or "Немає даних")


@router.message(Command("alert"))
async def alert(m: Message, command: CommandObject):
    try:
        coin, direction, target = parse_alert((command.args or "").split())
        cid = await cg.resolve(coin)
    except (ValueError, PriceError) as e:
        return await m.answer(str(e))
    aid = store.add_alert(m.chat.id, cid, coin.upper(), direction, target)
    word = "підніметься до" if direction == "above" else "опуститься до"
    await m.answer(f"✅ Алерт №{aid}: напишу, коли {coin.upper()} {word} {fmt_price(target)}")


@router.message(Command("alerts"))
async def alerts(m: Message):
    rows = store.alerts(m.chat.id)
    if not rows:
        return await m.answer("Алертів немає. Приклад: /alert btc above 70000")
    await m.answer("\n".join(f"№{r[0]}: {r[3]} {'≥' if r[4] == 'above' else '≤'} {fmt_price(r[5])}"
                             for r in rows))


@router.message(Command("del"))
async def delete(m: Message, command: CommandObject):
    ok = (command.args or "").strip().isdigit() and store.delete_alert(m.chat.id, int(command.args))
    await m.answer("Видалено" if ok else "Не знайшов такого алерту. Список: /alerts")


def _net_addr(args: str | None):
    parts = (args or "").split()
    if len(parts) == 1:
        parts = ["eth", parts[0]]
    if len(parts) != 2:
        raise ChainError(f"Формат: /balance eth 0x…  (мережі: {', '.join(NETWORKS)})")
    return parts[0].lower(), normalize(parts[1])


def _fmt_balances(network, address, bal):
    head = f"{NETWORKS[network]['name']} {address[:6]}…{address[-4:]}"
    return head + "\n" + "\n".join(f"{k}: {fmt_amount(v)}" for k, v in bal.items())


@router.message(Command("balance"))
async def balance(m: Message, command: CommandObject):
    try:
        net, addr = _net_addr(command.args)
        bal = await chain.balances(net, addr)
    except ChainError as e:
        return await m.answer(str(e))
    await m.answer(_fmt_balances(net, addr, bal))


@router.message(Command("watch"))
async def watch(m: Message, command: CommandObject):
    try:
        net, addr = _net_addr(command.args)
        bal = await chain.balances(net, addr)
    except ChainError as e:
        return await m.answer(str(e))
    if not store.add_watch(m.chat.id, net, addr, snapshot(bal)):
        return await m.answer("Вже стежу за цим гаманцем")
    await m.answer("👀 Стежу. Поточний стан:\n" + _fmt_balances(net, addr, bal))


@router.message(Command("watches"))
async def watches(m: Message):
    rows = store.watches(m.chat.id)
    await m.answer("\n".join(f"{NETWORKS[n]['name']}: {a}" for _, n, a, _ in rows)
                   or "Не стежу за жодним гаманцем. Приклад: /watch eth 0x…")


@router.message(Command("unwatch"))
async def unwatch(m: Message, command: CommandObject):
    try:
        addr = normalize(command.args or "")
    except ChainError as e:
        return await m.answer(str(e))
    n = store.delete_watch(m.chat.id, addr)
    await m.answer("Більше не стежу" if n else "Цього гаманця немає в списку")


async def check_loop(bot: Bot):
    """Фонова перевірка: алерти по ціні і зміни балансів."""
    while True:
        try:
            rows = store.alerts()
            if rows:
                prices = await cg.prices([r[2] for r in rows])
                for a, p in triggered(rows, prices):
                    await bot.send_message(a[1], f"🔔 {a[3]} зараз {fmt_price(p)} "
                                                 f"(ваш рівень {fmt_price(a[5])}). Алерт №{a[0]} виконано.")
                    store.delete_alert(a[1], a[0])
            for chat_id, net, addr, last in store.watches():
                try:
                    bal = await chain.balances(net, addr)
                except ChainError as e:
                    log.warning("watch %s %s: %s", net, addr, e)
                    continue
                changes = diff(last, bal)
                if changes:
                    text = "\n".join(f"{k}: {fmt_amount(b)} → {fmt_amount(a)} "
                                     f"({'+' if a > b else ''}{fmt_amount(a - b)})" for k, b, a in changes)
                    await bot.send_message(chat_id, f"💸 Рух на гаманці {addr[:6]}…{addr[-4:]} "
                                                    f"({NETWORKS[net]['name']})\n{text}")
                    store.update_watch(chat_id, net, addr, snapshot(bal))
        except PriceError as e:
            log.warning("prices: %s", e)
        except Exception:
            log.exception("check loop")
        await asyncio.sleep(CHECK_EVERY)


async def main():
    global cg
    logging.basicConfig(level=logging.INFO)
    async with aiohttp.ClientSession() as session:
        cg = CoinGecko(session, os.environ.get("COINGECKO_API_KEY") or None)
        bot = Bot(BOT_TOKEN)
        dp = Dispatcher()
        dp.include_router(router)
        asyncio.create_task(check_loop(bot))
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
