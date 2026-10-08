# Quenya Speak — local app

**Date:** 2026-10-08
**Status:** Draft for review

Speak Quenya text on your own machine. A Stage screen for sitting and listening, and a one-shot command when you already have the words. This repository is not the lesson app. It does not read Eldamo, lessons, phrases, or the Reader clip inventory.

The browser page is a later spec. It must produce the utterance strings in this document for the same phrases. It is not part of this design.

## Goal

From a checkout of this repository, a person can type Quenya and hear it. The program writes one WAV file and plays it. Pronunciation follows the lesson app's Appendix E phonetics and its Piper IPA mapping. The lesson app's files stay as they are.

## Licence

Original code in this repository, including the copied phonetics and utterance rules, is copyright 2026 De Villiers Neethling and is licensed CC BY-NC 4.0, the same licence as the Quenya app's original tooling.

`piper-tts` is a dependency. It is GPL-3.0 and is not vendored. The voice file is not committed.

## Decisions

- This directory is its own git repository, meant to be published on GitHub. Implementation does not create the GitHub remote.
- Python 3.11 or newer. Package layout under `src/quenya_speak`. Install with `pip install -e .`.
- Dependencies: `piper-tts` and `textual`. Tests use `unittest` from the standard library.
- Voice: Piper `en_GB-cori-high`. Length scale: `1.15`. No voice flag and no length flag.
- Output audio is WAV. No ffmpeg and no AAC.
- Default output path: `quenya.wav` in the current working directory. `--out` replaces that path. The parent directory of the output must already exist.
- Silence between spoken phrases: 300 ms.
- History file: `~/.quenya-speak/history.jsonl`. Last 50 texts. Stage shows 12.

## Command

```
quenya-say
quenya-say [--out PATH] TEXT...
quenya-say [--out PATH] --file PATH
```

Words passed on the command line are joined with a single space, then spoken. `--file` reads a UTF-8 file. Text and `--file` together is an error. No text and no `--file` opens Stage.

Exit codes:

| Code | When |
| --- | --- |
| 0 | The WAV was written. Playback ran, or no player was on `PATH`. |
| 1 | The text, the file, the voice, synthesis, or playback failed. |
| 2 | Text and `--file` were both given. |
| 130 | The player was interrupted with Ctrl-C. The WAV stays. |

On exit 0 with no player, stdout is `wrote <path>`. Other errors go to stderr and name the cause. A failure before the WAV is complete leaves any previous WAV in place. A player that starts and fails keeps the new WAV.

## Stage

Stage is a Textual app. The screen matches the Stage mockup: the phrase fills the center, the pronunciation sits under it, a pulse shows while audio plays, and earlier texts are chips along the bottom.

- The center starts empty.
- Enter inserts a line break.
- Ctrl-Enter, or a click on the Speak control, speaks the center.
- While audio plays, the status reads `speaking`, the pulse is visible, and Speak, chips, and Ctrl-O are ignored.
- Esc quits. Esc while audio plays stops the player and then quits. Ctrl-C quits the same way.
- Ctrl-O asks for a file path. Enter loads that UTF-8 file into the center and does not speak. Esc cancels the prompt and leaves the center as it was. A missing file or a file that is not UTF-8 is reported under the phrase and the center stays as it was.
- The top mark reads `quenya`. The status word is `ready` or `speaking`.
- The subtitle updates on each edit, before any sound. It is one line per utterance: the inside of the `[[...]]` string, with ` · ` between words. The string sent to Piper is still the `[[...]]` form.
- When the text cannot be spoken, the subtitle is the error and Speak does nothing.
- An empty center does not speak. The subtitle reads `nothing to speak`. Stage stays open.
- A chip shows the newest texts on the left. The label is the first line, cut to 40 characters plus `…` when longer. A click puts the full stored text in the center and speaks it.
- History is loaded when Stage opens. The first successful speak creates `~/.quenya-speak/` if needed.

## Phrases

`split_phrases` walks the text line by line. Blank lines are skipped. Inside a line, `.`, `?`, and `!` end a phrase and stay on that phrase. Text after the last terminator is its own phrase. A phrase that contains no word is skipped. If no phrase remains, the error is `nothing to speak`.

Each remaining phrase goes through `line_utterance`:

- Words are split on whitespace.
- The final `.`, `?`, or `!` is the utterance terminator. A phrase with no terminator ends in `.`.
- A comma, semicolon, or colon on a word becomes a comma and a space before the next word. On the last word the mark is removed and no pause is added.
- Each word is segmented and stressed by the phonetics module, then mapped to the Piper IPA characters below.

An unrecognised letter or a word with no vowel raises. The message names the letter or the spelling. Nothing is synthesized.

