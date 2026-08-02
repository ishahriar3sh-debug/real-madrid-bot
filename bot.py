"""
Real Madrid News Bot — Bot Handlers
Sends news with images when available.
"""
import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from config import (
    BOT_TOKEN, ADMIN_CHAT_ID, RSS_FEEDS, TELEGRAM_SOURCES,
    MAX_NEWS_PER_UPDATE, MAX_MESSAGES_PER_SEND,
    WELCOME_MSG, STATUS_MSG, SOURCES_MSG,
)
from news_fetcher import get_new_news
from summarizer import summarize_news_multi_persian

logger = logging.getLogger(__name__)

# Debounce: prevent rapid-fire button presses
_last_news_time = {}
DEBOUNCE_SECONDS = 10


# ─── Command Handlers ──────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    keyboard = [
        [
            InlineKeyboardButton("📰 دریافت اخبار", callback_data="get_news"),
            InlineKeyboardButton("📊 وضعیت", callback_data="get_status"),
        ],
        [InlineKeyboardButton("ℹ️ منابع خبری", callback_data="get_sources")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        WELCOME_MSG,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )
    logger.info(f"User {user.id} ({user.first_name}) started the bot")


async def news_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /news command — fetch, summarize, send with images."""
    await update.message.reply_text("🔍 در حال دریافت اخبار از تمام منابع...")

    news = get_new_news(RSS_FEEDS, TELEGRAM_SOURCES, MAX_NEWS_PER_UPDATE)
    if news:
        messages = summarize_news_multi_persian(news, max_per_msg=10)
        for msg in messages[:MAX_MESSAGES_PER_SEND]:
            # Find first news item with image for this message chunk
            img_url = _find_image_for_chunk(news, messages.index(msg), 10)
            if img_url:
                try:
                    await update.message.reply_photo(
                        photo=img_url,
                        caption=msg[:1024],  # Telegram caption limit
                        parse_mode="Markdown",
                    )
                except Exception:
                    # Fallback to text if image fails
                    await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
            else:
                await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await update.message.reply_text(
            "📭 خبر جدیدی یافت نشد. دوباره بعداً بررسی کن.",
            parse_mode="Markdown",
        )


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    await update.message.reply_text(
        STATUS_MSG.format(last_check=now, news_count="—", interval="3"),
        parse_mode="Markdown",
    )


async def sources_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sources command."""
    await update.message.reply_text(SOURCES_MSG, parse_mode="Markdown")


# ─── Callback Handlers (Inline Buttons) ────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses with debounce."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "get_news":
        # Debounce
        now = time.time()
        if user_id in _last_news_time and (now - _last_news_time[user_id]) < DEBOUNCE_SECONDS:
            await query.answer("⏳ لطفاً چند لحظه صبر کنید...", show_alert=True)
            return
        _last_news_time[user_id] = now

        await query.edit_message_text("🔍 در حال دریافت اخبار از تمام منابع...")
        news = get_new_news(RSS_FEEDS, TELEGRAM_SOURCES, MAX_NEWS_PER_UPDATE)
        if news:
            messages = summarize_news_multi_persian(news, max_per_msg=10)
            # Edit first message (with image if available)
            img_url = _find_image_for_chunk(news, 0, 10)
            if img_url:
                try:
                    await query.edit_message_text(messages[0], parse_mode="Markdown", disable_web_page_preview=True)
                    # Send photo separately
                    await query.message.reply_photo(
                        photo=img_url,
                        caption="🖼️ تصویر خبر اول",
                    )
                except Exception:
                    await query.edit_message_text(messages[0], parse_mode="Markdown", disable_web_page_preview=True)
            else:
                await query.edit_message_text(messages[0], parse_mode="Markdown", disable_web_page_preview=True)

            # Send additional messages
            for i, msg in enumerate(messages[1:MAX_MESSAGES_PER_SEND], 1):
                img_url = _find_image_for_chunk(news, i * 10, 10)
                if img_url:
                    try:
                        await query.message.reply_photo(
                            photo=img_url,
                            caption=msg[:1024],
                            parse_mode="Markdown",
                        )
                    except Exception:
                        await query.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
                else:
                    await query.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            await query.edit_message_text("📭 خبر جدیدی یافت نشد.")

    elif query.data == "get_status":
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        await query.edit_message_text(
            STATUS_MSG.format(last_check=now, news_count="—", interval="3"),
            parse_mode="Markdown",
        )

    elif query.data == "get_sources":
        await query.edit_message_text(SOURCES_MSG, parse_mode="Markdown")


# ─── Helper Functions ──────────────────────────────────────────

def _find_image_for_chunk(news_items: list[dict], start_idx: int, chunk_size: int) -> str:
    """Find the first image URL in a chunk of news items."""
    for item in news_items[start_idx:start_idx + chunk_size]:
        img = item.get("image_url", "")
        if img and img.startswith("http"):
            return img
    return ""


# ─── Scheduled News Sender ─────────────────────────────────────

async def send_scheduled_news(context: ContextTypes.DEFAULT_TYPE):
    """Send summarized news to admin chat — called by JobQueue."""
    admin_id = ADMIN_CHAT_ID
    news = get_new_news(RSS_FEEDS, TELEGRAM_SOURCES, MAX_NEWS_PER_UPDATE)

    if news:
        messages = summarize_news_multi_persian(news, max_per_msg=10)
        try:
            for i, msg in enumerate(messages[:MAX_MESSAGES_PER_SEND]):
                img_url = _find_image_for_chunk(news, i * 10, 10)
                if img_url:
                    try:
                        await context.bot.send_photo(
                            chat_id=admin_id,
                            photo=img_url,
                            caption=msg[:1024],
                            parse_mode="Markdown",
                        )
                    except Exception:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=msg,
                            parse_mode="Markdown",
                            disable_web_page_preview=True,
                        )
                else:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=msg,
                        parse_mode="Markdown",
                        disable_web_page_preview=True,
                    )
            logger.info(f"Sent {len(news)} news items in {len(messages[:MAX_MESSAGES_PER_SEND])} messages to admin")
        except Exception as e:
            logger.error(f"Failed to send news to admin: {e}")
    else:
        logger.info("No new news to send")


# ─── Bot Setup ─────────────────────────────────────────────────

def setup_bot() -> Application:
    """Setup and configure the bot."""
    # Set bot commands (English) to fix ???? display issue in Telegram menu
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("news", "Get latest Real Madrid news"),
        BotCommand("status", "Check bot status"),
        BotCommand("sources", "View news sources"),
    ]

    async def _post_init(application: Application) -> None:
        """Set bot commands and descriptions after initialization."""
        try:
            await application.bot.set_my_commands(commands)
            logger.info("Bot commands set successfully")
        except Exception as e:
            logger.warning(f"Failed to set bot commands: {e}")
        # Set bot description and short description in English
        try:
            await application.bot.set_my_description(
                "Real Madrid News Bot - Get the latest Real Madrid news in Persian"
            )
            await application.bot.set_my_short_description(
                "Real Madrid news in Persian"
            )
            logger.info("Bot descriptions set successfully")
        except Exception as e:
            logger.warning(f"Failed to set bot descriptions: {e}")

    app = Application.builder().token(BOT_TOKEN).post_init(_post_init).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("news", news_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("sources", sources_handler))

    # Inline button handler
    app.add_handler(CallbackQueryHandler(button_handler))

    # Scheduled job: every 3 hours
    app.job_queue.run_repeating(
        send_scheduled_news,
        interval=3 * 3600,
        first=60,
        name="real_madrid_news",
    )

    logger.info("Bot setup complete")
    return app
