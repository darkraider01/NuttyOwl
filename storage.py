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

    def all_events(self) -> List[Event]:
        with self._lock:
            return list(self._events.values())

    def get_events_map(self) -> Dict[str, Event]:
        with self._lock:
            return dict(self._events)

    def upsert_event(self, event: Event) -> None:
        with self._lock:
            self._events[event.time_hhmm] = event
            self.save()

    def remove_event(self, hhmm: str) -> bool:
        with self._lock:
            existed = hhmm in self._events
            if existed:
                del self._events[hhmm]
                self.save()
            return existed

    def clear_events(self) -> None:
        with self._lock:
            self._events.clear()
            self.save()

    def clear_clippers(self) -> None:
        with self._lock:
            self._clippers.clear()
            self.save()

    def all_clippers(self) -> List[Clipper]:
        with self._lock:
            return list(self._clippers.values())

    def get_clipper(self, command_name: str) -> Clipper | None:
        with self._lock:
            return self._clippers.get(command_name)

    def upsert_clipper(self, clipper: Clipper) -> None:
        with self._lock:
            self._clippers[clipper.command_name] = clipper
            self.save()

    def remove_clipper(self, command_name: str) -> bool:
        with self._lock:
            existed = command_name in self._clippers
            if existed:
                del self._clippers[command_name]
                self.save()
            return existed