Pinned utterances, copied from the lesson app. These are exact, including the brackets:

| Input | Utterance |
| --- | --- |
| `cirya` | `[[ˈkɪɹjɑ.]]` |
| `Eärendil` | `[[ɛɑˈɹɛndɪl.]]` |
| `andúnë` | `[[ɑnˈduːnɛ.]]` |
| `ancalima` | `[[ɑnˈkɑlɪmɑ.]]` |
| `né` | `[[ˈnɛː.]]` |
| `cirya né` | `[[ˈkɪɹjɑ ˈnɛː.]]` |
| `cirya, né` | `[[ˈkɪɹjɑ, ˈnɛː.]]` |
| `cirya; né` | `[[ˈkɪɹjɑ, ˈnɛː.]]` |
| `cirya: né` | `[[ˈkɪɹjɑ, ˈnɛː.]]` |
| `cirya né?` | `[[ˈkɪɹjɑ ˈnɛː?]]` |
| `aiya Eärendil elenion ancalima` | `[[ˈaɪjɑ ɛɑˈɹɛndɪl ɛˈlɛnɪɒn ɑnˈkɑlɪmɑ.]]` |
| `Elen síla.` | `[[ˈɛlɛn ˈsiːlɑ.]]` |
| `Aiya Eärendil!` | `[[ˈaɪjɑ ɛɑˈɹɛndɪl!]]` |
| `elen síla` | `[[ˈɛlɛn ˈsiːlɑ.]]` |

`Elen síla. Aiya Eärendil!` is two utterances: the `Elen síla.` row, then the `Aiya Eärendil!` row.

This text is two utterances. The first is `[[ˈaɪjɑ ɛɑˈɹɛndɪl.]]`. The second is `[[ˈɛlɛn ˈsiːlɑ.]]`.

```
aiya Eärendil
elen síla.
```

Phonetics rules, unchanged from `Quenya/claudeslop/quenya-app/tools/quenya_phonetics.py`:

- `c` is `k`. `qu` is `k` then `w`.
- `ty`, `hy`, `ny`, `ly`, and `hw` are one consonant segment. `ry` is two segments, so `cirya` is kir-ya.
- `x` is `k` then `s`. A geminate is two of the same consonant. `hl` and `hr` are `h` plus `l` or `r`.
- An acute marks a long vowel. A diaeresis keeps the vowel in its own syllable.
- Diphthongs are `ai`, `oi`, `ui`, `au`, `eu`, `iu`.
- Stress is never on the last syllable. Two syllables stress the first. Three or more stress the penult when it is heavy (long vowel, diphthong, or two or more following consonants), otherwise the antepenult.
- A trailing elision mark is dropped.

Piper mapping, unchanged from `tools/piper_utterance.py`. Stress is `ˈ` on the start of the stressed syllable. `r` is `ɹ`. Short `o` is `ɒ`. Long vowels use `ː`. Diphthongs are two characters.

## Modules

Each module is importable without opening Stage and without loading Piper, except `speech`, which imports Piper when synthesis is called.

`phonetics.py`

- `segments(word: str) -> list`
- `stress_index(segs: list) -> int | None`

Same segment tuples as `_segments` and `_stress_index` in the lesson app. `utterance` calls these public functions. It does not import private names.

`utterance.py`

- `word_utterance(spelling: str) -> str`
- `line_utterance(text: str) -> str`
- `split_phrases(text: str) -> list[str]`
- `text_utterances(text: str) -> list[str]`

`text_utterances` returns one Piper string per remaining phrase. It raises `ValueError("nothing to speak")` when none remain, and it lets phonetics errors through.

`history.py`

- `load() -> list[str]` — oldest to newest, at most 50. A missing file is an empty list. A line that is not a JSON object with a string `text` field is skipped. If the file cannot be read, the result is an empty list.
- `remember(text: str) -> list[str]` — removes any earlier entry with the same text, appends it, keeps the last 50, and writes the file. The write is a temp file in the same directory, then a replace.
- `chips(items: list[str]) -> list[tuple[str, str]]` — the last 12, newest first. Each pair is `(label, full text)`.

A record is one JSON object per line: `{"text": "<the spoken text>"}`, UTF-8, with non-ASCII characters written as themselves.

`speech.py`

- `voices_dir() -> Path`
- `synthesize(utterances: list[str], out: Path) -> Path`
- `play(path: Path) -> str` — returns `played`, `no_player`, or `failed`
- `speak(text: str, out: Path) -> str` — utterances, then synthesize, then `remember`, then `play`. Returns the play result.

Voice directory, in order:

1. `PIPER_VOICES_DIR` when it is set and non-empty.
2. The directory `Quenya/claudeslop/.piper-voices` next to this repository, when that directory exists.
3. `~/.piper-voices`.

