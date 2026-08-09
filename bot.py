import os
import asyncio
import logging
import yt_dlp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = "8732653374:AAEWcorFjqEJTJBNsTkPgLPUfruNZrN9wv8"
CHANNEL_USERNAME = "@samurayX77"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_search_results = {}

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["member", "creator", "administrator"]:
            return True
    except Exception:
        pass
    return False

async def ask_subscription(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"))
    builder.row(types.InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub"))
    
    await message.answer(
        "<b>⚠️ Botdan foydalanish uchun kanalimizga obuna bo'ling:</b>\n\n"
        f"👉 {CHANNEL_USERNAME}\n\n"
        "Obuna bo'lib, <b>'✅ Obunani tekshirish'</b> tugmasini bosing!",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await ask_subscription(message)
        return

    text = (
        "🔥 <b>Assalomu alaykum! Botga xush kelibsiz.</b>\n\n"
        "• <b>Instagram / TikTok / YouTube link</b> yuborsangiz — video yuklab beraman.\n"
        "• <b>Qo'shiq yoki artist nomini</b> yozsangiz — 10 tagacha musiqa topib beraman!"
    )
    await message.answer(text, parse_mode="HTML")

@dp.callback_query(F.data == "check_sub")
async def verify_subscription(callback: types.CallbackQuery):
    if await check_subscription(callback.from_user.id):
        await callback.message.delete()
        await callback.message.answer("<b>Rahmat! Endi havola yoki qo'shiq nomini yuborishingiz mumkin:</b>", parse_mode="HTML")
    else:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)

# Havolalar uchun
@dp.message(F.text & (F.text.contains("http://") | F.text.contains("https://")))
async def handle_link(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await ask_subscription(message)
        return

    url = message.text.strip()
    status_msg = await message.answer("⏳ Yuklanmoqda, kuting...")
    
    file_path = None
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'socket_timeout': 15,
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'noplaylist': True,
        }
        
        os.makedirs("downloads", exist_ok=True)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        if file_path and os.path.exists(file_path):
            video_file = types.FSInputFile(file_path)
            await message.answer_video(
                video=video_file,
                caption="📥 @muzika_skachat_video_bot orqali yuklab olindi"
            )
            os.remove(file_path)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ Faylni yuklab bo'lmadi.")
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        try:
            audio_opts = {
                'format': 'bestaudio/best',
                'outtmpl': 'downloads/%(id)s.%(ext)s',
                'noplaylist': True,
            }
            with yt_dlp.YoutubeDL(audio_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
            if file_path and os.path.exists(file_path):
                audio_file = types.FSInputFile(file_path)
                await message.answer_audio(audio=audio_file, caption="🎵 @muzika_skachat_video_bot")
                os.remove(file_path)
                await status_msg.delete()
                return
        except:
            pass

        await status_msg.edit_text("❌ Xatolik yuz berdi. Video hajmi juda katta yoki yopiq.")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# Qo'shiq nomi bo'yicha 10 ta qidirish
@dp.message(F.text)
async def search_song(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await ask_subscription(message)
        return

    query = message.text.strip()
    status_msg = await message.answer(f"🔍 <b>{query}</b> bo'yicha 10 ta musiqa qidirilmoqda...", parse_mode="HTML")

    try:
        ydl_opts = {
            'format': 'bestaudio',
            'default_search': 'ytsearch10',  # 10 ta qilib o'zgartirildi
            'noplaylist': True,
            'quiet': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get('entries', [])

        if not entries:
            await status_msg.edit_text("❌ Hech qanday musiqa topilmadi.")
            return

        response_text = f"🎵 <b>{query}</b> bo'yicha topilgan natijalar:\n\n"
        builder = InlineKeyboardBuilder()
        user_search_results[message.from_user.id] = []

        for idx, entry in enumerate(entries, 1):
            title = entry.get('title', 'Nomaʼlum')
            url = entry.get('url')
            duration = entry.get('duration_string', '')
            
            user_search_results[message.from_user.id].append({'title': title, 'url': url})
            response_text += f"<b>{idx}.</b> {title} <code>{duration}</code>\n"
            builder.add(types.InlineKeyboardButton(text=str(idx), callback_data=f"dl_{idx-1}"))

        builder.adjust(5) # Har bir qatorda 5 tadan tugma joylashadi (1 dan 10 gacha)
        await status_msg.delete()
        await message.answer(response_text, reply_markup=builder.as_markup(), parse_mode="HTML")

    except Exception as e:
        logging.error(f"Qidirishda xato: {e}")
        await status_msg.edit_text("❌ Qidirish vaqtida xatolik yuz berdi. Boshqa nom yozib ko'ring.")

@dp.callback_query(F.data.startswith("dl_"))
async def download_selected_audio(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_search_results:
        await callback.answer("Eski qidiruv natijasi. Qaytadan qidiring.", show_alert=True)
        return

    index = int(callback.data.split("_")[1])
    tracks = user_search_results[user_id]
    
    if index >= len(tracks):
        await callback.answer("Xatolik yuz berdi.", show_alert=True)
        return

    track = tracks[index]
    status_msg = await callback.message.answer(f"📥 <b>{track['title']}</b> yuklanmoqda...", parse_mode="HTML")

    file_path = None
    try:
        audio_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'noplaylist': True,
        }
        
        os.makedirs("downloads", exist_ok=True)
        with yt_dlp.YoutubeDL(audio_opts) as ydl:
            info = ydl.extract_info(track['url'], download=True)
            file_path = ydl.prepare_filename(info)

        if file_path and os.path.exists(file_path):
            audio_file = types.FSInputFile(file_path)
            await callback.message.answer_audio(audio=audio_file, caption=f"🎵 {track['title']}\n🤖 @muzika_skachat_video_bot")
            os.remove(file_path)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ Musiqani yuklab bo'lmadi.")
    except Exception as e:
        logging.error(f"Audio yuklashda xato: {e}")
        await status_msg.edit_text("❌ Musiqani yuklab bo'lmadi.")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
