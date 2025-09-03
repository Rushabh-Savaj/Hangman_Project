import unittest
import random
from hangman import HangmanEngine, MASK_CHAR

WORDS = ["HANGMAN", "SELECT", "BUTTON", "TESTING"]
PHRASES = ["UNIT TESTS", "OPEN SOURCE"]


class TestHangmanSingle(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(1234)

    def test_start_basic(self):
        eng = HangmanEngine(WORDS, PHRASES, lives=3, rng=self.rng)
        st = eng.start("basic")
        self.assertEqual(st.lives, 3)
        self.assertTrue(all(ch.isalpha() or ch == " " for ch in st.answer))

    def test_start_intermediate(self):
        eng = HangmanEngine(WORDS, PHRASES, lives=5, rng=self.rng)
        st = eng.start("intermediate")
        self.assertEqual(st.lives, 5)
        self.assertIn(" ", st.answer)

    def test_wrong_guesses_lose(self):
        eng = HangmanEngine(["A"], ["B C"], lives=2, rng=self.rng)
        eng.start("basic")
        eng.guess("Z"); st = eng.guess("Y")
        self.assertTrue(st.is_lost)

    def test_repeat_no_penalty(self):
        eng = HangmanEngine(["ABC"], ["X Y"], lives=3, rng=self.rng)
        eng.start("basic")
        eng.guess("Z")
        st = eng.guess("Z")
        self.assertEqual(st.lives, 2)

    def test_invalid_guess_ignored(self):
        eng = HangmanEngine(["ABC"], ["X Y"], lives=3, rng=self.rng)
        eng.start("basic")
        before = eng.state.lives
        eng.guess("1")
        self.assertEqual(before, eng.state.lives)

    def test_correct_flow_win(self):
        eng = HangmanEngine(["ABC"], ["X Y"], lives=6, rng=self.rng)
        eng.start("basic")
        eng.guess("A"); eng.guess("B"); st = eng.guess("C")
        self.assertTrue(st.is_won)
        self.assertFalse(st.is_lost)

    def test_timeout_deducts_life(self):
        eng = HangmanEngine(["ABC"], ["X Y"], lives=2, rng=self.rng)
        eng.start("basic")
        st = eng.timeout()
        self.assertEqual(st.lives, 1)

    def test_masking_and_reveal(self):
        eng = HangmanEngine(["ABA"], ["X Y"], lives=3, rng=self.rng)
        eng.start("basic")
        self.assertEqual(eng.state.masked.replace(" ",""), MASK_CHAR*3)
        eng.guess("A")
        self.assertIn("A", eng.state.masked)
        self.assertNotIn("B", eng.state.masked.replace(" ", ""))
    
if __name__ == "__main__":
    unittest.main(verbosity=2)
