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
    RoundTrackerState,
    RoundTrackerItem,
    TimeTrackerItem,
    TurnModeSettings,
    TimeModeSettings,
    ItemCategory,
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
            Era(
                name=e["name"],
                display_start=e.get("display_start", e.get("starting_year", 1)),
                absolute_start=e.get("absolute_start", e.get("starting_year", 1)),
                absolute_end=e.get("absolute_end", e.get("ending_year", 9999)),
                direction=EraDirection(e["direction"]),
            )
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
            default_start_date=data.get("default_start_date"),
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
            intercalary_period_index=data.get("intercalary_period_index"),
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

            round_tracker_state = RoundTrackerState()  # default (empty, default settings)
            if "round_tracker_state" in data:
                rts_data = data["round_tracker_state"]
                turn_items = [
                    RoundTrackerItem(
                        name=item["name"],
                        rounds=item["rounds"],
                        category=ItemCategory(item["category"]),
                    )
                    for item in rts_data.get("turn_items", [])
                ]
                time_items = [
                    TimeTrackerItem(
                        name=item["name"],
                        seconds=item["seconds"],
                        category=ItemCategory(item["category"]),
                    )
                    for item in rts_data.get("time_items", [])
                ]
                ts_data = rts_data.get("turn_settings", {})
                turn_settings = TurnModeSettings(
                    re_interval=ts_data.get("re_interval", 2),
                    time_per_turn=ts_data.get("time_per_turn", 6),
                    integrate_calendar=ts_data.get("integrate_calendar", True),
                    sound_effects=ts_data.get("sound_effects", True),
                )
                tms_data = rts_data.get("time_settings", {})
                time_settings = TimeModeSettings(
                    re_interval=tms_data.get("re_interval", 12),
                    combat_round_seconds=tms_data.get("combat_round_seconds", 10),
                    dungeon_round_minutes=tms_data.get("dungeon_round_minutes", 6),
                    integrate_calendar=tms_data.get("integrate_calendar", True),
                    sound_effects=tms_data.get("sound_effects", True),
                )
                round_tracker_state = RoundTrackerState(
                    turn_items=turn_items,
                    time_items=time_items,
                    turn_settings=turn_settings,
                    time_settings=time_settings,
                )

            return Project(
                name=data["name"],
                version=data["version"],
                calendar_definition=cal,
                tracked_date=tracked_date,
                calendar_source=data.get("calendar_source", ""),
                round_tracker_state=round_tracker_state,
            )
        except ProjectLoadError:
            raise
        except (KeyError, ValueError) as e:
            raise ProjectLoadError(f"Invalid project data: {e}") from e
