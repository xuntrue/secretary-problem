# The Secretary Problem: An Interactive Exploration

This project visually demonstrates the **Secretary Problem**, a classic decision-theory puzzle.
Originally, I first read about it from 	<ins>Algorithms to Live By: The Computer Science of Human Decisions by Brian Christian & Tom Griffiths</ins>. Highly recommended!
And there's a good reason why this problem is one of the first chapters in the book.

The problem goes: if you're interviewing a sequence of candidates one-by-one and must accept or reject each immediately, how do you maximize your chance of picking the *best* one?
The classic answer — reject the first ~37% (1/e) of candidates outright, then hire the next one who's better than everyone you've seen so far.

## What this project explores

Beyond just proving the 1/e rule, this project also digs into a couple of subtler questions:
- **"Best" isn't the only goal worth measuring.** Hiring the single best candidate isn't the same as hiring a *good* candidate.
  This project tracks both a strict "success rate" (did we hire the actual #1?) and a "near-optimal rate" (did we hire someone in the top slice of the field?).
- **Realistic candidates aren't cleanly ranked.** The classic version of the problem assumes every candidate has a unique rank from 1 to n.
  In real life, candidates can be nearly identical. This project supports a  **score mode**, where candidates get continuous, randomly distributed scores (with ties and near-ties possible).
- **Maximizing your odds of the best hire isn't the same as maximizing your average outcome.**
  Simulation results here show that the value of k that maximizes "chance of hiring the #1 candidate" is *not* the same k that maximizes "expected quality of whoever you hire"
  — rejecting fewer candidates upfront often does better on average, even though it's less likely to land the single best candidate. See `simulation.py`'s `expected_value` / `expected_rank_position` metrics.

## Current status
This project is still a **work in progress**. What's built so far:

- Full simulation engine (`simulation.py`), supporting both rank and score
  modes, near-optimal tracking, and batch statistics.
- An interactive, animated **Play** tab for single trials in both "rank" and "score" mode
- A tabbed desktop application tying both together (`secretary_problem.py`)

TODO:
- An **Analyze** tab for running large batches of trials and visualizing
  success rate / near-optimal rate / expected value across every value of
  k (this is where the "proof" really comes together statistically).

## Project structure
```
SecretaryProblem/
│
├── secretary_problem.py      # Entry point — builds the main window & tabs
├── simulation.py              # Core algorithm: rank & score modes, batch stats
├── animation_controller.py    # Drives the step-by-step animated reveal
├── ui_play_tab.py              # "Play (Rank)" tab — classic 1..n ranked candidates
├── ui_play_tab_score.py        # "Play (Score)" tab — continuous scores, bar-chart view
└── README.md
```

## How to run

Requires **Python 3.10+** and 'Tkinter', which ships with the standard Python installer on Windows/macOS.
No external packages are required — everything here uses only the Python
standard library.

```bash
python secretary_problem.py
```

This opens a window with two tabs:

- **Play (Rank):** set the number of candidates (n) and how many to
  automatically reject before considering a hire (k), then press Play to
  watch a single trial animate.
- **Play (Score):** the same idea, but candidates are drawn from a
  Gaussian or uniform score distribution and rendered as bars whose height
  is proportional to their score.

## The math, briefly

For n candidates interviewed in random order, if you reject the first k
and then hire the first candidate afterward who beats everyone you've
seen, the probability of hiring the single best candidate is maximized
when:

```
k/n ≈ 1/e ≈ 0.368
```

giving roughly a 37% chance of hiring the best candidate overall — far
better than the ~1/n chance of picking the best candidate at random. This
project lets you verify that result yourself, by running many trials and
watching where the success rate actually peaks.

## License

MIT License — see `LICENSE` for details.
