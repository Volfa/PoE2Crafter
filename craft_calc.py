import json
import os
import difflib
from price_manager import get_currency_price

# === ГЛОБАЛЬНЫЙ ЯЩИК ===
RESULT_BOX = {"text": None}

DB_FOLDER = "database"
ESSENCE_FILE = "essences_names.json"
MAPPING_FILE = "item_mapping.json"

def load_json(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f: return json.load(f)
    except UnicodeDecodeError:
        try:
            with open(filepath, "r", encoding="cp1251") as f: return json.load(f)
        except: return {}
    except: return {}

def load_essences():
    return load_json(ESSENCE_FILE)

def find_item_file(user_item_name):
    clean_name = user_item_name.strip()
    mapping = load_json(MAPPING_FILE)
    
    if clean_name in mapping:
        category = mapping[clean_name]
        return f"{DB_FOLDER}/{category.replace('/', '_').replace(':', '-')}.json"
    
    for k, v in mapping.items():
        if k.lower() in clean_name.lower():
            safe_cat = v.replace("/", "_").replace(":", "-")
            return f"{DB_FOLDER}/{safe_cat}.json"

    if not os.path.exists(DB_FOLDER): return None
    files = [f for f in os.listdir(DB_FOLDER) if f.endswith(".json")]
    matches = [f for f in files if clean_name.lower() in f.lower().replace("_", " ")]
    if matches: 
        best = max(matches, key=len)
        return f"{DB_FOLDER}/{best}"
    return None

def get_mod_data(data, mod_name_query, tier):
    # Очистка имени
    clean_query = "".join([c for c in mod_name_query if c.isalpha() or c.isspace()]).strip().lower()
    query_words = set(clean_query.split())
    if not query_words: return None, 0, None, "Пустой запрос"

    best_mod = None
    best_score = 0
    
    for mod in data["mods"]:
        name_lower = mod["name"].lower()
        matches = 0
        for word in query_words:
            if word in name_lower: matches += 1
        
        if matches > best_score:
            best_score = matches
            best_mod = mod
            
    if not best_mod or best_score < len(query_words) * 0.5:
         for mod in data["mods"]:
             if clean_query in mod["name"].lower():
                 best_mod = mod
                 break
    
    if not best_mod: return None, 0, None, f"Мод не найден."
    
    target_weight = 0
    for t in best_mod["tiers"]:
        if t["tier"] == tier:
            target_weight = t["weight"]
            break
    if target_weight == 0 and best_mod["tiers"]: target_weight = best_mod["tiers"][0]["weight"]

    return best_mod["name"], target_weight, best_mod.get("type"), None

# === УМНЫЙ АЛГОРИТМ КРАФТА v5.0 ===
def calculate_blue_strategy(data, wanted_mods, tier, real_item, essence_db):
    print(f"⚙️ [DEBUG] Строю Умный Гайд для {real_item}...")

    # 1. Сбор уникальных модов (Дедупликация)
    unique_mods = {} # Имя -> Данные
    
    for mod_query in wanted_mods:
        name, weight, mtype, err = get_mod_data(data, mod_query, tier)
        if err: continue
        
        # Если мод с таким именем уже есть, пропускаем (защита от дублей типа Light Radius/Accuracy)
        if name in unique_mods:
            continue
            
        ess = essence_db.get(name)
        unique_mods[name] = {"name": name, "weight": weight, "type": mtype, "essence": ess}

    if not unique_mods:
        msg = f"❌ Не смог распознать ни один мод для **{real_item}**."
        RESULT_BOX["text"] = msg
        return msg

    # 2. Разделение по типам
    prefixes = [m for m in unique_mods.values() if m['type'] == 'prefix']
    suffixes = [m for m in unique_mods.values() if m['type'] == 'suffix']
    unknowns = [m for m in unique_mods.values() if m['type'] not in ['prefix', 'suffix']]
    
    # Распихиваем неизвестные (обычно суффиксы, если нет данных)
    suffixes.extend(unknowns)
    
    # Сортируем каждую группу по редкости (вес по возрастанию)
    prefixes.sort(key=lambda x: x['weight'])
    suffixes.sort(key=lambda x: x['weight'])

    # === ГЕНЕРАЦИЯ СЦЕНАРИЯ ===
    guide = f"🛡️ **Smart Craft Guide: {real_item}**\n"
    guide += f"📊 Цели: {len(prefixes)} Префиксов, {len(suffixes)} Суффиксов.\n"
    
    guide += f"\n--- АНАЛИЗ ---\n"
    if prefixes: guide += f"🔹 **P:** {', '.join([m['name'] for m in prefixes])}\n"
    if suffixes: guide += f"🔸 **S:** {', '.join([m['name'] for m in suffixes])}\n"
    guide += "\n"

    # --- ШАГ 1: БАЗА (С чего начинать?) ---
    # Мы начинаем с самого редкого мода ВООБЩЕ (среди всех)
    all_sorted = sorted(unique_mods.values(), key=lambda x: x['weight'])
    hardest_mod = all_sorted[0]
    
    # Проверяем, есть ли Эссенция для старта
    start_with_essence = False
    best_essence_mod = None
    
    # Ищем, есть ли эссенции у наших модов
    for m in all_sorted:
        if m['essence']:
            best_essence_mod = m
            break
    
    guide += f"1️⃣ **Шаг 1: Подготовка Базы**\n"
    
    # Сценарий A: Есть очень редкий мод без эссенции -> Фрактур
    if hardest_mod['weight'] < 500 and not hardest_mod['essence']:
        guide += f"⚠️ Мод **{hardest_mod['name']}** очень редкий. Лучше купить базу с **Fractured** этим модом.\n"
        # Убираем его из списка целей, он уже есть
        if hardest_mod in prefixes: prefixes.remove(hardest_mod)
        if hardest_mod in suffixes: suffixes.remove(hardest_mod)
        guide += f"Затем переходим к крафту остальных.\n"
    
    # Сценарий B: Начинаем с Эссенции
    elif best_essence_mod:
        clean = best_essence_mod["essence"].replace("Essence of ", "")
        guide += f"Мы начнем с мода **{best_essence_mod['name']}**, так как для него есть Эссенция.\n"
        guide += f"Кидай **Greater Essence of {clean}**.\n"
        # Убираем этот мод из списка "нужно поймать", мы его гарантировали
        if best_essence_mod in prefixes: prefixes.remove(best_essence_mod)
        if best_essence_mod in suffixes: suffixes.remove(best_essence_mod)
    
    # Сценарий C: Альтерации (для синих вещей)
    else:
        guide += f"Эссенций нет. Берем белую базу, кидаем **Transmutation + Alteration**, пока не поймаем **{hardest_mod['name']}**.\n"
        guide += f"Затем **Regal Orb**.\n"
        if hardest_mod in prefixes: prefixes.remove(hardest_mod)
        if hardest_mod in suffixes: suffixes.remove(hardest_mod)

    # --- ШАГ 2: ДОКРАФТ (Хирургия) ---
    remaining_mods = prefixes + suffixes
    if remaining_mods:
        guide += f"\n2️⃣ **Шаг 2: Добавление свойств**\n"
        
        # Если есть еще моды с эссенциями - предлагаем Perfect
        next_essence_mod = next((m for m in remaining_mods if m["essence"]), None)
        
        if next_essence_mod:
            clean = next_essence_mod["essence"].replace("Essence of ", "")
            guide += f"Следующая цель: **{next_essence_mod['name']}**.\n"
            
            # Логика защиты Оменом
            target_side = next_essence_mod['type']
            if target_side == "prefix":
                guide += f"🛡️ Защити Суффиксы (**Omen of Sinistral Crystallization**).\n"
            else:
                guide += f"🛡️ Защити Префиксы (**Omen of Dextral Crystallization**).\n"
            
            guide += f"🧪 Кидай **Perfect Essence of {clean}**.\n"
        else:
            guide += f"Остались моды без эссенций ({', '.join([m['name'] for m in remaining_mods])}).\n"
            guide += f"Здесь нужен **Exalt Slam** с защитой через Омен (Necromancy).\n"

    # --- ШАГ 3: ФИНИШ ---
    guide += f"\n3️⃣ **Шаг 3: Финиш**\n"
    if len(prefixes) < 3: guide += "🛠 Докрафти Префикс на верстаке (Life/Damage).\n"
    elif len(suffixes) < 3: guide += "🛠 Докрафти Суффикс на верстаке (Resist/Speed).\n"
    else: guide += "🎉 Предмет полон! Кидай Ваал, если смелый.\n"

    print("\n--- [DEBUG] УМНЫЙ ГАЙД ГОТОВ ---")
    RESULT_BOX["text"] = guide
    return guide

def calculate_chance(item_name: str, mod_name: str, tier: int = 1):
    print(f"🚀 [DEBUG] Вход в calculate_chance. Item: {item_name}")
    
    filepath = find_item_file(item_name)
    if not filepath: 
        msg = f"❌ База не найдена для '{item_name}'."
        RESULT_BOX["text"] = msg
        return msg

    try:
        with open(filepath, "r", encoding="utf-8") as f: data = json.load(f)
    except Exception as e:
        msg = f"Ошибка чтения: {e}"
        RESULT_BOX["text"] = msg
        return msg
    
    real_item = data.get("item_name", item_name)
    essence_db = load_essences()
    
    # Чистим ввод от мусора
    raw_mods = mod_name.split(',')
    wanted_mods = [m.strip() for m in raw_mods if len(m.strip()) > 2] 

    return calculate_blue_strategy(data, wanted_mods, tier, real_item, essence_db)