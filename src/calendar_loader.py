import json
from src.errors import ProjectLoadError
from src.models import CalendarDefinition
from src.serializer import _load_calendar_definition

CALENDAR_REQUIRED_FIELDS = ("name", "months", "week_length", "weekday_names", "hours_per_day")


def load_calendar_file(path: str) -> CalendarDefinition:
    """
    Read a standalone calendar JSON file and return a CalendarDefinition.

    Raises ProjectLoadError on:
      - file not found
      - malformed JSON
      - missing required top-level fields
      - invalid field values (propagated from _load_calendar_definition)
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ProjectLoadError(f"Calendar file not found: {path}")
    except json.JSONDecodeError as e:
        raise ProjectLoadError(f"Invalid JSON in calendar file: {e}")

    for field in CALENDAR_REQUIRED_FIELDS:
        if field not in data:
            raise ProjectLoadError(f"Missing required calendar field: '{field}'")

    return _load_calendar_definition(data)
