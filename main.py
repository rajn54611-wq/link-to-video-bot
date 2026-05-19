import os
import logging
import asyncio
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8961931336:AAEaQA-s27bqa3QwP3uJ2VgksOlSeP0eza0"

# --- WEB SERVER CONFIGURATION FOR RENDER ---
def run_web_server():
    # Render provides a dynamic port via environment variables
    port = int(os.environ.get("PORT", 8080))
    server_address = ("", port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f"Web server keeping Render alive running on port {port}...")
    httpd.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to LinkToVideo Bot!\n\n"
        "Just drop a link to a video from Instagram, TikTok, Twitter/X, or YouTube here, "
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

def main():
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    # Start the dummy web server in a separate background thread
    threading.Thread(target=run_web_server, daemon=True).start()

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_download))

    print("LinkToVideo Bot cloud-service is initializing...")
    application.run_polling()

if __name__ == '__main__':
    main()


