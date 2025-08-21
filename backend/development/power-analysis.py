# %%

"""
Power analysis for comparing two proportions (baseline vs improved LLM accuracy).

This script computes the required number of graded student answers to detect
an improvement in binary accuracy from baseline p1 to improved p2 with
significance level alpha and power (1 - beta).

Notes:
- The calculation below follows the two-sample (independent) proportions Z-test.
- If you evaluate both LLMs on the SAME graded answers (paired design), the
  required number of unique graded answers is roughly the per-group n below
  (not 2*n). The independent design is conservative when used for a paired setup.

Usage examples:
  python power-analysis.py
  python power-analysis.py --p1 0.7 --p2 0.75 0.8 --alpha 0.05 --power 0.8 --questions 5 10
  python power-analysis.py --one-sided
"""

from __future__ import annotations

import argparse
import math
from typing import Iterable, List
from scipy.stats import norm


def compute_sample_size_two_proportions(
    baseline_accuracy: float,
    improved_accuracy: float,
    alpha: float = 0.05,
    power: float = 0.8,
    two_sided: bool = True,
) -> int:
    """
    Compute per-group sample size for a two-proportion Z-test.

    n = ((z_{alpha} + z_{beta})^2 * (p1(1-p1) + p2(1-p2))) / (p2 - p1)^2

    Returns ceil(n) as an integer.
    """
    if not (0 < baseline_accuracy < 1 and 0 < improved_accuracy < 1):
        raise ValueError("Accuracies must be in (0,1)")
    if improved_accuracy == baseline_accuracy:
        raise ValueError("Improved accuracy must differ from baseline accuracy")
    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0,1)")
    if not (0 < power < 1):
        raise ValueError("power must be in (0,1)")

    z_alpha = (
        float(norm.ppf(1 - alpha / 2)) if two_sided else float(norm.ppf(1 - alpha))
    )
    z_beta = float(norm.ppf(power))

    variance_sum = baseline_accuracy * (1 - baseline_accuracy) + improved_accuracy * (
        1 - improved_accuracy
    )
    delta = abs(improved_accuracy - baseline_accuracy)

    n = ((z_alpha + z_beta) ** 2 * variance_sum) / (delta**2)
    return int(math.ceil(n))


def format_results(
    p1: float,
    p2_values: Iterable[float],
    alpha: float,
    power: float,
    two_sided: bool,
    question_counts: Iterable[int],
) -> str:
    lines: List[str] = []
    alt = "two-sided" if two_sided else "one-sided (improvement)"
    lines.append(
        f"Power analysis for two-proportion test (alpha={alpha}, power={power}, {alt})"
    )
    lines.append("")

    for p2 in p2_values:
        n_per_group = compute_sample_size_two_proportions(
            baseline_accuracy=p1,
            improved_accuracy=p2,
            alpha=alpha,
            power=power,
            two_sided=two_sided,
        )

        # If both LLMs are run on the same graded answers, unique graded answers ~ n_per_group
        n_unique_graded = n_per_group
        n_total_if_independent_groups = 2 * n_per_group

        lines.append(f"Baseline p1={p1:.3f}, Improved p2={p2:.3f}, Δ={p2 - p1:+.3f}")
        lines.append(f"- Required per-group n: {n_per_group}")
        lines.append(
            f"- Unique graded answers if both models use the same set: {n_unique_graded}"
        )
        lines.append(
            f"- Total n if independent groups (different answer sets per model): {n_total_if_independent_groups}"
        )

        for q in question_counts:
            per_q = int(math.ceil(n_unique_graded / q))
            lines.append(
                f"  - With {q} questions: ~{per_q} graded answers per question (unique)"
            )

        lines.append("")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Power analysis for two-proportion accuracy comparison (LLM teacher scoring)."
    )
    parser.add_argument(
        "--p1",
        type=float,
        default=0.7,
        help="Baseline accuracy (default: 0.7)",
    )
    parser.add_argument(
        "--p2",
        type=float,
        nargs="+",
        default=[0.75, 0.8],
        help="Improved accuracy hypotheses (one or more). Default: 0.75 0.8",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="Significance level (default: 0.05)",
    )
    parser.add_argument(
        "--power",
        type=float,
        default=0.8,
        help="Desired power (default: 0.8)",
    )
    parser.add_argument(
        "--questions",
        type=int,
        nargs="+",
        default=[5, 10],
        help="Numbers of questions/tasks to split the graded answers across (default: 5 10)",
    )
    parser.add_argument(
        "--one-sided",
        action="store_true",
        help="Use one-sided test (testing for improvement). Default is two-sided.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    two_sided = not args.one_sided
    output = format_results(
        p1=args.p1,
        p2_values=args.p2,
        alpha=args.alpha,
        power=args.power,
        two_sided=two_sided,
        question_counts=args.questions,
    )
    print(output)


if __name__ == "__main__":
    main()
