"""Piper raw-phoneme utterances.

The phonetics module stays the pronunciation authority. This module only
re-spells its segments into the IPA characters an English Piper voice was
trained on, and places stress on the syllable onset.

The flat ``[[...]]`` string is not parsed. A stressed diphthong and two
adjacent vowels collapse to the same characters there (``'ai``), so the
segment list is what keeps them apart.
"""
from quenya_speak.phonetics import segments, stress_index

VOWELS = {
    "a": "ɑ", "a:": "ɑː",
    "e": "ɛ", "e:": "ɛː",
    "i": "ɪ", "i:": "iː",
    "o": "ɒ", "o:": "ɔː",
    "u": "ʊ", "u:": "uː",
    "ai": "aɪ", "au": "aʊ", "oi": "ɔɪ", "ui": "ʊɪ", "eu": "ɛʊ", "iu": "ɪʊ",
}
CONSONANTS = {
    "p": "p", "t": "t", "k": "k", "b": "b", "d": "d", "g": "g",
    "f": "f", "v": "v", "s": "s", "h": "h", "m": "m", "n": "n",
    "l": "l", "r": "ɹ", "w": "w", "j": "j",
}
PAUSE_MARKS = ",;:"
TERMINATORS = ".?!"


def word_utterance(spelling: str) -> str:
    """One word clip: a single raw-phoneme block ending in a statement mark."""
    return "[[" + _word_phones(spelling) + ".]]"


def line_utterance(text: str) -> str:
    """One line clip: words split before phonemicization, one block.

    A comma, semicolon, or colon on a word is a comma and a space before the
    next word. A final ``.`` ``?`` or ``!`` is that character; otherwise ``.``.
    """
    tokens = text.split()
    if not tokens:
        raise ValueError(f"empty line {text!r}")
    terminator = "."
    if tokens[-1][-1] in TERMINATORS:
        terminator = tokens[-1][-1]
        tokens[-1] = tokens[-1][:-1]
        if not tokens[-1]:
            tokens.pop()
    pieces = []
    pause_before = False
    for i, token in enumerate(tokens):
        pause = False
        body = token
        if body and body[-1] in PAUSE_MARKS:
            pause = True
            body = body[:-1]
        if not body:
            continue
        phones = _word_phones(body)
        if not pieces:
            pieces.append(phones)
        elif pause_before:
            pieces.append(", " + phones)
        else:
            pieces.append(" " + phones)
        pause_before = pause and i < len(tokens) - 1
    if not pieces:
        raise ValueError(f"no words in {text!r}")
    return "[[" + "".join(pieces) + terminator + "]]"


def _word_phones(spelling):
    segs = segments(spelling)
    stress = stress_index(segs)
    if stress is None:
        raise ValueError(f"no vowel in {spelling!r}")
    starts = _syllable_starts(segs)
    bounds = starts + [len(segs)]
    parts = []
    for start, end in zip(bounds, bounds[1:]):
        mapped = "".join(_map_piece(segs[i]) for i in range(start, end))
        if start <= stress < end:
            mapped = "ˈ" + mapped
        parts.append(mapped)
    return "".join(parts)


def _syllable_starts(segs):
    """Index of the first segment of each syllable.

    Consonants before the first vowel open it. Between vowels, the last
    consonant opens the next syllable and any earlier consonants close the
    current one. That keeps cirya as kir-ya.
    """
    nuclei = [i for i, seg in enumerate(segs) if seg[0] == "V"]
    starts = []
    for n, idx in enumerate(nuclei):
        if n == 0:
            starts.append(0)
            continue
        between = [j for j in range(nuclei[n - 1] + 1, idx) if segs[j][0] == "C"]
        starts.append(between[-1] if between else idx)
    return starts


def _map_piece(seg):
    piece = seg[1]
    if seg[0] == "V":
        try:
            return VOWELS[piece]
        except KeyError:
            raise ValueError(f"unmapped vowel {piece!r}") from None
    out = []
    for ch in piece:
        try:
            out.append(CONSONANTS[ch])
        except KeyError:
            raise ValueError(f"unmapped consonant {ch!r}") from None
    return "".join(out)


_PHRASE_ENDS = ".?!"


def split_phrases(text: str) -> list[str]:
    """Lines are separate. ``.`` ``?`` and ``!`` stay on the phrase they end."""
    phrases = []
    for line in text.splitlines():
        if not line.strip():
            continue
        start = 0
        for index, char in enumerate(line):
            if char not in _PHRASE_ENDS:
                continue
            phrase = line[start:index + 1].strip()
            if phrase:
                phrases.append(phrase)
            start = index + 1
        leftover = line[start:].strip()
        if leftover:
            phrases.append(leftover)
    return phrases


def text_utterances(text: str) -> list[str]:
    """One Piper string per phrase. Phonetics errors propagate."""
    spoken = []
    for phrase in split_phrases(text):
        try:
            spoken.append(line_utterance(phrase))
        except ValueError as exc:
            if str(exc).startswith("no words"):
                continue
            raise
    if not spoken:
        raise ValueError("nothing to speak")
    return spoken


def subtitle(text: str) -> str:
    """One line per utterance, or the error from ``text_utterances``."""
    try:
        utterances = text_utterances(text)
    except ValueError as exc:
        return str(exc)
    return "\n".join(utterance[2:-2].replace(" ", " · ") for utterance in utterances)
