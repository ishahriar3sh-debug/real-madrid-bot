"""
Real Madrid News Bot — Entry Point
"""
import asyncio
import logging
import os

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    from bot import setup_bot

    # Create event loop (Python 3.14 compatibility)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = setup_bot()
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
    RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
    webhook = WEBHOOK_URL or RENDER_EXTERNAL_URL

    if webhook:
        logger.info(f"Starting in WEBHOOK mode: {webhook}")
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8443)),
            url_path="webhook",
            webhook_url=f"{webhook}/webhook",
        )
    else:
        logger.info("Starting in POLLING mode")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
