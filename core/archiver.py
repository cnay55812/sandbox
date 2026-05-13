import os
import asyncio
import re
import glob

def sanitize_filename(name):
    return re.sub(r'[^\w\.\-\s]', '_', name)

async def process_archive(file_path: str, comp_mode: str, password: str, updater):
    updater.action_text = "📦 Processing File"
    file_path = os.path.abspath(file_path)
    dir_name = os.path.dirname(file_path)
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    raw_base = os.path.splitext(os.path.basename(file_path))[0]
    ext = os.path.splitext(file_path)[1].lower()
    new_base = sanitize_filename(raw_base)

    split_size = 95

    has_password = password and password != "None"

    if comp_mode == "raw" and file_size_mb <= split_size and not has_password:
        final_path = os.path.join(dir_name, f"{new_base}{ext}")
        if file_path != final_path:
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(file_path, final_path)
        return [final_path]

    if file_size_mb > split_size and ext in ['.mp4', '.mkv', '.avi', '.webm', '.mov'] and comp_mode == "raw" and not has_password:
        updater.action_text = "🎬 Splitting Video (FFmpeg)"

        out_pattern = os.path.join(dir_name, f"{new_base}_part_%03d{ext}")
        cmd =[
            "ffmpeg", "-i", file_path,
            "-c", "copy",
            "-f", "segment",
            "-segment_time", "300",
            "-reset_timestamps", "1",
            out_pattern, "-y"
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            err_msg = stderr.decode('utf-8', 'ignore')
            raise Exception(f"FFmpeg split failed!\n{err_msg}")

        if os.path.exists(file_path):
            os.remove(file_path)

        parts = glob.glob(os.path.join(dir_name, f"{new_base}_part_*{ext}"))
        parts.sort()

        if not parts:
            raise Exception("Video split failed: output parts not found.")
        return parts

    if ext == ".zip" or os.path.join(dir_name, f"{new_base}.zip") == file_path:
        new_base = f"{new_base}_RGit"

    zip_path = os.path.join(dir_name, f"{new_base}.zip")

    if file_size_mb > split_size:
        if has_password:
            updater.action_text = "🔐 Zipping & Splitting (7z+Pass)"

            # * We clean old parts and use '-y' (assume yes) to prevent it.
            for f in glob.glob(os.path.join(dir_name, f"{new_base}.zip.*")):
                if os.path.exists(f): os.remove(f)

            cmd = ["7z", "a", "-tzip", f"-v{split_size}m", f"-p{password}", "-mx=9", "-y", zip_path, file_path]
        else:
            updater.action_text = "✂️ Zipping & Splitting (zip)"

            cmd = ["zip", "-j", "-s", f"{split_size}m"]
            # NOTE: Apply 0-compression for all raw variants to speed up processing
            if comp_mode in ["rawnormal", "rawchunk", "zip_smart"]:
                cmd.append("-0")
            else:
                cmd.append("-9")

            cmd.extend([zip_path, file_path])
    else:
        updater.action_text = "📦 Zipping File (7z)"

        cmd = ["7z", "a", "-tzip"]
        if has_password:
            cmd.extend([f"-p{password}", "-mx=9"])
        elif comp_mode == "raw":
            cmd.append("-mx=0")
        else:
            cmd.append("-mx=9")

        cmd.extend([zip_path, file_path])

    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        err_msg = stderr.decode('utf-8', 'ignore') or stdout.decode('utf-8', 'ignore')
        raise Exception(f"Archiving failed!\n{err_msg}")

    if os.path.exists(file_path):
        os.remove(file_path)

    if file_size_mb > split_size:
        if has_password:
            parts = glob.glob(os.path.join(dir_name, f"{new_base}.zip.*"))
            parts.sort()
        else:
            parts = glob.glob(os.path.join(dir_name, f"{new_base}.z[0-9]*"))

            def extract_part_num(filename):
                match = re.search(r'\.z(\d+)$', filename)
                return int(match.group(1)) if match else 0

            parts.sort(key=extract_part_num)

            if os.path.exists(zip_path):
                parts.append(zip_path)

        if not parts:
            raise Exception("Archiving failed: output parts not found.")
        return parts
    else:
        if not os.path.exists(zip_path):
            raise Exception("Archiving failed: output zip not found.")
        return [zip_path]