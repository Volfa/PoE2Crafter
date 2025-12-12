import csv
import difflib
from price_manager import get_currency_price

CSV_FILE = "chance_data.csv"

def load_uniques():
    """Загружает CSV в список словарей."""
    uniques = []
    try:
        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                uniques.append(row)
    except FileNotFoundError:
        print("❌ Ошибка: Файл chance_data.csv не найден!")
    return uniques

def calculate_unique(item_name: str):
    """
    Ищет уникальный предмет и считает стоимость его получения через Orb of Chance.
    """
    data = load_uniques()
    if not data:
        return "Ошибка: База уникальных предметов пуста."

    # 1. Умный поиск (Fuzzy Search)
    # Собираем список всех имен уников из базы
    all_names = [row['name'] for row in data]
    
    # Ищем наиболее похожее название
    matches = difflib.get_close_matches(item_name, all_names, n=1, cutoff=0.5)
    
    if not matches:
        return f"Уникальный предмет '{item_name}' не найден в базе шансинга."
    
    target_name = matches[0]
    
    # 2. Достаем данные по найденному предмету
    item_info = next((row for row in data if row['name'] == target_name), None)
    
    if not item_info:
        return "Ошибка данных."

    # 3. Экономика 💰
    avg_orbs = int(item_info['averageOrbs'])
    chance_percent = item_info['chance']
    base_item = item_info['baseItem']
    tier = item_info['tier']
    
    # Узнаем цену Orb of Chance
    chance_orb_price = get_currency_price("Orb of Chance")
    if chance_orb_price == 0: chance_orb_price = 0.5 # Примерная цена, если не нашли
    
    chaos_price = get_currency_price("Chaos Orb")
    divine_price = get_currency_price("Divine Orb")

    total_cost_chaos = avg_orbs * chance_orb_price
    
    cost_string = f"{int(total_cost_chaos)} Chaos"
    if divine_price > 0 and total_cost_chaos > divine_price:
        divines = total_cost_chaos / divine_price
        cost_string += f" (~{divines:.1f} Divine)"

    # 4. Формируем ответ
    return (
        f"🌟 **Уникальный предмет:** {target_name}\n"
        f"🛡️ **База:** {base_item}\n"
        f"📊 **Редкость:** Tier {tier} (Шанс: {chance_percent})\n"
        f"🎲 **Нужно сфер удачи:** ~{avg_orbs}\n"
        f"💸 **Бюджет:** {cost_string}\n"
        f"⚠️ **Риск:** {item_info['destructionChance']} предметов сломается при попытках."
    )

# Тест
if __name__ == "__main__":
    print(calculate_unique("Widowhail"))