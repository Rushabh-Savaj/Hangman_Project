from __future__ import annotations
import string
import threading
import queue
import time
import random
from dataclasses import dataclass, field
from typing import Iterable, Optional, Set

# Engine (UI-agnostic)
MASK_CHAR = "_"  # underscore for hidden letters


def _normalize_answer(text: str) -> str:
    text = (text or "").upper()
    return "".join(ch for ch in text if ch in string.ascii_uppercase + " ").strip()


@dataclass
class HangmanState:
    answer: str
    lives: int
    guessed: Set[str] = field(default_factory=set)

    @property
    def masked(self) -> str:
        return " ".join(ch if (ch == " " or ch in self.guessed) else MASK_CHAR for ch in self.answer)

    @property
    def is_won(self) -> bool:
        return all(ch == " " or ch in self.guessed for ch in self.answer)

    @property
    def is_lost(self) -> bool:
        return self.lives <= 0 and not self.is_won


class HangmanEngine:
    def __init__(self, words: Iterable[str], phrases: Iterable[str], lives: int = 6, rng: Optional[random.Random] = None):
        self._rng = rng or random.Random()
        self._words = [w.strip() for w in words if w and w.strip()]
        self._phrases = [p.strip() for p in phrases if p and p.strip()]
        if not self._words:
            raise ValueError("words must not be empty")
        if not self._phrases:
            raise ValueError("phrases must not be empty")
        self._default_lives = lives
        self._state: Optional[HangmanState] = None

    def start(self, difficulty: str = "basic") -> HangmanState:
        if difficulty not in {"basic", "intermediate"}:
            raise ValueError("difficulty must be 'basic' or 'intermediate'")
        raw = self._rng.choice(self._words if difficulty == "basic" else self._phrases)
        self._state = HangmanState(answer=_normalize_answer(raw), lives=self._default_lives, guessed=set())
        return self.state

    @property
    def state(self) -> HangmanState:
        if self._state is None:
            raise RuntimeError("game not started")
        return self._state

    def guess(self, letter: str) -> HangmanState:
        if self._state is None:
            raise RuntimeError("game not started")
        letter = (letter or "").strip().upper()
        if len(letter) != 1 or letter not in string.ascii_uppercase:
            return self._state  # ignore invalid guesses
        if letter in self._state.guessed:
            return self._state  # no penalty for repeats
        guessed = set(self._state.guessed)
        guessed.add(letter)
        new_lives = self._state.lives - (0 if letter in self._state.answer else 1)
        self._state = HangmanState(answer=self._state.answer, lives=new_lives, guessed=guessed)
        return self._state

    def timeout(self) -> HangmanState:
        if self._state is None:
            raise RuntimeError("game not started")
        self._state = HangmanState(answer=self._state.answer, lives=self._state.lives - 1, guessed=set(self._state.guessed))
        return self._state


# Data
WORDS = [
    "python","hangman","algorithm","function","variable","object","module","package","notebook","testing",
    "class","method","loop","array","string","integer","float","boolean","operator","syntax","compile",
    "debug","version","control","commit","branch","merge","server","client","socket","thread","process",
    "binary","search","linked","list","stack","queue","graph","tree","hash","table","sort","insert",
    "update","delete","select","query","database","schema","index","cursor","commit","rollback","engine",
    "exception","handler","context","manager","package","import","export","virtual","environment",
    "user","interface","event","timer","window","frame","button","label","entry","canvas",
]

PHRASES = [
    "unit tests","software quality","hangman game","data migration","code review",
    "continuous integration","version control","clean code","test driven development",
    "graphical user interface","project management","bug triage","error handling",
    "static analysis","team collaboration","state machine","event loop","public interface",
    "separation of concerns"
]


