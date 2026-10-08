"""One-shot quenya-say command."""

import argparse
import sys
from pathlib import Path

from quenya_speak.speech import player, speak


def open_stage(out: Path) -> None:
    """Open Stage on ``out``. The TUI is imported only here."""
    from quenya_speak.tui import run

    run(out)


def main(argv: list[str] | None = None) -> int:
    """Speak words or a file, or open Stage when neither was given."""
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(prog="quenya-say")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("words", nargs="*")
    args = parser.parse_args(argv)
    if args.file is not None and args.words:
        print("pass text or --file, not both", file=sys.stderr)
        return 2
    if args.file is not None:
        try:
            text = args.file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"{args.file}: file is not UTF-8", file=sys.stderr)
            return 1
        except OSError as exc:
            print(f"{args.file}: {exc.strerror}", file=sys.stderr)
            return 1
    else:
        text = " ".join(args.words)
    out = args.out if args.out is not None else Path.cwd() / "quenya.wav"
    if not out.parent.is_dir():
        print(f"{out.parent}: output directory does not exist", file=sys.stderr)
        return 1
    if args.file is None and not args.words:
        open_stage(out)
        return 0
    try:
        result = speak(text, out)
    except KeyboardInterrupt:
        return 130
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    if result == "played":
        return 0
    if result == "no_player":
        print(f"wrote {out}")
        return 0
    print(f"{player()} playback failed", file=sys.stderr)
    return 1
