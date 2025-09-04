from __future__ import annotations
import string
import threading
import queue as _queue_mod
import time as _time_mod
import random as _random_mod
from dataclasses import dataclass, field
from typing import Iterable, Optional, Set

# Engine (UI-agnostic)
MASK_CHAR = "_"  # underscore for hidden letters  (kept name for compatibility)


def _normalize_answer(text_input: str) -> str:
    src = (text_input or "").upper()
    return "".join(ch for ch in src if ch in string.ascii_uppercase + " ").strip()


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
    def __init__(self, words: Iterable[str], phrases: Iterable[str], lives: int = 6, rng: Optional[_random_mod.Random] = None):
        self._prng = rng or _random_mod.Random()
        self._lexicon = [w.strip() for w in words if w and w.strip()]
        self._idioms = [p.strip() for p in phrases if p and p.strip()]
        if not self._lexicon:
            raise ValueError("words must not be empty")
        if not self._idioms:
            raise ValueError("phrases must not be empty")
        self._life_pool = lives
        self._game_state: Optional[HangmanState] = None

    def start(self, difficulty: str = "basic") -> HangmanState:
        if difficulty not in {"basic", "intermediate"}:
            raise ValueError("difficulty must be 'basic' or 'intermediate'")
        chosen_raw = self._prng.choice(self._lexicon if difficulty == "basic" else self._idioms)
        self._game_state = HangmanState(answer=_normalize_answer(chosen_raw), lives=self._life_pool, guessed=set())
        return self.state

    @property
    def state(self) -> HangmanState:
        if self._game_state is None:
            raise RuntimeError("game not started")
        return self._game_state

    def guess(self, letter: str) -> HangmanState:
        if self._game_state is None:
            raise RuntimeError("game not started")
        token = (letter or "").strip().upper()
        if len(token) != 1 or token not in string.ascii_uppercase:
            return self._game_state  # ignore invalid guesses
        if token in self._game_state.guessed:
            return self._game_state  # no penalty for repeats
        new_guessed = set(self._game_state.guessed)
        new_guessed.add(token)
        remaining_lives = self._game_state.lives - (0 if token in self._game_state.answer else 1)
        self._game_state = HangmanState(answer=self._game_state.answer, lives=remaining_lives, guessed=new_guessed)
        return self._game_state

    def timeout(self) -> HangmanState:
        if self._game_state is None:
            raise RuntimeError("game not started")
        self._game_state = HangmanState(answer=self._game_state.answer, lives=self._game_state.lives - 1, guessed=set(self._game_state.guessed))
        return self._game_state


