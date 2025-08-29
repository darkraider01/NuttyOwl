from __future__ import annotations
import asyncio
import discord
from discord.ext import commands
import datetime
from config import (
    DISCORD_BOT_TOKEN,
    COMMAND_PREFIX,
    EVENTS_PATH,
    DEFAULT_CHANNEL_NAME,
    get_roles_config,
    save_roles_config,
)
from storage import Storage
from scheduler import UtcScheduler
from cogs.events import EventsCog
import cogs.events
from typing import Union # Import Union

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True # Added to allow fetching members for addrole command

class PingBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = datetime.datetime.utcnow()

bot = PingBot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)

# Shared services
storage = Storage(EVENTS_PATH)
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
    config = get_roles_config()
    config["role_id"] = target.id
    save_roles_config(config)
    await ctx.send(f"✅ {target.mention} will be pinged for events.")


@bot.command(name="removerole")
async def remove_role(ctx: commands.Context):
    """
    Removes the role that is configured to be pinged.
    Usage: !removerole
    """
    config = get_roles_config()
    if "role_id" in config:
        del config["role_id"]
        save_roles_config(config)
        await ctx.send("✅ Configured role for pings has been removed.")
    else:
        await ctx.send("ℹ️ No role is currently configured for pings.")


@bot.command(name="uptime")
async def uptime(ctx: commands.Context):
    """
    Shows how long the bot has been online.
    """
    now = datetime.datetime.utcnow()
    delta = now - bot.start_time
    
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)

    if days > 0:
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        uptime_str = f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        uptime_str = f"{minutes}m {seconds}s"
    else:
        uptime_str = f"{seconds}s"
        
    await ctx.send(f"**Uptime:** {uptime_str}")


bot.remove_command('help')

@bot.command(name="help")
async def help_command(ctx: commands.Context):
    """
    Displays a list of available commands and their descriptions.
    """
    embed = discord.Embed(
        title="Bot Commands",
        description="Here is a list of all available commands:",
        color=discord.Color.blue()
    )

    # Dynamically get all commands, including those in cogs
    for command in bot.commands:
        # Format the command usage and description
        usage = f"`{COMMAND_PREFIX}{command.name} {command.signature}`"
        description = command.help or "No description provided."
        
        embed.add_field(name=usage, value=description, inline=False)

    await ctx.send(embed=embed)


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
