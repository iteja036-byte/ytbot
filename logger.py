"""
ytbot/logger.py — colored terminal output + file logging
"""

import os
import sys
import logging
from datetime import datetime
from config import LOGS_DIR

os.makedirs(LOGS_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOGS_DIR, f"ytbot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# ANSI colors
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]
)

_file_logger = logging.getLogger("ytbot")


def ok(msg: str):
    print(f"{GREEN}✅ {msg}{RESET}")
    _file_logger.info(msg)

def info(msg: str):
    print(f"{CYAN}ℹ  {msg}{RESET}")
    _file_logger.info(msg)

def warn(msg: str):
    print(f"{YELLOW}⚠  {msg}{RESET}")
    _file_logger.warning(msg)

def err(msg: str):
    print(f"{RED}❌ {msg}{RESET}")
    _file_logger.error(msg)

def step(msg: str):
    print(f"\n{BOLD}{CYAN}▶  {msg}{RESET}")
    _file_logger.info(f"STEP: {msg}")

def die(msg: str, code: int = 1):
    err(msg)
    sys.exit(code)

