import tkinter as tk
import math

from tkinter import ttk
from simulation import run_trial, TrialResult
from animation_controller import AnimationController

COLOR_PENDING = "#e9ecef"
COLOR_OBSERVATION = "#f4a261"        
COLOR_REJECTED_SELECTION = "#aeb4fa"
COLOR_HIRED = "#2a9d8f"
COLOR_PASSED = "#cdd5ed"
COLOR_BOUNDARY_LINE = "#e63946"
COLOR_STAR = "#e9c46a"  
COLOR_BASELINE = "#999999"
GAUSSIAN_MEAN = 50.0
GAUSSIAN_STD = 15.0
DISTRIBUTION_DISPLAY_TO_INTERNAL = {
    "Gaussian (bell curve)": "normal",
    "Uniform (equally likely)": "uniform",
}

BOX_GAP = 4
POSITION_LABEL_OFFSET = 16
VALUE_LABEL_GAP = 10       
STAR_LABEL_GAP = 24    
BAR_MIN_HEIGHT = 14 
BAR_MAX_HEIGHT = 140     # tallest a bar is ever drawn, for the highest score in the trial
PENDING_BAR_HEIGHT = 6   # tiny placeholder height before a candidate is revealed
BASELINE_MARGIN_BOTTOM = 40 
CANVAS_HEIGHT = 220      # taller than the rank-mode tab to fit bar growth + labels above
CANVAS_MIN_WIDTH = 600

