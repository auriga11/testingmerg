import os
import uuid
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

# Store video paths per user
user_videos = {}

# Watermark text, font, color, and position (can be customized)
watermark_text = "Watermark Test"
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Change if necessary
font_size = 30
font_color = "white"
position = "bottom-right"  # Options: center, bottom, bottom-right, top-left, etc.

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me 2 or more videos, then type /merge to combine them!")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    video = await update.message.video.get_file()
    file_path = f"{uuid.uuid4()}.mp4"
    await video.download_to_drive(file_path)

    user_videos.setdefault(user_id, []).append(file_path)
    await update.message.reply_text(f"Video {len(user_videos[user_id])} saved. Send more or type /merge.")

async def apply_watermark(input_video: str, output_video: str):
    # ffmpeg command to add watermark
    cmd = [
        "ffmpeg",
        "-i", input_video,
        "-vf", f"drawtext=text='{watermark_text}':fontfile={font_path}:x=(w-text_w)/2:y=(h-text_h)/2:fontcolor={font_color}:fontsize={font_size}",
        "-codec:a", "copy",
        output_video
    ]
    subprocess.run(cmd, check=True)

async def merge_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    videos = user_videos.get(user_id, [])

    if len(videos) < 2:
        await update.message.reply_text("Please send at least 2 videos before merging.")
        return

    # Create list.txt for ffmpeg concat
    list_file = f"list_{uuid.uuid4()}.txt"
    with open(list_file, "w") as f:
        for path in videos:
            f.write(f"file '{os.path.abspath(path)}'\n")

    # Merged output file
    merged_path = f"merged_{uuid.uuid4()}.mp4"
    cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", merged_path]
    subprocess.run(cmd, check=True)

    # Apply watermark on the merged video
    watermarked_path = f"watermarked_{uuid.uuid4()}.mp4"
    await apply_watermark(merged_path, watermarked_path)

    await update.message.reply_video(video=open(watermarked_path, "rb"))

    # Cleanup
    for v in videos:
        os.remove(v)
    os.remove(merged_path)
    os.remove(watermarked_path)
    os.remove(list_file)
    user_videos[user_id] = []

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    for v in user_videos.get(user_id, []):
        if os.path.exists(v):
            os.remove(v)
    user_videos[user_id] = []
    await update.message.reply_text("Your video list has been cleared.")

# Bot setup
TOKEN = os.getenv("BOT_TOKEN")
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("merge", merge_videos))
app.add_handler(CommandHandler("reset", reset))
app.add_handler(MessageHandler(filters.VIDEO, handle_video))

app.run_polling()
