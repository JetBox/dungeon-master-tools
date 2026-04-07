import json
import os
import tempfile
from dataclasses import asdict
from enum import Enum

from src.errors import ProjectLoadError
from src.models import (
    CalendarDefinition,
    Era,
    EraDirection,
    FantasyDateTime,
    IntercalaryPeriod,
    LunarCycle,
    MonthDefinition,
    Project,
    GREGORIAN_DEFAULT,
)

REQUIRED_FIELDS = ("name", "version")


def _to_serializable(data):
    if isinstance(data, dict):
        return {k: _to_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_to_serializable(item) for item in data]
    elif isinstance(data, Enum):
        return data.value
    return data


def _load_calendar_definition(data: dict) -> CalendarDefinition:
    try:
        months = [MonthDefinition(**m) for m in data["months"]]
        lunar_cycles = [LunarCycle(**lc) for lc in data.get("lunar_cycles", [])]
        intercalary_periods = [IntercalaryPeriod(**ip) for ip in data.get("intercalary_periods", [])]
        eras = [
            Era(name=e["name"], starting_year=e["starting_year"], direction=EraDirection(e["direction"]))
            for e in data.get("eras", [])
        ]
        return CalendarDefinition(
            name=data["name"],
            months=months,
            week_length=data["week_length"],
            weekday_names=data["weekday_names"],
            hours_per_day=data["hours_per_day"],
            lunar_cycles=lunar_cycles,
            intercalary_periods=intercalary_periods,
            eras=eras,
            week_start_offset=data.get("week_start_offset", 0),
        )
    except (KeyError, ValueError) as e:
        raise ProjectLoadError(f"Invalid calendar definition: {e}") from e


def _load_fantasy_datetime(data: dict, cal: CalendarDefinition) -> FantasyDateTime:
    try:
        era = None
        era_name = data.get("era")
        if era_name is not None:
            matching = [e for e in cal.eras if e.name == era_name]
            if not matching:
                raise ProjectLoadError(f"Era '{era_name}' not found in calendar definition")
            era = matching[0]
        return FantasyDateTime(
            calendar=cal,
            year=data["year"],
            month=data["month"],
            day=data["day"],
            hour=data["hour"],
            minute=data["minute"],
            second=data["second"],
            era=era,
        )
    except (KeyError, ValueError) as e:
        raise ProjectLoadError(f"Invalid tracked date: {e}") from e


class Serializer:
    def save(self, project: Project, path: str) -> None:
        """Write project to JSON atomically (temp file → replace)."""
        data = _to_serializable(asdict(project))

        # Strip redundant `calendar` field from tracked_date and convert era dict to name string
        if data.get("tracked_date") is not None:
            td = data["tracked_date"]
            td.pop("calendar", None)
            if isinstance(td.get("era"), dict):
                td["era"] = td["era"].get("name")

        dir_name = os.path.dirname(os.path.abspath(path))
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def load(self, path: str) -> Project:
        """Read and validate a project JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ProjectLoadError(f"Invalid JSON: {e}") from e

        for field in REQUIRED_FIELDS:
            if field not in data:
                raise ProjectLoadError(f"Missing required field: '{field}'")

        try:
            if "calendar_definition" in data:
                cal = _load_calendar_definition(data["calendar_definition"])
            else:
                cal = GREGORIAN_DEFAULT

            tracked_date = None
            if data.get("tracked_date") is not None:
                tracked_date = _load_fantasy_datetime(data["tracked_date"], cal)

            return Project(
                name=data["name"],
                version=data["version"],
                calendar_definition=cal,
                tracked_date=tracked_date,
                calendar_source=data.get("calendar_source", ""),
            )
        except ProjectLoadError:
            raise
        except (KeyError, ValueError) as e:
            raise ProjectLoadError(f"Invalid project data: {e}") from e
