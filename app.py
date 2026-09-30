"""TradingView -> Charles Schwab 下单桥.

TradingView 的 alert webhook 打到本服务的 /webhook,
本服务校验密钥后, 经 Schwab Trader API 下单.
"""
import hmac
import logging
import os
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from schwab_trader import SchwabTrader, SchwabError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("tv-schwab")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() in ("1", "true", "yes")
SYMBOL_ALLOWLIST = {
    s.strip().upper()
    for s in os.environ.get("SYMBOL_ALLOWLIST", "").split(",")
    if s.strip()
}
MAX_DOLLARS_PER_ORDER = float(os.environ.get("MAX_DOLLARS_PER_ORDER", "2000"))

app = FastAPI(title="TV-Schwab webhook bridge")
trader = SchwabTrader()


def _log_trade(entry: dict) -> None:
    os.makedirs("logs", exist_ok=True)
    with open("logs/trades.log", "a") as f:
        f.write(f"{datetime.now().isoformat()} {entry}\n")


@app.get("/health")
def health():
    return {"ok": True, "dry_run": DRY_RUN}


@app.post("/webhook")
async def webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "invalid json")

    if not WEBHOOK_SECRET or not hmac.compare_digest(
        str(payload.get("secret", "")), WEBHOOK_SECRET
    ):
        raise HTTPException(401, "bad secret")

    symbol = str(payload.get("symbol", "")).upper().strip()
    action = str(payload.get("action", "")).lower().strip()
    if not symbol or action not in ("buy", "sell", "close"):
        raise HTTPException(400, "need symbol and action=buy|sell|close")
    if SYMBOL_ALLOWLIST and symbol not in SYMBOL_ALLOWLIST:
        raise HTTPException(403, f"{symbol} not in allowlist")

    quantity = payload.get("quantity")
    dollars = payload.get("dollars")
    try:
        trader.ensure_client()
        if action == "close":
            qty = trader.position_quantity(symbol)
            if qty == 0:
                return {"ok": True, "note": f"no position in {symbol}, nothing to do"}
            side_action = "sell" if qty > 0 else "buy"
            qty = abs(qty)
        else:
            if quantity:
                qty = int(quantity)
            elif dollars:
                price = trader.last_price(symbol)
                qty = max(1, int(float(dollars) // price))
            else:
                raise HTTPException(400, "need quantity or dollars")
            if qty * trader.last_price(symbol) > MAX_DOLLARS_PER_ORDER:
                raise HTTPException(403, "order exceeds MAX_DOLLARS_PER_ORDER")
            side_action = action

        if DRY_RUN:
            note = f"[DRY-RUN] would {side_action} {qty} {symbol}"
            log.info(note)
            _log_trade({"dry_run": True, "symbol": symbol,
                        "side": side_action, "qty": qty, "payload": payload})
            return {"ok": True, "dry_run": True, "note": note}

        order_id = trader.place_market_order(symbol, side_action, qty)
        note = f"{side_action} {qty} {symbol} -> order {order_id}"
        log.info(note)
        _log_trade({"dry_run": False, "symbol": symbol, "side": side_action,
                    "qty": qty, "order_id": order_id})
        return {"ok": True, "order_id": order_id, "note": note}
    except SchwabError as e:
        log.error("schwab error: %s", e)
        _log_trade({"error": str(e), "payload": payload})
        return JSONResponse({"ok": False, "error": str(e)}, status_code=502)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        log.exception("unexpected")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
