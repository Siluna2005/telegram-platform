"""
Streaming Bot - User interface for browsing and watching media
"""

import os
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    ContextTypes
)
from telegram import InlineQueryResultArticle, InputTextMessageContent
from dotenv import load_dotenv

load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("STREAMING_BOT_TOKEN")
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID"))
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

async def is_approved(user_id: int) -> bool:
    """Check if user is approved"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_URL}/api/users/{user_id}/check"
            )
            data = response.json()
            return data.get("approved", False)
    except:
        return False


async def register_user(user):
    """Register new user"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{BACKEND_URL}/api/users/",
                json={
                    "telegram_id": user.id,
                    "username": user.username,
                    "first_name": user.first_name
                }
            )
    except:
        pass


async def send_video_from_channel(context, chat_id, video_data, caption):
    """Send video using message_id or file_id"""
    
    message_id = video_data.get("message_id")
    file_id = video_data.get("file_id")
    
    try:
        if message_id:
            # Use copy_message (BEST METHOD)
            await context.bot.copy_message(
                chat_id=chat_id,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=message_id,
                caption=caption,
                parse_mode="Markdown"
            )
            logger.info(f"✅ Sent via copy_message: {message_id}")
        else:
            # Fallback to file_id
            logger.warning(f"⚠️  No message_id, using file_id (may fail)")
            await context.bot.send_video(
                chat_id=chat_id,
                video=file_id,
                caption=caption,
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"❌ Failed to send video: {e}")
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# BOT COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user = update.effective_user
    
    # Register user
    await register_user(user)
    
    # Check approval
    if not await is_approved(user.id):
        await update.message.reply_text(
            "⏳ *Access Pending*\n\n"
            "Your request has been submitted.\n"
            "Wait for admin approval.",
            parse_mode="Markdown"
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("🎬 Browse Films", callback_data="browse_films")],
        [InlineKeyboardButton("📺 Browse Series", callback_data="browse_series")],
        [InlineKeyboardButton("🔍 Search", switch_inline_query_current_chat="")]
    ]
    
    await update.message.reply_text(
        f"👋 Welcome, {user.first_name}!\n\n"
        "🎬 Browse films and series\n"
        "🔍 Search with inline mode",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if not await is_approved(user_id):
        await query.message.reply_text("❌ Access denied")
        return
    
    data = query.data
    
    try:
        async with httpx.AsyncClient() as client:
            
            # Browse films
            if data == "browse_films":
                response = await client.get(f"{BACKEND_URL}/api/media/?type=film")
                films = response.json()
                
                if not films:
                    await query.message.reply_text("No films available")
                    return
                
                keyboard = []
                for film in films[:20]:
                    keyboard.append([InlineKeyboardButton(
                        f"🎬 {film['title']} ({film.get('year', 'N/A')})",
                        callback_data=f"film_{film['id']}"
                    )])
                
                await query.message.edit_text(
                    "🎬 *Select Film:*",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            
            # Browse series
            elif data == "browse_series":
                response = await client.get(f"{BACKEND_URL}/api/media/?type=series")
                series = response.json()
                
                if not series:
                    await query.message.reply_text("No series available")
                    return
                
                keyboard = []
                for s in series[:20]:
                    keyboard.append([InlineKeyboardButton(
                        f"📺 {s['title']} ({s.get('year', 'N/A')})",
                        callback_data=f"series_{s['id']}"
                    )])
                
                await query.message.edit_text(
                    "📺 *Select Series:*",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            
            # Play film
            elif data.startswith("film_"):
                film_id = data.split("_")[1]
                
                # Get film data
                response = await client.get(f"{BACKEND_URL}/api/media/film/{film_id}")
                film_data = response.json()
                
                # Get media info
                response = await client.get(f"{BACKEND_URL}/api/media/{film_id}")
                media = response.json()
                
                await query.message.delete()
                
                caption = f"🎬 *{media['title']}*"
                if media.get('year'):
                    caption += f" ({media['year']})"
                if media.get('imdb_rating'):
                    caption += f"\n⭐ {media['imdb_rating']}/10"
                
                await send_video_from_channel(
                    context,
                    query.message.chat_id,
                    film_data,
                    caption
                )
            
            # Show seasons
            elif data.startswith("series_"):
                series_id = data.split("_")[1]
                
                # Get seasons
                response = await client.get(f"{BACKEND_URL}/api/media/{series_id}/seasons")
                seasons = response.json()
                
                if not seasons:
                    await query.answer("No episodes available", show_alert=True)
                    return
                
                # Get media info
                response = await client.get(f"{BACKEND_URL}/api/media/{series_id}")
                media = response.json()
                
                keyboard = []
                for season in seasons:
                    keyboard.append([InlineKeyboardButton(
                        f"📁 Season {season}",
                        callback_data=f"season_{series_id}_{season}"
                    )])
                
                text = f"📺 *{media['title']}*\n\nSelect season:"
                
                await query.message.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            
            # Show episodes
            elif data.startswith("season_"):
                parts = data.split("_")
                series_id = parts[1]
                season = int(parts[2])
                
                # Get episodes
                response = await client.get(
                    f"{BACKEND_URL}/api/media/{series_id}/season/{season}"
                )
                episodes = response.json()
                
                keyboard = []
                for ep in episodes:
                    keyboard.append([InlineKeyboardButton(
                        f"▶️ Episode {ep['episode_number']}",
                        callback_data=f"play_{series_id}_{season}_{ep['episode_number']}"
                    )])
                
                keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f"series_{series_id}")])
                
                await query.message.edit_text(
                    f"📺 Season {season}\n\nSelect episode:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            
            # Play episode
            elif data.startswith("play_"):
                parts = data.split("_")
                series_id = parts[1]
                season = int(parts[2])
                episode = int(parts[3])
                
                # Get episode data
                response = await client.get(
                    f"{BACKEND_URL}/api/media/{series_id}/season/{season}/episode/{episode}"
                )
                ep_data = response.json()
                
                # Get media info
                response = await client.get(f"{BACKEND_URL}/api/media/{series_id}")
                media = response.json()
                
                await query.message.delete()
                
                caption = f"📺 *{media['title']}*\nS{season:02d}E{episode:02d}"
                
                await send_video_from_channel(
                    context,
                    query.message.chat_id,
                    ep_data,
                    caption
                )
                
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        await query.answer("❌ Error occurred", show_alert=True)


async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline search"""
    query = update.inline_query.query
    user_id = update.inline_query.from_user.id
    
    if not await is_approved(user_id):
        return
    
    if len(query) < 2:
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_URL}/api/media/search",
                params={"q": query}
            )
            results_data = response.json()
        
        results = []
        for item in results_data[:10]:
            title = item["title"]
            year = item.get("year", "")
            media_type = "🎬" if item["type"] == "film" else "📺"
            
            result = InlineQueryResultArticle(
                id=item["id"],
                title=f"{media_type} {title} ({year})",
                description=item.get("description", "")[:100],
                input_message_content=InputTextMessageContent(
                    f"/watch {item['id']}"
                ),
                thumb_url=item.get("poster_url")
            )
            results.append(result)
        
        await update.inline_query.answer(results, cache_time=10)
        
    except Exception as e:
        logger.error(f"Inline query error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Start the bot"""
    
    if not BOT_TOKEN:
        logger.error("❌ STREAMING_BOT_TOKEN not set!")
        return
    
    logger.info("🚀 Starting Streaming Bot...")
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(InlineQueryHandler(handle_inline_query))
    
    # Start bot
    logger.info("✅ Streaming Bot is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()