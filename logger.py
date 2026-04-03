"""
logger.py — Setup logging ke console dan file.
"""

import logging
import os
from datetime import datetime


def setup_logger() -> logging.Logger:
    os.makedirs("logs", exist_ok=True)
    log_filename = f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_filename, encoding="utf-8"),
        ],
    )
    return logging.getLogger(__name__)
