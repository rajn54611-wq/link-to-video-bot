import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# Set up clean logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Credentials verified from your dashboard settings
BOT_TOKEN = "8961931336:AAEaQA-s27bqa3QwP3uJ2VgksOlSeP0eza0"
RENDER_URL = "https://link-to-video-bot.onrender.com" 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to LinkToVideo Bot!\n\n"
        "Just drop a link to a video from Instagram, TikTok, YouTube Shorts, or Twitter/X here, "
        "and I will fetch the video file for you instantly.\n\n"
        "ℹ️ Note: Optimized for files up to 50 MB."
    )

async def handle_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith(("http://", "https://")):
        return 

    status_message = await update.message.reply_text("📥 Processing your link... Please wait.")
    
    # Create unique output path based on update message ID to prevent filename overlaps
    os.makedirs('downloads', exist_ok=True)
    outtmpl = f'downloads/{update.message.message_id}_%(id)s.%(ext)s'
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best', 
        'outtmpl': outtmpl, 
        'max_filesize': 50 * 1024 * 1024,
        'quiet': True,
    }
    
    # Run the blocking yt-dlp extraction in an isolated async background worker thread
    loop = asyncio.get_running_loop()
    
    try:
        await status_message.edit_text("⚡ Downloading video from platform...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # This allows other messages to process while this single download runs!
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            
            # Catch extensions that shifted dynamically (e.g., mkv -> mp4)
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
        logger.error(f"Error handling download: {e}")
        
    finally:
        if 'filename' in locals() and os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception:
                pass

def main():
    # Build application layout
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register command and message event handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_download))
    
    # Get port assigned dynamically by Render
    port = int(os.environ.get("PORT", 8080))
    
    logger.info("Starting native asynchronous webhook gateway handler...")
    
    # Let the telegram framework native web handler manage everything asynchronously!
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"{RENDER_URL}/{BOT_TOKEN}"
    )

if __name__ == '__main__':
    main()
