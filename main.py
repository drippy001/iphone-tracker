import os
import json
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
STATE_FILE = "status.json"

# iPhone 18 Pro Max Burgundy (256GB and 512GB)
TARGET_PARTS = ["MJW64LL/A", "MJWA4LL/A"] 
ZIP_CODES = ["92805", "68118"] # Anaheim and Omaha

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)

def check_stock():
    previous_data = load_state()
    alerts = []
    
    # Headers make the request look like a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Accept": "application/json"
    }

    for part in TARGET_PARTS:
        for zip_code in ZIP_CODES:
            key = f"{part}_{zip_code}"
            
            # This is Apple's exact inventory API used by their website
            url = f"https://www.apple.com/shop/fulfillment-messages?parts.0={part}&location={zip_code}"
            
            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                # Dig into Apple's JSON response to find the stores
                stores = data.get("body", {}).get("content", {}).get("pickupMessage", {}).get("stores", [])
                
                in_stock_stores = []
                for store in stores:
                    if store.get("pickupDisplay") == "available":
                        in_stock_stores.append(store.get("storeName"))
                
                is_in_stock = len(in_stock_stores) > 0
                old_state = previous_data.get(key, {"in_stock": False})
                was_in_stock = old_state.get("in_stock", False)
                
                if is_in_stock and not was_in_stock:
                    stores_str = ", ".join(in_stock_stores)
                    alerts.append(f"🚨 STOCK ALERT: {part} is available at {stores_str} (ZIP {zip_code})!\nBuy here: https://www.apple.com/shop/buy-iphone/iphone-18-pro?location={zip_code}")
                    
                previous_data[key] = {"in_stock": is_in_stock, "stores": in_stock_stores}
                print(f"Checked {part} in {zip_code}: {'IN STOCK' if is_in_stock else 'Out of Stock'}")

            except Exception as e:
                print(f"Error checking {part} in {zip_code}: {e}")
                continue

    save_state(previous_data)
    
    for alert in alerts:
        send_telegram(alert)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

if __name__ == "__main__":
    check_stock()
