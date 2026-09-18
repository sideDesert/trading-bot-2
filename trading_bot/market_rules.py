from dataclasses import dataclass, field
from datetime import date, time
from typing import Mapping

NSE_HOLIDAYS_2026 = frozenset(
    {
        date(2026, 1, 15),
        date(2026, 1, 26),
        date(2026, 3, 3),
        date(2026, 3, 26),
        date(2026, 3, 31),
        date(2026, 4, 3),
        date(2026, 4, 14),
        date(2026, 5, 1),
        date(2026, 5, 28),
        date(2026, 6, 26),
        date(2026, 9, 14),
        date(2026, 10, 2),
        date(2026, 10, 20),
        date(2026, 11, 10),
        date(2026, 11, 24),
        date(2026, 12, 25),
    }
)

NSE_SPECIAL_SESSIONS_2026 = {
    date(2026, 2, 1): (time(9, 15), time(15, 0)),
}

_NORMAL_SESSION = (time(9, 15), time(15, 40))


@dataclass(frozen=True)
class TradingCalendar:
    holidays: frozenset = NSE_HOLIDAYS_2026
    special_sessions: Mapping = field(
        default_factory=lambda: dict(NSE_SPECIAL_SESSIONS_2026)
    )
    supported_years: frozenset = frozenset({2026})

    def session_bounds(self, day: date) -> "tuple[time, time] | None":
        if day in self.special_sessions:
            return self.special_sessions[day]
        if day.year not in self.supported_years:
            return None
        if day.weekday() >= 5:
            return None
        if day in self.holidays:
            return None
        return _NORMAL_SESSION
