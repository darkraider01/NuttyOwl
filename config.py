from __future__ import annotations
import os
import json
from configure import DISCORD_BOT_TOKEN, COMMAND_PREFIX, EVENTS_FILE, DEFAULT_CHANNEL_NAME

# --- Path Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_ROLES_PATH = os.path.join(BASE_DIR, "config_roles.json")
EVENTS_PATH = os.path.join(BASE_DIR, EVENTS_FILE)



def get_roles_config(guild_id: int = None) -> dict:
    """
    Loads the roles configuration from JSON, creating the file if it doesn't exist.
    If guild_id is provided, returns only that guild's config.
    """
    if not os.path.exists(CONFIG_ROLES_PATH):
        with open(CONFIG_ROLES_PATH, "w") as f:
            json.dump({}, f)
    with open(CONFIG_ROLES_PATH, "r") as f:
        all_configs = json.load(f)
    
    if guild_id is None:
        return all_configs
    
    # Return guild-specific config or empty dict
    return all_configs.get(str(guild_id), {})


def save_roles_config(config: dict, guild_id: int = None) -> None:
    """
    Saves the roles configuration to JSON.
    If guild_id is provided, updates only that guild's config.
    """
    if guild_id is None:
        # Save entire config
        with open(CONFIG_ROLES_PATH, "w") as f:
            json.dump(config, f, indent=2)
    else:
        # Load all configs, update specific guild, save all
        all_configs = get_roles_config()
        all_configs[str(guild_id)] = config
        with open(CONFIG_ROLES_PATH, "w") as f:
            json.dump(all_configs, f, indent=2)

