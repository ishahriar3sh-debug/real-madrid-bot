"""
Real Madrid News Bot — Entry Point
Supports both long-polling (local) and webhook (cloud) modes.
Includes health check to keep Render service alive.
"""
import asyncio
import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    """Health check handler to keep Render service alive."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
    
    def log_message(self, format, *args):
        pass  # Suppress health check logs


def start_health_server(port=8080):
    """Start health check server in background thread."""
    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info(f"Health check server started on port {port}")
    except Exception as e:
        logger.warning(f"Could not start health server: {e}")


def main():
    from bot import setup_bot

    # Create event loop (Python 3.14 compatibility)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Start health check server to keep Render service alive
    health_port = int(os.environ.get("HEALTH_PORT", 8080))
    start_health_server(health_port)

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