# Data (kept identifiers but content is irrelevant for variable renaming)
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
        from tkinter import messagebox as _mbox
    except Exception as gui_exc:
        print("GUI unavailable:", gui_exc)
        raise

    core = HangmanEngine(WORDS, PHRASES, lives=6)

    app = tk.Tk()
    app.title("Hangman - TDD UI")
    app.geometry("820x520")
    app.resizable(False, False)

    level_mode = tk.StringVar(value="basic")
    ui_lives = tk.StringVar(value="-")
    ui_wrong = tk.StringVar(value="-")
    ui_time = tk.StringVar(value="15s")
    ui_masked = tk.StringVar(value="— — — — —")
    ui_status = tk.StringVar(value="Click 'Start / New Round' to begin.")

    # after-based timer 
    tick_box = {"value": 15}
    tick_handle = {"id": None}  # after() job id

    alpha_btns: dict[str, tk.Button] = {}

    def count_misses(st: HangmanState) -> int:
        return sum(1 for g in st.guessed if g not in st.answer)

    def set_alpha_state(state: str):
        for b in alpha_btns.values():
            b.config(state=state)

    def reset_alpha():
        for _ch, btn in alpha_btns.items():
            btn.config(state="normal")

    def halt_timer():
        if tick_handle["id"] is not None:
            try:
                app.after_cancel(tick_handle["id"])
            except Exception:
                pass
            tick_handle["id"] = None

    def on_tick():
        sec_now = tick_box["value"] - 1
        tick_box["value"] = sec_now
        ui_time.set(f"{sec_now}s")
        if sec_now <= 0:
            core.timeout()
            refresh_view()
            if not core.state.is_won and not core.state.is_lost:
                reset_timer()
            else:
                halt_timer()
        else:
            tick_handle["id"] = app.after(1000, on_tick)

    def reset_timer():
        halt_timer()
        tick_box["value"] = 15
        ui_time.set("15s")
        tick_handle["id"] = app.after(1000, on_tick)
    # ---------------------------------------------

    def begin_round():
        core.start(level_mode.get())
        reset_alpha()
        field_entry.delete(0, tk.END)
        reset_timer()
        refresh_view(initial=True)

    def end_round(msg: str, title: str):
        halt_timer()
        set_alpha_state("disabled")
        _mbox.showinfo(title, msg)

    def refresh_view(initial: bool = False):
        snap = core.state
        ui_masked.set(snap.masked)
        ui_lives.set(str(snap.lives))
        ui_wrong.set(str(count_misses(snap)))
        for ch in string.ascii_uppercase:
            if ch in snap.guessed:
                alpha_btns[ch].config(state="disabled")
        if snap.is_won:
            ui_status.set("You won! 🎉")
            end_round("Great job! You guessed the word/phrase.", "You won!")
        elif snap.is_lost:
            ui_status.set(f"Out of lives. Answer: {snap.answer}")
            end_round(f"You ran out of lives.\nAnswer: {snap.answer}", "Game over")
        else:
            if initial:
                ui_status.set("Round started. Enter a letter or click a button.")

    def make_guess(letter: str):
        core.guess(letter)
        refresh_view()
        if not core.state.is_won and not core.state.is_lost:
            reset_timer()  # reset to 15s on valid guess

    def handle_guess_click(ch: str):
        btn = alpha_btns.get(ch)
        if btn and btn["state"] == "normal":
            btn.config(state="disabled")
            make_guess(ch)

    def submit_from_field(_evt=None):
        # If round hasn't started, ignore
        try:
            _ = core.state
        except RuntimeError:
            ui_status.set("Click 'Start / New Round' to begin.")
            field_entry.delete(0, tk.END)
            return

        raw_val = field_entry.get().strip()
        field_entry.delete(0, tk.END)

        token = raw_val[:1].upper() if raw_val else ""
        if len(token) != 1 or token not in string.ascii_uppercase:
            ui_status.set("Enter a single letter A–Z.")
            return

        btn = alpha_btns.get(token)
        if btn is None or btn["state"] != "normal":
            ui_status.set("That letter is already used.")
            return

        btn.config(state="disabled")
        make_guess(token)

    # -------- layout --------
    hdr = tk.Frame(app, pady=8); hdr.pack(fill=tk.X)
    tk.Label(hdr, text="Hangman", font=("Segoe UI", 24, "bold")).pack()

    ctl = tk.Frame(app, pady=6); ctl.pack(fill=tk.X)
    tk.Label(ctl, text="Choose level:", font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=(12, 6))
    tk.Radiobutton(ctl, text="Basic (Word)", value="basic", variable=level_mode).pack(side=tk.LEFT)
    tk.Radiobutton(ctl, text="Intermediate (Phrase)", value="intermediate", variable=level_mode).pack(side=tk.LEFT, padx=(8, 0))
    tk.Button(ctl, text="Start / New Round", command=begin_round).pack(side=tk.LEFT, padx=12)
    tk.Button(ctl, text="Quit", command=app.destroy).pack(side=tk.LEFT)

    stat_row = tk.Frame(app, pady=4); stat_row.pack(fill=tk.X)
    tk.Label(stat_row, text="Lives:", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=(12, 4))
    tk.Label(stat_row, textvariable=ui_lives, font=("Segoe UI", 11)).pack(side=tk.LEFT)
    tk.Label(stat_row, text="   Wrong:", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
    tk.Label(stat_row, textvariable=ui_wrong, font=("Segoe UI", 11)).pack(side=tk.LEFT)
    tk.Label(stat_row, text="   Time:", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
    tk.Label(stat_row, textvariable=ui_time, font=("Segoe UI", 11)).pack(side=tk.LEFT)

    mask_frame = tk.Frame(app, pady=12); mask_frame.pack()
    tk.Label(mask_frame, textvariable=ui_masked, font=("Consolas", 28)).pack()

    guess_row = tk.Frame(app, pady=8); guess_row.pack()
    tk.Label(guess_row, text="Enter a letter:", font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=(0, 6))
    field_entry = tk.Entry(guess_row, width=5, font=("Segoe UI", 14)); field_entry.pack(side=tk.LEFT)
    field_entry.bind("<Return>", submit_from_field)
    tk.Button(guess_row, text="Guess", command=submit_from_field).pack(side=tk.LEFT, padx=8)

    letters_box = tk.LabelFrame(app, text="Letters", padx=8, pady=8)
    letters_box.pack(padx=12, pady=6, fill=tk.X)

    cols = 13
    for i, ch in enumerate(string.ascii_uppercase):
        r, c = divmod(i, cols)
        btn = tk.Button(letters_box, text=ch, width=3, command=lambda x=ch: handle_guess_click(x))
        btn.grid(row=r, column=c, padx=3, pady=4)
        alpha_btns[ch] = btn

    footer = tk.Frame(app, pady=10); footer.pack(fill=tk.X)
    tk.Label(footer, textvariable=ui_status, font=("Segoe UI", 10, "italic")).pack()

    set_alpha_state("disabled")
    app.mainloop()


# CLI fallback with real 15s timeout
def timed_input(prompt: str, timeout: int) -> Optional[str]:
    print(prompt, end="", flush=True)
    pipe: "_queue_mod.Queue[str]" = _queue_mod.Queue()

    def reader_task():
        try:
            line = input()
        except Exception:
            line = ""
        pipe.put(line)

    worker = threading.Thread(target=reader_task, daemon=True)
    worker.start()

    sec_left = timeout
    while sec_left > 0 and worker.is_alive():
        print(f"\rTime left: {sec_left:2d}s   ", end="", flush=True)
        _time_mod.sleep(1)
        sec_left -= 1

    if worker.is_alive():
        print("\n Time's up!")
        return None
    return pipe.get().strip()


def run_cli():
    print("Hangman — Single File (PRT582) [CLI]")
    core = HangmanEngine(WORDS, PHRASES, lives=6)
    mode = (input("Choose difficulty [basic/intermediate]: ").strip().lower() or "basic")
    if mode not in {"basic", "intermediate"}:
        mode = "basic"
    core.start(mode)

    while True:
        snap = core.state
        print(f"\n{snap.masked}\nLives: {snap.lives}  Guessed: {' '.join(sorted(snap.guessed))}")
        if snap.is_won:
            print("Correct! You guessed it.")
            break
        if snap.is_lost:
            print(f"Out of lives. Answer: {snap.answer}")
            break
        shot = timed_input("Enter a letter: ", 15)
        if shot is None:
            core.timeout()
            continue
        core.guess(shot)


if __name__ == "__main__":
    # Try GUI first; fall back to CLI
    try:
        run_gui()
    except Exception as exc:
        print("GUI not available or failed. Falling back to CLI.\nReason:", exc)
        run_cli()
