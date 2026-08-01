"""
Real Madrid News Bot — Entry Point
Supports both long-polling (local) and webhook (cloud) modes.
"""
import logging
import os
import sys

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    from bot import setup_bot

    app = setup_bot()
    PORT = int(os.environ.get("PORT", 8443))
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
    RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

    # If WEBHOOK_URL is set, use webhook mode (for cloud deployment)
    webhook = WEBHOOK_URL or RENDER_EXTERNAL_URL

    if webhook:
        logger.info(f"Starting bot in WEBHOOK mode: {webhook}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="webhook",
            webhook_url=f"{webhook}/webhook",
        )
    else:
        logger.info("Starting bot in POLLING mode (local)")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
