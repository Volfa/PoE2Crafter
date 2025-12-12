print("--- ЗАПУСК (ВЕРСИЯ С КОРОБКОЙ): СТАРТ ---")

import asyncio
import logging
import sys
import time

try:
    from aiogram import Bot, Dispatcher, types
    from aiogram.filters import CommandStart
    from google import genai
    from google.genai import types as genai_types
    
    import craft_calc 
    from craft_calc import calculate_chance 
    from unique_calc import calculate_unique
except ImportError as e:
    print(f"ОШИБКА ИМПОРТА: {e}")
    sys.exit()

# КЛЮЧИ (Вставь свои!)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

MODEL_ID = "gemini-2.5-flash" 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = genai.Client(api_key=GEMINI_KEY, http_options={'api_version': 'v1beta'})

SYSTEM_PROMPT = """
Ты — ИИ-помощник ExileForge.
Твоя задача — распарсить текст предмета и вызвать инструмент.

🔥🔥🔥 КАК ЧИТАТЬ ПРЕДМЕТЫ (ВАЖНО!) 🔥🔥🔥
В Path of Exile редкие предметы имеют такую структуру:
Строка 1: Случайное Имя (Например: "Vortex Mitts", "Dusk Fingers", "Loath Bane") -> ИГНОРИРУЙ ЭТО! Это не название предмета.
Строка 2: БАЗА ПРЕДМЕТА (Например: "Commander Gauntlets", "Crude Bow", "Elegant Wraps") -> ВОТ ЭТО НУЖНО БРАТЬ!

ИНСТРУКЦИЯ:
1. Если пользователь прислал описание предмета, пропусти первую строку.
2. Возьми ВТОРУЮ строку и передай её в `item_name`.
3. Собери моды (цифры и плюсы) и передай их в `mod_name`.

ПРИМЕР:
User:
"Vortex Mitts
Commander Gauntlets
..."
Assistant: Вызывает `calculate_chance(item_name="Commander Gauntlets", ...)` (Игнорирует Vortex Mitts!)

Если предмет Уникальный (оранжевый), у него одна строка названия (например "Widowhail"). Тогда бери первую.
"""

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Бот перезапущен. Коробка готова.")

@dp.message()
async def handle_message(message: types.Message):
    user_text = message.text
    print(f"\n📩 Запрос: {user_text[:30]}...") 

    # Очищаем коробку перед запросом!
    craft_calc.RESULT_BOX["text"] = None
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=user_text,
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=[calculate_chance, calculate_unique],
                    temperature=0.1,
                )
            )
            break 
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                print("⏳ Квота. Ждем 20 сек...")
                time.sleep(20)
            else:
                await message.answer(f"Ошибка API: {e}")
                return

    # --- ОТВЕТ (ПРОВЕРКА КОРОБКИ) ---
    
    # 1. Проверяем, положил ли калькулятор что-то в коробку
    box_content = craft_calc.RESULT_BOX["text"]
    
    if box_content:
        print(f"📦 ДОСТАЛ ИЗ КОРОБКИ: {len(box_content)} символов")
        await message.answer(box_content)
        return
    else:
        print("📭 Коробка пуста.")

    # 2. Если коробка пуста, смотрим ответ модели
    if response.text:
        await message.answer(response.text)
    else:
        # Проверка на ручной вызов (если модель вернула вызов, но не выполнила его автоматом - редкость, но бывает)
        if response.candidates and response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            if part.function_call:
                 print("⚙️ Дожим: Модель просит вызвать функцию вручную")
                 # ...тут можно добавить ручной вызов, но обычно в 2.5 работает автомат
                 await message.answer("Модель попыталась вызвать функцию, но коробка осталась пустой. Проверь логи (может файл не нашелся?)")
            else:
                 await message.answer("Бот промолчал.")

async def main():
    print(f"🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())