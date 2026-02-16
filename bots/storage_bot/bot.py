"""
Storage Bot - Handles video uploads and saves to channel with message_id
"""

import os
import logging
import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from dotenv import load_dotenv

load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("STORAGE_BOT_TOKEN")
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY")
BOT_NAME = "storage_bot"

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_URL}/api/users/admins/check/{user_id}",
                headers={"X-API-Key": API_KEY}
            )
            data = response.json()
            return data.get("is_admin", False)
    except:
        return False


async def save_to_backend(user_id: int, file_id: str, message_id: int):
    """Save upload to backend"""
    try:
        async with httpx.AsyncClient() as client:
            # Save to single upload
            await client.post(
                f"{BACKEND_URL}/api/uploads/",
                headers={"X-API-Key": API_KEY},
                json={
                    "user_id": user_id,
                    "file_id": file_id,
                    "bot_name": BOT_NAME,
                    "message_id": message_id
                }
            )
            
            # Add to queue for bulk linking
            await client.post(
                f"{BACKEND_URL}/api/uploads/{user_id}/queue",
                headers={"X-API-Key": API_KEY},
                json={
                    "user_id": user_id,
                    "file_id": file_id,
                    "bot_name": BOT_NAME,
                    "message_id": message_id
                }
            )
            
        logger.info(f"✅ Saved to backend: user={user_id}, message_id={message_id}")
    except Exception as e:
        logger.error(f"Failed to save to backend: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# BOT COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return
    
    await update.message.reply_text(
        "🎬 *Storage Bot*\n\n"
        "Send me videos to upload to storage channel.\n\n"
        "*Commands:*\n"
        "/start - Show this message\n"
        "/status - Check queue status\n"
        "/clear - Clear upload queue",
        parse_mode="Markdown"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show upload status"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Access denied.")
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_URL}/api/uploads/{user_id}/queue/count",
                headers={"X-API-Key": API_KEY}
            )
            data = response.json()
            count = data.get("count", 0)
        
        await update.message.reply_text(
            f"📊 *Queue Status*\n\n"
            f"Videos in queue: *{count}*\n\n"
            f"Use /clear to clear queue",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def clear_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear upload queue"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Access denied.")
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{BACKEND_URL}/api/uploads/{user_id}/queue",
                headers={"X-API-Key": API_KEY}
            )
            data = response.json()
            deleted = data.get("deleted", 0)
        
        await update.message.reply_text(f"✅ Cleared {deleted} videos from queue")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video uploads"""
    user_id = update.effective_user.id
    
    # Check admin
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Access denied. Admin only.")
        return
    
    # Get video
    video = update.message.video or update.message.document
    
    if not video:
        await update.message.reply_text("❌ Please send a video file")
        return
    
    # Check file size (2GB limit)
    if video.file_size > 2000 * 1024 * 1024:
        await update.message.reply_text("❌ File too large (max 2GB)")
        return
    
    await update.message.reply_text("📤 Uploading to storage channel...")
    
    try:
        # Forward to storage channel
        logger.info(f"Forwarding to channel: {STORAGE_CHANNEL_ID}")
        
        forwarded = await context.bot.forward_message(
            chat_id=STORAGE_CHANNEL_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
        
        channel_file_id = forwarded.video.file_id if forwarded.video else forwarded.document.file_id
        channel_message_id = forwarded.message_id
        
        logger.info(f"✅ Forwarded: file_id={channel_file_id[:30]}..., message_id={channel_message_id}")
        
        # Save to backend
        await save_to_backend(user_id, channel_file_id, channel_message_id)
        
        await update.message.reply_text(
            f"✅ *Video uploaded!*\n\n"
            f"Message ID: `{channel_message_id}`\n"
            f"Added to queue for linking\n\n"
            f"Use /status to check queue",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        await update.message.reply_text(f"❌ Upload failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Start the bot"""
    
    if not BOT_TOKEN:
        logger.error("❌ STORAGE_BOT_TOKEN not set!")
        return
    
    if not STORAGE_CHANNEL_ID:
        logger.error("❌ STORAGE_CHANNEL_ID not set!")
        return
    
    logger.info("🚀 Starting Storage Bot...")
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("clear", clear_queue))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    
    # Start bot
    logger.info("✅ Storage Bot is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
