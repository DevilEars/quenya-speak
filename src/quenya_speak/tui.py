"""Stage, for typing Quenya and hearing it."""

from functools import partial
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, HorizontalScroll, Vertical
from textual.content import Content
from textual.widgets import Button, Input, Static, TextArea
from textual.worker import Worker, WorkerState

from quenya_speak.history import chips, load
from quenya_speak.speech import player, speak, stop
from quenya_speak.utterance import subtitle, text_utterances


class ChipButton(Button):
    """An earlier text. The label is the short form; the button keeps the full text."""

    def __init__(self, label: str, full_text: str) -> None:
        # Button parses a str as markup and drops or rejects brackets.
        super().__init__(Content.from_text(label, markup=False), compact=True)
        self.full_text = full_text


class PathPrompt(Input):
    """Path field. Escape hides it and leaves the center unchanged."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    def action_cancel(self) -> None:
        stage = self.app
        assert isinstance(stage, Stage)
        stage.dismiss_path()


_WAVE = "▁▂▃▅▇▅▃▂▁▂▃▅▇▅▃▂▁"


class Stage(App[None]):
    """A narrow column: the phrase, its pronunciation, and earlier texts."""

    ESCAPE_TO_MINIMIZE = False

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=False, priority=True),
        Binding("escape", "quit", "Quit", show=False),
        Binding("ctrl+enter", "speak", "Speak", show=False, priority=True),
        Binding("ctrl+o", "open_file", "Open", show=False, priority=True),
    ]

    CSS = """
    Screen {
        background: #070b12;
        align-horizontal: center;
    }

    #column {
        width: 56;
        max-width: 100%;
        height: 1fr;
        background: #070b12;
        padding: 1 0;
    }

    #mark {
        height: 1;
        content-align: center middle;
        text-align: center;
        color: #8eb4d4;
        text-style: bold;
    }

    #phrase {
        height: auto;
        min-height: 3;
        max-height: 12;
        margin-top: 1;
        background: #070b12;
        color: #f7fbff;
        border: none;
        padding: 0;
    }

    #phrase:focus {
        border: none;
    }

    #phrase .text-area--cursor-line {
        background: #10182a;
    }

    #subtitle {
        height: auto;
        max-height: 8;
        margin-top: 1;
        color: #9fb6cc;
        text-align: center;
    }

    #pulse {
        height: 1;
        margin-top: 1;
        color: #8eb4d4;
        text-align: center;
    }

    #speak-row {
        height: auto;
        margin-top: 1;
        margin-bottom: 1;
    }

    #speak {
        width: auto;
        min-width: 14;
        background: #d5e6f5;
        color: #071018;
        border: none;
        text-style: bold;
    }

    #speak:hover {
        background: #f7fbff;
        color: #071018;
    }

    #speak:disabled {
        text-opacity: 0.5;
    }

    #file {
        margin-bottom: 1;
        background: #152033;
        color: #f7fbff;
        border: none;
    }

    #fill {
        height: 1fr;
    }

    #chips {
        height: auto;
        max-height: 3;
        align-horizontal: center;
    }

    ChipButton {
        margin: 0 1 0 0;
        min-width: 4;
        background: #152033;
        color: #c5d5e4;
        border: none !important;
        text-style: none;
    }

    ChipButton:hover {
        background: #1c3048;
        color: #f7fbff;
    }

    ChipButton:disabled {
        text-opacity: 0.45;
    }

    .hidden {
        display: none;
    }
    """

    def __init__(self, out: Path) -> None:
        super().__init__()
        self.out = out
        self._speaking = False
        self._quitting = False
        self._pulse_step = 0
        # ``load_text`` posts Changed later. Skip that one so a playback
        # message is not replaced by the pronunciation we already showed.
        self._skip_subtitle = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="column"):
            yield Static("quenya · ready", id="mark")
            yield TextArea(id="phrase", soft_wrap=True, compact=True)
            yield Static(subtitle(""), id="subtitle", markup=False)
            yield Static(self._wave_frame(), id="pulse", classes="hidden")
            with Center(id="speak-row"):
                yield Button("speak", id="speak", compact=True)
            yield PathPrompt(placeholder="file path", id="file", classes="hidden")
            yield Static("", id="fill")
            with HorizontalScroll(id="chips"):
                yield from _chip_buttons()

    def on_mount(self) -> None:
        self.query_one("#phrase", TextArea).focus()
        self.set_interval(0.16, self._blink_pulse)

    def _wave_frame(self) -> str:
        start = self._pulse_step % len(_WAVE)
        spun = _WAVE[start:] + _WAVE[:start]
        return spun[:18]

    def _blink_pulse(self) -> None:
        if not self._speaking:
            return
        self._pulse_step += 1
        self.query_one("#pulse", Static).update(self._wave_frame())

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if self._skip_subtitle:
            self._skip_subtitle -= 1
            return
        self._show_subtitle(subtitle(event.text_area.text))

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self._speaking and action in {"speak", "open_file"}:
            return False
        return True

    def action_speak(self) -> None:
        self._speak_center()

    def action_open_file(self) -> None:
        if self._speaking:
            return
        prompt = self.query_one("#file", PathPrompt)
        prompt.remove_class("hidden")
        prompt.focus()

    def dismiss_path(self) -> None:
        """Hide the path field. The center is left as it is."""
        prompt = self.query_one("#file", PathPrompt)
        prompt.value = ""
        prompt.add_class("hidden")
        self.query_one("#phrase", TextArea).focus()

    def action_quit(self) -> None:
        """Stop the player, if it is running, and leave Stage."""
        if self._quitting:
            return
        self._quitting = True
        stop()
        self.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if self._speaking:
            return
        button = event.button
        if isinstance(button, ChipButton):
            self._set_center(button.full_text)
            self._speak_center()
        elif button.id == "speak":
            self._speak_center()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "file":
            return
        self._read_file(event.value)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.name != "speak":
            return
        if event.state not in {
            WorkerState.SUCCESS,
            WorkerState.ERROR,
            WorkerState.CANCELLED,
        }:
            return
        if self._quitting or not self.is_running:
            return
        self._set_speaking(False)
        if event.state == WorkerState.CANCELLED:
            return
        if event.state == WorkerState.ERROR:
            self._show_subtitle(_error_text(event.worker.error))
        else:
            self._show_play_result(event.worker.result)
        self._reload_chips()

    def _speak_center(self) -> None:
        if self._speaking:
            return
        text = self.query_one("#phrase", TextArea).text
        try:
            text_utterances(text)
        except ValueError as exc:
            self._show_subtitle(str(exc))
            return
        parent = self.out.parent
        if not parent.is_dir():
            self._show_subtitle(f"{parent}: output directory does not exist")
            return
        self._set_speaking(True)
        self.run_worker(
            partial(speak, text, self.out),
            name="speak",
            thread=True,
            exclusive=False,
            exit_on_error=False,
        )

    def _set_speaking(self, speaking: bool) -> None:
        self._speaking = speaking
        mark = "quenya · speaking" if speaking else "quenya · ready"
        self.query_one("#mark", Static).update(mark)
        pulse = self.query_one("#pulse", Static)
        pulse.update(self._wave_frame())
        pulse.set_class(not speaking, "hidden")
        self.query_one("#speak", Button).disabled = speaking
        for chip in self.query(ChipButton):
            chip.disabled = speaking

    def _show_play_result(self, result: object) -> None:
        if result == "played":
            return
        if result == "no_player":
            self._show_subtitle(f"wrote {self.out}")
            return
        if result == "failed":
            self._show_subtitle(f"{player()} playback failed")
            return
        self._show_subtitle(str(result))

    def _set_center(self, text: str) -> None:
        self._skip_subtitle += 1
        self.query_one("#phrase", TextArea).text = text
        self._show_subtitle(subtitle(text))

    def _read_file(self, raw: str) -> None:
        path = Path(raw.strip()).expanduser()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            self._show_subtitle(f"{path}: file is not UTF-8")
            return
        except OSError as exc:
            detail = exc.strerror or str(exc)
            self._show_subtitle(f"{path}: {detail}")
            return
        self._set_center(text)
        self.dismiss_path()

    def _reload_chips(self) -> None:
        focused = self.focused
        row = self.query_one("#chips", HorizontalScroll)
        row.remove_children()
        buttons = _chip_buttons()
        if buttons:
            row.mount(*buttons)
            if self._speaking:
                for button in buttons:
                    button.disabled = True
        # Removing the focused chip drops focus. Put the cursor back in the phrase.
        if focused is not None and not focused.is_attached:
            self.query_one("#phrase", TextArea).focus()

    def _show_subtitle(self, text: str) -> None:
        self.query_one("#subtitle", Static).update(text)


def _chip_buttons() -> list[ChipButton]:
    return [ChipButton(label, text) for label, text in chips(load())]


def _error_text(error: BaseException | None) -> str:
    if error is None:
        return "speak failed"
    text = str(error)
    return text or error.__class__.__name__


def run(out: Path) -> None:
    """Run Stage. Speech is written to ``out``."""
    Stage(out).run()
