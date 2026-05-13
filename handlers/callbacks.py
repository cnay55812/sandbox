# file name ./handlers/callbacks.py
import os
import asyncio
import html
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.crud import get_user
from core.ytdlp_engine import download_media
from core.downloader import download_direct
from core.bunkr_engine import is_bunkr_url, download_bunkr
from core.progress import ProgressUpdater
from core.archiver import process_archive
from github_integration.git_manager import push_to_github
from config import YOUTUBE_COOKIES

router = Router()
task_store = {}
active_tasks = {}

class DownloadWorkflow(StatesGroup):
    waiting_for_password = State()

async def ask_compression(message: Message, batch_id: str, is_video: bool = False):
    raw_buttons = [InlineKeyboardButton(text="📄 Raw (Normal)", callback_data=f"comp_rawnormal_{batch_id}")]

    # NOTE: Only show the 5-min chunk option if the file is a video
    if is_video:
        raw_buttons.append(InlineKeyboardButton(text="🎬 Raw (5-Min Chunks)", callback_data=f"comp_rawchunk_{batch_id}"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        raw_buttons,
        [InlineKeyboardButton(text="📦 Zip (Max Compression)", callback_data=f"comp_zip_{batch_id}")],
        [InlineKeyboardButton(text="🔐 Zip with Password", callback_data=f"comp_pass_{batch_id}")]
    ])
    await message.answer("📥 **Ready!**\nHow should I process the batch?", reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data.startswith("qual_"))
async def process_quality(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    quality = parts[1]
    batch_id = parts[2] if len(parts) > 2 else ""

    if batch_id not in task_store:
        return await callback.answer("⚠️ Session expired!", show_alert=True)

    task_store[batch_id]["quality"] = quality
    await callback.message.delete()

    is_vid = task_store[batch_id].get("is_video", False)
    await ask_compression(callback.message, batch_id, is_video=is_vid)

@router.callback_query(F.data.startswith("comp_"))
async def process_compression(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    comp_type = parts[1]
    batch_id = parts[2] if len(parts) > 2 else ""

    if batch_id not in task_store:
        return await callback.answer("⚠️ Session expired!", show_alert=True)

    if comp_type == "pass":
        await callback.message.edit_text("🔐 **Send password for the Zip files:**", parse_mode="Markdown")
        await state.set_state(DownloadWorkflow.waiting_for_password)
        await state.update_data(batch_id=batch_id)
        return

    task_store[batch_id]["compression"] = comp_type
    status_msg = await callback.message.edit_text("⏳ **Starting Batch Process...**", parse_mode="Markdown")

    task = asyncio.create_task(run_batch(status_msg, batch_id, callback.message.chat.id))
    active_tasks[callback.message.chat.id] = task

@router.message(DownloadWorkflow.waiting_for_password)
async def handle_password(message: Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    batch_id = data.get("batch_id")
    await state.clear()

    if not batch_id or batch_id not in task_store:
        return await message.answer("❌ Session expired.")

    task_store[batch_id]["compression"] = "zip_pass"
    task_store[batch_id]["zip_password"] = password

    status_msg = await message.answer("⏳ **Starting Batch Process...**", parse_mode="Markdown")
    task = asyncio.create_task(run_batch(status_msg, batch_id, message.chat.id))
    active_tasks[message.chat.id] = task

async def run_batch(status_msg: Message, batch_id: str, chat_id: int):
    try:
        data = task_store.pop(batch_id, {})
        urls = data.get("urls",[])
        quality = data.get("quality", "best")
        comp_mode = data.get("compression", "raw")
        password = data.get("zip_password", "None")
        is_local = data.get("is_local", False)

        user = get_user(chat_id)
        success_links = []
        failed_links =[]

        await status_msg.edit_text(f"🚀 <b>Processing {len(urls)} link(s)...</b>\nPlease wait.", parse_mode="HTML")

        for idx, url in enumerate(urls, 1):
            file_msg = None
            try:
                safe_url = html.escape(url[:40])
                file_msg = await status_msg.answer(
                    f"🔄 <b>[{idx}/{len(urls)}] Processing:</b> <code>{safe_url}...</code>",
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                updater = ProgressUpdater(file_msg, action_text="Downloading File")

                downloaded_file = None
                if is_local:
                    downloaded_file = url
                else:
                    media_domains =["youtube.com", "youtu.be", "twitch.tv", "reddit.com", "vimeo.com", "soundcloud.com"]
                    if is_bunkr_url(url):
                        downloaded_file = await download_bunkr(url, updater)
                    elif any(domain in url for domain in media_domains):
                        downloaded_file = await download_media(url, quality, updater, YOUTUBE_COOKIES)
                    else:
                        downloaded_file = await download_direct(url, updater)

                if not downloaded_file or not os.path.exists(downloaded_file):
                    raise Exception("Failed to retrieve file.")

                try:
                    final_files = await process_archive(downloaded_file, comp_mode, password, updater)
                    try:
                        raw_links = await push_to_github(chat_id, user, final_files, updater)
                        success_links.extend(raw_links)
                        await file_msg.delete()
                    finally:
                        for f in final_files:
                            if os.path.exists(f): os.remove(f)
                finally:
                    if downloaded_file and not is_local and os.path.exists(downloaded_file):
                        os.remove(downloaded_file)

            except Exception as e:
                error_text = html.escape(str(e).replace('\n', ' '))
                if len(error_text) > 200:
                    error_text = error_text[:200] + "..."

                failed_links.append(f"❌ <code>{html.escape(url[:30])}</code> -> {error_text}")

                if file_msg:
                    try:
                        await file_msg.edit_text(f"❌ <b>[{idx}/{len(urls)}] Failed!</b>\n<code>{error_text}</code>", parse_mode="HTML")
                    except:
                        pass

            if idx < len(urls):
                await asyncio.sleep(5)

        final_text = f"🏁 <b>Batch Completed! ({len(urls)} Links)</b>\n\n"
        if success_links:
            links_str = "\n\n".join(success_links)
            final_text += f"✅ <b>Successful Uploads:</b>\n{links_str}\n\n"
        if failed_links:
            fails_str = "\n".join(failed_links)
            final_text += f"❌ <b>Failed Uploads:</b>\n{fails_str}"

        if len(final_text) <= 4000:
            await status_msg.edit_text(final_text, parse_mode="HTML", disable_web_page_preview=True)
        else:
            await status_msg.edit_text("🏁 <b>Batch Completed!</b>\nSending results...", parse_mode="HTML")
            lines = final_text.split('\n')
            chunk = ""
            for line in lines:
                if len(chunk) + len(line) + 1 > 4000:
                    await status_msg.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)
                    chunk = line + "\n"
                    await asyncio.sleep(1)
                else:
                    chunk += line + "\n"
            if chunk.strip():
                await status_msg.answer(chunk, parse_mode="HTML", disable_web_page_preview=True)

    except asyncio.CancelledError:
        try:
            await status_msg.edit_text("🛑 <b>Operation Cancelled!</b>\nProcess stopped and temporary files are cleared.", parse_mode="HTML")
        except:
            pass
        raise
    finally:
        active_tasks.pop(chat_id, None)