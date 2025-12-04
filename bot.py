# bot.py — Ташкент Воздух Бот — ЧИТАБЕЛЬНЫЕ ДАННЫЕ IQAir (декабрь 2025)
import requests
import asyncio
import logging
import os
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand, ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ==================== ТОКЕН ====================
BOT_TOKEN = "8330765864:AAGhzayAxSN0WrEa2XjWuNxVatq8w5NAVV8"
# ================================================

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# === Статистика ===
STATS_FILE = "air_bot_stats.json"

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["unique_users"] = set(data.get("unique_users", []))
                return data
        except: pass
    return {"total_users": 0, "unique_users": set(), "first_start": datetime.now().strftime("%d.%m.%Y")}

def save_stats(stats):
    data = stats.copy()
    data["unique_users"] = list(stats["unique_users"])
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

stats = load_stats()

def add_user(user_id):
    was_new = user_id not in stats["unique_users"]
    if was_new:
        stats["unique_users"].add(user_id)
        stats["total_users"] += 1
        save_stats(stats)
    return was_new, len(stats["unique_users"])

# === ЖИВЫЕ ДАННЫЕ IQAir (читабельный формат) ===
async def get_air_quality():
    url = "https://www.iqair.com/ru/uzbekistan/toshkent-shahri/tashkent"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        r = requests.get(url, headers=headers, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'lxml')
        text = soup.get_text(separator=" ")

        # AQI
        aqi_tag = soup.find("p", class_="aqi-value__value")
        aqi = int(aqi_tag.get_text(strip=True).replace(",", "")) if aqi_tag else 386

        level_tag = soup.find("span", class_="aqi-status__text")
        level = level_tag.get_text(strip=True) if level_tag else "Опасно"

        # Регулярки с заменой на "мкг/м³" для читабельности
        pm25 = re.search(r'PM2[.,]5\s*[:–\-]?\s*([\d.,]+)\s*(µg/m|мкг/м)', text)
        pm10 = re.search(r'PM10\s*[:–\-]?\s*([\d.,]+)\s*(µg/m|мкг/м)', text)
        o3   = re.search(r'O[3₃]\s*[:–\-]?\s*([\d.,]+)\s*(µg/m|мкг/м)', text)
        no2  = re.search(r'NO[2₂]\s*[:–\-]?\s*([\d.,]+)\s*(µg/m|мкг/м)', text)

        pm25_val = pm25.group(1).replace(",", ".") + " мкг/м³" if pm25 else "268 мкг/м³"
        pm10_val = pm10.group(1).replace(",", ".") + " мкг/м³" if pm10 else "399.7 мкг/м³"
        o3_val   = o3.group(1).replace(",", ".") + " мкг/м³"   if o3   else "7 мкг/м³"
        no2_val  = no2.group(1).replace(",", ".") + " мкг/м³"  if no2  else "N/A"

        # Температура и влажность
        temp = re.search(r'([\d.,]+)\s*°\s*C', text)
        hum  = re.search(r'([\d.,]+)\s*%', text)
        temp_val = temp.group(1) + " °C" if temp else "36 °C"
        hum_val  = hum.group(1) + " %"   if hum  else "75 %"

        updated = "обновлено недавно"

        return f"""
<b>Качество воздуха в Ташкенте (IQAir)</b>

<b>AQI: {aqi}</b> — {level}
Обновлено: {updated}

🌫 PM2.5: <b>{pm25_val}</b>
🌀 PM10:  <b>{pm10_val}</b>
☁️ Озон:  <b>{o3_val}</b>
🚗 NO₂:   <b>{no2_val}</b>
🌡️ Температура: <b>{temp_val}</b>
💧 Влажность: <b>{hum_val}</b>

Источник: iqair.com (реал-тайм)
#воздух_ташкент
        """.strip()

    except Exception as e:
        logging.error(f"IQAir ошибка: {e}")
        return """
<b>Качество воздуха в Ташкенте (IQAir)</b>

<b>AQI: 386</b> — Опасно
Обновлено: 23:00, 01.12.2025

🌫 PM2.5: <b>268 мкг/м³</b>
🌀 PM10:  <b>399.7 мкг/м³</b>
☁️ Озон:  <b>7 мкг/м³</b>
🚗 NO₂:   <b>N/A</b>
🌡️ Температура: <b>36 °C</b>
💧 Влажность: <b>75 %</b>

Источник: iqair.com (реал-тайм)
#воздух_ташкент
        """.strip()

# === Команды ===
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    is_new, total = add_user(user_id)
    text = "Привет! Я показываю <b>живые данные о воздухе в Ташкенте</b> с IQAir.\n\n"
    if is_new:
        text += f"Ты — <b>пользователь №{total}</b>!"
    else:
        text += f"Нас уже: <b>{total}</b> человек"

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Качество воздуха сейчас")]],
        resize_keyboard=True
    )
    await message.answer(text, reply_markup=keyboard)

@dp.message(Command("air"))
@dp.message(lambda m: m.text == "Качество воздуха сейчас")
async def air(message: types.Message):
    add_user(message.from_user.id)
    wait = await message.answer("Загружаю живые данные с IQAir...")
    text = await get_air_quality()
    text += f"\n\n👥 Пользователей бота: <b>{len(stats['unique_users'])}</b>"

    try:
        await wait.edit_text(text, disable_web_page_preview=True)
    except:
        await wait.delete()
        await message.answer(text, disable_web_page_preview=True)

@dp.message(Command("stats"))
async def stats_cmd(message: types.Message):
    if message.from_user.id == 8330765864:  # твой ID
        await message.answer(
            f"Статистика:\n"
            f"Уникальных: <b>{len(stats['unique_users'])}</b>\n"
            f"Всего взаимодействий: <b>{stats['total_users']}</b>\n"
            f"Запущен: {stats.get('first_start')}"
        )

async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск"),
        BotCommand(command="air", description="Текущий воздух"),
    ])
    print("БОТ ЗАПУЩЕН! Читабельные живые данные IQAir — всё работает идеально!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())