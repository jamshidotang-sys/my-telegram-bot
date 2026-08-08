from aiohttp import web

import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from yt_dlp import YoutubeDL
from ShazamAPI import Shazam

BOT_TOKEN = "8732653374:AAEWcorFjqEJTJBNsTkPgLPUfruNZrN9wv8"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

YDL_OPTIONS = {
    'format': 'best',
    'outtmpl': '%(id)s.%(ext)s',
    'max_filesize': 50 * 1024 * 1024,
}

@dp.message()
async def process_message(message: types.Message):
    url = message.text
    
    # 1. Agar foydalanuvchi havola (link) yuborgan bo'lsa
    if "instagram.com" in url or "youtube.com" in url or "youtu.be" in url:
        status_msg = await message.answer("⏳ Video yuklanmoqda...")
        try:
            with YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
            
            await status_msg.edit_text("🔍 Musiqa qidirilmoqda...")
            
            # Videodagi musiqani Shazam orqali topishga harakat qilamiz
            caption_text = "✅ Video yuklab olindi!"
            try:
                with open(file_path, 'rb') as f:
                    shazam = Shazam(f.read())
                    recognize_generator = shazam.recognizeSong()
                    for offset, match in recognize_generator:
                        if match.get('track'):
                            title = match['track']['title']
                            artist = match['track']['subtitle']
                            caption_text = f"✅ Video yuklab olindi!\n🎵 Musiqa: {artist} - {title}"
                            break
            except Exception:
                caption_text = "✅ Video yuklab olindi!\n⚠️ Afsuski musiqa topilmadi."

            video_file = types.FSInputFile(file_path)
            await message.answer_video(video=video_file, caption=caption_text)
            
            if os.path.exists(file_path):
                os.remove(file_path)
            await status_msg.delete()
            
        except Exception:
            await status_msg.exit_text("❌ Xatolik bo'ldi yoki video hajmi 50MB dan katta.") if 'status_msg' in locals() else await message.answer("❌ Xatolik yuz berdi.")
            
    # 2. Agar havola emas, shunchaki so'z (qo'shiq nomi) yozilgan bo'lsa
    else:
        status_msg = await message.answer("🔍 Qidirilmoqda...")
        try:
            query = f"ytsearch10:{url}"  # 10 ta natija qidirish
            with YoutubeDL({'format': 'bestaudio', 'extract_flat': True}) as ydl:
                results = ydl.extract_info(query, download=False)
                
            if 'entries' in results and results['entries']:
                text_res = f"🎵 *{url}* bo'yicha topilgan natijalar:\n\n"
                for i, entry in enumerate(results['entries'], 1):
                    title = entry.get('title', 'Nomaʼlum')
                    text_res += f"{i}. {title}\n"
                await message.answer(text_res, parse_mode="Markdown")
            else:
                await message.answer("❌ Hech narsa topilmadi.")
        except Exception:
            await message.answer("❌ Qidirishda xatolik yuz berdi.")
        
        await status_msg.delete()
                

            video_file = types.FSInputFile(file_path)
            await message.answer_video(video=video_file, caption=caption_text)

            if os.path.exists(file_path):
                os.remove(file_path)
            await status_msg.delete()
        except Exception:
            await status_msg.edit_text("❌ Xatolik bo'ldi yoki video hajmi 50MB dan katta.")
    else:
        await message.answer("To'g'ri havola kiriting.")

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
        
