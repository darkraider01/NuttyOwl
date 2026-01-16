from __future__ import annotations
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
import discord
import logging
from storage import Storage
from models import Event


class UtcScheduler:
    """
    Periodically checks the UTC clock and fires events whose time matches HH:MM.
    - Resolution: 30 seconds (so we don't miss minute boundaries).
    - Clears unfired events at UTC midnight to keep "daily" semantics.
    """
    def __init__(self, client: discord.Client, storage: Storage, default_channel_name: str) -> None:
        self.client = client
        self.storage = storage
        self.default_channel_name = default_channel_name
        self._task: Optional[asyncio.Task] = None
        self._last_midnight = self._utc_midnight_key(datetime.now(timezone.utc))

    @staticmethod
    def _utc_now_hhmm() -> str:
        return datetime.now(timezone.utc).strftime("%H:%M")

    @staticmethod
    def _utc_midnight_key(dt: datetime) -> str:
        d = dt.astimezone(timezone.utc).date()
        return d.isoformat()

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="utc-scheduler-loop")

    async def _run(self) -> None:
        try:
            while True:
                await self._tick()
                await asyncio.sleep(30)  # 30s cadence
        except asyncio.CancelledError:
            pass

    async def _tick(self) -> None:
        # Clear events when a new UTC day starts
        now = datetime.now(timezone.utc)
        key = self._utc_midnight_key(now)
        if key != self._last_midnight:
            self._last_midnight = key
            # wipe any remaining events (daily semantics)
            self.storage.clear_events()

        hhmm = self._utc_now_hhmm()
        # Check all events to see if any match the current time
        all_events = self.storage.all_events()
        for event in all_events:
            if event.time_hhmm == hhmm:
                await self._fire_event(event)
                # remove after firing
                self.storage.remove_event(hhmm, event.guild_id)

    async def _fire_event(self, event: Event) -> None:
        # Fire event only in the guild it was created for
        guild = self.client.get_guild(event.guild_id)
        if guild is None:
            logging.warning(f"Guild {event.guild_id} not found for event {event.description}")
            return
        
        target = guild.get_role(event.role_id)
        if target is None:
            try:
                target = await guild.fetch_member(event.role_id)
            except discord.NotFound:
                logging.warning(f"Role/member {event.role_id} not found in guild {guild.id}")
                return
        
        if target is None:
            return

        channel = self._pick_channel(guild)
        if channel is None:
            logging.warning(f"No suitable channel found in guild {guild.id}")
            return

        try:
            await channel.send(f"🔔 {target.mention} Reminder (UTC {event.time_hhmm}): **{event.description}**")
        except discord.Forbidden:
            # Missing permissions in this channel; skip
            logging.warning(f"Missing permissions in channel {channel.id} in guild {guild.id}")
        except discord.HTTPException as e:
            # Catch other Discord API errors
            logging.error(f"Error sending message in guild {guild.id}, channel {channel.id}: {e}")
        except Exception as e:
            # Catch any other unexpected errors
            logging.error(f"An unexpected error occurred in guild {guild.id}, channel {channel.id}: {e}")

    def _pick_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        # Prefer system channel if sendable; else by name; else first sendable text channel
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            return guild.system_channel

        # Try default by name
        channel_by_name = discord.utils.get(guild.text_channels, name=self.default_channel_name)
        if channel_by_name and channel_by_name.permissions_for(guild.me).send_messages:
            return channel_by_name

        # Fallback: any text channel we can send to
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                return ch
        return None
