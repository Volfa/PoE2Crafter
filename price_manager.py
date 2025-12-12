import json
import os
import requests
import time

CACHE_FILE = "live_prices.json"

# Если ты хочешь цены именно для POE 2, нужно проверить актуальную лигу.
# Пока оставим Standard (это цены PoE 1, но для теста механики подойдет).
LEAGUE = "Standard" 

ENDPOINTS = {
    "Currency": f"https://poe.ninja/api/data/currencyoverview?league={LEAGUE}&type=Currency",
    "Fragment": f"https://poe.ninja/api/data/currencyoverview?league={LEAGUE}&type=Fragment",
    "Essence": f"https://poe.ninja/api/data/itemoverview?league={LEAGUE}&type=Essence",
    "Omen": f"https://poe.ninja/api/data/itemoverview?league={LEAGUE}&type=Omen",
    "Oil": f"https://poe.ninja/api/data/itemoverview?league={LEAGUE}&type=Oil"
}

def update_prices():
    print(f"📉 [Updater] Обновляю цены с poe.ninja ({LEAGUE})...")
    
    combined_prices = {}
    
    for category, url in ENDPOINTS.items():
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200: continue
                
            data = response.json()
            lines = data.get("lines", [])
            
            count = 0
            for item in lines:
                # Имя может быть в разных полях
                name = item.get("currencyTypeName") or item.get("name")
                
                # --- ВОТ ГЛАВНЫЙ ФИКС ---
                # Ищем цену в обоих возможных полях
                price = item.get("chaosValue") or item.get("chaosEquivalent")
                # ------------------------
                
                if name and price:
                    combined_prices[name] = float(price)
                    count += 1
            
            print(f"   ✅ {category}: загружено {count} шт.")
            
        except Exception as e:
            print(f"   ❌ Ошибка {category}: {e}")

    # Хардкод базы
    combined_prices["Chaos Orb"] = 1.0

    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(combined_prices, f, indent=4, ensure_ascii=False)
        print(f"💾 Успех! Всего цен в базе: {len(combined_prices)}")
        return True
    except: return False

def get_currency_price(name):
    try:
        if not os.path.exists(CACHE_FILE): update_prices()
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            prices = json.load(f)
            
        if name in prices: return prices[name]
        
        # Нечеткий поиск (для надежности)
        for p_name, p_price in prices.items():
            if name.lower() == p_name.lower(): return p_price
        return 0
    except: return 0

if __name__ == "__main__":
    update_prices()
    print("\n--- ПРОВЕРКА ЦЕН ---")
    print(f"Divine Orb: {get_currency_price('Divine Orb')}c")
    print(f"Omen of Blanching: {get_currency_price('Omen of Blanching')}c")