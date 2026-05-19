import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8961931336:AAEaQA-s27bqa3QwP3uJ2VgksOlSeP0eza0"
RENDER_URL = "https://link-to-video-bot.onrender.com" 

app = Flask(__name__)
telegram_app = Application.builder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to LinkToVideo Bot!\n\n"
        "Just drop a link to a video from Instagram, TikTok, YouTube Shorts, or Twitter/X here, "
        "and I will fetch the video file for you instantly."
    )

async def handle_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith(("http://", "https://")):
        return 

    status_message = await update.message.reply_text("📥 Processing your link... Please wait.")
    ydl_opts = {
        'format': 'best[ext=mp4]/best', 
        'outtmpl': 'downloads/%(id)s.%(ext)s', 
        'max_filesize': 50 * 1024 * 1024,
        'quiet': True,
    }
    loop = asyncio.get_event_loop()
    
    try:
        await status_message.edit_text("⚡ Downloading video from platform...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                base, _ = os.path.splitext(filename)
                for file in os.listdir("downloads"):
                    if file.startswith(os.path.basename(base)):
                        filename = os.path.join("downloads", file)
                        break

        await status_message.edit_text("📤 Uploading video to Telegram...")
        with open(filename, 'rb') as video_file:
            await update.message.reply_video(
                video=video_file, 
                caption=f"🎥 **Title:** {info.get('title', 'Downloaded Video')}\n\nProcessed by LinkToVideo Bot.",
                parse_mode="Markdown"
            )
        await status_message.delete()
    except Exception as e:
        await status_message.edit_text("❌ Failed to process. The file might be over 50MB or private.")
        logger.error(f"Error: {e}")
    finally:
        if 'filename' in locals() and os.path.exists(filename):
            os.remove(filename)

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        asyncio.run(telegram_app.process_update(update))
        return "OK", 200

@app.route('/', methods=['GET'])
def index():
    return "Bot is running via Webhook!", 200

def init_bot():
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
        
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_download))
    
    async def set_webhook():
        await telegram_app.initialize()
        await telegram_app.bot.set_webhook(url=f"{RENDER_URL}/{BOT_TOKEN}")
        logger.info(f"Webhook successfully set to {RENDER_URL}")
        
    asyncio.run(set_webhook())

init_bot()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
