import unittest
import random as _rand
from hangman import HangmanEngine, MASK_CHAR 

WORDS = ["HANGMAN", "SELECT", "BUTTON", "TESTING"]
PHRASES = ["UNIT TESTS", "OPEN SOURCE"]


class TestHangmanSingle(unittest.TestCase):
    def setUp(self):
        self._seed = _rand.Random(1234)

    def test_start_basic(self):
        game = HangmanEngine(WORDS, PHRASES, lives=3, rng=self._seed)
        snap = game.start("basic")
        self.assertEqual(snap.lives, 3)
        self.assertTrue(all(ch.isalpha() or ch == " " for ch in snap.answer))

    def test_start_intermediate(self):
        game = HangmanEngine(WORDS, PHRASES, lives=5, rng=self._seed)
        snap = game.start("intermediate")
        self.assertEqual(snap.lives, 5)
        self.assertIn(" ", snap.answer)

    def test_wrong_guesses_lose(self):
        game = HangmanEngine(["A"], ["B C"], lives=2, rng=self._seed)
        game.start("basic")
        game.guess("Z"); snap = game.guess("Y")
        self.assertTrue(snap.is_lost)

    def test_repeat_no_penalty(self):
        game = HangmanEngine(["ABC"], ["X Y"], lives=3, rng=self._seed)
        game.start("basic")
        game.guess("Z")
        snap = game.guess("Z")
        self.assertEqual(snap.lives, 2)

    def test_invalid_guess_ignored(self):
        game = HangmanEngine(["ABC"], ["X Y"], lives=3, rng=self._seed)
        game.start("basic")
        before = game.state.lives
        game.guess("1")
        self.assertEqual(before, game.state.lives)

    def test_correct_flow_win(self):
        game = HangmanEngine(["ABC"], ["X Y"], lives=6, rng=self._seed)
        game.start("basic")
        game.guess("A"); game.guess("B"); snap = game.guess("C")
        self.assertTrue(snap.is_won)
        self.assertFalse(snap.is_lost)

    def test_timeout_deducts_life(self):
        game = HangmanEngine(["ABC"], ["X Y"], lives=2, rng=self._seed)
        game.start("basic")
        snap = game.timeout()
        self.assertEqual(snap.lives, 1)

    def test_masking_and_reveal(self):
        game = HangmanEngine(["ABA"], ["X Y"], lives=3, rng=self._seed)
        game.start("basic")
        self.assertEqual(game.state.masked.replace(" ",""), MASK_CHAR*3)
        game.guess("A")
        self.assertIn("A", game.state.masked) 
        self.assertNotIn("B", game.state.masked.replace(" ", " "))

    def test_case_insensitive_guess(self):
        game = HangmanEngine(["DOG"], ["BIG CAT"], lives=3, rng=self._seed)
        game.start("basic")
        game.guess("d")
        game.guess("o")
        snap = game.guess("G")
        self.assertTrue(snap.is_won)

    def test_phrase_whitespace_preserved(self):
        game = HangmanEngine(["DOG"], ["BIG CAT"], lives=3, rng=self._seed)
        snap = game.start("intermediate")
        self.assertIn(" ", snap.answer)
        self.assertIn(" ", snap.masked)

    def test_guess_before_start_raises(self):
        game = HangmanEngine(["DOG"], ["BIG CAT"], lives=3, rng=self._seed)
        with self.assertRaises(RuntimeError):
            game.guess("D")

    def test_timeout_before_start_raises(self):
        game = HangmanEngine(["DOG"], ["BIG CAT"], lives=3, rng=self._seed)
        with self.assertRaises(RuntimeError):
            game.timeout()

    def test_multiple_wrong_guesses_reduce_lives(self):
        game = HangmanEngine(["DOG"], ["BIG CAT"], lives=4, rng=self._seed)
        game.start("basic")
        game.guess("X")
        game.guess("Y")
        snap = game.guess("Z")
        self.assertEqual(snap.lives, 1)

    def test_win_on_last_life(self):
        game = HangmanEngine(["DOG"], ["BIG CAT"], lives=2, rng=self._seed)
        game.start("basic")
        game.guess("X")
        game.guess("D")
        game.guess("O")
        snap = game.guess("G")
        self.assertTrue(snap.is_won)
        self.assertEqual(snap.lives, 1)

if __name__ == "__main__":
    unittest.main(verbosity=2)
