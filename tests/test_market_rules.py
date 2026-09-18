import unittest
from datetime import date, time

from trading_bot.market_rules import (
    NSE_HOLIDAYS_2026,
    NSE_SPECIAL_SESSIONS_2026,
    TradingCalendar,
)


class TradingCalendarTests(unittest.TestCase):
    def setUp(self):
        self.cal = TradingCalendar()

    def test_normal_weekday(self):
        self.assertEqual(
            self.cal.session_bounds(date(2026, 9, 22)),
            (time(9, 15), time(15, 40)),
        )

    def test_weekend_none(self):
        self.assertIsNone(self.cal.session_bounds(date(2026, 9, 20)))
        self.assertIsNone(self.cal.session_bounds(date(2026, 9, 19)))

    def test_holidays(self):
        for day in sorted(NSE_HOLIDAYS_2026):
            self.assertIsNone(self.cal.session_bounds(day))
        self.assertEqual(len(NSE_HOLIDAYS_2026), 16)

    def test_unsupported_year(self):
        self.assertIsNone(self.cal.session_bounds(date(2025, 9, 22)))
        self.assertIsNone(self.cal.session_bounds(date(2027, 1, 5)))

    def test_special_session_wins(self):
        special = date(2026, 2, 1)
        self.assertEqual(special.weekday(), 6)
        self.assertEqual(
            self.cal.session_bounds(special), (time(9, 15), time(15, 0))
        )
        self.assertEqual(
            NSE_SPECIAL_SESSIONS_2026[special], (time(9, 15), time(15, 0))
        )


if __name__ == "__main__":
    unittest.main()
