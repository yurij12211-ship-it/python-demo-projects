# Python demo projects: Telegram bots, Web3, web scraper, landing page

Small, complete projects I use to show how I work. Each one runs on its own.

| Project | What it does | Stack |
| --- | --- | --- |
| [bot/](bot/) | Telegram booking bot for a barbershop or salon: service, date, free time slot, phone via one button, admin notification, `/today` for the owner. Double booking is impossible. | Python, aiogram 3, SQLite |
| [crypto-bot/](crypto-bot/) | Crypto Alert Bot for Telegram: price alerts, wallet balances and movement notifications read straight from the blockchain (Ethereum, BNB Chain, Base). 11 automated tests. | Python, aiogram 3, web3.py, CoinGecko API, SQLite |
| [parser/](parser/) | Scrapes a product catalog (books.toscrape.com, a public sandbox for scraping practice), walks all 50 pages and exports 1000 items to a formatted Excel file. | Python, requests, BeautifulSoup, openpyxl |
| [landing/](landing/) | One-page cafe website with a table booking form. Mobile-friendly, no frameworks. | HTML, CSS |

## Run the bot

```bash
pip install "aiogram>=3,<4"
BOT_TOKEN=<token from @BotFather> ADMIN_ID=<your telegram id> python bot/bot.py
```

## Run the crypto bot

```bash
pip install -r crypto-bot/requirements.txt
cd crypto-bot && cp .env.example .env   # BOT_TOKEN from @BotFather
python bot.py
```

## Run the parser

```bash
pip install requests beautifulsoup4 openpyxl
python parser/parser.py   # creates books.xlsx
```

## Landing page

Open `landing/index.html` in a browser.
