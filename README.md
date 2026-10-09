# Quenya Speak

This program speaks Quenya text on your own machine. It is not a lesson course. It does not read Eldamo, lessons, phrases, or a Reader clip inventory.

## Already on this machine

`<existing-piper-venv>` is a virtual environment that already has `piper-tts` installed. `PIPER_VOICES_DIR` points at a voice directory you already have. The path below is an example you fill in. The program does not search for that directory.

```
export PIPER_VOICES_DIR=/path/to/Quenya/claudeslop/.piper-voices
source <existing-piper-venv>/bin/activate
pip install -e .
quenya-say
```

## A new machine

```
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
quenya-say "elen síla"
```

The first speak downloads `en_GB-cori-high` into `~/.piper-voices`, or into `PIPER_VOICES_DIR` when that is set.

## Command

```
quenya-say
quenya-say "elen síla"
quenya-say --file PATH
quenya-say --out PATH
```

`quenya-say` opens Stage. `quenya-say "elen síla"` speaks those words. `quenya-say --file` reads a UTF-8 file and speaks it. `--out` replaces the default WAV path, `quenya.wav` in the current directory.

## Stage

- Enter for a new line.
- Ctrl-Enter or Speak to speak.
- Esc to quit. Ctrl-C quits the same way and stops playback first.
- Ctrl-O to open a file. Enter loads that UTF-8 file into the center and does not speak. Esc on the path field hides it and leaves the center unchanged.
- A chip speaks that text again.

## Licence

Original code in this repository is copyright 2026 De Villiers Neethling and is licensed CC BY-NC 4.0.

The voice file is downloaded and is not in the repository.
