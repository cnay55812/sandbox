import os
import asyncio
import aiohttp
import base64
import urllib.parse
import html
import shutil
import uuid
from datetime import datetime, timedelta
from database.models import User
from core.progress import ProgressUpdater

git_locks = {}

async def run_cmd(*args, cwd=None, hide_token=None):
    process = await asyncio.create_subprocess_exec(
        *args, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        err = stderr.decode('utf-8', 'ignore')
        cmd_str = ' '.join(args)
        if hide_token:
            err = err.replace(hide_token, "***")
            cmd_str = cmd_str.replace(hide_token, "***")
        raise Exception(f"Git Command failed: {cmd_str}\n{err}")
    return stdout.decode('utf-8', 'ignore')

async def push_to_github(user_id: int, user: User, file_paths: list, updater: ProgressUpdater):
    repo = user.github_repo
    token = user.github_token

    if not repo or not token:
        raise Exception("GitHub Repo or Token is not configured.")

    if user_id not in git_locks:
        git_locks[user_id] = asyncio.Lock()

    updater.action_text = "Waiting in Queue"
    updater.update_sync(5, "-", "-")

    async with git_locks[user_id]:
        updater.action_text = "Fast Cloning (Sparse)"
        updater.update_sync(10, "-", "-")

        clone_dir = os.path.abspath(os.path.join("tmp_downloads", f"rgit_clone_{uuid.uuid4().hex[:8]}"))
        os.makedirs(clone_dir, exist_ok=True)

        try:
            repo_url = f"https://{token}@github.com/{repo}.git"

            await run_cmd("git", "clone", "--depth=1", "--no-checkout", "--filter=blob:none", repo_url, clone_dir, hide_token=token)
            await run_cmd("git", "config", "core.sparseCheckout", "true", cwd=clone_dir)

            await run_cmd("git", "config", "http.postBuffer", "157286400", cwd=clone_dir)

            sparse_path = os.path.join(clone_dir, ".git", "info", "sparse-checkout")
            with open(sparse_path, "w") as f:
                f.write("/*\n!/dl/\n!/apks/\n")

            await run_cmd("git", "checkout", "main", cwd=clone_dir)

            await run_cmd("git", "config", "user.name", "RGit Bot", cwd=clone_dir)
            await run_cmd("git", "config", "user.email", "bot@rgit.bot", cwd=clone_dir)

            dl_dir = os.path.join(clone_dir, "dl")
            os.makedirs(dl_dir, exist_ok=True)

            links =[]
            uploaded_filenames =[]
            total_files = len(file_paths)
            tehran_time = (datetime.utcnow() + timedelta(hours=3, minutes=30)).strftime("%Y-%m-%d %H:%M")
            new_links_content = f"### 📅 {tehran_time} (IR Time)\n"

            for i, fp in enumerate(file_paths):
                fname = os.path.basename(fp)
                uploaded_filenames.append(fname)

                updater.action_text = f"Copying ({i+1}/{total_files})"
                updater.update_sync(20 + (50 * i / total_files), fname[:10], "-")

                dest_path = os.path.join(dl_dir, fname)
                shutil.move(fp, dest_path)

                size_mb = os.path.getsize(dest_path) / (1024 * 1024)
                size_str = f"{size_mb / 1024:.2f} GB" if size_mb >= 1024 else f"{size_mb:.2f} MB"
                encoded_name = urllib.parse.quote(fname)
                raw_url = f"https://github.com/{repo}/raw/main/dl/{encoded_name}"

                display_text = f"{fname} `{size_str}`"
                safe_display = html.escape(display_text)

                if "_part_" in fname:
                    icon = "🎬"
                elif fname.endswith((".mp4", ".mkv", ".avi")):
                    icon = "🎬"
                elif fname.endswith((".mp3", ".m4a")):
                    icon = "🎵"
                elif ".zip." in fname or fname.endswith(".zip"):
                    icon = "🗜️"
                elif fname.endswith(".apk"):
                    icon = "📱"
                else:
                    icon = "📥"

                links.append(f"{icon} <b><a href='{raw_url}'>{safe_display}</a></b>")
                new_links_content += f"- {icon} [{fname}]({raw_url}) `{size_str}`\n"

            updater.action_text = "Updating Links.md"
            updater.update_sync(80, "-", "-")
            links_md_path = os.path.join(clone_dir, "Links.md")

            default_header = "## 🔗 Direct Download Links\n> Click on any link below to start downloading directly.<br><br/>\n\n"
            links_md_content = ""
            if os.path.exists(links_md_path):
                with open(links_md_path, "r", encoding="utf-8") as f:
                    links_md_content = f.read()

            if links_md_content:
                split_marker = "### 📅"
                if split_marker in links_md_content:
                    parts = links_md_content.split(split_marker, 1)
                    preserved_header = parts[0]
                    old_links = split_marker + parts[1]
                else:
                    preserved_header = links_md_content if links_md_content.strip() else default_header
                    old_links = ""
            else:
                preserved_header = default_header
                old_links = ""

            if not preserved_header.endswith("\n\n"):
                preserved_header = preserved_header.rstrip() + "\n\n"

            final_links_md = preserved_header + new_links_content + "\n" + old_links

            with open(links_md_path, "w", encoding="utf-8") as f:
                f.write(final_links_md)

            updater.action_text = "Committing (Sparse)"
            updater.update_sync(90, "-", "-")

            add_args = ["git", "add", "--sparse", "-f", "Links.md"]
            for fname in uploaded_filenames:
                add_args.append(f"dl/{fname}")

            await run_cmd(*add_args, cwd=clone_dir)
            await run_cmd("git", "commit", "-m", f"✨ Add new files [skip ci]", cwd=clone_dir)

            updater.action_text = "Pushing to GitHub"
            updater.update_sync(95, "-", "-")
            await run_cmd("git", "push", "origin", "main", cwd=clone_dir, hide_token=token)

            updater.action_text = "Upload Complete"
            updater.update_sync(100, "-", "-")
            return links
        finally:
            if os.path.exists(clone_dir):
                shutil.rmtree(clone_dir, ignore_errors=True)

async def _update_repo_tree(user: User, tree_items: list, commit_message: str):
    repo = user.github_repo
    token = user.github_token
    api_base = f"https://api.github.com/repos/{repo}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(f"{api_base}/git/refs/heads/main") as resp:
            ref_data = await resp.json()
            commit_sha = ref_data['object']['sha']

        async with session.get(f"{api_base}/git/commits/{commit_sha}") as resp:
            commit_data = await resp.json()
            base_tree_sha = commit_data['tree']['sha']

        async with session.post(f"{api_base}/git/trees", json={"base_tree": base_tree_sha, "tree": tree_items}) as resp:
            tree_data = await resp.json()
            new_tree_sha = tree_data['sha']

        async with session.post(f"{api_base}/git/commits", json={"message": commit_message, "tree": new_tree_sha, "parents":[commit_sha]}) as resp:
            new_commit_data = await resp.json()
            new_commit_sha = new_commit_data['sha']

        await session.patch(f"{api_base}/git/refs/heads/main", json={"sha": new_commit_sha, "force": True})

async def delete_file_from_github(user: User, filename: str):
    repo = user.github_repo
    token = user.github_token
    api_base = f"https://api.github.com/repos/{repo}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}

    async with aiohttp.ClientSession(headers=headers) as session:
        links_md_path = "Links.md"
        async with session.get(f"{api_base}/contents/{links_md_path}") as resp:
            if resp.status != 200:
                raise Exception("Links.md not found.")
            file_info = await resp.json()
            links_md_content = base64.b64decode(file_info['content']).decode('utf-8')

        new_lines =[]
        for line in links_md_content.split('\n'):
            if f"[{filename}]" not in line and f"{filename} `" not in line:
                new_lines.append(line)
        new_links_md = '\n'.join(new_lines)

        tree_items = [{"path": f"dl/{filename}", "mode": "100644", "type": "blob", "sha": None}]

        async with session.post(f"{api_base}/git/blobs", json={"content": base64.b64encode(new_links_md.encode('utf-8')).decode('utf-8'), "encoding": "base64"}) as resp:
            blob_data = await resp.json()
            tree_items.append({"path": links_md_path, "mode": "100644", "type": "blob", "sha": blob_data['sha']})

    await _update_repo_tree(user, tree_items, f"🗑️ Delete {filename} [skip ci]")

async def clear_github_repo(user: User):
    repo = user.github_repo
    token = user.github_token
    api_base = f"https://api.github.com/repos/{repo}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}

    async with aiohttp.ClientSession(headers=headers) as session:
        default_header = "## 🔗 Direct Download Links\n\n"
        async with session.post(f"{api_base}/git/blobs", json={"content": base64.b64encode(default_header.encode('utf-8')).decode('utf-8'), "encoding": "base64"}) as resp:
            blob_data = await resp.json()

        tree_items = [{"path": "Links.md", "mode": "100644", "type": "blob", "sha": blob_data['sha']}]

        async with session.post(f"{api_base}/git/trees", json={"tree": tree_items}) as resp:
            tree_data = await resp.json()
            new_tree_sha = tree_data['sha']

        async with session.post(f"{api_base}/git/commits", json={"message": "🧹 Clear repository & wipe history [skip ci]", "tree": new_tree_sha, "parents":[]}) as resp:
            new_commit_data = await resp.json()
            new_commit_sha = new_commit_data['sha']

        await session.patch(f"{api_base}/git/refs/heads/main", json={"sha": new_commit_sha, "force": True})