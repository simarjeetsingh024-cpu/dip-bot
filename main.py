from fastapi import FastAPI, Request
import requests
import os

app = FastAPI()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ALERT_CHAT_ID = os.getenv("TELEGRAM_ALERT_CHAT_ID", "")

def send_telegram(chat_id, text: str):
    if not TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=5)
    except Exception:
        pass

def get_crypto_price(asset: str = "BTC-USD") -> float:
    url = f"https://api.coinbase.com/v2/prices/{asset}/spot"
    r = requests.get(url, timeout=5).json()
    return float(r["data"]["amount"])

def get_yahoo_price(symbol: str) -> float:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    r = requests.get(url, timeout=5).json()
    return float(r["chart"]["result"][0]["meta"]["regularMarketPrice"])

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/price")
def price(asset: str, source: str = "crypto"):
    if source == "crypto":
        p = get_crypto_price(asset)
    else:
        p = get_yahoo_price(asset)
    return {"asset": asset, "source": source, "price": p}

@app.get("/dip-alert")
def dip_alert(asset: str, dip: float = 3.0, source: str = "crypto"):
    if source == "crypto":
        current = get_crypto_price(asset)
    else:
        current = get_yahoo_price(asset)
    target = current * (1 - dip / 100)
    return {"asset": asset, "source": source, "dip_percent": dip, "current_price": current, "target_price": target}

@app.post("/tv-webhook")
async def tv_webhook(request: Request):
    data = await request.json()
    asset = data.get("asset", "UNKNOWN")
    market = data.get("market", "unknown")
    msg = data.get("msg", "")
    extra = data.get("extra", "")
    text = f"⚠️ DIP ALERT\nAsset: {asset}\nMarket: {market}\nMsg: {msg}\nExtra: {extra}"
    if TELEGRAM_ALERT_CHAT_ID:
        send_telegram(TELEGRAM_ALERT_CHAT_ID, text)
    return {"status": "ok"}

@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    update = await request.json()
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        return {"ok": True}

    parts = text.split()
    cmd = parts[0].lower()

    if cmd == "/start":
        send_telegram(chat_id, "Dip Bot ready.")
        return {"ok": True}

    if cmd == "/price" and len(parts) >= 2:
        asset = parts[1].upper()
        source = "crypto"
        if len(parts) >= 3 and parts[2].lower() in ["stock", "future"]:
            source = "stock"
        try:
            price = get_crypto_price(asset) if source=="crypto" else get_yahoo_price(asset)
            send_telegram(chat_id, f"{asset} ({source}) price: {price}")
        except:
            send_telegram(chat_id, "Error.")
        return {"ok": True}

    if cmd == "/dip" and len(parts) >= 3:
        asset = parts[1].upper()
        try:
            dip = float(parts[2])
        except:
            send_telegram(chat_id, "Dip must be number.")
            return {"ok": True}
        source = "crypto"
        if len(parts)>=4 and parts[3].lower() in ["stock","future"]:
            source = "stock"
        try:
            current = get_crypto_price(asset) if source=="crypto" else get_yahoo_price(asset)
            target = current*(1-dip/100)
            send_telegram(chat_id, f"DIP PLAN\nAsset: {asset}\nCurrent: {current}\nTarget: {target}")
        except:
            send_telegram(chat_id, "Error.")
        return {"ok": True}

    send_telegram(chat_id, "Unknown command.")
    return {"ok": True}
