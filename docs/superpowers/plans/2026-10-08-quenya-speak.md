# Quenya Speak Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Speak Quenya from a Stage screen or a one-shot command, writing one WAV and playing it.

**Architecture:** Copy the lesson app's phonetics and Piper utterance rules into a small package. Phrase splitting, history, and WAV synthesis sit on top of those rules. The command and the Textual Stage screen both call `speak`.

**Tech Stack:** Python 3.11+, `piper-tts`, `textual`, `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-08-quenya-speak-design.md`

## Global Constraints

- Python 3.11 or newer. Package layout under `src/quenya_speak`. Install with `pip install -e .`.
- Dependencies: `piper-tts` and `textual`. Tests use `unittest`. Run them with `PYTHONPATH=src python -m unittest discover -s tests -v` from this repository.
- Voice: Piper `en_GB-cori-high`. Length scale: `1.15`. No voice flag and no length flag.
- WAV only. No ffmpeg and no AAC.
- Default output: `quenya.wav` in the current working directory. `--out` replaces it. The parent directory must already exist.
- 300 ms of silence between spoken phrases.
- History: `~/.quenya-speak/history.jsonl`. Keep 50 texts. Stage shows 12.
- Voice directory: `PIPER_VOICES_DIR` when set and non-empty after stripping whitespace, otherwise `~/.piper-voices`. Never search a parent, a sibling checkout, or another repository.
- Do not edit the lesson app. Do not create a GitHub remote or push. Do not commit a voice file, and do not write a home-directory path into the repository.
- Copyright 2026 De Villiers Neethling, CC BY-NC 4.0. `piper-tts` stays a dependency and is not vendored.
- Commit messages are full sentences, in the style of the commits already on `main`.

## Review Focus

These are the failures a person is most likely to hit that the spec's named tests do not already list. Each one has a test in the task that owns it.

- A checkout that sits next to the lesson app must not read or write that app's voice directory unless `PIPER_VOICES_DIR` points there.
- An unrecognised letter is named, and no WAV is written.
- Two spoken phrases become one WAV with 300 ms of silence between them, and no silence after the last phrase.
- Text and `--file` together exits 2 and does not speak.
- A comma, semicolon, or colon on the last word is dropped and does not become a pause.

## File structure

- `pyproject.toml` — package metadata and the `quenya-say` script.
- `src/quenya_speak/phonetics.py` — `segments`, `stress_index`.
- `src/quenya_speak/utterance.py` — Piper strings, phrase splits, subtitle text.
- `src/quenya_speak/history.py` — the JSONL history file.
- `src/quenya_speak/speech.py` — voice directory, synthesis, playback.
- `src/quenya_speak/cli.py` — `main`.
- `src/quenya_speak/tui.py` — the Stage screen.
- `tests/test_utterance.py`, `tests/test_history.py`, `tests/test_speech.py`, `tests/test_cli.py`.
- `README.md` — the two setups and the Stage keys.

---

### Task 1: Pronunciation

**Files:**
- Create: `pyproject.toml`
- Create: `src/quenya_speak/__init__.py`
- Create: `src/quenya_speak/phonetics.py`
- Create: `src/quenya_speak/utterance.py`
- Test: `tests/test_utterance.py`

**Interfaces:**
- Consumes: nothing in this repository. Copy behavior from `../Quenya/claudeslop/quenya-app/tools/quenya_phonetics.py` and `../Quenya/claudeslop/quenya-app/tools/piper_utterance.py`.
- Produces:
  - `segments(word: str) -> list`
  - `stress_index(segs: list) -> int | None`
  - `word_utterance(spelling: str) -> str`
  - `line_utterance(text: str) -> str`
  - `split_phrases(text: str) -> list[str]`
  - `text_utterances(text: str) -> list[str]`
  - `subtitle(text: str) -> str`

- [ ] **Step 1: Write the failing test**

Create `tests/test_utterance.py`. Pin the spec table through `text_utterances`, and the single-word rows through `word_utterance` as well.

