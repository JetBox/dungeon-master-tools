import datetime
from dataclasses import dataclass, field
from enum import Enum


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


@dataclass
class TimeTrackerItem:
    name: str
    seconds: int          # total duration in seconds, >= 1
    category: ItemCategory = field(default=ItemCategory.OTHER)


@dataclass
class TurnModeSettings:
    re_interval: int = 2
    time_per_turn: int = 6
    integrate_calendar: bool = True
    sound_effects: bool = True


@dataclass
class TimeModeSettings:
    re_interval: int = 12
    combat_round_seconds: int = 10
    dungeon_round_minutes: int = 6
    integrate_calendar: bool = True
    sound_effects: bool = True


@dataclass
class RoundTrackerState:
    turn_items: list[RoundTrackerItem] = field(default_factory=list)
    time_items: list[TimeTrackerItem] = field(default_factory=list)
    turn_settings: TurnModeSettings = field(default_factory=TurnModeSettings)
    time_settings: TimeModeSettings = field(default_factory=TimeModeSettings)


@dataclass
class CalendarDay:
    date: datetime.date


@dataclass
class TableEntry:
    name: str
    weight: int  # >= 1


@dataclass
class RandomTable:
    name: str
    entries: list[TableEntry] = field(default_factory=list)
# --- Custom Calendar Models ---

class EraDirection(Enum):
    ASCENDING = "ascending"
    DESCENDING = "descending"


@dataclass
class MonthDefinition:
    name: str
    day_count: int                        # base day count; 5–100
    leap_every_n_years: int | None = None # optional; must be >= 2 if set

    def __post_init__(self):
        if not (5 <= self.day_count <= 100):
            raise ValueError(f"day_count must be between 5 and 100, got {self.day_count}")
        if self.leap_every_n_years is not None and self.leap_every_n_years < 2:
            raise ValueError(
                f"leap_every_n_years must be >= 2 if set, got {self.leap_every_n_years}"
            )

    def effective_day_count(self, year: int) -> int:
        """Return the actual number of days in this month for the given year."""
        if self.leap_every_n_years is not None and year % self.leap_every_n_years == 0:
            return self.day_count + 1
        return self.day_count


@dataclass
class LunarCycle:
    name: str
    phase_interval: int
    phase_offset: int = 0

    def __post_init__(self):
        if self.phase_interval < 1:
            raise ValueError(f"phase_interval must be >= 1, got {self.phase_interval}")


@dataclass
class IntercalaryPeriod:
    name: str
    day_count: int
    after_month: int

    def __post_init__(self):
        if self.day_count < 1:
            raise ValueError(f"day_count must be >= 1, got {self.day_count}")


@dataclass
class Era:
    name: str
    display_start: int   # display year number at the start of this era (>= 1)
    absolute_start: int  # absolute calendar year where this era begins (>= 1)
    absolute_end: int    # absolute calendar year where this era ends (>= absolute_start)
    direction: EraDirection

    def __post_init__(self):
        if self.display_start < 1:
            raise ValueError(f"display_start must be >= 1, got {self.display_start}")
        if self.absolute_start < 1:
            raise ValueError(f"absolute_start must be >= 1, got {self.absolute_start}")
        if self.absolute_end < self.absolute_start:
            raise ValueError(
                f"Era '{self.name}': absolute_end ({self.absolute_end}) must be >= absolute_start ({self.absolute_start})"
            )

    def contains_year(self, year: int) -> bool:
        """Return True if the given absolute calendar year falls within this era."""
        return self.absolute_start <= year <= self.absolute_end

    def display_year(self, year: int) -> int:
        """Convert an absolute calendar year to the era-relative display year."""
        offset = year - self.absolute_start  # 0-based offset from era start
        if self.direction == EraDirection.ASCENDING:
            return self.display_start + offset
        else:
            return self.display_start - offset