class PlayTabScore(ttk.Frame):
    """ A single-trial, animated bar-chart view of the secretary problem in score mode """

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self._trial: TrialResult | None = None
        self._box_ids: list[tuple[int, int, int]] = []   # (rect_id, text_id, star_id) per position
        self._bar_x_ranges: list[tuple[float, float]] = []  # (x0, x1) per position — fixed once drawn
        self._baseline_y: float = 0.0
        self._value_min: float = 0.0
        self._value_max: float = 1.0

        self._n = tk.IntVar(value=20)
        self._k = tk.IntVar(value=7)
        self._near_optimal_top_m = tk.IntVar(value=max(1, math.ceil(self._n.get() / 10)))
        self._score_distribution_display = tk.StringVar(value="Gaussian (bell curve)")

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

        self._n.trace_add("write", self._clamp_k_to_n)  # Keep k within [0, n] whenever n changes
        self._n.trace_add("write", self._clamp_m_to_n)  # Keep near_optimal_top_m at "top 10% of n"

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

        self._pause_button = ttk.Button(controls, text="\u23f8 Pause", command=self._on_pause_clicked, state="disabled" )
        self._pause_button.grid(row=0, column=7, padx=(0, 6))

        self._reset_button = ttk.Button(controls, text="\u27f2 Reset", command=self._on_reset_clicked)
        self._reset_button.grid(row=0, column=8)

        # Second row: distribution choice, specific to score mode. The
        # user picks a shape, not raw parameters — mean/std (or the
        # uniform range) are fixed constants, kept simple on purpose.
        score_controls = ttk.Frame(self)
        score_controls.pack(side="top", fill="x", padx=10, pady=(0, 5))

        ttk.Label(score_controls, text="Score distribution:").grid(row=0, column=0, sticky="w")
        distribution_combo = ttk.Combobox(
            score_controls, textvariable=self._score_distribution_display,
            values=list(DISTRIBUTION_DISPLAY_TO_INTERNAL.keys()),
            state="readonly", width=22,
        )
        distribution_combo.grid(row=0, column=1, padx=(4, 20))

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
        ttk.Label(result_frame, textvariable=self._result_text, font=("Segoe UI", 11, "bold")).pack(side="left")

    # Control callbacks
    def _clamp_k_to_n(self, *_args):
        try:
            n = self._n.get()
        except tk.TclError:
            return
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
        try:
            n = self._n.get()
            k = self._k.get()
        except tk.TclError:
            return

        distribution = DISTRIBUTION_DISPLAY_TO_INTERNAL[self._score_distribution_display.get()]

        trial = run_trial(
            n, k, mode="score", near_optimal_top_m=self._near_optimal_top_m.get(),
            score_distribution=distribution, score_mean=GAUSSIAN_MEAN, score_std=GAUSSIAN_STD,
            score_round_decimals=1,
        )
        self._trial = trial

        # Peek at the full set of scores up front (already generated, just
        # not yet revealed) purely to fix the bar-height scale for this
        # trial — this does NOT display any scores early.
        values = [event.value for event in trial.history]
        self._value_min = min(values)
        self._value_max = max(values)

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
        self._bar_x_ranges = []
        self._result_text.set("Press Play to run a trial.")
        self._play_button.configure(state="normal")
        self._pause_button.configure(state="disabled", text="\u23f8 Pause")

    # Canvas drawing
    def _value_to_height(self, value: float) -> float:
        """Map a raw score to a bar height in pixels, scaled to this trial's own min/max."""
        if self._value_max == self._value_min:
            return BAR_MIN_HEIGHT
        fraction = (value - self._value_min) / (self._value_max - self._value_min)
        return BAR_MIN_HEIGHT + fraction * (BAR_MAX_HEIGHT - BAR_MIN_HEIGHT)

    def _prepare_canvas(self, n, k):
        self._canvas.delete("all")
        self._box_ids = []
        self._bar_x_ranges = []

        canvas_width = max(self._canvas.winfo_width(), CANVAS_MIN_WIDTH)
        usable_width = canvas_width - 20
        box_width = max((usable_width - (n - 1) * BOX_GAP) / n, 4)

        self._baseline_y = CANVAS_HEIGHT - BASELINE_MARGIN_BOTTOM

        # The bar chart's baseline ("x-axis")
        self._canvas.create_line(10, self._baseline_y, 10 + usable_width, self._baseline_y, fill=COLOR_BASELINE)

        # Mark where "reject" phase ends
        if 0 < k < n:
            boundary_x = 10 + k * (box_width + BOX_GAP) - BOX_GAP / 2
            self._canvas.create_line(
                boundary_x, 10, boundary_x, self._baseline_y + 10,
                fill=COLOR_BOUNDARY_LINE, dash=(4, 2), width=2,
            )
            self._canvas.create_text(
                boundary_x, 10, text="reject zone ends", anchor="sw",
                fill=COLOR_BOUNDARY_LINE, font=("Segoe UI", 8),
            )

        for i in range(n):
            x0 = 10 + i * (box_width + BOX_GAP)
            x1 = x0 + box_width
            self._bar_x_ranges.append((x0, x1))

            # Drawn as a short, pending-colored placeholder bar
            rect_id = self._canvas.create_rectangle(
                x0, self._baseline_y - PENDING_BAR_HEIGHT, x1, self._baseline_y,
                fill=COLOR_PENDING, outline="#999",
            )
            text_id = self._canvas.create_text(
                (x0 + x1) / 2, self._baseline_y - PENDING_BAR_HEIGHT - VALUE_LABEL_GAP,
                text="", font=("Segoe UI", 9),
            )
            star_id = self._canvas.create_text(
                (x0 + x1) / 2, self._baseline_y - PENDING_BAR_HEIGHT - STAR_LABEL_GAP,
                text="", fill=COLOR_STAR, font=("Segoe UI", 11, "bold"),
            )
            self._canvas.create_text(
                (x0 + x1) / 2, self._baseline_y + POSITION_LABEL_OFFSET,
                text=str(i + 1), fill="#666", font=("Segoe UI", 8),
            )
            self._box_ids.append((rect_id, text_id, star_id))

    def _on_step(self, event, index, total):
        rect_id, text_id, star_id = self._box_ids[index]
        x0, x1 = self._bar_x_ranges[index]

        color_map = {
            ("observation", "rejected"): COLOR_OBSERVATION,
            ("selection", "rejected"): COLOR_REJECTED_SELECTION,
            ("selection", "hired"): COLOR_HIRED,
            ("selection", "passed"): COLOR_PASSED,
        }
        color = color_map.get((event.phase, event.decision), COLOR_PENDING)

        height = self._value_to_height(event.value)
        top_y = self._baseline_y - height

        self._canvas.coords(rect_id, x0, top_y, x1, self._baseline_y)
        self._canvas.itemconfigure(rect_id, fill=color)

        self._canvas.coords(text_id, (x0 + x1) / 2, top_y - VALUE_LABEL_GAP)
        self._canvas.itemconfigure(text_id, text=f"{event.value:.1f}")

        if event.is_best_so_far and event.decision != "passed":
            self._canvas.coords(star_id, (x0 + x1) / 2, top_y - STAR_LABEL_GAP)
            self._canvas.itemconfigure(star_id, text="\u2605")

    def _on_complete(self, trial: TrialResult):
        self._play_button.configure(state="normal")
        self._pause_button.configure(state="disabled", text="\u23f8 Pause")

        if trial.hired_value is None:
            self._result_text.set(
                f"No hire! The best score ({self._value_max:.1f}) appeared during the reject phase."
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
            f"(score {trial.hired_value:.1f}, rank #{(trial.n + 1) - trial.hired_rank_position} of {trial.n}). {outcome}"
        )