```python
ROWS = {
    "cirya": "[[ˈkɪɹjɑ.]]",
    "Eärendil": "[[ɛɑˈɹɛndɪl.]]",
    "andúnë": "[[ɑnˈduːnɛ.]]",
    "ancalima": "[[ɑnˈkɑlɪmɑ.]]",
    "né": "[[ˈnɛː.]]",
    "cirya né": "[[ˈkɪɹjɑ ˈnɛː.]]",
    "cirya, né": "[[ˈkɪɹjɑ, ˈnɛː.]]",
    "cirya; né": "[[ˈkɪɹjɑ, ˈnɛː.]]",
    "cirya: né": "[[ˈkɪɹjɑ, ˈnɛː.]]",
    "cirya né?": "[[ˈkɪɹjɑ ˈnɛː?]]",
    "aiya Eärendil elenion ancalima": "[[ˈaɪjɑ ɛɑˈɹɛndɪl ɛˈlɛnɪɒn ɑnˈkɑlɪmɑ.]]",
    "Elen síla.": "[[ˈɛlɛn ˈsiːlɑ.]]",
    "Aiya Eärendil!": "[[ˈaɪjɑ ɛɑˈɹɛndɪl!]]",
    "elen síla": "[[ˈɛlɛn ˈsiːlɑ.]]",
}
```

Assertions:

- For every row, `text_utterances(text) == [utterance]`.
- For `cirya`, `Eärendil`, `andúnë`, `ancalima`, and `né`, `word_utterance(text) == utterance`.
- `text_utterances("Elen síla. Aiya Eärendil!")` is the `Elen síla.` utterance then the `Aiya Eärendil!` utterance.
- `text_utterances("aiya Eärendil\nelen síla.")` is `["[[ˈaɪjɑ ɛɑˈɹɛndɪl.]]", "[[ˈɛlɛn ˈsiːlɑ.]]"]`.
- `text_utterances("cirya") == text_utterances("cirya.")`.
- `text_utterances("cirya\n\nné")` is the `cirya` utterance then the `né` utterance.
- `text_utterances("cirya,") == ["[[ˈkɪɹjɑ.]]"]`. Same equality for `cirya;` and `cirya:`.
- `text_utterances("anza")` raises `ValueError` whose message contains `unrecognised letter` and `'z'` and `'anza'`.
- `text_utterances("hl")` raises `ValueError` whose message contains `no vowel` and `'hl'`.
- `text_utterances("")` and `text_utterances("...")` raise `ValueError("nothing to speak")`.
- `subtitle("cirya né") == "ˈkɪɹjɑ · ˈnɛː."`.
- `subtitle("Elen síla. Aiya Eärendil!")` is `"ˈɛlɛn · ˈsiːlɑ.\nˈaɪjɑ · ɛɑˈɹɛndɪl!"`.
- `subtitle("")` and `subtitle("   ")` equal `nothing to speak`.
- `subtitle("anza")` contains `unrecognised letter` and `anza`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_utterance -v`

Expected: FAIL because `quenya_speak.utterance` does not exist.

- [ ] **Step 3: Implement pronunciation**

Add `pyproject.toml` with `requires-python = ">=3.11"`, dependencies `piper-tts` and `textual`, and package discovery under `src`. Leave the console script for Task 4. `src/quenya_speak/__init__.py` is an empty docstring.

`phonetics.py`: copy `_segments` and `_stress_index` from the lesson app into public `segments` and `stress_index`. Do not copy `to_phonemes` or the `__main__` block.

`utterance.py`: copy `word_utterance`, `line_utterance`, and their helpers. Import `segments` and `stress_index`. Do not import private names.

`split_phrases` walks lines, skips a blank line, and keeps `.`, `?`, and `!` on the phrase they end. Leftover text on that line is its own phrase.

`text_utterances` calls `line_utterance` on each phrase. Skip a phrase whose error message starts with `no words`. Let every other `ValueError` through. If nothing remains, raise `ValueError("nothing to speak")`.

`subtitle` returns `nothing to speak` when `text_utterances` does. On `ValueError`, return `str(exc)`. Otherwise return one line per utterance: the inside of `[[...]]`, with each single space between words replaced by ` · `.

- [ ] **Step 4: Run the test to verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_utterance -v`

Expected: PASS. The test does not import Piper.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/quenya_speak/__init__.py src/quenya_speak/phonetics.py src/quenya_speak/utterance.py tests/test_utterance.py
git commit -m "Add Quenya pronunciation and phrase splitting."
```

---

### Task 2: History

**Files:**
- Create: `src/quenya_speak/history.py`
- Test: `tests/test_history.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces:
  - `load() -> list[str]`
  - `remember(text: str) -> list[str]`
  - `chips(items: list[str]) -> list[tuple[str, str]]`

The path is `Path.home() / ".quenya-speak" / "history.jsonl"`, computed on each call, not at import.

- [ ] **Step 1: Write the failing test**

`tests/test_history.py` sets `HOME` to a temporary directory in `setUp` and restores it in `tearDown`.

