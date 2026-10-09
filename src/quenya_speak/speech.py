"""Voice directory, one WAV, and playback.

Piper is imported by ``synthesize``, not when this module is imported.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

from quenya_speak.history import remember
from quenya_speak.utterance import text_utterances

_VOICE = "en_GB-cori-high"
_LENGTH_SCALE = 1.15
_GAP_SECONDS = 0.3

_playback: subprocess.Popen[bytes] | None = None
_cancel = False


def voices_dir() -> Path:
    """``PIPER_VOICES_DIR`` when set and not blank, otherwise ~/.piper-voices."""
    configured = os.environ.get("PIPER_VOICES_DIR", "")
    if configured.strip():
        return Path(configured.strip())
    return Path.home() / ".piper-voices"


def player() -> str | None:
    """First match on PATH: ``afplay`` on macOS, then ``ffplay``, then ``aplay``."""
    if sys.platform == "darwin" and shutil.which("afplay"):
        return "afplay"
    if shutil.which("ffplay"):
        return "ffplay"
    if shutil.which("aplay"):
        return "aplay"
    return None


def concat_wavs(paths: list[Path], out: Path) -> Path:
    """Join clips with 300 ms of silence between them and not after the last."""
    if not paths:
        raise ValueError("no audio to join")
    layouts = []
    payloads = []
    for path in paths:
        with wave.open(str(path), "rb") as wav:
            layouts.append((wav.getframerate(), wav.getsampwidth(), wav.getnchannels()))
            payloads.append(wav.readframes(wav.getnframes()))
    rate, sampwidth, channels = layouts[0]
    for layout in layouts[1:]:
        if layout != (rate, sampwidth, channels):
            raise ValueError("voice returned mismatched audio")
    gap_frames = int(rate * _GAP_SECONDS)
    gap = b"\x00" * (gap_frames * sampwidth * channels)
    pieces: list[bytes] = []
    for index, payload in enumerate(payloads):
        if index:
            pieces.append(gap)
        pieces.append(payload)
    return _replace_wav(out, rate, sampwidth, channels, b"".join(pieces))


def _replace_wav(out: Path, rate: int, sampwidth: int, channels: int, payload: bytes) -> Path:
    """Write a complete wave beside ``out``, then replace it."""
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".speech-",
        suffix=".wav",
        dir=out.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with wave.open(str(temporary), "wb") as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(sampwidth)
            wav.setframerate(rate)
            wav.writeframes(payload)
        os.replace(temporary, out)
    except BaseException:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return out


def synthesize(utterances: list[str], out: Path) -> Path:
    """Synthesize each utterance and concatenate the clips into ``out``."""
    try:
        from piper import PiperVoice, SynthesisConfig
    except ImportError:
        raise ValueError(
            "piper-tts is not installed in the active virtual environment"
        ) from None
    model = _ensure_voice(voices_dir())
    voice = PiperVoice.load(model)
    phonemes = voice.config.phoneme_id_map
    for utterance in utterances:
        _require_phonemes(utterance, phonemes)
    config = SynthesisConfig(length_scale=_LENGTH_SCALE)
    clips: list[Path] = []
    try:
        for utterance in utterances:
            clips.append(_clip(voice, config, utterance, out.parent))
        return concat_wavs(clips, out)
    finally:
        for clip in clips:
            clip.unlink(missing_ok=True)


def _ensure_voice(directory: Path) -> Path:
    model = directory / f"{_VOICE}.onnx"
    config = directory / f"{_VOICE}.onnx.json"
    if _nonempty(model) and _nonempty(config):
        return model
    directory.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "piper.download_voices",
        _VOICE,
        "--data-dir",
        str(directory),
    ]
    result = subprocess.run(command)
    if result.returncode != 0 or not _nonempty(model) or not _nonempty(config):
        raise ValueError("voice download failed: " + " ".join(command))
    return model


def _nonempty(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def _require_phonemes(utterance: str, phonemes) -> None:
    if utterance.startswith("[[") and utterance.endswith("]]"):
        body = utterance[2:-2]
    else:
        body = utterance
    for character in body:
        if character not in phonemes:
            raise ValueError(f"voice phoneme map is missing {character!r} in {utterance}")


def _clip(voice, config, utterance: str, directory: Path) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".clip-",
        suffix=".wav",
        dir=directory,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with wave.open(str(temporary), "wb") as wav:
            voice.synthesize_wav(utterance, wav, syn_config=config)
    except BaseException:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return temporary


def _terminate(process: subprocess.Popen[bytes]) -> None:
    """Stop ``process`` if it is still running. Does not wait."""
    if process.poll() is not None:
        return
    try:
        process.terminate()
    except OSError:
        return


def play(path: Path) -> str:
    """Play ``path``. Returns ``played``, ``no_player``, or ``failed``."""
    global _playback
    if _cancel:
        return "failed"
    program = player()
    if program is None:
        return "no_player"
    command = [program]
    if program == "ffplay":
        command.extend(["-nodisp", "-autoexit", "-loglevel", "error"])
    command.append(str(path))
    process = subprocess.Popen(command)
    _playback = process
    # stop() can land after the pre-Popen check and before this assignment.
    if _cancel:
        _terminate(process)
        return "failed"
    if process.wait() == 0:
        return "played"
    return "failed"


def stop() -> None:
    """Latch cancel and terminate a player that is already running."""
    global _cancel
    _cancel = True
    process = _playback
    if process is None:
        return
    _terminate(process)


def speak(text: str, out: Path) -> str:
    """Synthesize ``text``, remember it, and play the WAV."""
    global _cancel
    _cancel = False
    utterances = text_utterances(text)
    synthesize(utterances, out)
    try:
        remember(text)
    except Exception:
        print("history was not saved", file=sys.stderr)
    return play(out)
