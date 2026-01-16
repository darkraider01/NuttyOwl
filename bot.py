from __future__ import annotations
import asyncio
import discord
from discord.ext import commands
import datetime
import logging
import logging.handlers
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
from events import EventsCog
from models import Clipper
from typing import Union

# Configure logging
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)

handler = logging.handlers.RotatingFileHandler(
    filename='discord.log',
    encoding='utf-8',
    maxBytes=32 * 1024 * 1024, # 32 MiB
    backupCount=5, # Rotate through 5 files
)
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Add a StreamHandler to output log messages to the console
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True # Added to allow fetching members for addrole command

class PingBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = datetime.datetime.now(datetime.timezone.utc)

bot = PingBot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)

# Shared services
storage = Storage(EVENTS_PATH)
scheduler = UtcScheduler(bot, storage, DEFAULT_CHANNEL_NAME)


@bot.event
async def on_ready():
    # Load persisted data once connected
    storage.load()
    print(f"✅ Logged in as {bot.user} (id={bot.user.id})")
    # Start background scheduler
    await scheduler.start()
    
    
    # Recreate asyncio tasks for existing events
    events_cog = bot.get_cog('EventsCog')
    if events_cog and bot.guilds:
        # Recreate tasks for each guild
        for guild in bot.guilds:
            # Find a suitable channel to use as context for this guild
            ctx_channel = None
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    ctx_channel = channel
                    break
            
            if ctx_channel:
                await events_cog.recreate_tasks_for_existing_events(ctx_channel, guild.id)
        print("✅ Recreated scheduled tasks for existing events")
    
    # Register dynamic clipper commands
    # Unregister dynamic commands first to prevent CommandRegistrationError on reconnects
    for clipper in storage.all_clippers():
        existing_command = bot.get_command(clipper.command_name)
        if existing_command:
            bot.remove_command(existing_command.name)

    # Then, register dynamic clipper commands
    for clipper in storage.all_clippers():
        bot.add_command(create_clipper_command(clipper.command_name, clipper.description, clipper.guild_id))
    print(f"✅ Loaded {len(storage.all_clippers())} clipper commands.")


@bot.command(name="addrole")
async def add_role(ctx: commands.Context, target: Union[discord.Role, discord.Member]):
    """
    Adds a role or user to be pinged for events.
    Usage: !addrole @Role or !addrole @User
    """
    guild_id = ctx.guild.id
    config = get_roles_config(guild_id)
    config["role_id"] = target.id
    save_roles_config(config, guild_id)
    await ctx.send(f"✅ {target.mention} will be pinged for events in this server.")


@bot.command(name="removerole")
async def remove_role(ctx: commands.Context):
    """
    Removes the role that is configured to be pinged.
    Usage: !removerole
    """
    guild_id = ctx.guild.id
    config = get_roles_config(guild_id)
    if "role_id" in config:
        del config["role_id"]
        save_roles_config(config, guild_id)
        await ctx.send("✅ Configured role for pings has been removed from this server.")
    else:
        await ctx.send("ℹ️ No role is currently configured for pings in this server.")


@bot.command(name="uptime")
async def uptime(ctx: commands.Context):
    """
    Shows how long the bot has been online.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
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


def create_clipper_command(command_name: str, description: str, guild_id: int):
    @bot.command(name=command_name, help=description)
    async def dynamic_clipper_command(ctx: commands.Context):
        """
        A custom clipper command.
        """
        # Only respond if command is used in the correct guild
        if ctx.guild.id == guild_id:
            await ctx.send(description)
    return dynamic_clipper_command


@bot.command(name="clipper")
async def clipper_command(ctx: commands.Context, command_name: str, *, description: str):
    """
    Saves a new clipper command.
    Usage: !clipper <command_name> <description>
    """
    guild_id = ctx.guild.id
    if storage.get_clipper(command_name, guild_id):
        await ctx.send(f"❌ Clipper command `!{command_name}` already exists in this server.")
        return

    clipper = Clipper(command_name=command_name, description=description, guild_id=guild_id)
    storage.upsert_clipper(clipper)

    # Register the new command dynamically
    bot.add_command(create_clipper_command(command_name, description, guild_id))
    await ctx.send(f"✅ Clipper command `!{command_name}` saved for this server.")


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
        # Filter out dynamically created clipper commands from the main help if they are not explicitly defined
        if command.name not in ["addrole", "removerole", "uptime", "clipper", "clippers", "clearclippers", "help"] and storage.get_clipper(command.name):
            continue

        # Format the command usage and description
        usage = f"`{COMMAND_PREFIX}{command.name} {command.signature}`"
        description = command.help or "No description provided."
        
        embed.add_field(name=usage, value=description, inline=False)

    await ctx.send(embed=embed)


@bot.command(name="clippers")
async def list_clippers(ctx: commands.Context):
    """
    Lists all saved clipper commands for this server.
    """
    guild_id = ctx.guild.id
    clippers = storage.all_clippers(guild_id)
    if not clippers:
        await ctx.send("ℹ️ No clipper commands saved yet in this server.")
        return

    embed = discord.Embed(
        title="Saved Clipper Commands",
        description="Here are all the clipper commands you've saved in this server:",
        color=discord.Color.green()
    )

    for clipper in clippers:
        # Truncate description for embed field to prevent HTTPException (max 1024 characters)
        description = clipper.description
        # Truncate description for embed field to a shorter length for readability
        max_length = 200  # Adjust this value as needed
        if len(description) > max_length:
            description = description[:max_length - 3] + "..." # Truncate and add ellipsis
        embed.add_field(name=f"`!{clipper.command_name}`", value=description, inline=False)
    
    await ctx.send(embed=embed)


@bot.command(name="clearclippers")
async def clear_clippers(ctx: commands.Context):
    """
    Clears all saved clipper commands for this server.
    """
    guild_id = ctx.guild.id
    # Unregister dynamic commands for this guild
    for clipper in storage.all_clippers(guild_id):
        command = bot.get_command(clipper.command_name)
        if command:
            bot.remove_command(command.name)

    storage.clear_clippers(guild_id)
    await ctx.send("✅ All clipper commands have been cleared for this server.")


async def main():
    async with bot:
        # Register cogs before login
        await bot.add_cog(EventsCog(bot, storage))
        await bot.start(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
