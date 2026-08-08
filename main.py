import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from yt_dlp import YoutubeDL
from ShazamAPI import Shazam

BOT_TOKEN = "8732653374:AAEWcorFjqEJTJBNsTkPgLPUfruNZrN9wv8"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()




YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(id)s.%(ext)s',
}

# Foydalanuvchilar qidirgan natijalarini vaqtincha saqlash uchun lug'at
user_search_results = {}

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Salom! Menga Instagram/YouTube havolasini, oddiy video yoki ovozli xabar (voice) yuboring, musiqasini topib beraman.")

# 1. Instagram/YouTube havolalari uchun
@dp.message(F.text & (F.text.contains("instagram.com") | F.text.contains("youtube.com") | F.text.contains("youtu.be")))
async def handle_link(message: types.Message):
    url = message.text
    status_msg = await message.answer("⏳ Video yuklanmoqda...")
    try:
        with YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
        
        await status_msg.edit_text("🔍 Musiqa qidirilmoqda...")
        
        caption_text = "✅ Video yuklab olindi!"
        try:
            with open(file_path, 'rb') as f:
                shazam = Shazam(f.read())
                recognize_generator = shazam.recognizeSong()
                for offset, match in recognize_generator:
                    if match.get('track'):
                        title = match['track']['title']
                        artist = match['track']['subtitle']
                        caption_text = f"🎵 {artist} — {title}"
                        break
        except Exception:
            caption_text = "⚠️ Afsuski musiqa aniqlanmadi."

        video_file = types.FSInputFile(file_path)
        await message.answer_video(video=video_file, caption=caption_text)
        
        if os.path.exists(file_path):
            os.remove(file_path)
        await status_msg.delete()
    except Exception:
        await status_msg.edit_text("❌ Xatolik bo'ldi yoki video hajmi juda katta.")

# 2. Ovozli xabar (voice) yoki oddiy video fayl tashlaganda shazam qilish uchun
@dp.message(F.voice | F.video)
async def handle_media_file(message: types.Message):
    status_msg = await message.answer("🔍 Fayldan musiqa qidirilmoqda...")
    try:
        file_id = message.voice.file_id if message.voice else message.video.file_id
        file = await bot.get_file(file_id)
        file_path = f"temp_{message.from_user.id}.mp4"
        await bot.download_file(file.file_path, file_path)

        with open(file_path, 'rb') as f:
            shazam = Shazam(f.read())
            recognize_generator = shazam.recognizeSong()
            found = False
            for offset, match in recognize_generator:
                if match.get('track'):
                    title = match['track']['title']
                    artist = match['track']['subtitle']
                    found = True
                    break
        
        if os.path.exists(file_path):
            os.remove(file_path)
        
        if found:
            query = f"ytsearch1: {artist} - {title}"
        else:
            await status_msg.edit_text("❌ Musiqa topilmadi.")
            return

        await status_msg.edit_text(f"Topildi: {artist} - {title}. Qidirilmoqda...")
        
        with YoutubeDL({'format': 'bestaudio', 'extract_flat': True}) as ydl:
            results = ydl.extract_info(query, download=False)
            
        if 'entries' in results and results['entries']:
            entry = results['entries'][0]
            audio_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
            
            # Musiqani yuklab yuborish
            with YoutubeDL(YDL_OPTIONS) as ydl:
                audio_info = ydl.extract_info(audio_url, download=True)
                audio_path = ydl.prepare_filename(audio_info)
            
            audio_file = types.FSInputFile(audio_path)
            await message.answer_audio(audio=audio_file, caption=f"🎵 {artist} — {title}")
            
            if os.path.exists(audio_path):
                os.remove(audio_path)
            await status_msg.delete()
        else:
            await status_msg.delete()
            await message.answer("❌ Internetdan musiqa topib bo'lmadi.")
            
    except Exception as e:
        await status_msg.edit_text("❌ Xatolik yuz berdi.")

# 3. Oddiy matn (so'z yoki qo'shiq nomi) yozib yuborganda 5 talik ro'yxat va tugmalar chiqarish
@dp.message(F.text)
async def search_song(message: types.Message):
    query_text = message.text
    status_msg = await message.answer("🔍 Qidirilmoqda...")
    try:
        query = f"ytsearch5:{query_text}"
        with YoutubeDL({'format': 'bestaudio', 'extract_flat': True}) as ydl:
            results = ydl.extract_info(query, download=False)

        if 'entries' in results and results['entries']:
            entries = results['entries'][:5]
            user_search_results[message.from_user.id] = entries
            
            text_res = f"🎵 **{query_text}** bo'yicha topilgan natijalar:\n\n"
            builder = InlineKeyboardBuilder()
            
            for i, entry in enumerate(entries, 1):
                title = entry.get('title', 'Nomaʼlum')
                text_res += f"{i}. {title}\n"
                builder.button(text=str(i), callback_data=f"dl_{i}")
            
            builder.adjust(5)
            await message.answer(text_res, reply_markup=builder.as_markup(), parse_mode="Markdown")
        else:
            await message.answer("❌ Hech narsa topilmadi.")
    except Exception:
        await message.answer("❌ Qidirishda xatolik yuz berdi.")
    
    await status_msg.delete()

# 4. Raqamli tugmalarni bosganda musiqani yuklab tashlab berish
@dp.callback_query(F.data.startswith("dl_"))
async def download_selected_audio(callback: types.CallbackQuery):
    index = int(callback.data.split("_")[1]) - 1
    user_id = callback.from_user.id
    
    if user_id not in user_search_results or index >= len(user_search_results[user_id]):
        await callback.answer("Eskirgan natija, qaytadan qidiring!", show_alert=True)
        return
        
    entry = user_search_results[user_id][index]
    video_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
    title = entry.get('title', 'Musiqa')
    
    await callback.answer("Musiqa yuklanmoqda, kuting...")
    
    try:
        with YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(video_url, download=True)
            file_path = ydl.prepare_filename(info)
            
        audio_file = types.FSInputFile(file_path)
        await callback.message.answer_audio(audio=audio_file, caption=f"🎵 {title}")
        
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        await callback.message.answer("❌ Musiqani yuklab bo'lmadi.")

async def handle(request):
    return web.Response(text="Bot is running!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
