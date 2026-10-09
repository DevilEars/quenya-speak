"""The one-shot quenya-say command."""

import io
import os
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from quenya_speak.cli import main


@contextmanager
def _working_directory(path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class CliTests(unittest.TestCase):
    def _run(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_text_and_file_together_are_rejected(self):
        with (
            mock.patch("quenya_speak.cli.speak") as speak,
            mock.patch("quenya_speak.cli.open_stage"),
        ):
            code, _stdout, stderr = self._run(["--file", "a.txt", "elen"])
        self.assertEqual(code, 2)
        self.assertIn("pass text or --file, not both", stderr)
        speak.assert_not_called()

    def test_missing_file_names_the_path(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.txt"
            with (
                mock.patch("quenya_speak.cli.speak") as speak,
                mock.patch("quenya_speak.cli.open_stage"),
            ):
                code, _stdout, stderr = self._run(["--file", str(missing)])
        self.assertEqual(code, 1)
        self.assertIn(str(missing), stderr)
        speak.assert_not_called()

    def test_file_that_is_not_utf8_names_the_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.txt"
            path.write_bytes(b"\xff")
            with (
                mock.patch("quenya_speak.cli.speak") as speak,
                mock.patch("quenya_speak.cli.open_stage"),
            ):
                code, _stdout, stderr = self._run(["--file", str(path)])
        self.assertEqual(code, 1)
        self.assertIn(str(path), stderr)
        speak.assert_not_called()

    def test_missing_output_parent_names_the_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            missing_dir = Path(directory) / "missing"
            with (
                mock.patch("quenya_speak.cli.speak") as speak,
                mock.patch("quenya_speak.cli.open_stage"),
            ):
                code, _stdout, stderr = self._run(
                    ["--out", str(missing_dir / "a.wav"), "cirya"]
                )
        self.assertEqual(code, 1)
        self.assertIn(str(missing_dir), stderr)
        speak.assert_not_called()

    def test_unrecognised_letter_writes_no_wav(self):
        # Pronunciation fails inside speak. Do not patch it.
        with tempfile.TemporaryDirectory() as directory:
            with (
                _working_directory(directory),
                mock.patch("quenya_speak.cli.open_stage"),
            ):
                code, _stdout, stderr = self._run(["anza"])
            self.assertEqual(list(Path(directory).iterdir()), [])
        self.assertEqual(code, 1)
        self.assertIn("unrecognised letter", stderr)
        self.assertIn("anza", stderr)

    def test_empty_text_has_nothing_to_speak(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                _working_directory(directory),
                mock.patch("quenya_speak.cli.open_stage"),
            ):
                code, _stdout, stderr = self._run([""])
            self.assertEqual(list(Path(directory).iterdir()), [])
        self.assertEqual(code, 1)
        self.assertIn("nothing to speak", stderr)

    def test_no_text_opens_stage(self):
        expected = Path.cwd() / "quenya.wav"
        with (
            mock.patch("quenya_speak.cli.speak") as speak,
            mock.patch("quenya_speak.cli.open_stage") as open_stage,
        ):
            code, _stdout, _stderr = self._run([])
        self.assertEqual(code, 0)
        open_stage.assert_called_once_with(expected)
        speak.assert_not_called()

    def test_played_is_silent_success(self):
        expected = Path.cwd() / "quenya.wav"
        with (
            mock.patch("quenya_speak.cli.speak", return_value="played") as speak,
            mock.patch("quenya_speak.cli.open_stage"),
        ):
            code, stdout, _stderr = self._run(["cirya"])
        self.assertEqual(code, 0)
        self.assertEqual(stdout, "")
        speak.assert_called_once_with("cirya", expected)

    def test_no_player_reports_the_path(self):
        expected = Path.cwd() / "quenya.wav"
        with (
            mock.patch("quenya_speak.cli.speak", return_value="no_player") as speak,
            mock.patch("quenya_speak.cli.open_stage"),
        ):
            code, stdout, _stderr = self._run(["cirya"])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.strip(), f"wrote {expected}")
        speak.assert_called_once_with("cirya", expected)

    def test_failed_playback_names_the_player(self):
        with (
            mock.patch("quenya_speak.cli.speak", return_value="failed"),
            mock.patch("quenya_speak.cli.player", return_value="afplay"),
            mock.patch("quenya_speak.cli.open_stage"),
        ):
            code, _stdout, stderr = self._run(["cirya"])
        self.assertEqual(code, 1)
        self.assertEqual(stderr.strip(), "afplay playback failed")

    def test_keyboard_interrupt_returns_130(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "kept.wav"
            out.write_bytes(b"keep")
            with (
                mock.patch("quenya_speak.cli.speak", side_effect=KeyboardInterrupt),
                mock.patch("quenya_speak.cli.open_stage"),
            ):
                code, _stdout, _stderr = self._run(["--out", str(out), "cirya"])
            self.assertEqual(code, 130)
            self.assertEqual(out.read_bytes(), b"keep")

    def test_failed_playback_keeps_an_existing_wav(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "kept.wav"
            out.write_bytes(b"keep")
            with (
                mock.patch("quenya_speak.cli.speak", return_value="failed"),
                mock.patch("quenya_speak.cli.player", return_value="afplay"),
                mock.patch("quenya_speak.cli.open_stage"),
            ):
                code, _stdout, stderr = self._run(["--out", str(out), "cirya"])
            self.assertEqual(code, 1)
            self.assertEqual(stderr.strip(), "afplay playback failed")
            self.assertEqual(out.read_bytes(), b"keep")

    def test_positional_words_are_joined(self):
        expected = Path.cwd() / "quenya.wav"
        with (
            mock.patch("quenya_speak.cli.speak", return_value="played") as speak,
            mock.patch("quenya_speak.cli.open_stage"),
        ):
            code, stdout, _stderr = self._run(["elen", "síla"])
        self.assertEqual(code, 0)
        self.assertEqual(stdout, "")
        speak.assert_called_once_with("elen síla", expected)

    def test_file_text_is_spoken(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "phrase.txt"
            source.write_text("elen síla", encoding="utf-8")
            out = root / "line.wav"
            with (
                mock.patch("quenya_speak.cli.speak", return_value="played") as speak,
                mock.patch("quenya_speak.cli.open_stage"),
            ):
                code, stdout, _stderr = self._run(
                    ["--out", str(out), "--file", str(source)]
                )
        self.assertEqual(code, 0)
        self.assertEqual(stdout, "")
        speak.assert_called_once_with("elen síla", out)

    def test_none_argv_reads_sys_argv(self):
        expected = Path.cwd() / "quenya.wav"
        with (
            mock.patch("quenya_speak.cli.speak", return_value="played") as speak,
            mock.patch("quenya_speak.cli.open_stage"),
            mock.patch("sys.argv", ["quenya-say", "cirya", "né"]),
        ):
            code, _stdout, _stderr = self._run(None)
        self.assertEqual(code, 0)
        speak.assert_called_once_with("cirya né", expected)


if __name__ == "__main__":
    unittest.main()
