"""
Real Madrid News Bot — Bot Handlers
"""
import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from config import BOT_TOKEN, ADMIN_CHAT_ID, RSS_FEEDS, TELEGRAM_SOURCES, MAX_NEWS_PER_UPDATE, WELCOME_MSG, STATUS_MSG, SOURCES_MSG
from news_fetcher import get_new_news
from summarizer import summarize_news_persian

logger = logging.getLogger(__name__)

# Debounce: prevent rapid-fire button presses
_last_news_time = {}
DEBOUNCE_SECONDS = 10  # Min seconds between news requests


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
    """Handle /news command."""
    await update.message.reply_text("🔍 در حال دریافت اخبار...")

    news = get_new_news(RSS_FEEDS, TELEGRAM_SOURCES, MAX_NEWS_PER_UPDATE)
    if news:
        msg = summarize_news_persian(news)
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
        # Debounce: ignore if pressed too recently
        now = time.time()
        if user_id in _last_news_time and (now - _last_news_time[user_id]) < DEBOUNCE_SECONDS:
            await query.answer("⏳ لطفاً چند لحظه صبر کنید...", show_alert=True)
            return
        _last_news_time[user_id] = now

        await query.edit_message_text("🔍 در حال دریافت اخبار...")
        news = get_new_news(RSS_FEEDS, TELEGRAM_SOURCES, MAX_NEWS_PER_UPDATE)
        if news:
            msg = summarize_news_persian(news)
            await query.edit_message_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
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


# ─── Scheduled News Sender ─────────────────────────────────────

async def send_scheduled_news(context: ContextTypes.DEFAULT_TYPE):
    """Send summarized news to admin chat — called by JobQueue."""
    admin_id = ADMIN_CHAT_ID
    news = get_new_news(RSS_FEEDS, TELEGRAM_SOURCES, MAX_NEWS_PER_UPDATE)

    if news:
        msg = summarize_news_persian(news)
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=msg,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
            logger.info(f"Sent {len(news)} summarized news items to admin")
        except Exception as e:
            logger.error(f"Failed to send news to admin: {e}")
    else:
        logger.info("No new news to send")


# ─── Bot Setup ─────────────────────────────────────────────────

def setup_bot() -> Application:
    """Setup and configure the bot."""
    app = Application.builder().token(BOT_TOKEN).build()

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
        interval=3 * 3600,  # 3 hours in seconds
        first=60,  # First run after 1 minute
        name="real_madrid_news",
    )

    logger.info("Bot setup complete")
    return app
