import os
import logging
import sys

# Logging Setup
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL),
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Config Variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ODOO_URL = os.getenv("ODOO_URL", "").strip()
ODOO_DB = os.getenv("ODOO_DB", "odoo").strip()
ODOO_EMAIL = os.getenv("ODOO_EMAIL", "").strip()
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "").strip()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "").strip()

if not TELEGRAM_BOT_TOKEN:
    logger.warning("TELEGRAM_BOT_TOKEN is not set!")
if not ODOO_URL:
    logger.warning("ODOO_URL is not set!")
if not ENCRYPTION_KEY:
    logger.warning("ENCRYPTION_KEY is not set!")