- `remember("elen")` then `remember("síla")` then `load()` is `["elen", "síla"]`.
- `remember("elen")`, `remember("síla")`, `remember("elen")` leaves `["síla", "elen"]`.
- Remembering 51 distinct texts leaves the last 50. The first text is gone.
- `chips` of 13 texts returns 12 pairs, newest first. Each pair is `(label, full text)`.
- A first line longer than 40 characters has a label of the first 40 characters plus `…` (U+2026). The full text is unchanged.
- A text whose first line is `elen síla` and whose second line is `lúmenn'` has the label `elen síla`.
- A history file containing one valid line, one non-JSON line, and `{"text": 1}` loads as only the valid string.
- When the history path is a directory, `load()` is `[]`.
- After `remember("andúnë")`, the file contains the characters `andúnë` and does not contain `\u`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_history -v`

Expected: FAIL because `quenya_speak.history` does not exist.

- [ ] **Step 3: Implement `load`, `remember`, and `chips`**

A record is one JSON object per line: `{"text": "<the spoken text>"}`, UTF-8, `ensure_ascii=False`. `load` skips a line that is not an object with a string `text`. If the file is missing or cannot be read, return `[]`.

`remember` drops any earlier equal text, appends the new text, keeps the last 50, and replaces the file through a temporary file in the same directory. Create `~/.quenya-speak/` when remembering the first text.

`chips` takes the last 12, newest first. The label is the first line, stripped. Longer than 40 characters, it is cut to 40 and `…` is added.

- [ ] **Step 4: Run the test to verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_history -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/quenya_speak/history.py tests/test_history.py
git commit -m "Remember the last fifty spoken texts."
```

---

### Task 3: Speech

**Files:**
- Create: `src/quenya_speak/speech.py`
- Test: `tests/test_speech.py`

**Interfaces:**
- Consumes: `text_utterances(text: str) -> list[str]`, `word_utterance(spelling: str) -> str`, `remember(text: str) -> list[str]`.
- Produces:
  - `voices_dir() -> Path`
  - `player() -> str | None`
  - `concat_wavs(paths: list[Path], out: Path) -> Path`
  - `synthesize(utterances: list[str], out: Path) -> Path`
  - `play(path: Path) -> str`
  - `stop() -> None`
  - `speak(text: str, out: Path) -> str`

`play` returns `played`, `no_player`, or `failed`. Import Piper inside `synthesize`, not at module import.

- [ ] **Step 1: Write the failing test**

`tests/test_speech.py`:

