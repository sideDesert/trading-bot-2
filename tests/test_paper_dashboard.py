import json
import re
import unittest
from datetime import datetime

from trading_bot.features import IST
from trading_bot.paper import PaperTrade
from trading_bot.paper_dashboard import render_dashboard

NOW = datetime(2026, 9, 25, 16, 0, tzinfo=IST)


def trade(decision_id, status="CLOSED", net=1000.0, **kw):
    stamp = "2026-09-25T10:05:00+05:30"
    values = dict(
        decision_id=decision_id, created_at=stamp, decided_at=stamp, status=status,
        action="LONG_CALL", instrument_key="NSE_FO|1", strike=23050.0, limit_entry=150.0,
        stop_price=130.0, target_price=190.0, lot_size=65, lots=7, entry_fill=150.0,
        exit_fill=160.0, exit_reason="TARGET_HIT", exit_at=stamp, gross_pnl=net + 100.0,
        charges=100.0, net_pnl=net,
    )
    values.update(kw)
    return PaperTrade(**values)


def embedded(page):
    return json.loads(re.search(r"const DATA = (.*);\n", page).group(1).replace("<\\/", "</"))


class DashboardTests(unittest.TestCase):
    def test_embeds_trades_with_quantity(self):
        page = render_dashboard([trade("a"), trade("b", net=-500.0)], NOW)
        data = embedded(page)
        self.assertEqual([t["decision_id"] for t in data["trades"]], ["a", "b"])
        self.assertEqual(data["trades"][0]["quantity"], 455)
        self.assertEqual(data["generated"], "25 Sep 2026, 16:00 IST")
        self.assertNotIn("__DATA__", page)
        self.assertNotIn("__BANNER__", page)

    def test_script_breakout_in_notes_is_escaped(self):
        page = render_dashboard([trade("a", notes="</script><script>alert(1)</script>")], NOW)
        self.assertEqual(page.count("</script>"), 1)
        self.assertEqual(embedded(page)["trades"][0]["notes"], "</script><script>alert(1)</script>")

    def test_banner_is_html_escaped(self):
        page = render_dashboard([], NOW, banner="<b>Sample</b>")
        self.assertIn('<div class="banner">&lt;b&gt;Sample&lt;/b&gt;</div>', page)

    def test_no_external_resources(self):
        page = render_dashboard([trade("a")], NOW)
        self.assertNotRegex(page, r'(src|href)="https?://')


if __name__ == "__main__":
    unittest.main()
