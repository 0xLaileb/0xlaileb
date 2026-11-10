"""python -m unittest discover -s tools -p "test_*.py" """

import hashlib
import unittest
import xml.dom.minidom

import play
import profile_svg as p


class Games(unittest.TestCase):
    def test_poke_titles(self):
        self.assertEqual(p.parse_poke("poke 3F E0"), (0x3F, 0xE0))
        self.assertEqual(p.parse_poke("  POKE 0x0 0xff "), (0, 255))
        for bad in ("poke 100 00", "poke 3F", "poke 3F E0; rm -rf /", "poke 3F E0\npoke 00 01", "poke zz 00", "peek 3F E0"):
            self.assertIsNone(p.parse_poke(bad), bad)

    def test_proof_is_bound_to_login(self):
        good = p.proof("Visitor")
        self.assertEqual(good, hashlib.sha256(f"{p.flag()}:visitor".encode()).hexdigest())
        self.assertEqual(play.decide(f"crackme {good.upper()}", "visitor")[:2], ("solved", True))
        self.assertEqual(play.decide(f"crackme {good}", "someone-else")[:2], ("invalid", False))
        self.assertEqual(play.decide(f"crackme {good}", "visitor", already_solved=True)[:2], ("duplicate", False))

    def test_flag_shape(self):
        self.assertEqual(len(p.flag()), 16)
        self.assertTrue(all(len(row) == 16 for row in p.ROWS))

    def test_decisions(self):
        self.assertEqual(play.decide("poke 3F E0", "v")[:2], ("poke", True))
        self.assertEqual(play.decide("poke 3F E0", "v", pokes_today=play.DAILY_POKES)[:2], ("rate-limited", False))
        self.assertEqual(play.decide("poke `id` $(id)", "v")[:2], ("invalid", False))


class Cards(unittest.TestCase):
    def test_every_card_is_well_formed(self):
        data = p.demo()
        empty = {**data, "repos": [], "fame": [], "last": None, "memory": bytes(256), "pokes": 0, "painters": 0}
        hostile = {**data, "fame": [{"login": '<a"&>', "date": "2026-01-01"}],
                   "repos": [{**data["repos"][0], "name": '</text><script>&"'}]}
        for colors in p.THEMES.values():
            xml.dom.minidom.parseString(p.render_header(colors))
            for sample in (data, empty, hostile):
                for render in (p.render_stats, p.render_activity, p.render_memory, p.render_fame):
                    doc = render(colors, sample)
                    xml.dom.minidom.parseString(doc)
                    self.assertNotIn("<script", doc)

    def test_export_has_no_plaintext_flag(self):
        self.assertNotIn(p.flag(), str(p.export(p.demo(), "u", "u/u")))


if __name__ == "__main__":
    unittest.main()