"""Читання балансів гаманців з блокчейну через web3.py і публічний RPC (без ключа)."""
from decimal import Decimal

from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider

# Мережі EVM з публічними RPC. Можна замінити на свій RPC (Infura, Alchemy) у .env
NETWORKS = {
    "eth": {"name": "Ethereum", "rpc": "https://ethereum-rpc.publicnode.com", "coin": "ETH",
            "tokens": {"USDT": ("0xdAC17F958D2ee523a2206206994597C13D831ec7", 6),
                       "USDC": ("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 6)}},
    "bsc": {"name": "BNB Chain", "rpc": "https://bsc-rpc.publicnode.com", "coin": "BNB",
            "tokens": {"USDT": ("0x55d398326f99059fF775485246999027B3197955", 18)}},
    "base": {"name": "Base", "rpc": "https://base-rpc.publicnode.com", "coin": "ETH",
             "tokens": {"USDC": ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 6)}},
}

ERC20_ABI = [{"name": "balanceOf", "type": "function", "stateMutability": "view",
              "inputs": [{"name": "owner", "type": "address"}],
              "outputs": [{"name": "", "type": "uint256"}]}]


class ChainError(Exception):
    pass


def normalize(address: str) -> str:
    """Перевіряє адресу і повертає її у checksum-формі."""
    a = address.strip()
    if not AsyncWeb3.is_address(a):
        raise ChainError("Це не схоже на адресу гаманця (0x… 42 символи)")
    return AsyncWeb3.to_checksum_address(a)


class Chain:
    def __init__(self, rpc_overrides: dict[str, str] | None = None):
        self.w3 = {}
        for key, net in NETWORKS.items():
            url = (rpc_overrides or {}).get(key) or net["rpc"]
            self.w3[key] = AsyncWeb3(AsyncHTTPProvider(url, request_kwargs={"timeout": 15}))

    async def balances(self, network: str, address: str) -> dict[str, Decimal]:
        """Баланс нативної монети і основних стейблкоїнів."""
        if network not in NETWORKS:
            raise ChainError(f"Невідома мережа. Доступні: {', '.join(NETWORKS)}")
        w3, net, addr = self.w3[network], NETWORKS[network], normalize(address)
        try:
            out = {net["coin"]: Decimal(await w3.eth.get_balance(addr)) / Decimal(10**18)}
            for sym, (token, decimals) in net["tokens"].items():
                c = w3.eth.contract(address=AsyncWeb3.to_checksum_address(token), abi=ERC20_ABI)
                raw = await c.functions.balanceOf(addr).call()
                out[sym] = Decimal(raw) / Decimal(10**decimals)
        except ChainError:
            raise
        except Exception as e:  # мережеві збої RPC
            raise ChainError(f"RPC {net['name']} не відповів: {type(e).__name__}") from e
        return out
