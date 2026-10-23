from decimal import Decimal

import pytest

from chain import ChainError, normalize
from logic import diff, fmt_price, parse_alert, snapshot, triggered
from storage import Storage


def test_parse_alert():
    assert parse_alert(["btc", "above", "70000"]) == ("btc", "above", 70000.0)
    assert parse_alert(["eth", "<", "2,5"]) == ("eth", "below", 2.5)
    for bad in (["btc", "up", "1"], ["btc", "above", "abc"], ["btc", "above", "-1"], ["btc"]):
        with pytest.raises(ValueError):
            parse_alert(bad)


def test_triggered():
    alerts = [(1, 10, "bitcoin", "BTC", "above", 70000.0),
              (2, 10, "bitcoin", "BTC", "below", 60000.0),
              (3, 11, "ethereum", "ETH", "below", 2500.0),
              (4, 11, "solana", "SOL", "above", 1.0)]  # немає ціни -> пропуск
    hits = triggered(alerts, {"bitcoin": {"usd": 71000}, "ethereum": {"usd": 2500}})
    assert [a[0] for a, _ in hits] == [1, 3]


def test_diff_and_snapshot():
    old = snapshot({"ETH": Decimal("1.5"), "USDT": Decimal("100")})
    new = {"ETH": Decimal("1.5"), "USDT": Decimal("250.5"), "USDC": Decimal("0")}
    assert diff(old, new) == [("USDT", Decimal("100"), Decimal("250.5"))]


def test_normalize():
    a = normalize("0xdac17f958d2ee523a2206206994597c13d831ec7")
    assert a == "0xdAC17F958D2ee523a2206206994597C13D831ec7"
    with pytest.raises(ChainError):
        normalize("0x123")


def test_fmt_price():
    assert fmt_price(71234.5) == "$71,234"
    assert fmt_price(2.5) == "$2.50"
    assert fmt_price(0.000123) == "$0.000123"


def test_storage(tmp_path):
    s = Storage(str(tmp_path / "t.db"))
    aid = s.add_alert(1, "bitcoin", "BTC", "above", 70000)
    assert s.alerts(1)[0][0] == aid and s.alerts(2) == []
    assert not s.delete_alert(2, aid) and s.delete_alert(1, aid)
    assert s.add_watch(1, "eth", "0xA", {"ETH": "1"}) and not s.add_watch(1, "eth", "0xA", {})
    s.update_watch(1, "eth", "0xA", {"ETH": "2"})
    assert s.watches(1) == [(1, "eth", "0xA", {"ETH": "2"})]
    assert s.delete_watch(1, "0xA") == 1
