import tkinter as tk
import math

from tkinter import ttk
from simulation import run_trial, TrialResult
from animation_controller import AnimationController

COLOR_PENDING = "#e9ecef"              # not yet revealed
COLOR_OBSERVATION = "#f4a261"          # rejected during the "learning" phase
COLOR_REJECTED_SELECTION = "#aeb4fa"  # rejected during selection (not better than best seen)
COLOR_HIRED = "#2a9d8f"                # hired!
COLOR_PASSED = "#cdd5ed"               # revealed after someone was already hired
COLOR_BOUNDARY_LINE = "#e63946"        # marks where the reject phase ends
COLOR_STAR = "#e9c46a"                 # "best so far" indicator

BOX_HEIGHT = 90
BOX_GAP = 4
POSITION_LABEL_OFFSET = 16
CANVAS_HEIGHT = 160
CANVAS_MIN_WIDTH = 600

class PlayTab(ttk.Frame):
    """ A single-trial, animated view of the secretary problem strategy """

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self._trial: TrialResult | None = None
        self._box_ids: list[tuple[int, int, int]] = []  # (rect_id, text_id, star_id) per position

        self._n = tk.IntVar(value=20)
        self._k = tk.IntVar(value=7)
        self._near_optimal_top_m = tk.IntVar(value=max(1, math.ceil(self._n.get() / 10)))

        self._speed_ms = tk.IntVar(value=500)
        self._result_text = tk.StringVar(value="Press Play to run a trial.")

        self._build_controls()
        self._build_canvas()
        self._build_legend()
        self._build_result_label()

        self._controller = AnimationController(
            widget=self,
            on_step=self._on_step,
            on_complete=self._on_complete,
            step_delay_ms=self._speed_ms.get(),
        )

        self._n.trace_add("write", self._clamp_k_to_n) # Keep k within [0, n] whenever n changes
        self._n.trace_add("write", self._clamp_m_to_n) # Keep near_optimal_top_m at "top 10% of n"

    # Widget construction
    def _build_controls(self):
        controls = ttk.Frame(self)
        controls.pack(side="top", fill="x", padx=10, pady=(10, 5))

        ttk.Label(controls, text="Number of candidates (n):").grid(row=0, column=0, sticky="w")
        self._n_spin = ttk.Spinbox(controls, from_=2, to=50, textvariable=self._n, width=6)
        self._n_spin.grid(row=0, column=1, padx=(4, 20))

        ttk.Label(controls, text="Reject first (k):").grid(row=0, column=2, sticky="w")
        self._k_spin = ttk.Spinbox(controls, from_=0, to=50, textvariable=self._k, width=6)
        self._k_spin.grid(row=0, column=3, padx=(4, 20))

        ttk.Label(controls, text="Speed:").grid(row=0, column=4, sticky="w")
        speed_scale = ttk.Scale(
            controls, from_=1000, to=50, variable=self._speed_ms,
            orient="horizontal", length=120, command=self._on_speed_change,
        )
        speed_scale.grid(row=0, column=5, padx=(4, 20))

        self._play_button = ttk.Button(controls, text="\u25b6 Play", command=self._on_play_clicked)
        self._play_button.grid(row=0, column=6, padx=(0, 6))

        self._pause_button = ttk.Button(
            controls, text="\u23f8 Pause", command=self._on_pause_clicked, state="disabled"
        )
        self._pause_button.grid(row=0, column=7, padx=(0, 6))

        self._reset_button = ttk.Button(controls, text="\u27f2 Reset", command=self._on_reset_clicked)
        self._reset_button.grid(row=0, column=8)

    def _build_canvas(self):
        self._canvas = tk.Canvas(
            self, height=CANVAS_HEIGHT, background="white",
            highlightthickness=1, highlightbackground="#ccc",
        )
        self._canvas.pack(side="top", fill="x", padx=10, pady=5)

    def _build_legend(self):
        legend = ttk.Frame(self)
        legend.pack(side="top", fill="x", padx=10)
 
        items = [
            (COLOR_OBSERVATION, "Observed & rejected (learning phase)", None),
            (COLOR_STAR, "Best seen so far", "\u2605"),
            (COLOR_REJECTED_SELECTION, "Rejected (not better than best seen)", None),
            (COLOR_HIRED, "Hired!", None),
            (COLOR_PASSED, "Seen after hire (too late)", None),
        ]

        for color, label, symbol in items:
            swatch = tk.Canvas(legend, width=14, height=14, highlightthickness=1, highlightbackground="#999")
            if symbol:
                swatch.create_text(7, 7, text=symbol, fill=color, font=("Segoe UI", 10, "bold"))
            else:
                swatch.create_rectangle(1, 1, 13, 13, fill=color, outline="")
            swatch.pack(side="left", padx=(0, 4))
            ttk.Label(legend, text=label).pack(side="left", padx=(0, 16))

    def _build_result_label(self):
        result_frame = ttk.Frame(self)
        result_frame.pack(side="top", fill="x", padx=10, pady=(8, 10))
        ttk.Label(
            result_frame, textvariable=self._result_text, font=("Segoe UI", 11, "bold")
        ).pack(side="left")

    # Control callbacks
    def _clamp_k_to_n(self, *_args):
        try:
            n = self._n.get()
        except tk.TclError:
            return  # user is mid-edit (e.g. field temporarily empty)
        self._k_spin.configure(to=n)
        if self._k.get() > n:
            self._k.set(n)

    def _clamp_m_to_n(self, *_args):
        try:
            n = self._n.get()
        except tk.TclError:
            return
        self._near_optimal_top_m.set(min(n, max(1, math.ceil(n / 10))))

    def _on_speed_change(self, value):
        try:
            delay = int(float(value))
        except ValueError:
            return
        self._controller.set_speed(delay)

    def _on_play_clicked(self):
        # Every Play press runs a brand-new trial from the top.
        try:
            n = self._n.get()
            k = self._k.get()
        except tk.TclError:
            return  # a field is empty/invalid — ignore the click

        trial = run_trial(n, k, mode="rank", near_optimal_top_m=self._near_optimal_top_m.get())
        self._trial = trial

        self._prepare_canvas(n, k)
        self._result_text.set("Running...")

        self._controller.set_speed(int(self._speed_ms.get()))
        self._controller.load_trial(trial)
        self._controller.play()

        self._play_button.configure(state="disabled")
        self._pause_button.configure(state="normal", text="\u23f8 Pause")

    def _on_pause_clicked(self):
        if self._controller.is_playing:
            self._controller.pause()
            self._pause_button.configure(text="\u25b6 Resume")
        else:
            self._controller.play()
            self._pause_button.configure(text="\u23f8 Pause")

    def _on_reset_clicked(self):
        self._controller.stop()
        self._trial = None
        self._canvas.delete("all")
        self._box_ids = []
        self._result_text.set("Press Play to run a trial.")
        self._play_button.configure(state="normal")
        self._pause_button.configure(state="disabled", text="\u23f8 Pause")

    # Canvas drawing
    def _prepare_canvas(self, n, k):
        self._canvas.delete("all")
        self._box_ids = []

        canvas_width = max(self._canvas.winfo_width(), CANVAS_MIN_WIDTH)
        usable_width = canvas_width - 20
        box_width = max((usable_width - (n - 1) * BOX_GAP) / n, 4)

        top = 30
        bottom = top + BOX_HEIGHT

        # Mark where the "automatically reject" phase ends, if applicable.
        if 0 < k < n:
            boundary_x = 10 + k * (box_width + BOX_GAP) - BOX_GAP / 2
            self._canvas.create_line(
                boundary_x, 10, boundary_x, bottom + 10,
                fill=COLOR_BOUNDARY_LINE, dash=(4, 2), width=2,
            )
            self._canvas.create_text(
                boundary_x, 10, text="reject zone ends", anchor="sw",
                fill=COLOR_BOUNDARY_LINE, font=("Segoe UI", 8),
            )

        for i in range(n):
            x0 = 10 + i * (box_width + BOX_GAP)
            x1 = x0 + box_width
            rect_id = self._canvas.create_rectangle(x0, top, x1, bottom, fill=COLOR_PENDING, outline="#999")
            text_id = self._canvas.create_text((x0 + x1) / 2, (top + bottom) / 2, text="", font=("Segoe UI", 9))
            star_id = self._canvas.create_text(
                (x0 + x1) / 2, top - 10, text="", fill=COLOR_STAR, font=("Segoe UI", 11, "bold")
            )
            self._canvas.create_text(
                (x0 + x1) / 2, bottom + POSITION_LABEL_OFFSET,
                text=str(i + 1), fill="#666", font=("Segoe UI", 8),
            )
            self._box_ids.append((rect_id, text_id, star_id))

    def _on_step(self, event, index, total):
        rect_id, text_id, star_id = self._box_ids[index]

        color_map = {
            ("observation", "rejected"): COLOR_OBSERVATION,
            ("selection", "rejected"): COLOR_REJECTED_SELECTION,
            ("selection", "hired"): COLOR_HIRED,
            ("selection", "passed"): COLOR_PASSED,
        }
        color = color_map.get((event.phase, event.decision), COLOR_PENDING)

        self._canvas.itemconfigure(rect_id, fill=color)
        self._canvas.itemconfigure(text_id, text=str(int(event.value)))

        if event.is_best_so_far and event.decision != "passed":
            self._canvas.itemconfigure(star_id, text="\u2605")

    def _on_complete(self, trial: TrialResult):
        self._play_button.configure(state="normal")
        self._pause_button.configure(state="disabled", text="\u23f8 Pause")

        if trial.hired_value is None:
            self._result_text.set(
                f"No hire! The best candidate (rank {trial.n}) appeared during the reject phase."
            )
            return

        if trial.is_best_possible:
            outcome = "Best possible candidate!"
        elif trial.is_near_optimal:
            outcome = "Near-optimal pick."
        else:
            outcome = "Not the best, but still hired someone."

        self._result_text.set(
            f"Hired the candidate at position {trial.hired_position} "
            f"(rank {trial.hired_rank_position} of {trial.n}). {outcome}"
        )