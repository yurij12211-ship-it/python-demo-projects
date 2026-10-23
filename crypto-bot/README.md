# Crypto Alert Bot (Telegram, Python, web3.py)

Telegram bot that watches crypto prices and on-chain wallets so you don't have to.

**Features**
- `/price btc eth sol` — live prices and 24h change (CoinGecko)
- `/alert btc above 70000` — notification when price crosses a level (`above` / `below`)
- `/balance eth 0x…` — wallet balance: native coin + USDT/USDC, read directly from the blockchain via **web3.py**
- `/watch eth 0x…` — tracks a wallet and reports every balance change (deposits, withdrawals)
- Networks: **Ethereum, BNB Chain, Base** (any EVM chain can be added in `chain.py`)
- Alerts and watched wallets stored in SQLite, background checker runs every 60 s
- No paid API keys required: public RPC + free CoinGecko endpoint; your own RPC (Infura/Alchemy) can be set in `.env`

**Stack:** Python 3.11+, aiogram 3, web3.py 7 (AsyncWeb3, ERC-20 `balanceOf`), aiohttp, SQLite, pytest

## Run
```bash
pip install -r requirements.txt
cp .env.example .env   # put BOT_TOKEN from @BotFather
python bot.py
```
On Windows just double-click `run_bot.bat`.

## Tests
```bash
pytest -q   # 11 tests: alert parsing/triggering, balance diff, storage, handlers and background loop with mocked APIs and mocked RPC
```

## Structure
| File | What it does |
| --- | --- |
| `bot.py` | Telegram commands and background check loop |
| `chain.py` | web3.py: native + ERC-20 balances on EVM networks |
| `prices.py` | CoinGecko client with ticker → id resolving |
| `logic.py` | Pure logic: alert triggering, balance diff, formatting |
| `storage.py` | SQLite for alerts and watched wallets |
