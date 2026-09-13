import random

from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class CandidateEvent:
    """ Represents what happened with a single candidate during a trial """
    position: int
    value: float           # Candidate's "rank" OR "score"
    rank_position: int     # Candidate's rank position out of n, 1=worst, n=best
    is_best_so_far: bool
    decision: str          # "rejected", "hired", "passed"
    phase: str             # "observation", "selection"

@dataclass
class TrialResult:
    """ Full result of a single run of the secretary problem strategy """
    n: int                         # total number of candidates
    k: int                         # size of the observation phase
    mode: str                      # "rank" OR "score"
    near_optimal_top_m: int        # "near optimal" = hired someone in the top m
    history: List[CandidateEvent] = field(default_factory=list)
    hired_value: Optional[float] = None
    hired_position: Optional[int] = None
    hired_rank_position: Optional[int] = None
    is_best_possible: bool = False
    is_near_optimal: bool = False

def generate_candidates(
    n: int,
    mode: str = "rank",
    seed: int = None,
    score_distribution: str = "normal",
    score_mean: float = 50.0,
    score_std: float = 15.0,
    score_round_decimals: Optional[int] = 1,
) -> List[float]:
    """ Generate the values for n candidates, in random order """
    if n < 1:
        raise ValueError("n must be at least 1")

    rng = random.Random(seed)
    if mode == "rank":
        values = list(range(1, n + 1))
        rng.shuffle(values)
        return [float(v) for v in values]

    elif mode == "score":
        if score_distribution == "normal":
            raw = [rng.gauss(score_mean, score_std) for _ in range(n)]
        elif score_distribution == "uniform":
            raw = [rng.uniform(0.0, 100.0) for _ in range(n)]
        else:
            raise ValueError(f"Unknown score_distribution: {score_distribution!r}")

        if score_round_decimals is not None:
            raw = [round(v, score_round_decimals) for v in raw]
        return raw

    else:
        raise ValueError(f"Unknown mode: {mode!r} (expected 'rank' or 'score')")

def _compute_rank_positions(values: List[float]) -> List[int]:
    """ Compute each candidate's rank position (1=worst, n_unique=best) """
    unique_sorted = sorted(set(values))
    rank_map = {v: i + 1 for i, v in enumerate(unique_sorted)}
    return [rank_map[v] for v in values]

def run_trial(
    n: int,
    k: int,
    mode: str = "rank",
    seed: int = None,
    near_optimal_top_m: int = 3,
    **generation_kwargs,
) -> TrialResult:
    """ Run a single trial of the secretary problem strategy """
    if not (0 <= k <= n):
        raise ValueError("k must be between 0 and n (inclusive)")
    if not (1 <= near_optimal_top_m <= n):
        raise ValueError("near_optimal_top_m must be between 1 and n (inclusive)")

    values = generate_candidates(n, mode=mode, seed=seed, **generation_kwargs)
    rank_positions = _compute_rank_positions(values)

    result = TrialResult(n=n, k=k, mode=mode, near_optimal_top_m=near_optimal_top_m)

    best_seen_in_observation = None
    hired = False

    for position, (value, rank_position) in enumerate(zip(values, rank_positions), start=1):
        phase = "observation" if position <= k else "selection"
        is_best_so_far = (best_seen_in_observation is None) or (value > best_seen_in_observation)

        if phase == "observation": # Just observe and collect a baseline
            decision = "rejected"
            if best_seen_in_observation is None or value > best_seen_in_observation:
                best_seen_in_observation = value
        else:
            beats_observation = (best_seen_in_observation is None) or (value > best_seen_in_observation)
            if not hired and beats_observation: # Hire first candidate > baseline
                decision = "hired"
                hired = True
                result.hired_value = value
                result.hired_position = position
                result.hired_rank_position = rank_position
            else:
                decision = "passed" if hired else "rejected"

        result.history.append(
            CandidateEvent(
                position=position,
                value=value,
                rank_position=rank_position,
                is_best_so_far=is_best_so_far,
                decision=decision,
                phase=phase,
            )
        )

    if hired:
        n_unique = len(set(values))
        near_optimal_threshold = n_unique - near_optimal_top_m + 1
        result.is_best_possible = (result.hired_value == max(values))
        result.is_near_optimal = (result.hired_rank_position >= near_optimal_threshold)

    return result

def run_batch(
    n: int,
    k: int,
    mode: str = "rank",
    num_trials: int = 10_000,
    seed: int = None,
    near_optimal_top_m: int = 3,
    **generation_kwargs,
) -> dict:
    """ Run many trials for a given (n, k) pair and report aggregate statistics """
    rng = random.Random(seed)
    success_count = 0
    near_optimal_count = 0
    no_hire_count = 0
    hired_values = []
    hired_rank_positions = []
    best_possible_values = []

    for _ in range(num_trials):
        trial_seed = rng.randint(0, 2**31 - 1)
        result = run_trial(
            n, k, mode=mode, seed=trial_seed,
            near_optimal_top_m=near_optimal_top_m, **generation_kwargs
        )

        best_possible_values.append(max(event.value for event in result.history))

        if result.hired_value is None:
            no_hire_count += 1
            continue

        hired_values.append(result.hired_value)
        hired_rank_positions.append(result.hired_rank_position)

        if result.is_best_possible:
            success_count += 1
        if result.is_near_optimal:
            near_optimal_count += 1

    return {
        "n": n,
        "k": k,
        "mode": mode,
        "num_trials": num_trials,
        "near_optimal_top_m": near_optimal_top_m,
        "success_count": success_count,
        "success_rate": success_count / num_trials,
        "near_optimal_count": near_optimal_count,
        "near_optimal_rate": near_optimal_count / num_trials,
        "no_hire_count": no_hire_count,
        "no_hire_rate": no_hire_count / num_trials,
        "mean_hired_value": (sum(hired_values) / len(hired_values)) if hired_values else None,
        "mean_hired_rank_position": (sum(hired_rank_positions) / len(hired_rank_positions)) if hired_rank_positions else None,
        "mean_best_possible_value": sum(best_possible_values) / len(best_possible_values),
    }

def find_best_k(
    n: int,
    mode: str = "rank",
    num_trials: int = 2_000,
    seed: int = None,
    near_optimal_top_m: int = 3,
    **generation_kwargs,
) -> dict:
    """ Sweep every possible value of k (0..n-1) and find which one yields the highest success rate """
    results = []
    for k in range(0, n):
        batch = run_batch(
            n, k, mode=mode, num_trials=num_trials, seed=seed,
            near_optimal_top_m=near_optimal_top_m, **generation_kwargs
        )
        results.append(batch)

    best = max(results, key=lambda r: r["success_rate"])

    return {
        "n": n,
        "mode": mode,
        "results": results,
        "best_k": best["k"],
        "best_success_rate": best["success_rate"],
    }