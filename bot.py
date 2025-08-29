from __future__ import annotations
import asyncio
import discord
from discord.ext import commands
from configure import DISCORD_BOT_TOKEN, COMMAND_PREFIX, EVENTS_FILE, DEFAULT_CHANNEL_NAME
import json
from storage import Storage
from scheduler import UtcScheduler
from cogs.events import EventsCog
import cogs.events
from typing import Union # Import Union

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True # Added to allow fetching members for addrole command

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)

# Shared services
storage = Storage(EVENTS_FILE)
scheduler = UtcScheduler(bot, storage, DEFAULT_CHANNEL_NAME)


@bot.event
async def on_ready():
    # Load persisted events once connected
    storage.load()
    print(f"✅ Logged in as {bot.user} (id={bot.user.id})")
    # Start background scheduler
    await scheduler.start()
    
    # Recreate asyncio tasks for existing events
    events_cog = bot.get_cog('EventsCog')
    if events_cog and bot.guilds:
        # Find a suitable channel to use as context
        ctx_channel = None
        for guild in bot.guilds:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    ctx_channel = channel
                    break
            if ctx_channel:
                break
        
        if ctx_channel:
            await events_cog.recreate_tasks_for_existing_events(ctx_channel)
            print("✅ Recreated scheduled tasks for existing events")


@bot.command(name="addrole")
async def add_role(ctx: commands.Context, target: Union[discord.Role, discord.Member]):
    """
    Adds a role or user to be pinged for events.
    Usage: !addrole @Role or !addrole @User
    """
    with open("config_roles.json", "r") as f:
        config = json.load(f)
    config["role_id"] = target.id
    with open("config_roles.json", "w") as f:
        json.dump(config, f, indent=2)
    await ctx.send(f"✅ {target.mention} will be pinged for events.")


@bot.command(name="removerole")
async def remove_role(ctx: commands.Context):
    """
    Removes the role that is configured to be pinged.
    Usage: !removerole
    """
    with open("config_roles.json", "r") as f:
        config = json.load(f)
    if "role_id" in config:
        del config["role_id"]
        with open("config_roles.json", "w") as f:
            json.dump(config, f, indent=2)
        await ctx.send("✅ Configured role for pings has been removed.")
    else:
        await ctx.send("ℹ️ No role is currently configured for pings.")


async def main():
    async with bot:
        # Register cogs before login
        await bot.add_cog(cogs.events.EventsCog(bot, storage))
        await bot.start(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
