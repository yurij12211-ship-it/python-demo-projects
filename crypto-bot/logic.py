"""Чиста логіка без мережі: що спрацювало і що змінилось. Покрита тестами."""
from decimal import Decimal


def fmt_price(p: float) -> str:
    if p >= 1000:
        return f"${p:,.0f}"
    if p >= 1:
        return f"${p:,.2f}"
    return f"${p:.6f}".rstrip("0")


def fmt_amount(x: Decimal) -> str:
    q = x.quantize(Decimal("0.0001")).normalize()
    return f"{q:f}"


def triggered(alerts, prices: dict[str, dict]):
    """alerts: (id, chat_id, coin_id, symbol, direction, target).
    Повертає список (alert, поточна ціна) для тих, що спрацювали."""
    hits = []
    for a in alerts:
        price = (prices.get(a[2]) or {}).get("usd")
        if price is None:
            continue
        if (a[4] == "above" and price >= a[5]) or (a[4] == "below" and price <= a[5]):
            hits.append((a, price))
    return hits


def diff(old: dict, new: dict[str, Decimal], min_change=Decimal("0.000001")):
    """Порівнює баланси. Повертає список (актив, було, стало) для змінених."""
    changes = []
    for asset, value in new.items():
        before = Decimal(str(old.get(asset, "0")))
        if abs(value - before) >= min_change:
            changes.append((asset, before, value))
    return changes


def snapshot(balances: dict[str, Decimal]) -> dict[str, str]:
    return {k: str(v) for k, v in balances.items()}


def parse_alert(args: list[str]):
    """'/alert btc above 70000' -> ('btc', 'above', 70000.0). Приймає > і < теж."""
    if len(args) != 3:
        raise ValueError("Формат: /alert btc above 70000  або  /alert eth below 2500")
    coin, d, target = args
    d = {"above": "above", ">": "above", "вище": "above",
         "below": "below", "<": "below", "нижче": "below"}.get(d.lower())
    if not d:
        raise ValueError("Напрямок: above або below")
    try:
        t = float(target.replace(",", ".").replace("$", ""))
    except ValueError:
        raise ValueError("Ціна має бути числом, наприклад 70000 або 0.35") from None
    if t <= 0:
        raise ValueError("Ціна має бути більшою за нуль")
    return coin, d, t
