"""History chips keep the stored first line as literal text."""

import unittest

from quenya_speak.tui import ChipButton


class ChipButtonTests(unittest.TestCase):
    def test_bracketed_labels_stay_literal(self):
        elen = ChipButton("[elen] síla", "[elen] síla")
        cirya = ChipButton("cirya[/]", "cirya[/]")
        self.assertEqual(elen.label.plain, "[elen] síla")
        self.assertEqual(cirya.label.plain, "cirya[/]")