- With `PIPER_VOICES_DIR` unset and `HOME` set to a temporary directory, `voices_dir()` is `Path(home) / ".piper-voices"`.
- With `PIPER_VOICES_DIR` set to `"   "`, the result is the same home path.
- With `PIPER_VOICES_DIR` set to a temporary directory, `voices_dir()` is that path.
- Build two mono 16-bit WAV files at 16000 Hz with 100 frames each, using the standard-library `wave` module. `concat_wavs` of those two files has `100 + 100 + int(16000 * 0.3)` frames. The frames of the gap are zero. There is no extra gap after the second clip.
- A second clip at 8000 Hz raises `ValueError` with `voice returned mismatched audio`, and the output path is not created.
- With `PATH` set to an empty directory, `play(Path("missing.wav"))` returns `no_player`.
- Write a tiny WAV and put a fake player named `afplay` on `PATH` that exits 1. On macOS `play` returns `failed` and the WAV still exists. Skip this assertion when `sys.platform` is not `darwin`, and instead use a fake `ffplay`.
- If `import piper` fails, `synthesize([word_utterance("cirya")], out)` raises `ValueError` whose message is `piper-tts is not installed in the active virtual environment`, and `out` is not created. Skip this test when Piper imports.
- If Piper imports, point `PIPER_VOICES_DIR` at an empty temporary directory and patch `subprocess.run` to return code 1. `synthesize` raises `ValueError` whose message contains `-m`, `piper.download_voices`, `en_GB-cori-high`, and `--data-dir`. The output WAV is not created. Skip this test when Piper does not import.
- If Piper imports and both `en_GB-cori-high.onnx` and `en_GB-cori-high.onnx.json` in `voices_dir()` are non-empty, `synthesize([word_utterance("cirya")], out)` writes a WAV with at least one frame. Skip otherwise. Do not download and do not play.
- In that same voice-present case, `synthesize(["[[☺.]]"], out)` raises `ValueError` containing `☺` and `[[☺.]]`, and `out` is not created.
- Patch `synthesize` to write a tiny valid WAV and return its path, patch `remember` to raise `OSError`, and patch `play` to return `played`. `speak("cirya", out)` returns `played`, the WAV exists, and stderr contains `history was not saved`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_speech -v`

Expected: FAIL because `quenya_speak.speech` does not exist.

- [ ] **Step 3: Implement speech**

`voices_dir` follows the Global Constraints order and does not look at any neighbouring path.

`player` returns `afplay` on macOS when it is on `PATH`, otherwise `ffplay` when it is on `PATH`, otherwise `aplay`. Otherwise `None`.

`concat_wavs` reads the clips with `wave`. Sample rate, sample width, and channel count come from the first clip. A later clip that differs raises `ValueError("voice returned mismatched audio")` and does not create `out`. Insert `int(rate * 0.3)` frames of silence between clips and not after the last. Write to a temporary file in `out`'s directory and replace `out` only when the wave is complete. `out`'s parent must already exist.

`synthesize` raises `ValueError("piper-tts is not installed in the active virtual environment")` when `import piper` fails. It creates `voices_dir()` if needed. If either voice file is missing or empty, it runs, without a shell:

```text
<sys.executable> -m piper.download_voices en_GB-cori-high --data-dir <voice directory>
```

A non-zero exit, or files that are still missing, raises `ValueError` and the message includes that command. A present non-empty pair is left in place.

Load the voice and reject an utterance before writing audio when any character inside `[[...]]` is absent from `voice.config.phoneme_id_map`. The message contains the character's `repr` and the utterance. Synthesize each utterance with `SynthesisConfig(length_scale=1.15)` into its own temporary WAV via `PiperVoice.synthesize_wav`. Use `generate_audio.py` in the lesson app only to see that call. Do not copy its inventory, cache, or ffmpeg steps. Pass the clip paths to `concat_wavs`.

`play` uses `player()`. `None` returns `no_player` and does not start a process. Otherwise start the program with the WAV path as an argument. `ffplay` also gets `-nodisp`, `-autoexit`, and `-loglevel error`. Do not use a shell. Wait. Return `played` on exit code 0 and `failed` otherwise. Keep the `Popen` where `stop()` can terminate it. `stop()` terminates that process if it is running, and does nothing otherwise. Do not delete the WAV.

`speak` calls `text_utterances`, then `synthesize`, then `remember`, then `play`. If `remember` raises, write `history was not saved` to stderr and still return the play result. Return `played`, `no_player`, or `failed`.

- [ ] **Step 4: Run the test to verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_speech tests.test_utterance tests.test_history -v`

Expected: PASS. The cirya synthesis test is skipped when the voice is not already in `voices_dir()`.

- [ ] **Step 5: Commit**

```bash
git add src/quenya_speak/speech.py tests/test_speech.py
git commit -m "Synthesize a Quenya phrase to one WAV."
```

---

### Task 4: One-shot command

**Files:**
- Create: `src/quenya_speak/cli.py`
- Modify: `pyproject.toml`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `speak(text: str, out: Path) -> str`, `player() -> str | None`, and `run(out: Path) -> None` from Task 5.
- Produces: `main(argv: list[str] | None = None) -> int` and `open_stage(out: Path) -> None`

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py` patches `quenya_speak.cli.speak` and `quenya_speak.cli.open_stage` so no audio starts and Stage is not imported.

- `main(["--file", "a.txt", "elen"])` returns 2. stderr contains `pass text or --file, not both`. `speak` is not called.
- `main(["--file", str(missing)])` returns 1. stderr contains that path. `speak` is not called.
- A `--file` whose bytes are `b"\xff"` returns 1. stderr contains the path.
- `main(["--out", str(missing_dir / "a.wav"), "cirya"])` returns 1. stderr contains the missing directory. `speak` is not called.
- `main(["anza"])` returns 1. stderr contains `unrecognised letter` and `anza`. No WAV is created. Do not patch `speak` for this case; pronunciation fails first.
- `main([""])` returns 1. stderr contains `nothing to speak`.
- `main([])` returns 0 and calls `open_stage` once with `Path.cwd() / "quenya.wav"`.
- When `speak` returns `played`, `main(["cirya"])` returns 0 and stdout is empty.
- When `speak` returns `no_player`, stdout is `wrote <path>` and the exit code is 0.
- Patch `player` to return `afplay`. When `speak` returns `failed`, the exit code is 1 and stderr is `afplay playback failed`.
- When `speak` raises `KeyboardInterrupt`, `main` returns 130.

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=src python -m unittest tests.test_cli -v`

Expected: FAIL because `quenya_speak.cli` does not exist.

- [ ] **Step 3: Implement `main`**

Add to `pyproject.toml`:

```toml
[project.scripts]
quenya-say = "quenya_speak.cli:main"
```

