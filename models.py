from dataclasses import dataclass, asdict

@dataclass
class Event:
    time_hhmm: str
    role_id: int
    description: str

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)