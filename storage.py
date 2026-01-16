from __future__ import annotations
import json
import os
import threading
from typing import Dict, List
from models import Event, Clipper


class Storage:
    """
    Simple JSON-based persistence for today's events.
    Key: "HH:MM" -> Event
    """
    def __init__(self, file_path: str) -> None:
        self.events_file_path = file_path
        self.clippers_file_path = "clippers.json" # New file for clippers
        self._lock = threading.RLock()
        self._events: Dict[str, Event] = {}
        self._clippers: Dict[str, Clipper] = {} # New dictionary for clippers

    def load(self) -> None:
        with self._lock:
            # Load events
            if not os.path.exists(self.events_file_path):
                self._events = {}
            else:
                try:
                    with open(self.events_file_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    self._events = {k: Event.from_dict(v) for k, v in raw.items()}
                except Exception:
                    self._events = {}
            
            # Load clippers
            if not os.path.exists(self.clippers_file_path):
                self._clippers = {}
            else:
                try:
                    with open(self.clippers_file_path, "r", encoding="utf-8") as f:
                        raw_clippers = json.load(f)
                    self._clippers = {k: Clipper.from_dict(v) for k, v in raw_clippers.items()}
                except Exception:
                    self._clippers = {}


    def save(self) -> None:
        with self._lock:
            # Save events
            serial_events = {k: v.to_dict() for k, v in self._events.items()}
            with open(self.events_file_path, "w", encoding="utf-8") as f:
                json.dump(serial_events, f, indent=2, ensure_ascii=False)
            
            # Save clippers
            serial_clippers = {k: v.to_dict() for k, v in self._clippers.items()}
            with open(self.clippers_file_path, "w", encoding="utf-8") as f:
                json.dump(serial_clippers, f, indent=2, ensure_ascii=False)

    def all_events(self, guild_id: int = None) -> List[Event]:
        with self._lock:
            if guild_id is None:
                return list(self._events.values())
            return [e for e in self._events.values() if e.guild_id == guild_id]

    def get_events_map(self) -> Dict[str, Event]:
        with self._lock:
            return dict(self._events)

    def upsert_event(self, event: Event) -> None:
        with self._lock:
            # Use composite key: guild_id:time_hhmm
            key = f"{event.guild_id}:{event.time_hhmm}"
            self._events[key] = event
            self.save()

    def remove_event(self, hhmm: str, guild_id: int = None) -> bool:
        with self._lock:
            # Create a composite key for guild-specific events
            key = f"{guild_id}:{hhmm}" if guild_id else hhmm
            existed = key in self._events
            if existed:
                del self._events[key]
                self.save()
            return existed

    def clear_events(self, guild_id: int = None) -> None:
        with self._lock:
            if guild_id is None:
                self._events.clear()
            else:
                # Remove only events for this guild
                keys_to_remove = [k for k, v in self._events.items() if v.guild_id == guild_id]
                for key in keys_to_remove:
                    del self._events[key]
            self.save()

    def clear_clippers(self, guild_id: int = None) -> None:
        with self._lock:
            if guild_id is None:
                self._clippers.clear()
            else:
                # Remove only clippers for this guild
                keys_to_remove = [k for k, v in self._clippers.items() if v.guild_id == guild_id]
                for key in keys_to_remove:
                    del self._clippers[key]
            self.save()

    def all_clippers(self, guild_id: int = None) -> List[Clipper]:
        with self._lock:
            if guild_id is None:
                return list(self._clippers.values())
            return [c for c in self._clippers.values() if c.guild_id == guild_id]

    def get_clipper(self, command_name: str, guild_id: int = None) -> Clipper | None:
        with self._lock:
            clipper = self._clippers.get(command_name)
            if clipper and guild_id is not None and clipper.guild_id != guild_id:
                return None
            return clipper

    def upsert_clipper(self, clipper: Clipper) -> None:
        with self._lock:
            # Use composite key: guild_id:command_name
            key = f"{clipper.guild_id}:{clipper.command_name}"
            self._clippers[key] = clipper
            self.save()

    def remove_clipper(self, command_name: str, guild_id: int = None) -> bool:
        with self._lock:
            key = f"{guild_id}:{command_name}" if guild_id else command_name
            existed = key in self._clippers
            if existed:
                del self._clippers[key]
                self.save()
            return existed