# Tkinter GUI 
def run_gui():
    try:
        import tkinter as tk
        from tkinter import messagebox
    except Exception as e:
        print("GUI unavailable:", e)
        raise

    engine = HangmanEngine(WORDS, PHRASES, lives=6)

    root = tk.Tk()
    root.title("Hangman - TDD UI")
    root.geometry("820x520")
    root.resizable(False, False)

    difficulty = tk.StringVar(value="basic")
    lives_var = tk.StringVar(value="-")
    wrong_var = tk.StringVar(value="-")
    time_var = tk.StringVar(value="15s")
    masked_var = tk.StringVar(value="— — — — —")
    status_var = tk.StringVar(value="Click 'Start / New Round' to begin.")

    # after-based timer 
    timer_seconds = {"value": 15}
    timer_job = {"id": None}  # after() job id

    letter_buttons: dict[str, tk.Button] = {}

    def wrong_count(st: HangmanState) -> int:
        return sum(1 for g in st.guessed if g not in st.answer)

    def set_all_letter_state(state: str):
        for b in letter_buttons.values():
            b.config(state=state)

    def reset_letters():
        for ch, b in letter_buttons.items():
            b.config(state="normal")

    def stop_timer():
        if timer_job["id"] is not None:
            try:
                root.after_cancel(timer_job["id"])
            except Exception:
                pass
            timer_job["id"] = None

    def tick():
        sec = timer_seconds["value"] - 1
        timer_seconds["value"] = sec
        time_var.set(f"{sec}s")
        if sec <= 0:
            engine.timeout()
            update_view()
            if not engine.state.is_won and not engine.state.is_lost:
                restart_timer()
            else:
                stop_timer()
        else:
            timer_job["id"] = root.after(1000, tick)

    def restart_timer():
        stop_timer()
        timer_seconds["value"] = 15
        time_var.set("15s")
        timer_job["id"] = root.after(1000, tick)
    # ---------------------------------------------

    def start_round():
        engine.start(difficulty.get())
        reset_letters()
        entry.delete(0, tk.END)
        restart_timer()
        update_view(initial=True)

    def finish_round(msg: str, title: str):
        stop_timer()
        set_all_letter_state("disabled")
        messagebox.showinfo(title, msg)

    def update_view(initial: bool = False):
        st = engine.state
        masked_var.set(st.masked)
        lives_var.set(str(st.lives))
        wrong_var.set(str(wrong_count(st)))
        for ch in string.ascii_uppercase:
            if ch in st.guessed:
                letter_buttons[ch].config(state="disabled")
        if st.is_won:
            status_var.set("You won! 🎉")
            finish_round("Great job! You guessed the word/phrase.", "You won!")
        elif st.is_lost:
            status_var.set(f"Out of lives. Answer: {st.answer}")
            finish_round(f"You ran out of lives.\nAnswer: {st.answer}", "Game over")
        else:
            if initial:
                status_var.set("Round started. Enter a letter or click a button.")

    def apply_guess(letter: str):
        engine.guess(letter)
        update_view()
        if not engine.state.is_won and not engine.state.is_lost:
            restart_timer()  # reset to 15s on valid guess

    def on_guess_click(ch: str):
        btn = letter_buttons.get(ch)
        if btn and btn["state"] == "normal":
            btn.config(state="disabled")
            apply_guess(ch)

    def submit_from_entry(_evt=None):
        # If round hasn't started, ignore
        try:
            _ = engine.state
        except RuntimeError:
            status_var.set("Click 'Start / New Round' to begin.")
            entry.delete(0, tk.END)
            return

        raw = entry.get().strip()
        entry.delete(0, tk.END)

        ch = raw[:1].upper() if raw else ""
        if len(ch) != 1 or ch not in string.ascii_uppercase:
            status_var.set("Enter a single letter A–Z.")
            return

        btn = letter_buttons.get(ch)
        if btn is None or btn["state"] != "normal":
            status_var.set("That letter is already used.")
            return

        btn.config(state="disabled")
        apply_guess(ch)

    # -------- layout --------
    header = tk.Frame(root, pady=8); header.pack(fill=tk.X)
    tk.Label(header, text="Hangman", font=("Segoe UI", 24, "bold")).pack()

    controls = tk.Frame(root, pady=6); controls.pack(fill=tk.X)
    tk.Label(controls, text="Choose level:", font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=(12, 6))
    tk.Radiobutton(controls, text="Basic (Word)", value="basic", variable=difficulty).pack(side=tk.LEFT)
    tk.Radiobutton(controls, text="Intermediate (Phrase)", value="intermediate", variable=difficulty).pack(side=tk.LEFT, padx=(8, 0))
    tk.Button(controls, text="Start / New Round", command=start_round).pack(side=tk.LEFT, padx=12)
    tk.Button(controls, text="Quit", command=root.destroy).pack(side=tk.LEFT)

    status_row = tk.Frame(root, pady=4); status_row.pack(fill=tk.X)
    tk.Label(status_row, text="Lives:", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=(12, 4))
    tk.Label(status_row, textvariable=lives_var, font=("Segoe UI", 11)).pack(side=tk.LEFT)
    tk.Label(status_row, text="   Wrong:", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
    tk.Label(status_row, textvariable=wrong_var, font=("Segoe UI", 11)).pack(side=tk.LEFT)
    tk.Label(status_row, text="   Time:", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
    tk.Label(status_row, textvariable=time_var, font=("Segoe UI", 11)).pack(side=tk.LEFT)

    masked = tk.Frame(root, pady=12); masked.pack()
    tk.Label(masked, textvariable=masked_var, font=("Consolas", 28)).pack()

    guess_row = tk.Frame(root, pady=8); guess_row.pack()
    tk.Label(guess_row, text="Enter a letter:", font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=(0, 6))
    entry = tk.Entry(guess_row, width=5, font=("Segoe UI", 14)); entry.pack(side=tk.LEFT)
    entry.bind("<Return>", submit_from_entry)
    tk.Button(guess_row, text="Guess", command=submit_from_entry).pack(side=tk.LEFT, padx=8)

    letters_frame = tk.LabelFrame(root, text="Letters", padx=8, pady=8)
    letters_frame.pack(padx=12, pady=6, fill=tk.X)

    cols = 13
    for i, ch in enumerate(string.ascii_uppercase):
        r, c = divmod(i, cols)
        btn = tk.Button(letters_frame, text=ch, width=3, command=lambda x=ch: on_guess_click(x))
        btn.grid(row=r, column=c, padx=3, pady=4)
        letter_buttons[ch] = btn

    footer = tk.Frame(root, pady=10); footer.pack(fill=tk.X)
    tk.Label(footer, textvariable=status_var, font=("Segoe UI", 10, "italic")).pack()

    set_all_letter_state("disabled")
    root.mainloop()


# CLI fallback with real 15s timeout
def timed_input(prompt: str, timeout: int) -> Optional[str]:
    print(prompt, end="", flush=True)
    q: "queue.Queue[str]" = queue.Queue()

    def _reader():
        try:
            line = input()
        except Exception:
            line = ""
        q.put(line)

    t = threading.Thread(target=_reader, daemon=True)
    t.start()

    remaining = timeout
    while remaining > 0 and t.is_alive():
        print(f"\rTime left: {remaining:2d}s   ", end="", flush=True)
        time.sleep(1)
        remaining -= 1

    if t.is_alive():
        print("\n Time's up!")
        return None
    return q.get().strip()


def run_cli():
    print("Hangman — Single File (PRT582) [CLI]")
    engine = HangmanEngine(WORDS, PHRASES, lives=6)
    diff = (input("Choose difficulty [basic/intermediate]: ").strip().lower() or "basic")
    if diff not in {"basic", "intermediate"}:
        diff = "basic"
    engine.start(diff)

    while True:
        st = engine.state
        print(f"\n{st.masked}\nLives: {st.lives}  Guessed: {' '.join(sorted(st.guessed))}")
        if st.is_won:
            print("Correct! You guessed it.")
            break
        if st.is_lost:
            print(f"Out of lives. Answer: {st.answer}")
            break
        guess = timed_input("Enter a letter: ", 15)
        if guess is None:
            engine.timeout()
            continue
        engine.guess(guess)


if __name__ == "__main__":
    # Try GUI first; fall back to CLI
    try:
        run_gui()
    except Exception as exc:
        print("GUI not available or failed. Falling back to CLI.\nReason:", exc)
        run_cli()