`synthesize` creates the voice directory if needed. If `en_GB-cori-high.onnx` or `en_GB-cori-high.onnx.json` is missing or empty, it runs:

```
<sys.executable> -m piper.download_voices en_GB-cori-high --data-dir <voice directory>
```

If that command fails, or the files are still missing, it raises and the message includes that command. A present, non-empty pair is left in place.

Before writing audio, every character inside each `[[...]]` string must be in the loaded voice's phoneme map. A missing character raises. The message names the character and the phrase. Nothing is written.

Each utterance is synthesized with `SynthesisConfig(length_scale=1.15)`. The clips are concatenated in order with 300 ms of silence between them. Sample rate, sample width, and channel count come from the first clip. A later clip that differs raises `voice returned mismatched audio` and does not replace the output. The finished WAV is written to a temp file in the output directory and replaces the target only after the wave header and frames are complete.

`play` uses the first program on `PATH`: `afplay` on macOS, otherwise `ffplay` (`-nodisp -autoexit -loglevel error`), otherwise `aplay`. The WAV path is an argument, not a shell string. `no_player` means none of those programs was found. `failed` means the program ran and returned non-zero.

`speak` records history only after the WAV replace succeeds, including when playback is `no_player` or `failed`. If recording history fails, the WAV still stands, the play result is unchanged, and stderr says the history was not saved.

`cli.py`

- `main(argv: list[str] | None = None) -> int`

`tui.py`

- `run(out: Path) -> None`

The one-shot command calls `speak`. Stage calls `text_utterances` for the subtitle and `speak` for Speak.

## Errors

| Condition | One-shot | Stage |
| --- | --- | --- |
| Unrecognised letter, no vowel, or empty of words | stderr, exit 1, no new WAV | subtitle is the error, Speak does nothing |
| Phoneme missing from the voice | stderr names the character and the phrase, exit 1, no new WAV | same text in the subtitle, no new WAV |
| `--file` missing or not UTF-8 | stderr, exit 1 | path prompt reports it, center unchanged |
| Output parent directory missing | stderr, exit 1 | subtitle reports it |
| Voice download fails | stderr includes the download command, exit 1 | subtitle includes that command |
| `piper-tts` is not installed | stderr tells the person to install it in the active virtual environment, exit 1 | subtitle says the same |
| No player on `PATH` | stdout `wrote <path>`, exit 0 | subtitle shows `wrote <path>`, status returns to `ready` |
| Player returns non-zero | stderr `<player> playback failed`, exit 1, WAV kept | subtitle shows that message, status returns to `ready` |
| History line damaged | that line is ignored | that chip is absent |
| History file unreadable | Stage still opens with no chips. The one-shot still speaks and does not fail because of history. | same |

## Tests

`tests/test_utterance.py` pins every row in the utterance table, the two-phrase sentence `Elen síla. Aiya Eärendil!`, and the two-line sample. It also pins that `cirya.` and `cirya` produce the same phones with a final `.`, and that a blank line does not add a phrase. It does not import Piper.

`tests/test_history.py` uses a temporary home. It checks append, exact-text dedupe, the 50-item cap, chip order (newest first, 12 labels), a skipped bad line, and an unreadable file returning an empty list.

`tests/test_speech.py` calls `synthesize` on `word_utterance("cirya")` only when `piper-tts` imports and the resolved voice files are already present and non-empty. It expects a WAV with at least one frame. It does not download a voice, does not play audio, and does not compare samples. When the voice or the package is missing, the test is skipped.

Stage is not driven in a test. The subtitle and Speak refusal are the utterance errors above.

## README

The README says what the program does and that it is not a lesson course. It gives two setups.

Already on this machine:

```
source <existing-piper-venv>/bin/activate
pip install -e .
quenya-say
```

`<existing-piper-venv>` is a virtual environment that already has `piper-tts` installed. The voice directory beside this repository is used when it is present. `PIPER_VOICES_DIR` overrides it.

A new machine:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
quenya-say "elen síla"
```

The first speak downloads `en_GB-cori-high` into `~/.piper-voices`, or into `PIPER_VOICES_DIR` when that is set. The README lists the Stage keys and the one-shot forms, states the CC BY-NC 4.0 licence, and states that the voice file is downloaded and is not in the repository.

## Out of scope

- The GitHub Pages page, and any JavaScript port of these rules.
- Editing `quenya-app`, including `tools/quenya_phonetics.py`, `tools/piper_utterance.py`, and `tools/generate_audio.py`.
- Choosing another voice, another length, or writing AAC.
- A lexicon, a lesson, or Tengwar.
- Keeping old WAV files for each chip. A chip speaks by synthesizing again.
- Creating the GitHub remote or pushing to it.
