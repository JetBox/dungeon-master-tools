from dataclasses import dataclass


@dataclass
class Project:
    name: str
    version: str = "1.0"
