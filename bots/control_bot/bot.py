"""
Control Bot - Admin-only management interface
Handles media creation, user approval, and bulk season linking
"""

import os
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
from dotenv import load_dotenv

load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("CONTROL_BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY")

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
        "🎛️ *Control Bot - Admin Panel*\n\n"
        "*Media Management:*\n"
        "/addfilm <title> [year] - Add new film\n"
        "/addseries <title> [year] - Add new series\n"
        "/linkfilm <film_id> - Link video to film\n"
        "/linkseason <series_id> <season> <episodes> - Bulk link season\n\n"
        "*User Management:*\n"
        "/pending - Show pending users\n"
        "/approve <telegram_id> - Approve user\n"
        "/reject <telegram_id> - Reject user\n\n"
        "*Other:*\n"
        "/stats - Platform statistics",
        parse_mode="Markdown"
    )


async def add_film(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add new film"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Access denied.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /addfilm <title> [year]")
        return
    
    title = " ".join(context.args[:-1] if context.args[-1].isdigit() else context.args)
    year = int(context.args[-1]) if context.args[-1].isdigit() else None
    
    await update.message.reply_text(f"Creating film: {title}...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/media/",
                headers={"X-API-Key": API_KEY},
                json={
                    "title": title,
                    "type": "film",
                    "year": year
                }
            )
            data = response.json()
        
        film_id = data["id"]
        await update.message.reply_text(
            f"✅ *Film created!*\n\n"
            f"Title: {title}\n"
            f"ID: `{film_id}`\n\n"
            f"Now upload video to Storage Bot, then:\n"
            f"`/linkfilm {film_id}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def add_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add new series"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Access denied.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /addseries <title> [year]")
        return
    
    title = " ".join(context.args[:-1] if context.args[-1].isdigit() else context.args)
    year = int(context.args[-1]) if context.args[-1].isdigit() else None
    
    await update.message.reply_text(f"Creating series: {title}...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/media/",
                headers={"X-API-Key": API_KEY},
                json={
                    "title": title,
                    "type": "series",
                    "year": year
                }
            )
            data = response.json()
        
        series_id = data["id"]
        await update.message.reply_text(
            f"✅ *Series created!*\n\n"
            f"Title: {title}\n"
            f"ID: `{series_id}`\n\n"
            f"Upload episodes to Storage Bot, then:\n"
            f"`/linkseason {series_id} 1 <episode_count>`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def link_film(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Link video to film"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Access denied.")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /linkfilm <film_id>")
        return
    
    film_id = context.args[0]
    
    try:
        async with httpx.AsyncClient() as client:
            # Get last upload
            response = await client.get(
                f"{BACKEND_URL}/api/uploads/{user_id}",
                headers={"X-API-Key": API_KEY}
            )
            upload = response.json()
            
            # Link to film
            await client.post(
                f"{BACKEND_URL}/api/media/film/link",
                headers={"X-API-Key": API_KEY},
                json={
                    "film_id": film_id,
                    "file_id": upload["file_id"],
                    "message_id": upload.get("message_id"),
                    "storage_bot": upload["bot_name"],
                    "uploader_id": user_id
                }
            )
            
            # Clear upload
            await client.delete(
                f"{BACKEND_URL}/api/uploads/{user_id}",
                headers={"X-API-Key": API_KEY}
            )
            
            # Get film details
            response = await client.get(f"{BACKEND_URL}/api/media/{film_id}")
            media = response.json()
        
        await update.message.reply_text(
            f"✅ *Film linked!*\n\n"
            f"Title: {media['title']}\n"
            f"ID: `{film_id}`\n"
            f"Message ID: `{upload.get('message_id', 'N/A')}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def link_season(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bulk link season episodes"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Access denied.")
        return
    
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /linkseason <series_id> <season> <episode_count>")
        return
    
    series_id = context.args[0]
    season = int(context.args[1])
    episode_count = int(context.args[2])
    
    await update.message.reply_text(f"Linking {episode_count} episodes...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Check queue
            response = await client.get(
                f"{BACKEND_URL}/api/uploads/{user_id}/queue",
                headers={"X-API-Key": API_KEY}
            )
            queue = response.json()
            
            if len(queue) < episode_count:
                await update.message.reply_text(
                    f"❌ Not enough videos in queue\n"
                    f"Found: {len(queue)}\n"
                    f"Need: {episode_count}\n\n"
                    f"Upload more videos to Storage Bot"
                )
                return
            
            await update.message.reply_text(f"📝 Queue has {len(queue)} videos. Linking...")
            
            # Bulk link
            response = await client.post(
                f"{BACKEND_URL}/api/media/season/link-bulk",
                headers={"X-API-Key": API_KEY},
                params={
                    "media_id": series_id,
                    "season_number": season,
                    "episode_count": episode_count,
                    "uploader_id": user_id
                }
            )
            result = response.json()
            
            # Get series details
            response = await client.get(f"{BACKEND_URL}/api/media/{series_id}")
            media = response.json()
        
        await update.message.reply_text(
            f"✅ *Season linked!*\n\n"
            f"Series: {media['title']}\n"
            f"Season {season}: {result['linked_successfully']}/{episode_count} episodes\n\n"
            f"Users can now watch in Streaming Bot!",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def show_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending users"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Access denied.")
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_URL}/api/users/?status=pending",
                headers={"X-API-Key": API_KEY}
            )
            users = response.json()
        
        if not users:
            await update.message.reply_text("✅ No pending users")
            return
        
        text = "👥 *Pending Users:*\n\n"
        for user in users[:10]:
            text += f"• {user.get('first_name', 'Unknown')} (@{user.get('username', 'no_username')})\n"
            text += f"  ID: `{user['telegram_id']}`\n"
            text += f"  `/approve {user['telegram_id']}` | `/reject {user['telegram_id']}`\n\n"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve user"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Access denied.")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /approve <telegram_id>")
        return
    
    target_id = int(context.args[0])
    
    try:
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{BACKEND_URL}/api/users/{target_id}",
                headers={"X-API-Key": API_KEY},
                json={"status": "approved"}
            )
        
        await update.message.reply_text(f"✅ User {target_id} approved!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def reject_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject user"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Access denied.")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /reject <telegram_id>")
        return
    
    target_id = int(context.args[0])
    
    try:
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{BACKEND_URL}/api/users/{target_id}",
                headers={"X-API-Key": API_KEY},
                json={"status": "rejected"}
            )
        
        await update.message.reply_text(f"✅ User {target_id} rejected")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show platform statistics"""
    user_id = update.effective_user.id
    
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Access denied.")
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_URL}/api/users/stats/",
                headers={"X-API-Key": API_KEY}
            )
            stats = response.json()
        
        await update.message.reply_text(
            f"📊 *Platform Statistics*\n\n"
            f"🎬 Films: {stats['total_films']}\n"
            f"📺 Series: {stats['total_series']}\n"
            f"📹 Episodes: {stats['total_episodes']}\n"
            f"👥 Users: {stats['total_users']}\n"
            f"⏳ Pending: {stats['pending_users']}\n"
            f"👑 Admins: {stats['total_admins']}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Start the bot"""
    
    if not BOT_TOKEN:
        logger.error("❌ CONTROL_BOT_TOKEN not set!")
        return
    
    logger.info("🚀 Starting Control Bot...")
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addfilm", add_film))
    app.add_handler(CommandHandler("addseries", add_series))
    app.add_handler(CommandHandler("linkfilm", link_film))
    app.add_handler(CommandHandler("linkseason", link_season))
    app.add_handler(CommandHandler("pending", show_pending))
    app.add_handler(CommandHandler("approve", approve_user))
    app.add_handler(CommandHandler("reject", reject_user))
    app.add_handler(CommandHandler("stats", show_stats))
    
    # Start bot
    logger.info("✅ Control Bot is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
