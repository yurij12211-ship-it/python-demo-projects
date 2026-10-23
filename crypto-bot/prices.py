"""Ціни монет через публічний CoinGecko API (без ключа)."""
import aiohttp

API = "https://api.coingecko.com/api/v3"

# Найпопулярніші тікери, щоб не робити зайвий запит /search
KNOWN = {
    "btc": "bitcoin", "eth": "ethereum", "sol": "solana", "bnb": "binancecoin",
    "xrp": "ripple", "ton": "the-open-network", "doge": "dogecoin", "ada": "cardano",
    "trx": "tron", "usdt": "tether", "usdc": "usd-coin", "link": "chainlink",
    "matic": "matic-network", "pol": "polygon-ecosystem-token", "arb": "arbitrum",
}


class PriceError(Exception):
    pass


class CoinGecko:
    def __init__(self, session: aiohttp.ClientSession, api_key: str | None = None):
        self.session = session
        self.headers = {"x-cg-demo-api-key": api_key} if api_key else {}
        self._ids: dict[str, str] = dict(KNOWN)

    async def _get(self, path: str, params: dict) -> dict:
        async with self.session.get(f"{API}{path}", params=params, headers=self.headers,
                                    timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status == 429:
                raise PriceError("CoinGecko: забагато запитів, спробуйте за хвилину")
            if r.status != 200:
                raise PriceError(f"CoinGecko: помилка {r.status}")
            return await r.json()

    async def resolve(self, symbol: str) -> str:
        """Тікер (btc) або id (bitcoin) -> id CoinGecko."""
        s = symbol.lower().strip()
        if s in self._ids:
            return self._ids[s]
        data = await self._get("/search", {"query": s})
        coins = data.get("coins") or []
        exact = [c for c in coins if c.get("symbol", "").lower() == s or c.get("id") == s]
        if not exact:
            raise PriceError(f"Монету «{symbol}» не знайдено")
        # найвищий за капіталізацією (менший market_cap_rank) серед точних збігів
        best = min(exact, key=lambda c: c.get("market_cap_rank") or 10**9)
        self._ids[s] = best["id"]
        return best["id"]

    async def prices(self, ids: list[str]) -> dict[str, dict]:
        """Повертає {id: {"usd": ціна, "usd_24h_change": %}} одним запитом."""
        if not ids:
            return {}
        data = await self._get("/simple/price", {
            "ids": ",".join(sorted(set(ids))), "vs_currencies": "usd",
            "include_24hr_change": "true",
        })
        return data
