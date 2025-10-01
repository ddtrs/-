import logging
import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")  # берем токен из переменных окружения

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Хранилище ссылок, чтобы потом резать и качать
user_links = {}

# старт
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("👋 Привет! Я бот для скачивания с YouTube.\n"
                         "Отправь мне ссылку на видео.")

# получаем ссылку
@dp.message_handler(lambda msg: "youtube.com" in msg.text or "youtu.be" in msg.text)
async def get_video(message: types.Message):
    url = message.text
    user_links[message.from_user.id] = url

    # вытаскиваем инфо о видео
    ydl_opts = {"quiet": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    title = info.get("title", "Видео")
    formats = info.get("formats", [])

    # кнопки с вариантами
    kb = InlineKeyboardMarkup()
    added = set()
    for f in formats:
        if f.get("ext") == "mp4" and f.get("height") and f["height"] <= 720:
            q = f"{f['height']}p"
            if q not in added:
                kb.add(InlineKeyboardButton(f"🎥 {q}", callback_data=f"video_{f['height']}"))
                added.add(q)

    kb.add(InlineKeyboardButton("🎵 MP3 (аудио)", callback_data="audio"))

    await message.answer(f"Нашёл видео: <b>{title}</b>\nВыбери качество 👇",
                         parse_mode="HTML", reply_markup=kb)

# обработка кнопок
@dp.callback_query_handler(lambda call: call.data.startswith("video_") or call.data == "audio")
async def process_choice(call: types.CallbackQuery):
    url = user_links.get(call.from_user.id)
    if not url:
        await call.answer("Сначала отправь ссылку!")
        return

    await call.message.answer("⏳ Скачиваю...")

    if call.data == "audio":
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": "download.%(ext)s",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        }
    else:
        height = call.data.split("_")[1]
        ydl_opts = {
            "format": f"bestvideo[height={height}]+bestaudio/best[height<={height}]",
            "outtmpl": "download.%(ext)s"
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        if call.data == "audio":
            filename = filename.rsplit(".", 1)[0] + ".mp3"

        with open(filename, "rb") as f:
            if call.data == "audio":
                await call.message.answer_audio(f)
            else:
                await call.message.answer_video(f)

        os.remove(filename)

    except Exception as e:
        await call.message.answer(f"❌ Ошибка: {e}")

# запуск
async def main():
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
