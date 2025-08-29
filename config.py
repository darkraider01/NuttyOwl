from __future__ import annotations
import os
import json
from configure import DISCORD_BOT_TOKEN, COMMAND_PREFIX, EVENTS_FILE, DEFAULT_CHANNEL_NAME

# --- Path Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_ROLES_PATH = os.path.join(BASE_DIR, "config_roles.json")
EVENTS_PATH = os.path.join(BASE_DIR, EVENTS_FILE)


def get_roles_config() -> dict:
    """
    Loads the roles configuration from JSON, creating the file if it doesn't exist.
    """
    if not os.path.exists(CONFIG_ROLES_PATH):
        with open(CONFIG_ROLES_PATH, "w") as f:
            json.dump({}, f)
    with open(CONFIG_ROLES_PATH, "r") as f:
        return json.load(f)


def save_roles_config(config: dict) -> None:
    """
    Saves the roles configuration to JSON.
    """
    with open(CONFIG_ROLES_PATH, "w") as f:
        json.dump(config, f, indent=2)
