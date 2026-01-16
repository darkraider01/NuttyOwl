from dataclasses import dataclass, asdict

@dataclass
class Event:
    time_hhmm: str
    role_id: int
    description: str
    guild_id: int  # Discord server ID

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

@dataclass
class Clipper:
    command_name: str
    description: str
    guild_id: int  # Discord server ID

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)