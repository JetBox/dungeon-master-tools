from dataclasses import dataclass, field
from enum import Enum


@dataclass
class Project:
    name: str
    version: str = "1.0"


class ItemCategory(Enum):
    LIGHT = "light"
    MAGIC_SPELL = "magic spell"
    DEATH_SAVES = "death saves"
    SPECIAL_ABILITY = "special ability"
    OTHER = "other"


# Maps category → (border colour, emoji prefix)
CATEGORY_STYLE: dict[ItemCategory, tuple[str, str]] = {
    ItemCategory.LIGHT:           ("#FFD700", "💡"),
    ItemCategory.MAGIC_SPELL:     ("#6EC6FF", "🔮"),
    ItemCategory.DEATH_SAVES:     ("#222222", "💀"),
    ItemCategory.SPECIAL_ABILITY: ("#4CAF50", "⚡"),
    ItemCategory.OTHER:           ("#9E9E9E", ""),
}


@dataclass
class RoundTrackerItem:
    name: str
    rounds: int
    category: ItemCategory = field(default=ItemCategory.OTHER)
