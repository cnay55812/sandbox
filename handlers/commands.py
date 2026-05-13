import os
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from database.crud import create_or_update_user, get_user
from github_integration.git_manager import delete_file_from_github, clear_github_repo
from config import YOUTUBE_COOKIES
from handlers.callbacks import active_tasks
import aiohttp

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    create_or_update_user(message.from_user.id)
    welcome_text = (
        "👋 **Welcome to RGit uploader!**\n\n"
        "I'm here to bypass restrictions and upload files directly to your GitHub repository.\n\n"
        "⚙️ **Setup Instructions:**\n"
        "1️⃣ `/set_token <YOUR_GITHUB_PAT>` - Set your PAT.\n"
        "2️⃣ `/set_repo <username/repo>` - Set your target repository.\n\n"
        "💡 *Just send me any direct link, file, or media URL to start!*"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

@router.message(Command("set_token"))
async def set_token(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ **Usage:** `/set_token <PAT>`", parse_mode="Markdown")
        return
    create_or_update_user(message.from_user.id, github_token=args[1].strip())
    await message.answer("✅ **GitHub Token saved!**", parse_mode="Markdown")

@router.message(Command("set_repo"))
async def set_repo(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ **Usage:** `/set_repo <user/repo>`", parse_mode="Markdown")
        return
    create_or_update_user(message.from_user.id, github_repo=args[1].strip())
    await message.answer(f"✅ **Repo set to:** `{args[1].strip()}`", parse_mode="Markdown")

@router.message(Command("status"))
async def cmd_status(message: Message):
    user = get_user(message.from_user.id)
    if not user: return

    t_st = "✅" if user.github_token else "❌"
    r_st = f"✅ `{user.github_repo}`" if user.github_repo else "❌"
    c_st = "✅ (Global)" if YOUTUBE_COOKIES else "❌ `Not set in .env`"

    repo_size_str = "Unknown"
    if user.github_token and user.github_repo:
        headers = {"Authorization": f"Bearer {user.github_token}"}
        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.get(f"https://api.github.com/repos/{user.github_repo}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        size_kb = data.get("size", 0)
                        if size_kb > 1048576:
                            repo_size_str = f"{size_kb / 1048576:.2f} GB"
                        else:
                            repo_size_str = f"{size_kb / 1024:.2f} MB"
            except Exception:
                repo_size_str = "Error fetching"

    text = f"📊 **Status:**\n\n🔑 **User Token:** {t_st}\n📁 **User Repo:** {r_st}\n📦 **Repo Size:** `{repo_size_str}`\n🍪 **Global Cookies:** {c_st}"
    await message.answer(text, parse_mode="Markdown")
@router.message(Command("del"))
async def cmd_delete_file(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ **Usage:** `/del <filename.ext>`\nExample: `/del Video_123.mp4`", parse_mode="Markdown")
        return

    user = get_user(message.from_user.id)
    if not user or not user.github_token:
        return await message.answer("⚠️ GitHub token not set.")

    filename = args[1].strip()
    status = await message.answer(f"⏳ Deleting `{filename}` from GitHub...", parse_mode="Markdown")
    try:
        await delete_file_from_github(user, filename)
        await status.edit_text(f"✅ **Deleted successfully!**\n`{filename}` was removed from Repo and Links.md.", parse_mode="Markdown")
    except Exception as e:
        await status.edit_text(f"❌ **Failed to delete:**\n`{str(e)}`", parse_mode="Markdown")

@router.message(Command("clear_repo"))
async def cmd_clear_repo(message: Message):
    user = get_user(message.from_user.id)
    if not user or not user.github_token:
        return await message.answer("⚠️ GitHub token not set.")

    status = await message.answer("🧹 **Clearing repository...**\nDeleting all files in `dl/` and resetting Links.md.", parse_mode="Markdown")
    try:
        await clear_github_repo(user)
        await status.edit_text("✅ **Repository Cleared!**\nAll files have been successfully deleted.", parse_mode="Markdown")
    except Exception as e:
        await status.edit_text(f"❌ **Failed to clear repo:**\n`{str(e)}`", parse_mode="Markdown")

@router.message(Command("stop"))
async def cmd_stop(message: Message):
    user_id = message.from_user.id
    if user_id in active_tasks:
        active_tasks[user_id].cancel()
        await message.answer("🛑 **Stopping process...**\nPlease wait a moment for cleanup.", parse_mode="Markdown")
    else:
        await message.answer("⚠️ You have no active downloads/uploads running.", parse_mode="Markdown")