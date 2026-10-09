"""Voice directory, WAV joining, synthesis, and playback."""

import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
import wave
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

import quenya_speak.speech as speech
from quenya_speak.speech import concat_wavs, play, speak, stop, synthesize, voices_dir
from quenya_speak.utterance import text_utterances, word_utterance


def _piper_imports() -> bool:
    try:
        import piper  # noqa: F401
    except ImportError:
        return False
    return True


def _voice_ready() -> bool:
    directory = voices_dir()
    model = directory / "en_GB-cori-high.onnx"
    config = directory / "en_GB-cori-high.onnx.json"
    return (
        model.is_file()
        and model.stat().st_size > 0
        and config.is_file()
        and config.stat().st_size > 0
    )


def _reject_voice_download(real_run):
    def run(*args, **kwargs):
        command = args[0] if args else kwargs.get("args", [])
        if isinstance(command, (list, tuple)) and "piper.download_voices" in command:
            raise AssertionError("voice download was attempted")
        return real_run(*args, **kwargs)

    return run


def _write_wav(path: Path, frames: bytes, rate: int = 16000) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(frames)


class SpeechTests(unittest.TestCase):
    def setUp(self):
        self._saved_env = {
            "HOME": os.environ.get("HOME"),
            "PIPER_VOICES_DIR": os.environ.get("PIPER_VOICES_DIR"),
            "PATH": os.environ.get("PATH"),
        }
        self._reset_playback()

    def tearDown(self):
        self._reset_playback()
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _reset_playback(self):
        speech._playback = None
        if hasattr(speech, "_cancel"):
            speech._cancel = False

    def test_voices_dir_uses_home_when_unset(self):
        os.environ.pop("PIPER_VOICES_DIR", None)
        with tempfile.TemporaryDirectory() as home:
            os.environ["HOME"] = home
            self.assertEqual(voices_dir(), Path(home) / ".piper-voices")

    def test_blank_voices_dir_uses_home(self):
        with tempfile.TemporaryDirectory() as home:
            os.environ["HOME"] = home
            os.environ["PIPER_VOICES_DIR"] = "   "
            self.assertEqual(voices_dir(), Path(home) / ".piper-voices")

    def test_voices_dir_uses_a_set_path(self):
        with tempfile.TemporaryDirectory() as directory:
            os.environ["PIPER_VOICES_DIR"] = directory
            self.assertEqual(voices_dir(), Path(directory))

    def test_concat_inserts_silence_only_between_clips(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.wav"
            second = root / "second.wav"
            out = root / "out.wav"
            first_frames = b"\x01\x00" * 100
            second_frames = b"\x02\x00" * 100
            _write_wav(first, first_frames)
            _write_wav(second, second_frames)
            concat_wavs([first, second], out)
            with wave.open(str(out), "rb") as wav:
                self.assertEqual(wav.getnframes(), 100 + 100 + int(16000 * 0.3))
                payload = wav.readframes(wav.getnframes())
            gap_frames = int(16000 * 0.3)
            gap = payload[200:200 + gap_frames * 2]
            self.assertEqual(gap, b"\x00" * (gap_frames * 2))
            self.assertEqual(payload[:200], first_frames)
            self.assertEqual(payload[200 + gap_frames * 2:], second_frames)

    def test_concat_rejects_a_mismatched_sample_rate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.wav"
            second = root / "second.wav"
            out = root / "out.wav"
            _write_wav(first, b"\x01\x00" * 100, rate=16000)
            _write_wav(second, b"\x01\x00" * 100, rate=8000)
            with self.assertRaises(ValueError) as caught:
                concat_wavs([first, second], out)
            self.assertEqual(str(caught.exception), "voice returned mismatched audio")
            self.assertFalse(out.exists())

    def test_play_without_a_player_returns_no_player(self):
        with tempfile.TemporaryDirectory() as directory:
            os.environ["PATH"] = directory
            self.assertEqual(play(Path("missing.wav")), "no_player")

    def test_failed_player_keeps_the_wav(self):
        name = "afplay" if sys.platform == "darwin" else "ffplay"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            program = bin_dir / name
            program.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            program.chmod(0o755)
            wav = root / "clip.wav"
            _write_wav(wav, b"\x00\x00" * 8)
            os.environ["PATH"] = str(bin_dir)
            self.assertEqual(play(wav), "failed")
            self.assertTrue(wav.is_file())

    def test_missing_piper_names_the_active_environment(self):
        if _piper_imports():
            self.skipTest("piper-tts is installed")
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "out.wav"
            with self.assertRaises(ValueError) as caught:
                synthesize([word_utterance("cirya")], out)
            self.assertEqual(
                str(caught.exception),
                "piper-tts is not installed in the active virtual environment",
            )
            self.assertFalse(out.exists())

    def test_voice_download_failure_names_the_command(self):
        if not _piper_imports():
            self.skipTest("piper-tts is not installed")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            voices = root / "voices"
            voices.mkdir()
            out = root / "out.wav"
            os.environ["PIPER_VOICES_DIR"] = str(voices)
            completed = subprocess.CompletedProcess(args=[], returncode=1)
            with mock.patch(
                "quenya_speak.speech.subprocess.run",
                return_value=completed,
            ) as run:
                with self.assertRaises(ValueError) as caught:
                    synthesize([word_utterance("cirya")], out)
            message = str(caught.exception)
            self.assertIn("-m", message)
            self.assertIn("piper.download_voices", message)
            self.assertIn("en_GB-cori-high", message)
            self.assertIn("--data-dir", message)
            self.assertFalse(out.exists())
            command = run.call_args.args[0]
            self.assertIsInstance(command, list)
            self.assertFalse(run.call_args.kwargs.get("shell", False))

    def test_synthesize_cirya_writes_a_wav_when_the_voice_is_present(self):
        if not _piper_imports():
            self.skipTest("piper-tts is not installed")
        if not _voice_ready():
            self.skipTest("voice is not already in voices_dir")
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "cirya.wav"
            with mock.patch(
                "quenya_speak.speech.subprocess.run",
                side_effect=_reject_voice_download(subprocess.run),
            ):
                synthesize([word_utterance("cirya")], out)
            with wave.open(str(out), "rb") as wav:
                self.assertGreaterEqual(wav.getnframes(), 1)

    def test_unknown_phoneme_writes_nothing(self):
        if not _piper_imports():
            self.skipTest("piper-tts is not installed")
        if not _voice_ready():
            self.skipTest("voice is not already in voices_dir")
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "bad.wav"
            with self.assertRaises(ValueError) as caught:
                synthesize(["[[☺.]]"], out)
            message = str(caught.exception)
            self.assertIn("☺", message)
            self.assertIn("[[☺.]]", message)
            self.assertFalse(out.exists())

    def test_speak_still_plays_when_history_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "out.wav"
            order = []

            def write_wav(utterances, target):
                order.append(("synthesize", utterances))
                _write_wav(target, b"\x00\x01" * 4)
                return target

            def remember_fails(text):
                order.append(("remember", text))
                raise OSError("full")

            def play_wav(path):
                order.append(("play", path))
                return "played"

            stderr = io.StringIO()
            with (
                mock.patch("quenya_speak.speech.synthesize", side_effect=write_wav),
                mock.patch("quenya_speak.speech.remember", side_effect=remember_fails),
                mock.patch("quenya_speak.speech.play", side_effect=play_wav),
                redirect_stderr(stderr),
            ):
                result = speak("cirya", out)
            self.assertEqual(result, "played")
            self.assertTrue(out.is_file())
            self.assertIn("history was not saved", stderr.getvalue())
            self.assertEqual(
                order,
                [
                    ("synthesize", text_utterances("cirya")),
                    ("remember", "cirya"),
                    ("play", out),
                ],
            )

    def test_stop_before_play_does_not_start_a_player(self):
        with tempfile.TemporaryDirectory() as directory:
            wav = Path(directory) / "clip.wav"
            _write_wav(wav, b"\x00\x00" * 8)
            stop()
            process = mock.Mock()
            process.wait.return_value = 0
            process.poll.return_value = None
            started = time.monotonic()
            with (
                mock.patch("quenya_speak.speech.player", return_value="afplay"),
                mock.patch(
                    "quenya_speak.speech.subprocess.Popen",
                    return_value=process,
                ) as popen,
            ):
                result = play(wav)
            elapsed = time.monotonic() - started
            self.assertEqual(result, "failed")
            popen.assert_not_called()
            process.wait.assert_not_called()
            self.assertLess(elapsed, 0.5)

    def test_stop_during_popen_terminates_without_waiting(self):
        with tempfile.TemporaryDirectory() as directory:
            wav = Path(directory) / "clip.wav"
            _write_wav(wav, b"\x00\x00" * 8)
            process = mock.Mock()
            process.wait.return_value = 0
            process.poll.return_value = None

            def popen(command):
                stop()
                return process

            started = time.monotonic()
            with (
                mock.patch("quenya_speak.speech.player", return_value="afplay"),
                mock.patch(
                    "quenya_speak.speech.subprocess.Popen",
                    side_effect=popen,
                ),
            ):
                result = play(wav)
            elapsed = time.monotonic() - started
            self.assertEqual(result, "failed")
            process.terminate.assert_called_once()
            process.wait.assert_not_called()
            self.assertLess(elapsed, 0.5)

    def test_speak_clears_a_stop_from_before_it(self):
        with tempfile.TemporaryDirectory() as directory:
            os.environ["HOME"] = directory
            out = Path(directory) / "out.wav"
            stop()

            def write_wav(utterances, target):
                _write_wav(target, b"\x00\x01" * 4)
                return target

            process = mock.Mock()
            process.wait.return_value = 0
            process.poll.return_value = None
            with (
                mock.patch("quenya_speak.speech.synthesize", side_effect=write_wav),
                mock.patch("quenya_speak.speech.player", return_value="afplay"),
                mock.patch(
                    "quenya_speak.speech.subprocess.Popen",
                    return_value=process,
                ) as popen,
            ):
                result = speak("cirya", out)
            self.assertEqual(result, "played")
            popen.assert_called_once()
            process.terminate.assert_not_called()
            process.wait.assert_called_once()
            self.assertEqual(popen.call_args.args[0], ["afplay", str(out)])
            self.assertTrue(out.is_file())


if __name__ == "__main__":
    unittest.main()
