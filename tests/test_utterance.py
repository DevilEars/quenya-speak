"""Pinned Quenya utterances, phrase splits, and subtitles."""

import unittest

from quenya_speak.utterance import subtitle, text_utterances, word_utterance

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

SINGLE_WORDS = ("cirya", "Eärendil", "andúnë", "ancalima", "né")


class UtteranceTests(unittest.TestCase):
    def test_table_rows_are_one_utterance(self):
        for text, utterance in ROWS.items():
            with self.subTest(text=text):
                self.assertEqual(text_utterances(text), [utterance])

    def test_single_words_match_word_utterance(self):
        for text in SINGLE_WORDS:
            with self.subTest(text=text):
                self.assertEqual(word_utterance(text), ROWS[text])

    def test_sentence_enders_split_into_two_utterances(self):
        self.assertEqual(
            text_utterances("Elen síla. Aiya Eärendil!"),
            [ROWS["Elen síla."], ROWS["Aiya Eärendil!"]],
        )

    def test_newline_is_a_phrase_boundary(self):
        self.assertEqual(
            text_utterances("aiya Eärendil\nelen síla."),
            ["[[ˈaɪjɑ ɛɑˈɹɛndɪl.]]", "[[ˈɛlɛn ˈsiːlɑ.]]"],
        )

    def test_bare_word_matches_word_with_period(self):
        self.assertEqual(text_utterances("cirya"), text_utterances("cirya."))

    def test_blank_line_separates_phrases(self):
        self.assertEqual(
            text_utterances("cirya\n\nné"),
            [ROWS["cirya"], ROWS["né"]],
        )

    def test_trailing_pause_marks_are_dropped(self):
        expected = ["[[ˈkɪɹjɑ.]]"]
        for text in ("cirya,", "cirya;", "cirya:"):
            with self.subTest(text=text):
                self.assertEqual(text_utterances(text), expected)

    def test_unrecognised_letter_names_the_letter_and_word(self):
        with self.assertRaises(ValueError) as caught:
            text_utterances("anza")
        message = str(caught.exception)
        self.assertIn("unrecognised letter", message)
        self.assertIn("'z'", message)
        self.assertIn("'anza'", message)

    def test_word_with_no_vowel_names_the_spelling(self):
        with self.assertRaises(ValueError) as caught:
            text_utterances("hl")
        message = str(caught.exception)
        self.assertIn("no vowel", message)
        self.assertIn("'hl'", message)

    def test_empty_and_punctuation_only_have_nothing_to_speak(self):
        for text in ("", "..."):
            with self.subTest(text=text):
                with self.assertRaises(ValueError) as caught:
                    text_utterances(text)
                self.assertEqual(str(caught.exception), "nothing to speak")

    def test_subtitle_puts_a_dot_between_words(self):
        self.assertEqual(subtitle("cirya né"), "ˈkɪɹjɑ · ˈnɛː.")

    def test_subtitle_is_one_line_per_phrase(self):
        self.assertEqual(
            subtitle("Elen síla. Aiya Eärendil!"),
            "ˈɛlɛn · ˈsiːlɑ.\nˈaɪjɑ · ɛɑˈɹɛndɪl!",
        )

    def test_subtitle_of_blank_text_is_nothing_to_speak(self):
        self.assertEqual(subtitle(""), "nothing to speak")
        self.assertEqual(subtitle("   "), "nothing to speak")

    def test_subtitle_of_an_error_is_the_message(self):
        message = subtitle("anza")
        self.assertIn("unrecognised letter", message)
        self.assertIn("anza", message)


if __name__ == "__main__":
    unittest.main()
