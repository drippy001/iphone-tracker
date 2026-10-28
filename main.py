import os
import json
import re
import requests
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
STATE_FILE = "status.json"

TARGET_PARTS = ["MK1E4LL/A", "MK1F4LL/A", "MJW64LL/A"]
ZIP_CODES = ["68118", "92805"]

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)

def check_stock():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for zip_code in ZIP_CODES:
            url = f"https://www.apple.com/shop/buy-iphone/iphone-duo?location={zip_code}"
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            html = page.content()
            match = re.search(r'window\.REFURB_GRID_BOOTSTRAP\s*=\s*(\{.+?\});', html, re.DOTALL)
            
            if not match:
                print(f"Could not find inventory data for ZIP {zip_code}")
                continue
                
            data = json.loads(match.group(1))
            tiles = data.get("tiles", [])
            
            current_stock = {}
            for tile in tiles:
                part = tile.get("partNumber")
                if part in TARGET_PARTS:
                    current_stock[part] = True
                    
            previous_stock = load_state()
            alerts = []
            
            for part in TARGET_PARTS:
                was_in_stock = previous_stock.get(f"{part}_{zip_code}", False)
                is_in_stock = current_stock.get(part, False)
                
                if is_in_stock and not was_in_stock:
                    alerts.append(f"🚨 STOCK ALERT: {part} is available near {zip_code}!\nBuy here: {url}")
                
                previous_stock[f"{part}_{zip_code}"] = is_in_stock
                
            save_state(previous_stock)
            
            for alert in alerts:
                send_telegram(alert)
                
        browser.close()

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
