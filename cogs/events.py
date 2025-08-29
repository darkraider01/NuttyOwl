from __future__ import annotations
from datetime import datetime, timedelta
from typing import List
import discord
from discord.ext import commands
from storage import Storage
from models import Event
import asyncio
import logging
from config import get_roles_config

# Enable logging
logging.basicConfig(level=logging.INFO)


def _validate_hhmm(hhmm: str) -> bool:
    try:
        datetime.strptime(hhmm, "%H:%M")
        return True
    except ValueError:
        return False


class EventsCog(commands.Cog):
    """
    Commands to manage today's UTC events.
    """
    def __init__(self, bot: commands.Bot, storage: Storage) -> None:
        self.bot = bot
        self.storage = storage

    async def _schedule_ping(self, ctx: commands.Context, time: str, description: str, delta: timedelta):
        """
        Schedules a ping for the event.
        """
        logging.info(f"Scheduling ping for event: {description} at {time} with delta {delta}")
        try:
            event_time = datetime.strptime(time, "%H:%M").time()
        except ValueError:
            await ctx.send("❌ Invalid time format. Please use HH:MM (24h, UTC). Example: `14:30`")
            return

        now = datetime.utcnow()
        target_time = datetime(now.year, now.month, now.day, event_time.hour, event_time.minute) - delta
        if target_time < now:
            target_time += timedelta(days=1)  # Schedule for tomorrow if in the past

        seconds_until_ping = (target_time - now).total_seconds()
        logging.info(f"Time until ping: {seconds_until_ping} seconds")

        async def ping():
            logging.info(f"Firing ping for event: {description} at {time}")
            config = get_roles_config()
            role_id = config.get("role_id")
            if not role_id:
                await ctx.send("❌ No role configured for pings. Use `!addrole` to set a role.")
                return

            try:
                # Try to get as role first
                target = ctx.guild.get_role(int(role_id))
                if not target:
                    # If not a role, try to get as member
                    target = await ctx.guild.fetch_member(int(role_id))
                if not target:
                    await ctx.send("❌ Invalid role/user ID. Please use `!addrole` to set a valid role or user.")
                    return
                
                # Check if the target is a user and if they are mentionable
                if isinstance(target, discord.Member) and not target.bot and target.mention:
                    await ctx.send(f"🔔 {target.mention} Reminder (UTC {time}): **{description}**")
                elif isinstance(target, discord.Role) and target.mentionable:
                    await ctx.send(f"🔔 {target.mention} Reminder (UTC {time}): **{description}**")
                else:
                    await ctx.send(f"🔔 Reminder (UTC {time}): **{description}** (Couldn't mention {target.name})")

            except ValueError:
                await ctx.send("❌ Invalid role/user ID format. Please use `!addrole` to set a valid role or user.")
                return
            except discord.NotFound:
                await ctx.send("❌ Configured role/user not found in this guild. Please use `!addrole` to set a valid role or user.")
                return
            # Remove the event only after the final ping (at event time)
            if delta == timedelta(minutes=0):
                self.storage.remove(time)
                logging.info(f"Removed event: {description} at {time} from storage")

        await asyncio.sleep(seconds_until_ping)
        await ping()

    async def recreate_tasks_for_existing_events(self, ctx: commands.Context):
        """
        Recreates asyncio tasks for all existing events from storage.
        """
        events = self.storage.all()
        logging.info(f"Recreating tasks for {len(events)} events.")
        for event in events:
            # Schedule 1-hour, 5-minute, and at-event-time pings
            asyncio.create_task(self._schedule_ping(ctx, event.time_hhmm, event.description, timedelta(hours=1)))
            asyncio.create_task(self._schedule_ping(ctx, event.time_hhmm, event.description, timedelta(minutes=5)))
            asyncio.create_task(self._schedule_ping(ctx, event.time_hhmm, event.description, timedelta(minutes=0)))
        logging.info("Finished recreating tasks.")

    @commands.command(name="addevent")
    async def add_event(self, ctx: commands.Context, time: str = None, *, description: str = None):
        """
        Add an event at UTC HH:MM.
        Usage: !addevent 14:30 Description...
        Also can be used by mentioning the bot: @Bot addevent 14:30 Description...
        """
        if time is None or description is None:
            await ctx.send("❌ Invalid syntax. Usage: `!addevent HH:MM Description...`\nExample: `!addevent 14:30 Meeting about the new project`")
            return

        if not _validate_hhmm(time):
            await ctx.send("❌ Time must be in **HH:MM** (24h, UTC). Example: `14:30`")
            return

        config = get_roles_config()
        role_id = config.get("role_id")
        if not role_id:
            await ctx.send("❌ No role configured for events. Use `!addrole` to set a role first.")
            return

        event = Event(time_hhmm=time, role_id=role_id, description=description.strip())
        self.storage.upsert(event)
        
        # Get the target (role or user) to mention
        target_mention = ""
        try:
            target = ctx.guild.get_role(int(role_id))
            if not target:
                target = await ctx.guild.fetch_member(int(role_id))
            if target:
                target_mention = target.mention
            else:
                target_mention = f"<@&{role_id}>" # Fallback to raw mention if not found
        except (ValueError, discord.NotFound):
            target_mention = f"<@&{role_id}>" # Fallback to raw mention if conversion fails

        await ctx.send(f"📌 Added event at **{time} UTC** for {target_mention}: **{event.description}**")
        logging.info(f"Added event: {description} at {time} to storage")

        # Schedule 1-hour and 5-minute pre-event pings
        asyncio.create_task(self._schedule_ping(ctx, time, description, timedelta(hours=1)))
        asyncio.create_task(self._schedule_ping(ctx, time, description, timedelta(minutes=5)))
        asyncio.create_task(self._schedule_ping(ctx, time, description, timedelta(minutes=0))) # Ping at event time

    @commands.command(name="listevents")
    async def list_events(self, ctx: commands.Context):
        """
        List today's events (UTC).
        """
        events = sorted(self.storage.all(), key=lambda e: e.time_hhmm)
        if not events:
            await ctx.send("No events scheduled today (UTC).")
            return

        lines: List[str] = [
            f"⏰ **{e.time_hhmm} UTC** → <@&{e.role_id}> : {e.description}"
            for e in events
        ]
        await ctx.send("**Today's Events (UTC):**\n" + "\n".join(lines))

    @commands.command(name="clearevents")
    async def clear_events(self, ctx: commands.Context):
        """
        Clear all of today's events.
        """
        self.storage.clear()
        await ctx.send("🗑️ Cleared all events for today (UTC).")
        logging.info("Cleared all events from storage")

    @commands.command(name="removeevent")
    async def remove_event(self, ctx: commands.Context, time: str):
        """
        Remove a specific event by its UTC HH:MM.
        Usage: !removeevent 14:30
        """
        if not _validate_hhmm(time):
            await ctx.send("❌ Time must be in **HH:MM** (24h, UTC). Example: `14:30`")
            return

        removed = self.storage.remove(time)
        if removed:
            await ctx.send(f"✅ Removed event at **{time} UTC**.")
            logging.info(f"Removed event: {time} from storage")
        else:
            await ctx.send(f"ℹ️ No event found at **{time} UTC**.")

    @commands.command(name="listroles")
    async def list_roles(self, ctx: commands.Context):
        """
        Shows the role that is configured to be pinged.
        """
        config = get_roles_config()
        role_id = config.get("role_id")
        if not role_id:
            await ctx.send("❌ No role configured for pings. Use `!addrole` to set a role.")
            return

        try:
            # Try to get as role first
            target = ctx.guild.get_role(int(role_id))
            if not target:
                # If not a role, try to get as member
                target = await ctx.guild.fetch_member(int(role_id))
            if not target:
                await ctx.send("❌ Invalid role/user ID. Please use `!addrole` to set a valid role or user.")
                return
            await ctx.send(f"Currently configured role for pings: {target.mention}")
        except ValueError:
            await ctx.send("❌ Invalid role/user ID format. Please use `!addrole` to set a valid role or user.")
            return
        except discord.NotFound:
            await ctx.send("❌ Configured role/user not found in this guild. Please use `!addrole` to set a valid role or user.")
            return

