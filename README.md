<div align="center">
  <h1>🚀 RGit Uploader Bot</h1>
  <p>A powerful Telegram bot to download, process, and push files directly to your GitHub repository for filter-free raw direct links.</p>
</div>

---

## 🔑 How to Get Your GitHub Token (PAT)
To use this bot, you need a **Personal Access Token (PAT)** from your GitHub account so the bot can upload files on your behalf. Follow these simple steps:

1. Go to [GitHub.com](https://github.com) and log in.
2. Click on your profile picture in the top right corner and select **Settings**.
3. Scroll down the left sidebar and click on **Developer settings** (at the very bottom).
4. Click on **Personal access tokens**, then select **Tokens (classic)**.
5. Click the **Generate new token** button -> **Generate new token (classic)**.
6. **Note:** Give it any name (e.g., "RGit Bot").
7. **Expiration:** Set it to *No expiration* (or whatever you prefer).
8. **Select scopes (Crucial Step):** Check the box next to **`repo`** (Full control of private repositories). This gives the bot the `Contents: Write` permission it needs to upload files.
9. Scroll to the bottom and click **Generate token**.
10. Copy your new token (it usually starts with `ghp_...`). **Save it! You won't be able to see it again.**

---

## ⚠️ CRITICAL SETUP INSTRUCTION (MUST READ)

When linking your token and repository to the bot in Telegram, **DO NOT** use brackets like `< >` or `[ ]`. Send the exact string!

❌ **WRONG:** `/set_token <ghp_123456789abcde...>`
✅ **CORRECT:** `/set_token ghp_123456789abcde...`

❌ **WRONG:** `/set_repo <Arshia/MyVideoRepo>`
✅ **CORRECT:** `/set_repo Arshia/MyVideoRepo`

---

## ✨ Features
- ⚡ **Blazing Fast:** Uses `Aria2c` and `yt-dlp` for media and direct links.
- 📁 **Telegram Files:** Supports large files up to 2GB via Pyrogram.
- 🗜️ **Smart Archiving:** Dynamically bypasses GitHub's 100MB file limit by smart-zipping and chunking files.
- 📝 **Auto Links:** Automatically manages `Links.md` with Tehran (IR) timestamps.
- 🧹 **Repo Management:** Clear repository and wipe git history directly from Telegram to free up space.

---

## ⚙️ Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/sandbox.git
   cd sandbox
   ```

2. **Install system dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y aria2 ffmpeg p7zip-full git unzip
   sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
   sudo chmod a+rx /usr/local/bin/yt-dlp
   ```

3. **Install Python dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Environment Variables (`.env`):**
   ```env
   BOT_TOKEN=Your_Telegram_Bot_Token
   TG_API_ID=Your_API_ID
   TG_API_HASH=Your_API_HASH
   YOUTUBE_COOKIES=youtube_cookies.txt  # Optional
   ```

5. **Run the bot:**
   ```bash
   python bot.py
   ```

## 🤖 Telegram Commands
- `/start` - Initialize the bot
- `/set_token PAT` - Link your GitHub token
- `/set_repo user/repo` - Set target repository
- `/status` - Check configuration & repo size
- `/del filename.ext` - Delete specific file
- `/clear_repo` - Wipe all files and Git history
- `/stop` - Cancel active tasks