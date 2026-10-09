"""Spoken-text history under a temporary home directory."""

import os
import tempfile
import unittest
from pathlib import Path

from quenya_speak.history import chips, load, remember


def _history_path() -> Path:
    return Path.home() / ".quenya-speak" / "history.jsonl"


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self._old_home = os.environ.get("HOME")
        self._temporary = tempfile.TemporaryDirectory()
        os.environ["HOME"] = self._temporary.name

    def tearDown(self):
        if self._old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self._old_home
        self._temporary.cleanup()

    def test_missing_history_is_empty(self):
        self.assertEqual(load(), [])

    def test_remember_appends_in_order(self):
        self.assertEqual(remember("elen"), ["elen"])
        self.assertEqual(remember("síla"), ["elen", "síla"])
        self.assertEqual(load(), ["elen", "síla"])

    def test_remember_moves_an_equal_text_to_the_end(self):
        remember("elen")
        remember("síla")
        self.assertEqual(remember("elen"), ["síla", "elen"])
        self.assertEqual(load(), ["síla", "elen"])

    def test_remember_keeps_the_last_fifty(self):
        texts = [f"text-{index}" for index in range(51)]
        for text in texts:
            remember(text)
        loaded = load()
        self.assertEqual(len(loaded), 50)
        self.assertEqual(loaded, texts[1:])
        self.assertNotIn(texts[0], loaded)

    def test_chips_are_the_last_twelve_newest_first(self):
        texts = [f"text-{index}" for index in range(13)]
        pairs = chips(texts)
        self.assertEqual(len(pairs), 12)
        self.assertEqual(pairs, [(text, text) for text in reversed(texts[-12:])])

    def test_long_first_line_is_cut_to_forty_characters(self):
        text = "a" * 41
        label, full = chips([text])[0]
        self.assertEqual(label, ("a" * 40) + "\u2026")
        self.assertEqual(full, text)
        exact = "b" * 40
        self.assertEqual(chips([exact]), [(exact, exact)])

    def test_chip_label_is_the_first_line(self):
        text = "elen síla\nlúmenn'"
        self.assertEqual(chips([text]), [("elen síla", text)])

    def test_chip_label_strips_the_first_line(self):
        text = "  elen síla  \nlúmenn'"
        self.assertEqual(chips([text]), [("elen síla", text)])

    def test_damaged_lines_are_skipped(self):
        path = _history_path()
        path.parent.mkdir(parents=True)
        path.write_text(
            '{"text": "elen"}\n'
            "not json\n"
            '{"text": 1}\n',
            encoding="utf-8",
        )
        self.assertEqual(load(), ["elen"])
        path.write_text(
            '{"text": "elen"}\n'
            "not json\n"
            '{"text": 1}\n'
            '{"text": "síla"}\n',
            encoding="utf-8",
        )
        self.assertEqual(load(), ["elen", "síla"])

    def test_unreadable_history_is_empty(self):
        path = _history_path()
        path.parent.mkdir(parents=True)
        path.mkdir()
        self.assertEqual(load(), [])

    def test_history_file_keeps_non_ascii_characters(self):
        remember("andúnë")
        contents = _history_path().read_text(encoding="utf-8")
        self.assertIn("andúnë", contents)
        self.assertNotIn("\\u", contents)


if __name__ == "__main__":
    unittest.main()