Import `speak` and `player` at module level so tests can patch `quenya_speak.cli.speak` and `quenya_speak.cli.player`. `open_stage` is the only place that imports `quenya_speak.tui.run`, and it does that inside the function.

`main(None)` reads `sys.argv[1:]`. Join positional words with a single space. `--file` and positional text together return 2 with stderr `pass text or --file, not both`. A missing file, a file that is not UTF-8, or a missing output parent returns 1 and names the path. Check the output parent before `speak`.

No positional text and no `--file` calls `open_stage(out)` and returns 0. Otherwise call `speak(text, out)`. `played` returns 0. `no_player` prints `wrote <path>` to stdout and returns 0. `failed` prints `{player()} playback failed` to stderr and returns 1. `KeyboardInterrupt` returns 130. Do not delete a WAV that was already written.

- [ ] **Step 4: Run the test to verify it passes**

Run: `PYTHONPATH=src python -m unittest tests.test_cli tests.test_utterance -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/quenya_speak/cli.py tests/test_cli.py
git commit -m "Add the one-shot quenya-say command."
```

---

### Task 5: Stage and README

**Files:**
- Create: `src/quenya_speak/tui.py`
- Create: `README.md`

**Interfaces:**
- Consumes: `subtitle(text: str) -> str`, `text_utterances(text: str) -> list[str]`, `chips(items: list[str]) -> list[tuple[str, str]]`, `load() -> list[str]`, `speak(text: str, out: Path) -> str`, `stop() -> None`, `player() -> str | None`.
- Produces: `run(out: Path) -> None`

- [ ] **Step 1: Confirm the import fails**

Do not drive the screen. The spec leaves Stage untested as a UI. Subtitle text is already pinned in Task 1.

Run: `PYTHONPATH=src python -c "from quenya_speak.tui import run"`

Expected: `ModuleNotFoundError`.

- [ ] **Step 2: Implement Stage**

`run(out: Path) -> None` runs a Textual `App`. The screen has:

- A top mark `quenya` and a status whose words are `ready` and `speaking`.
- A `TextArea`, starting empty. Enter inserts a newline.
- A subtitle static. On every edit, set it from `subtitle(text)`.
- A pulse static, hidden until audio is playing.
- A row of buttons from `chips(load())`, newest on the left.
- A Speak button.
- A file input, hidden until Ctrl-O.

Ctrl-Enter and the Speak button speak. Speaking calls `text_utterances` first. On `ValueError`, show that message and do not call `speak`. Run `speak` in a worker so the status can read `speaking` and the pulse can show. While that worker runs, ignore Speak, chips, and Ctrl-O. Then set the status back to `ready`. `played` leaves the pronunciation in the subtitle. `no_player` sets the subtitle to `wrote <path>`. `failed` sets it to `{player()} playback failed`.

A chip sets the center to the stored full text and speaks it. Ctrl-O shows the path input. Enter there reads the file as UTF-8 into the center and does not speak. Esc on that input hides it and leaves the center unchanged. A missing file or a file that is not UTF-8 is shown in the subtitle and the center stays unchanged.

Esc and Ctrl-C call `stop()` and quit the app. Esc during playback therefore stops the player and then quits.

- [ ] **Step 3: Write the README**

`README.md` says this program speaks Quenya text and is not a lesson course. Include both setups from the spec, with `<existing-piper-venv>` and `PIPER_VOICES_DIR=/path/to/Quenya/claudeslop/.piper-voices` as examples the person fills in. State that the program does not search for that directory. List `quenya-say`, `quenya-say "elen síla"`, `quenya-say --file`, and `--out`. List the Stage keys: Enter for a new line, Ctrl-Enter or Speak to speak, Esc to quit, Ctrl-O to open a file, and a chip to speak that text again. State CC BY-NC 4.0, copyright 2026 De Villiers Neethling, and that the voice file is downloaded and is not in the repository.

- [ ] **Step 4: Verify**

Run: `pip install -e .` and then `PYTHONPATH=src python -m unittest discover -s tests -v`

Expected: PASS, with the voice synthesis tests skipped unless the voice is already in `voices_dir()`.

Then run `quenya-say` and confirm the screen opens and Esc quits. Run `quenya-say "elen síla"` only when `PIPER_VOICES_DIR` or `~/.piper-voices` already has the voice, or accept the download that the spec describes. Do not point the program at a neighbouring repository from code.

- [ ] **Step 5: Commit**

```bash
git add src/quenya_speak/tui.py README.md
git commit -m "Add the Stage screen and the README."
```
