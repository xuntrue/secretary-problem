import math
import tkinter as tk

from tkinter import ttk
from simulation import run_trial, run_batch, find_best_k, TrialResult

from ui_play_tab import PlayTab
from animation_controller import AnimationController

def run_simulation():
    mode = "rank"
    near_optimal_top_m = 3

    n = 20
    k = 7
    num_trials=5_000

    print(f"MODE: {mode}\n")
    print(f"Single trial (n={n}, k={k}):")
    trial = run_trial(n, k, mode=mode, seed=26, near_optimal_top_m=near_optimal_top_m)
    for event in trial.history:
        print(f"  Position {event.position:2d}: rank={event.rank_position:3d} "
              f"phase={event.phase} decision={event.decision}")
    print(f"Hired rank: {trial.hired_rank_position}")
    print(f"Best possible: {n} -> Success: {trial.is_best_possible}")
    print()

    print(f"Batch of {num_trials} trials (n={n}, k={k}):")
    batch = run_batch(n, k, mode=mode, num_trials=num_trials, seed=1, near_optimal_top_m=near_optimal_top_m)
    print(f"  Success rate (hired #1 best): {batch['success_rate']:.3f}")
    print(f"  Near-optimal rate (hired top {near_optimal_top_m}):  {batch['near_optimal_rate']:.3f}")
    if mode == "score":
        print(f"  Mean hired score:                 {batch['mean_hired_value']:.2f}")
        print(f"  Mean best possible score:         {batch['mean_best_possible_value']:.2f}")
    print(f"  No-hire rate:                     {batch['no_hire_rate']:.3f}")
    print(f"  Mean hired rank position:         {batch['mean_hired_rank_position']:.2f} (out of {n})")
    print()

    print(f"Sweeping all k values for n={n}, batch_size={num_trials}:")
    sweep = find_best_k(n, mode=mode, num_trials=num_trials, seed=2, near_optimal_top_m=near_optimal_top_m)
    for r in sweep["results"]:
        print(
            f"  k={r['k']:2d} -> success_rate={r['success_rate']:.3f}  "
            f"near_optimal_rate={r['near_optimal_rate']:.3f}  "
            f"mean_hired_score={r['mean_hired_value']:.1f}" if r['mean_hired_value'] is not None
            else f"  k={r['k']:2d} -> success_rate={r['success_rate']:.3f} (no hires)"
        )
    print(f"Theoretical best k: {math.floor(n / math.e)}")
    print(f"Best k: {sweep['best_k']} (success rate: {sweep['best_success_rate']:.4f})")
    print()

    print(f"Theoretical optimal k/n ratio: 1/e ≈ {1/math.e:.4f}")
    print(f"Achieved optimal k/n ratio  : {sweep['best_k']}/{n} = {sweep['best_k']/n}")

def main():
    root = tk.Tk()
    root.title("Secretary Problem simulator")
    root.geometry("900x350")
    root.minsize(700, 400)

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=8, pady=8)

    play_tab = PlayTab(notebook)
    notebook.add(play_tab, text="Run trial")

    root.mainloop()

if __name__ == "__main__":
    main()