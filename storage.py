from __future__ import annotations
import json
import os
import threading
from typing import Dict, List
from models import Event


class Storage:
    """
    Simple JSON-based persistence for today's events.
    Key: "HH:MM" -> Event
    """
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self._lock = threading.RLock()
        self._events: Dict[str, Event] = {}

    def load(self) -> None:
        with self._lock:
            if not os.path.exists(self.file_path):
                self._events = {}
                return
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                self._events = {k: Event.from_dict(v) for k, v in raw.items()}
            except Exception:
                # Corrupt file—start fresh but don't crash the bot
                self._events = {}

    def save(self) -> None:
        with self._lock:
            serial = {k: v.to_dict() for k, v in self._events.items()}
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(serial, f, indent=2, ensure_ascii=False)

    def all(self) -> List[Event]:
        with self._lock:
            return list(self._events.values())

    def get_map(self) -> Dict[str, Event]:
        with self._lock:
            return dict(self._events)

    def upsert(self, event: Event) -> None:
        with self._lock:
            self._events[event.time_hhmm] = event
            self.save()

    def remove(self, hhmm: str) -> bool:
        with self._lock:
            existed = hhmm in self._events
            if existed:
                del self._events[hhmm]
                self.save()
            return existed

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self.save()
