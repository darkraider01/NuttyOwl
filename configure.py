import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "").strip()
COMMAND_PREFIX: str = os.getenv("COMMAND_PREFIX", "!").strip() or "!"
EVENTS_FILE: str = os.getenv("EVENTS_FILE", "events.json").strip()
DEFAULT_CHANNEL_NAME: str = os.getenv("DEFAULT_CHANNEL_NAME", "general").strip()

if not DISCORD_BOT_TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN is not set. Put it in your .env")
