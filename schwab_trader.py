"""Schwab Trader API 封装 (基于 schwab-py).

认证: 首次运行 python auth.py 做一次 OAuth 浏览器授权, token 存到
token.json. 之后 easy_client 会自动用 refresh token 续期.
注意: Schwab 的 refresh token 7 天过期, 每周跑一次 python auth.py 续签.
"""
import json
import logging
import os

log = logging.getLogger("tv-schwab")

API_KEY = os.environ.get("SCHWAB_API_KEY", "")
APP_SECRET = os.environ.get("SCHWAB_APP_SECRET", "")
CALLBACK_URL = "https://127.0.0.1:8182"
TOKEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")


class SchwabError(RuntimeError):
    pass


class SchwabTrader:
    def __init__(self):
        self._client = None
        self._account_hash = None

    def ensure_client(self):
        if self._client is not None:
            return self._client
        if not API_KEY or not APP_SECRET:
            raise SchwabError("SCHWAB_API_KEY / SCHWAB_APP_SECRET 未配置")
        if not os.path.exists(TOKEN_PATH):
            raise SchwabError("token.json 不存在, 先跑 python auth.py 做一次授权")
        import schwab.auth
        try:
            self._client = schwab.auth.easy_client(
                API_KEY, APP_SECRET, CALLBACK_URL, TOKEN_PATH,
                interactive=False,
            )
        except Exception as e:  # token 过期等
            raise SchwabError(f"Schwab 认证失败(可能 refresh token 超过7天, 重跑 auth.py): {e}")
        return self._client

    def _account_hash_value(self):
        if self._account_hash is None:
            r = self.ensure_client().get_account_numbers()
            if r.status_code != 200:
                raise SchwabError(f"取账户失败: {r.status_code} {r.text[:200]}")
            accounts = r.json()
            if not accounts:
                raise SchwabError("Schwab 账户列表为空")
            self._account_hash = accounts[0]["hashValue"]
        return self._account_hash

    def last_price(self, symbol: str) -> float:
        r = self.ensure_client().get_quote(symbol)
        if r.status_code != 200:
            raise SchwabError(f"取 {symbol} 报价失败: {r.status_code}")
        q = r.json().get(symbol, {})
        price = (q.get("quote") or {}).get("lastPrice") or (q.get("quote") or {}).get("closePrice")
        if not price:
            raise SchwabError(f"{symbol} 无有效报价")
        return float(price)

    def position_quantity(self, symbol: str) -> int:
        """返回持仓股数(整数股). 正数为多头, 负数为空头, 0 为无持仓."""
        from schwab.client import Client
        r = self.ensure_client().get_account(
            self._account_hash_value(), fields=Client.Account.Fields.POSITIONS
        )
        if r.status_code != 200:
            raise SchwabError(f"取持仓失败: {r.status_code}")
        positions = (
            r.json().get("securitiesAccount", {}).get("positions", []) or []
        )
        for p in positions:
            inst = p.get("instrument", {})
            if inst.get("symbol", "").upper() == symbol.upper():
                qty = p.get("longQuantity", 0) - p.get("shortQuantity", 0)
                return int(qty)
        return 0

    def place_market_order(self, symbol: str, side: str, quantity: int) -> str:
        from schwab.orders import equities
        builder = {
            "buy": equities.equity_buy_market,
            "sell": equities.equity_sell_market,
        }[side](symbol, quantity)
        r = self.ensure_client().place_order(self._account_hash_value(), builder)
        if r.status_code not in (200, 201):
            raise SchwabError(f"下单失败: {r.status_code} {r.text[:300]}")
        # Schwab 在 Location 头返回订单号
        loc = r.headers.get("Location", "")
        order_id = loc.rstrip("/").split("/")[-1] if loc else "unknown"
        # 落盘记录订单请求, 方便对账
        with open("logs/last_order.json", "w") as f:
            json.dump({"symbol": symbol, "side": side,
                       "quantity": quantity, "order_id": order_id}, f)
        return order_id
