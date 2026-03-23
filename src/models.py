from dataclasses import dataclass


@dataclass
class Project:
    name: str
    version: str = "1.0"


@dataclass
class RoundTrackerItem:
    name: str
    rounds: int
