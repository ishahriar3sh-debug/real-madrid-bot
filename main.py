"""
Real Madrid News Bot — Entry Point
Supports both long-polling (local) and webhook (cloud) modes.
"""
import asyncio
import logging
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    """Simple health check endpoint for Render."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
    
    def log_message(self, format, *args):
        pass


def start_health_server():
    """Start a minimal HTTP server to keep Render happy."""
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health server started on port {port}")
    server.serve_forever()


def main():
    from bot import setup_bot

    # Start health server in background thread (for Render Web Service)
    PORT = os.environ.get("PORT")
    if PORT:
        thread = threading.Thread(target=start_health_server, daemon=True)
        thread.start()
        logger.info("Render mode: health server started")

    WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
    RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
    webhook = WEBHOOK_URL or RENDER_EXTERNAL_URL

    # Create event loop explicitly (Python 3.14 compatibility)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = setup_bot()

    if webhook:
        logger.info(f"Starting bot in WEBHOOK mode: {webhook}")
        app.run_webhook(
            listen="0.0.0.0",
            port=int(PORT or 8443),
            url_path="webhook",
            webhook_url=f"{webhook}/webhook",
        )
    else:
        logger.info("Starting bot in POLLING mode (local)")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
