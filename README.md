<div align="center">
  <h1>🚀 RGit Uploader Bot</h1>
  <p>A powerful Telegram bot that acts as an ultimate download and bypass tool. It downloads direct links, videos, local Telegram files, processes them, and pushes them directly to your GitHub repository to generate filter-free raw direct links.</p>
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

- ⚡ **Blazing Fast Downloads:** Uses `Aria2c` (up to 4 concurrent connections) for direct links.
- 🎬 **Media Extraction:** Integrated with `yt-dlp` to download videos from YouTube, Twitch, Vimeo, Reddit, SoundCloud, and more.
- 🔓 **Bunkr Bypass:** Built-in custom API decryptor to download directly from Bunkr domains without restrictions.
- 📁 **Telegram File Support:** Forward or upload any local file (Document, Video, Audio, Photo) directly to the bot. **Supports large files up to 2GB via Pyrogram!**
- 🗜️ **Smart Archiving & Splitting:** Automatically uses `7-Zip` or `zip` to compress files. Dynamically splits large files to seamlessly bypass GitHub's limits. Password protection is fully supported.
- 📝 **Auto `Links.md` Generator:** Automatically updates a `Links.md` file in your repository with categorized download links and timestamps.
- 🧹 **Deep Repo Cleaning:** The `/clear_repo` command uses GitHub's Orphan Commits API to completely wipe your repository and Git history, keeping your cloning process fast and light.
- 📊 **Live Progress Bar:** Clean and non-spammy progress updates inside Telegram.

---

## 🛠️ Prerequisites

Ensure you have **Python 3.9+** and the required CLI tools installed:

```bash
sudo apt-get update
sudo apt-get install -y aria2 ffmpeg p7zip-full git unzip
```

Install `yt-dlp` (latest binary — recommended over apt version):
```bash
sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
sudo chmod a+rx /usr/local/bin/yt-dlp
```

> ⚠️ **Important:** Do NOT use `apt install yt-dlp` — the apt version is outdated and will fail on modern YouTube.

---

## ⚙️ Setup & Installation

### Option 1: Using Git (Recommended)
```bash
git clone https://github.com/YOUR_USERNAME/sandbox.git
cd sandbox
```

### Option 2: Using Wget
```bash
wget https://github.com/YOUR_USERNAME/sandbox/archive/refs/heads/main.zip -O sandbox.zip
unzip sandbox.zip
cd sandbox-main
```

**1. Create the Virtual Environment:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**2. Install Python Dependencies:**
```bash
pip install -r requirements.txt
```

**3. Configure Environment Variables:**

Create a `.env` file in the root directory:

```env
# Get this from @BotFather on Telegram
BOT_TOKEN=123456789:YOUR_BOT_TOKEN_HERE

# Database URI (SQLite is default, no setup needed)
DB_URL=sqlite:///database/bot.db

# Telegram API Credentials (REQUIRED for downloading files > 20MB)
# Get these from https://my.telegram.org
TG_API_ID=1234567
TG_API_HASH=your_api_hash_here

# YouTube Cookies — Optional (see cookie setup section below)
# Option A: Path to a cookies.txt file on your server
YOUTUBE_COOKIES=youtube_cookies.txt
```

---

## 🚀 Running the Bot

```bash
python bot.py
```

**For production (using PM2):**
```bash
pm2 start bot.py --name "rgit-bot" --interpreter ./venv/bin/python
pm2 save
```

> ⚠️ **Important Note for YouTube Cookies:** If you plan to use `YOUTUBE_COOKIES` to bypass YouTube restrictions, it is highly recommended to run the bot using **`screen`** instead of `PM2`. `PM2` often creates an isolated environment that may fail to initialize the dependencies required for cookie-based authentication.

---

## 🤖 Telegram Commands

| Command | Description |
|---|---|
| `/start` | Initialize the bot |
| `/set_token <PAT>` | Link your GitHub Personal Access Token *(Requires `Contents: Write` scope)* |
| `/set_repo <username/repo>` | Set your target GitHub repository |
| `/status` | Check your configuration & **Live Repo Size** |
| `/del <filename.ext>` | Safely delete a specific file from your repo and `Links.md` |
| `/clear_repo` | Completely wipe all uploaded files and reset Git history (Orphan Commit) |
| `/stop` | Cancel the currently running download/upload task |

> 💡 **Usage:** Just send any **URL** or **Telegram File** to the bot. Choose your desired quality and compression type via the inline buttons, and you will receive your raw direct links!

---

## 📱 Setting Up Telegram API (For Large Files > 20MB)

Telegram's standard Bot API restricts file downloads to **20MB**. To bypass this and download files up to **2GB**, you must provide your Telegram API credentials.

1. Log in to [my.telegram.org](https://my.telegram.org).
2. Go to **API development tools**.
3. Create a new application.
4. Copy your **App api_id** and **App api_hash**.
5. Add them to your `.env` file under `TG_API_ID` and `TG_API_HASH`.

---

## 🍪 Setting Up YouTube Cookies (Optional but Recommended)

YouTube may block downloads from server IPs. Providing cookies from a logged-in browser session can help bypass this.

> ⚠️ **Use a secondary/burner Google account** — never your main account.

**Step 1 — Install the browser extension:**
- [Chrome — Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
- [Firefox — Get cookies.txt LOCALLY](https://addons.mozilla.org/en-US/firefox/addon/get-cookies-txt-locally/)

**Step 2 — Export cookies:**
Log in to YouTube, click the extension, and export as `cookies.txt`.

**Step 3 — Add to your server:**
Upload `cookies.txt` to your bot's directory, then in `.env`:
```env
YOUTUBE_COOKIES=youtube_cookies.txt
```

---

## 📦 How to Extract Split Zip Files (.zip.001, .zip.002, .z01)

Since GitHub has file size limits, the bot safely splits large files into multiple parts (`.z01`, `.zip.001`, etc.) to bypass restrictions.

### 📱 On Android (Termux)
1. Install `p7zip`:
   ```bash
   pkg update
   pkg install p7zip
   ```
2. Navigate to your download folder and extract the **first part** (it will automatically find and merge the rest):
   ```bash
   7z x your_file_name.zip.001  # or your_file_name.zip
   ```

### 💻 On Windows / PC
1. Download all parts (`.001`, `.002`, or `.z01`, `.z02` along with `.zip`) and put them in the **same folder**.
2. Install [7-Zip](https://www.7-zip.org/) or [WinRAR](https://www.win-rar.com/).
3. Right-click on the base `.zip` or `.zip.001` file and select **Extract Here**.

---

## ⚠️ Important Notes

- GitHub has a **100MB hard limit** per file. The bot safely chunks files into 95MB parts and uses an expanded HTTP POST Buffer (150MB) to prevent upload connection drops.
- The `Links.md` file in your repo is updated automatically with every upload and includes Tehran (IR) timestamps.
- `tmp_downloads/` is used as a working directory and is cleaned up automatically.
- Do **not** commit your `.env` file or `youtube_cookies.txt` — add them to `.gitignore`.