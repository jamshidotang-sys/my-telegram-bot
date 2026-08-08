        import asyncio
import logging
import os
import re
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
import yt_dlp

TOKEN = "SIZNING_BOT_TOKENINGIZ"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "Assalomu alaykum! 👋\n"
        "Menga Instagram'dan **Reels**, **Post** yoki **Video** havolasini yuboring, darhol yuklab beraman!"
    )

@dp.message(F.text)
async def download_instagram_media(message: types.Message):
    url = message.text.strip()
    
    if not re.search(r"instagram\.com", url):
        await message.answer("⚠️ Iltimos, faqat Instagram havolasini yuboring! (YouTube va musiqa qidirish vaqtincha o'chirilgan)")
        return

    processing_msg = await message.answer("⏳ Media yuklab olinmoqda, biroz kuting...")
    
    output_template = "downloads/%(id)s.%(ext)s"
    os.makedirs("downloads", exist_ok=True)
    
    ydl_opts = {
        'outtmpl': output_template,
        'format': 'best',
        'quiet': True,
    }

    file_path = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        if file_path and os.path.exists(file_path):
            input_file = types.FSInputFile(file_path)
            await message.answer_video(
                video=input_file,
                caption="📥 SaveIt Bot orqali yuklab olindi!"
            )
            await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        else:
            await processing_msg.edit_text("❌ Videoni yuklab bo'lmadi. Havola yopiq profilga tegishli bo'lishi mumkin.")

    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await processing_msg.edit_text("❌ Xatolik yuz berdi. Boshqa havola yuborib ko'ring.")
    
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
