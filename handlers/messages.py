import os
import aiohttp
import uuid
import re
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.crud import get_user
from handlers.callbacks import task_store, ask_compression
from core.progress import ProgressUpdater
from config import TG_API_ID, TG_API_HASH, BOT_TOKEN
from core.tg_downloader import download_large_tg_file

router = Router()

async def download_tg_file(bot, file_path: str, dest_path: str, updater: ProgressUpdater):
    url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            with open(dest_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        updater.update_sync(percent, "TG Server", "Calc...")

@router.message(F.text)
async def handle_text(message: Message, state: FSMContext):
    urls = re.findall(r'https?://[^\s]+', message.text)
    if not urls:
        return

    user = get_user(message.from_user.id)
    if not user or not user.github_token:
        await message.answer("⚠️ Please set your token via /set_token first.")
        return

    batch_id = uuid.uuid4().hex[:8]
    media_domains =["youtube.com", "youtu.be", "twitch.tv", "reddit.com", "vimeo.com", "soundcloud.com"]
    is_media = any(any(d in u for d in media_domains) for u in urls)

    task_store[batch_id] = {
        "urls": urls,
        "quality": "best",
        "is_local": False,
        "is_video": is_media
    }

    if is_media:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🌟 Best Quality", callback_data=f"qual_best_{batch_id}")],[InlineKeyboardButton(text="📺 720p", callback_data=f"qual_720p_{batch_id}"), InlineKeyboardButton(text="📱 480p", callback_data=f"qual_480p_{batch_id}")],[InlineKeyboardButton(text="📉 360p", callback_data=f"qual_360p_{batch_id}"), InlineKeyboardButton(text="🎵 Audio", callback_data=f"qual_audio_{batch_id}")]
        ])
        await message.answer(f"🎬 **{len(urls)} Media link(s) detected!**\nPlease select quality for all:", reply_markup=keyboard, parse_mode="Markdown")
    else:
        await ask_compression(message, batch_id, is_video=is_media)

# fix: improved audio metadata extraction and filename sanitization
@router.message(F.document | F.video | F.photo | F.audio)
async def handle_file(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user or not user.github_token:
        await message.answer("⚠️ Please set your token via /set_token first.")
        return

    def clean_fname(name: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()

    if message.document:
        file_name = message.document.file_name or f"Document_{message.message_id}"
        file_id = message.document.file_id
        file_size = message.document.file_size or 0
    elif message.video:
        file_name = message.video.file_name or f"Video_{message.message_id}.mp4"
        file_id = message.video.file_id
        file_size = message.video.file_size or 0
    elif message.audio:
        if message.audio.performer and message.audio.title:
            raw_name = f"{message.audio.performer} - {message.audio.title}.mp3"
            file_name = clean_fname(raw_name)
        elif message.audio.file_name:
            file_name = message.audio.file_name
        elif message.caption:
            clean_cap = clean_fname(message.caption.split('\n')[0][:50])
            file_name = f"{clean_cap}.mp3" if clean_cap else f"Audio_{message.message_id}.mp3"
        else:
            file_name = f"Audio_{message.message_id}.mp3"

        file_id = message.audio.file_id
        file_size = message.audio.file_size or 0
    else:
        file_name = f"Photo_{message.message_id}.jpg"
        file_id = message.photo[-1].file_id
        file_size = message.photo[-1].file_size or 0

    status_msg = await message.answer("⬇️ **Downloading from Telegram...**", parse_mode="Markdown")
    updater = ProgressUpdater(status_msg, action_text="Fetching File")

    dl_dir = os.path.join("tmp_downloads", uuid.uuid4().hex[:8])
    os.makedirs(dl_dir, exist_ok=True)
    file_path = os.path.join(dl_dir, file_name)

    try:
        if file_size > 20 * 1024 * 1024:
            if not TG_API_ID or not TG_API_HASH:
                await status_msg.edit_text("❌ **File too large!**\n\nAdd `TG_API_ID` and `TG_API_HASH` to `.env` to enable large file support.", parse_mode="Markdown")
                return

            await download_large_tg_file(
                api_id=TG_API_ID, api_hash=TG_API_HASH, bot_token=BOT_TOKEN,
                message_id=message.message_id, chat_id=message.chat.id,
                dest_path=file_path, updater=updater
            )
        else:
            file_info = await message.bot.get_file(file_id)
            await download_tg_file(message.bot, file_info.file_path, file_path, updater)
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Error downloading: {str(e)}")
        return

    batch_id = uuid.uuid4().hex[:8]
    is_vid = bool(message.video or (message.document and message.document.mime_type and message.document.mime_type.startswith('video/')))

    task_store[batch_id] = {"urls": [file_path], "quality": "raw", "is_local": True, "is_video": is_vid}
    await ask_compression(message, batch_id, is_video=is_vid)