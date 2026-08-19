"""
Real Madrid News Bot - Bot Handlers
Purple/dark theme, category-grouped news, improved Persian translation.
"""
import logging
import time
from datetime import datetime, timezone
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
    WELCOME_MSG, STATUS_MSG, SOURCES_MSG, CATEGORY_LABELS,
)
from news_fetcher import get_new_news, get_player_news
from players import get_players, format_players_list, find_player_by_number
from summarizer import summarize_news_multi_persian

logger = logging.getLogger(__name__)

# Debounce
_last_news_time = {}
DEBOUNCE_SECONDS = 10


# ─── Helpers ────────────────────────────────────────────────────

def _build_menu():
    """Build the main inline keyboard (2 per row, emoji-only)."""
    keyboard = [
        [
            InlineKeyboardButton("news", callback_data="get_news"),
            InlineKeyboardButton("stats", callback_data="get_status"),
        ],
        [
            InlineKeyboardButton("players", callback_data="get_players"),
            InlineKeyboardButton("paper", callback_data="get_sources"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def _build_back_menu():
    """Back to main menu button."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("back", callback_data="back_to_menu")]])


def _build_back_players():
    """Back to players button."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("back", callback_data="get_players")]])


def _find_image_for_chunk(news_items, start_idx, chunk_size):
    """Find first image URL in a chunk."""
    for item in news_items[start_idx:start_idx + chunk_size]:
        img = item.get("image_url", "")
        if img and img.startswith("http"):
            return img
    return ""


def _group_by_category(news_items):
    """Group news items by their category."""
    groups = {}
    for item in news_items:
        cat = item.get("category", "general")
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(item)
    return groups


async def _send_news_messages(query_or_message, news, is_callback=False):
    """Send news with category grouping and images."""
    messages = summarize_news_multi_persian(news, max_per_msg=10)
    if not messages:
        return

    for i, msg in enumerate(messages[:MAX_MESSAGES_PER_SEND]):
        img_url = _find_image_for_chunk(news, i * 10, 10)
        if img_url:
            try:
                if is_callback and i == 0:
                    await query_or_message.edit_message_text(
                        msg, parse_mode="Markdown", disable_web_page_preview=True
                    )
                    await query_or_message.message.reply_photo(
                        photo=img_url, caption="image news"
                    )
                else:
                    await query_or_message.reply_photo(
                        photo=img_url, caption=msg[:1024], parse_mode="Markdown"
                    )
            except Exception:
                await _safe_send_text(query_or_message, msg, is_callback, i)
        else:
            await _safe_send_text(query_or_message, msg, is_callback, i)


async def _safe_send_text(target, msg, is_callback, idx):
    """Send text message safely."""
    if is_callback and idx == 0:
        await target.edit_message_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await target.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)


# ─── Command Handlers ──────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    await update.message.reply_text(
        WELCOME_MSG,
        parse_mode="Markdown",
        reply_markup=_build_menu(),
    )
    logger.info(f"User {user.id} ({user.first_name}) started the bot")


async def news_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /news command."""
    await update.message.reply_text("search fetching news...")
    news = get_new_news(RSS_FEEDS, TELEGRAM_SOURCES, MAX_NEWS_PER_UPDATE)
    if news:
        await _send_news_messages(update.message, news)
    else:
        await update.message.reply_text("empty no new news found.")


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    await update.message.reply_text(
        STATUS_MSG.format(last_check=now, news_count="N/A", interval="3"),
        parse_mode="Markdown",
    )


async def sources_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sources command."""
    await update.message.reply_text(SOURCES_MSG, parse_mode="Markdown")


async def players_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /players command."""
    await update.message.reply_text("search fetching players...")
    players = get_players()
    if not players:
        await update.message.reply_text("error failed to fetch players.")
        return

    text = format_players_list(players)
    keyboard = []
    row = []
    for p in players:
        num = p.get("number", "")
        name = p.get("name", "")
        row.append(InlineKeyboardButton(f"{num}", callback_data=f"player_{num}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("back", callback_data="back_to_menu")])

    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─── Callback Handlers ──────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses with debounce."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "get_news":
        now = time.time()
        if user_id in _last_news_time and (now - _last_news_time[user_id]) < DEBOUNCE_SECONDS:
            await query.answer("wait please wait...", show_alert=True)
            return
        _last_news_time[user_id] = now

        await query.edit_message_text("search fetching news...")
        news = get_new_news(RSS_FEEDS, TELEGRAM_SOURCES, MAX_NEWS_PER_UPDATE)
        if news:
            await _send_news_messages(query, news, is_callback=True)
        else:
            await query.edit_message_text("empty no new news found.")

    elif query.data == "get_status":
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        await query.edit_message_text(
            STATUS_MSG.format(last_check=now, news_count="N/A", interval="3"),
            parse_mode="Markdown",
        )

    elif query.data == "get_sources":
        await query.edit_message_text(SOURCES_MSG, parse_mode="Markdown")

    elif query.data == "back_to_menu":
        await query.edit_message_text(
            WELCOME_MSG, parse_mode="Markdown", reply_markup=_build_menu()
        )

    elif query.data == "get_players":
        await query.edit_message_text("search fetching players...")
        players = get_players()
        if not players:
            await query.edit_message_text("error failed to fetch players.")
            return

        text = format_players_list(players)
        keyboard = []
        row = []
        for p in players:
            num = p.get("number", "")
            row.append(InlineKeyboardButton(f"{num}", callback_data=f"player_{num}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("back", callback_data="back_to_menu")])

        await query.edit_message_text(
            text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("player_"):
        try:
            player_num = int(query.data.split("_")[1])
        except (IndexError, ValueError):
            await query.answer("invalid player")
            return

        players = get_players()
        player = find_player_by_number(players, player_num)
        if not player:
            await query.answer("player not found")
            return

        player_name = player.get("name", "")
        await query.edit_message_text(f"search searching news for {player_name}...")

        player_news = get_player_news(
            RSS_FEEDS, TELEGRAM_SOURCES, player_name, max_items=10
        )
        if not player_news:
            await query.edit_message_text(
                f"empty no news for {player_name}.",
                reply_markup=_build_back_players(),
            )
            return

        messages = summarize_news_multi_persian(player_news, max_per_msg=10)
        img_url = _find_image_for_chunk(player_news, 0, 10)

        if img_url:
            try:
                await query.edit_message_text(
                    messages[0], parse_mode="Markdown", disable_web_page_preview=True
                )
                await query.message.reply_photo(
                    photo=img_url, caption=f"image news {player_name}"
                )
            except Exception:
                await query.edit_message_text(
                    messages[0],
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                    reply_markup=_build_back_players(),
                )
        else:
            await query.edit_message_text(
                messages[0],
                parse_mode="Markdown",
                disable_web_page_preview=True,
                reply_markup=_build_back_players(),
            )

        for i, msg in enumerate(messages[1:3], 1):
            img_url = _find_image_for_chunk(player_news, i * 10, 10)
            if img_url:
                try:
                    await query.message.reply_photo(
                        photo=img_url, caption=msg[:1024], parse_mode="Markdown"
                    )
                except Exception:
                    await query.message.reply_text(
                        msg, parse_mode="Markdown", disable_web_page_preview=True
                    )
            else:
                await query.message.reply_text(
                    msg, parse_mode="Markdown", disable_web_page_preview=True
                )


# ─── Scheduled News Sender ─────────────────────────────────────

async def send_scheduled_news(context: ContextTypes.DEFAULT_TYPE):
    """Send summarized news to admin chat via JobQueue."""
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
            logger.info(f"Sent {len(news)} news items to admin")
        except Exception as e:
            logger.error(f"Failed to send news to admin: {e}")
    else:
        logger.info("No new news to send")


# ─── Bot Setup ─────────────────────────────────────────────────

def setup_bot() -> Application:
    """Setup and configure the bot."""
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("news", "Get latest Real Madrid news"),
        BotCommand("status", "Check bot status"),
        BotCommand("sources", "View news sources"),
        BotCommand("players", "View Real Madrid squad"),
    ]

    async def _post_init(application: Application) -> None:
        try:
            await application.bot.set_my_commands(commands)
            logger.info("Bot commands set successfully")
        except Exception as e:
            logger.warning(f"Failed to set bot commands: {e}")
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

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("news", news_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("sources", sources_handler))
    app.add_handler(CommandHandler("players", players_handler))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.job_queue.run_repeating(
        send_scheduled_news,
        interval=3 * 3600,
        first=60,
        name="real_madrid_news",
    )

    logger.info("Bot setup complete")
    return app