@dataclass
class CalendarDefinition:
    name: str
    months: list[MonthDefinition]
    week_length: int
    weekday_names: list[str]
    hours_per_day: int
    lunar_cycles: list[LunarCycle] = field(default_factory=list)
    intercalary_periods: list[IntercalaryPeriod] = field(default_factory=list)
    eras: list[Era] = field(default_factory=list)
    week_start_offset: int = 0  # shifts day_of_week so epoch day 1 maps to the correct weekday
    default_start_date: dict | None = None  # optional {year, month, day, hour, minute, second}

    def __post_init__(self):
        if not (1 <= len(self.months) <= 30):
            raise ValueError(f"months count must be between 1 and 30, got {len(self.months)}")
        if not (1 <= self.week_length <= 20):
            raise ValueError(f"week_length must be between 1 and 20, got {self.week_length}")
        if len(self.weekday_names) != self.week_length:
            raise ValueError(f"weekday_names length must equal week_length ({self.week_length}), got {len(self.weekday_names)}")
        if not (1 <= self.hours_per_day <= 99):
            raise ValueError(f"hours_per_day must be between 1 and 99, got {self.hours_per_day}")


GREGORIAN_DEFAULT = CalendarDefinition(
    name="Gregorian",
    months=[
        MonthDefinition("January", 31), MonthDefinition("February", 28, leap_every_n_years=4),
        MonthDefinition("March", 31),   MonthDefinition("April", 30),
        MonthDefinition("May", 31),     MonthDefinition("June", 30),
        MonthDefinition("July", 31),    MonthDefinition("August", 31),
        MonthDefinition("September", 30), MonthDefinition("October", 31),
        MonthDefinition("November", 30), MonthDefinition("December", 31),
    ],
    week_length=7,
    weekday_names=["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
    hours_per_day=24,
    week_start_offset=6,  # Jan 1 AD 1 was a Saturday; aligns day_of_week with real Gregorian dates
    eras=[
        Era("BC", display_start=4000, absolute_start=1, absolute_end=4000, direction=EraDirection.DESCENDING),
        Era("AD", display_start=1, absolute_start=4001, absolute_end=9999, direction=EraDirection.ASCENDING),
    ],
    default_start_date={"year": 6026, "month": 1, "day": 1, "hour": 0, "minute": 0, "second": 0},
)


PHASE_NAMES = [
    "New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
    "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent",
]


@dataclass
class FantasyDateTime:
    calendar: CalendarDefinition
    year: int
    month: int  # 1-based regular month; for intercalary: the month after which the period falls (after_month + 1)
    day: int    # 1-based day within the month or intercalary period
    hour: int
    minute: int
    second: int
    era: Era | None = None
    intercalary_period_index: int | None = None  # index into calendar.intercalary_periods when on an intercalary day

    def __post_init__(self):
        max_hour = self.calendar.hours_per_day - 1
        if not (0 <= self.hour <= max_hour):
            raise ValueError(f"hour must be between 0 and {max_hour}, got {self.hour}")
        if self.intercalary_period_index is not None:
            ip = self.calendar.intercalary_periods[self.intercalary_period_index]
            if not (1 <= self.day <= ip.day_count):
                raise ValueError(f"day must be between 1 and {ip.day_count}, got {self.day}")
        else:
            num_months = len(self.calendar.months)
            if not (1 <= self.month <= num_months):
                raise ValueError(f"month must be between 1 and {num_months}, got {self.month}")
            max_day = self.calendar.months[self.month - 1].effective_day_count(self.year)
            if not (1 <= self.day <= max_day):
                raise ValueError(f"day must be between 1 and {max_day}, got {self.day}")

    @property
    def is_intercalary(self) -> bool:
        return self.intercalary_period_index is not None

    def total_elapsed_days(self) -> int:
        cal = self.calendar

        def intercalary_days_after(month_index: int) -> int:
            return sum(
                ip.day_count for ip in cal.intercalary_periods
                if ip.after_month == month_index
            )

        total = 0
        # Complete years before self.year
        for yr in range(1, self.year):
            for mi, m in enumerate(cal.months):
                total += m.effective_day_count(yr) + intercalary_days_after(mi)

        if self.intercalary_period_index is not None:
            ip = cal.intercalary_periods[self.intercalary_period_index]
            # All months up to and including after_month, plus their intercalary days
            for mi in range(ip.after_month + 1):
                total += cal.months[mi].effective_day_count(self.year)
                # Add intercalary days after this month, but stop before our own period
                for other_ip in cal.intercalary_periods:
                    if other_ip.after_month == mi and other_ip is not ip:
                        total += other_ip.day_count
            # Days into this intercalary period
            total += self.day
        else:
            # Complete months before self.month in self.year
            for mi in range(self.month - 1):
                total += cal.months[mi].effective_day_count(self.year) + intercalary_days_after(mi)
            total += self.day

        return total

    def day_of_week(self) -> int:
        return (self.total_elapsed_days() + self.calendar.week_start_offset) % self.calendar.week_length

    def add_seconds(self, delta: int) -> "FantasyDateTime":
        cal = self.calendar

        def intercalary_days_after(month_index: int) -> int:
            return sum(
                ip.day_count for ip in cal.intercalary_periods
                if ip.after_month == month_index
            )

        # Carry seconds → minutes → hours → days
        total_seconds = self.second + delta
        seconds_per_minute = 60
        minutes_per_hour = 60
        total_minutes, second = divmod(total_seconds, seconds_per_minute)
        total_hours, minute = divmod(self.minute + total_minutes, minutes_per_hour)
        total_days_carry, hour = divmod(self.hour + total_hours, cal.hours_per_day)

        if total_days_carry == 0:
            return FantasyDateTime(
                calendar=cal, year=self.year, month=self.month, day=self.day,
                hour=hour, minute=minute, second=second, era=self.era,
                intercalary_period_index=self.intercalary_period_index,
            )

        # Work in "absolute day" space to avoid complex carry logic.
        # Convert current position to an absolute day number, apply carry, then decode.
        abs_day = self.total_elapsed_days() + total_days_carry

        # Decode abs_day back into (year, month, day) or intercalary position
        return _abs_day_to_fdt(cal, abs_day, hour, minute, second, self.era)

    def lunar_phase(self, cycle: LunarCycle) -> str:
        return PHASE_NAMES[(self.total_elapsed_days() + cycle.phase_offset) // cycle.phase_interval % 8]


def _abs_day_to_fdt(
    cal: CalendarDefinition,
    abs_day: int,
    hour: int,
    minute: int,
    second: int,
    era: "Era | None",
) -> "FantasyDateTime":
    """Convert an absolute day number (1-based) back to a FantasyDateTime."""

    def intercalary_days_after(month_index: int) -> int:
        return sum(
            ip.day_count for ip in cal.intercalary_periods
            if ip.after_month == month_index
        )

    def days_in_year(yr: int) -> int:
        total = 0
        for mi, m in enumerate(cal.months):
            total += m.effective_day_count(yr) + intercalary_days_after(mi)
        return total

    # Find the year
    year = 1
    while abs_day > days_in_year(year):
        abs_day -= days_in_year(year)
        year += 1

    # Walk through months (and intercalary periods) within the year
    for mi, month_def in enumerate(cal.months):
        month_days = month_def.effective_day_count(year)
        if abs_day <= month_days:
            return FantasyDateTime(
                calendar=cal, year=year, month=mi + 1, day=abs_day,
                hour=hour, minute=minute, second=second, era=era,
            )
        abs_day -= month_days

        # Check intercalary periods after this month
        for ip_idx, ip in enumerate(cal.intercalary_periods):
            if ip.after_month == mi:
                if abs_day <= ip.day_count:
                    return FantasyDateTime(
                        calendar=cal, year=year, month=mi + 1, day=abs_day,
                        hour=hour, minute=minute, second=second, era=era,
                        intercalary_period_index=ip_idx,
                    )
                abs_day -= ip.day_count

    # Fallback — shouldn't happen with valid input
    raise ValueError(f"Could not decode absolute day {abs_day} for calendar {cal.name}")


@dataclass
class Project:
    name: str
    version: str = "1.0"
    calendar_definition: CalendarDefinition = field(default_factory=lambda: GREGORIAN_DEFAULT)
    tracked_date: FantasyDateTime | None = None
    calendar_days: list[CalendarDay] = field(default_factory=list)
    calendar_source: str = ""
    round_tracker_state: RoundTrackerState = field(default_factory=RoundTrackerState)
