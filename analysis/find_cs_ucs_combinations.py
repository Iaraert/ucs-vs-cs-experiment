#!/usr/bin/env python3
"""
CS_genericとUCS_genericの値を同時に分類し、
(high, mid, low)×(high, mid, low) の9通りすべてを満たす (a, b, c, d)
の代表例を探索するユーティリティ。

Monte Carlo の乱数系列を事前に固定しておくことで、同じパラメータで
繰り返し実行しても結果がブレないようにしている。
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

EPS = 1e-12
LABEL_ORDER = ("low", "mid", "high")


def log_mean_exp(log_vals: np.ndarray) -> float:
    """Return log(mean(exp(x))) computed in a numerically stable fashion."""
    max_val = float(np.max(log_vals))
    return max_val + float(np.log(np.mean(np.exp(log_vals - max_val))))


@dataclass
class SearchConfig:
    """User-configurable knobs for the CS/UCS sweep."""
    threshold: float = 0.3  # Upper bound for background edge sampling in Monte Carlo
    cs_loops: int = 12000  # Number of Monte Carlo draws used by CS_generic
    ucs_loops: int = 12000  # Number of Monte Carlo draws used by UCS_generic
    seed: int = 0  # Shared RNG seed so experiments stay reproducible
    is_gene: bool = True  # True: generative cause, False: inhibitory cause
    max_total: int = 18  # Search all tables where a+b+c+d <= this bound
    cs_thresholds: Optional[Tuple[float, float]] = None  # Optional manual cut-offs for CS labels
    ucs_thresholds: Optional[Tuple[float, float]] = None  # Optional manual cut-offs for UCS labels
    csv_path: Optional[Path] = None  # Write the full result table when provided
    where_condition: Optional[str] = None  # Arbitrary filter condition from --where


class CSUCSMonteCarlo:
    """Pre-sampled Monte Carlo tables for CS_generic / UCS_generic."""

    def __init__(self, config: SearchConfig):
        self.config = config
        self._rng = np.random.default_rng(config.seed)
        self._build_cs_tables()
        self._build_ucs_tables()

    def _build_cs_tables(self) -> None:
        """Sample CS-specific probabilities once so subsequent score calls reuse them."""
        cfg = self.config
        rng = self._rng
        power0 = rng.uniform(0.0, 1.0, cfg.cs_loops)
        power1 = rng.uniform(1e-8, cfg.threshold, cfg.cs_loops)

        # Precompute noisy-OR style probabilities under causal (G1) and null (G0) models
        probs1 = np.stack(
            (
                power1,              # P(E=1|C=1)
                1.0 - power1,        # P(E=0|C=1)
                power0,              # P(E=1|C=0)
                1.0 - power0,        # P(E=0|C=0)
            ),
            axis=1,
        )
        probs0 = np.stack(
            (
                power0,              # P(E=1|C=1)
                1.0 - power0,        # P(E=0|C=1)
                power0,              # P(E=1|C=0)
                1.0 - power0,        # P(E=0|C=0)
            ),
            axis=1,
        )

        self.cs_log_probs1 = np.log(np.clip(probs1, EPS, None))
        self.cs_log_probs0 = np.log(np.clip(probs0, EPS, None))

    def _build_ucs_tables(self) -> None:
        """Sample UCS-specific probabilities once so subsequent score calls reuse them."""
        cfg = self.config
        rng = self._rng
        power0 = rng.uniform(0.0, 1.0, cfg.ucs_loops)
        power1 = rng.uniform(1e-8, cfg.threshold, cfg.ucs_loops)
        power2 = rng.uniform(1e-8, cfg.threshold, cfg.ucs_loops)

        # Cache complements to simplify later formulas
        om0 = 1.0 - power0
        om1 = 1.0 - power1
        om2 = 1.0 - power2

        if cfg.is_gene:
            t11 = np.sqrt(
                power1 * power2 * (1.0 - om0 * om1) * (1.0 - om0 * om2)
            )
            t10 = np.sqrt(
                power1 * (1.0 - power2) * power1 * (om0 * (1.0 - power2))
            )
            t01 = np.sqrt(
                (1.0 - power1) * power2 * power2 * (om0 * (1.0 - power1))
            )
            t00 = om1 * om2
        else:
            t11 = np.sqrt(
                power1 * power2 * ((power1 * om0) * (power2 * om0))
            )
            t10 = np.sqrt(
                power1 * (1.0 - power2) * power1 * (1.0 - (power2 * om0))
            )
            t01 = np.sqrt(
                (1.0 - power1) * power2 * (1.0 - (power1 * om0)) * power2
            )
            t00 = om1 * om2

        denom = np.clip(t11 + t10 + t01 + t00, EPS, None)
        probs1 = np.stack((t11 / denom, t10 / denom, t01 / denom, t00 / denom), axis=1)
        probs0 = np.stack(
            (
                power1 * power2,
                power1 * om2,
                om1 * power2,
                om1 * om2,
            ),
            axis=1,
        )

        self.ucs_log_probs1 = np.log(np.clip(probs1, EPS, None))
        self.ucs_log_probs0 = np.log(np.clip(probs0, EPS, None))

    def cs_generic(self, counts: Tuple[int, int, int, int]) -> float:
        """Evaluate CS_generic for a single contingency table using cached log probs."""
        counts_arr = np.asarray(counts, dtype=float)
        loglike1 = self.cs_log_probs1 @ counts_arr
        loglike0 = self.cs_log_probs0 @ counts_arr
        return log_mean_exp(loglike1) - log_mean_exp(loglike0)

    def ucs_generic(self, counts: Tuple[int, int, int, int]) -> float:
        """Evaluate UCS_generic for a single contingency table using cached log probs."""
        counts_arr = np.asarray(counts, dtype=float)
        loglike1 = self.ucs_log_probs1 @ counts_arr
        loglike0 = self.ucs_log_probs0 @ counts_arr
        return log_mean_exp(loglike1) - log_mean_exp(loglike0)


def generate_counts(max_total: int) -> Iterable[Tuple[int, int, int, int]]:
    """Yield all non-negative (a, b, c, d) with a+b+c+d ∈ [1, max_total]."""
    for total in range(1, max_total + 1):
        for a in range(total + 1):
            for b in range(total - a + 1):
                for c in range(total - a - b + 1):
                    d = total - a - b - c
                    yield a, b, c, d


def determine_thresholds(values: np.ndarray, explicit: Optional[Tuple[float, float]]) -> Tuple[float, float]:
    if explicit is not None:
        return explicit
    low, high = np.quantile(values, [1.0 / 3.0, 2.0 / 3.0])
    if np.isclose(low, high):
        delta = max(1e-4, abs(low) * 1e-4)
        low -= delta
        high += delta
    return float(low), float(high)


def assign_label(value: float, low_thr: float, high_thr: float) -> str:
    """Label a scalar value as low/mid/high based on two threshold cut-offs."""
    if value <= low_thr:
        return "low"
    if value >= high_thr:
        return "high"
    return "mid"


def pick_label_examples(rows: List[Dict[str, float]]) -> Dict[Tuple[str, str], Dict[str, float]]:
    """Pick one representative row for each CS/UCS label combination."""
    ordered = sorted(
        rows,
        key=lambda r: (r["total"], abs(r["CS_generic"]) + abs(r["UCS_generic"]))
    )
    picked: Dict[Tuple[str, str], Dict[str, float]] = {}
    for row in ordered:
        key = (row["CS_label"], row["UCS_label"])
        if key not in picked:
            picked[key] = row
        if len(picked) == len(LABEL_ORDER) ** 2:
            break
    return picked


def write_csv(rows: List[Dict[str, float]], path: Path) -> None:
    """Persist the full search table for later inspection or plotting."""
    fieldnames = ["a", "b", "c", "d", "total", "CS_generic", "UCS_generic", "CS_label", "UCS_label"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in fieldnames})


def build_condition_predicate(expr: Optional[str]):
    """Compile the --where expression into a callable predicate over (a,b,c,d,total)."""
    if expr is None:
        return lambda counts: True

    # Compile once so we can evaluate the user expression quickly during the search loop
    code = compile(expr, "<where>", "eval")
    allowed_names = {"a", "b", "c", "d", "total"}
    used_names = set(code.co_names)
    unknown = used_names - allowed_names
    if unknown:
        raise ValueError(f"where 条件で利用できるのは {sorted(allowed_names)} のみです (不明な識別子: {sorted(unknown)})")

    def predicate(counts: Tuple[int, int, int, int]) -> bool:
        a, b, c, d = counts
        total = a + b + c + d
        # Eval with a restricted namespace for safety; only expose the four counts and total
        return bool(eval(code, {"__builtins__": {}}, {"a": a, "b": b, "c": c, "d": d, "total": total}))

    return predicate


def parse_args() -> SearchConfig:
    parser = argparse.ArgumentParser(
        description="CS_generic と UCS_generic の9分類を満たす (a,b,c,d) を探索する"
    )
    parser.add_argument("--threshold", type=float, default=1.0, help="稀少性制約 (U[0,x]) の上限 x")
    parser.add_argument("--cs-loops", type=int, default=50000, help="CS_generic Monte Carlo サンプル数")
    parser.add_argument("--ucs-loops", type=int, default=50000, help="UCS_generic Monte Carlo サンプル数")
    parser.add_argument("--seed", type=int, default=0, help="乱数シード")
    parser.add_argument("--max-total", type=int, default=18, help="探索する合計カウントの最大値")
    parser.add_argument("--inhibitory", action="store_true", help="抑制型 (is_gene=False) を使う")
    parser.add_argument("--cs-low", type=float, help="CS_generic の low 境界値")
    parser.add_argument("--cs-high", type=float, help="CS_generic の high 境界値")
    parser.add_argument("--ucs-low", type=float, help="UCS_generic の low 境界値")
    parser.add_argument("--ucs-high", type=float, help="UCS_generic の high 境界値")
    parser.add_argument("--csv", type=Path, help="探索結果をCSVに保存するパス")
    parser.add_argument(
        "--where",
        type=str,
        help="(a,b,c,d,total) を使った条件式。例: 'a > 4 and total >= 10'",
    )

    ns = parser.parse_args()

    cs_thresholds: Optional[Tuple[float, float]] = None
    if ns.cs_low is not None and ns.cs_high is not None:
        cs_thresholds = (ns.cs_low, ns.cs_high)
    elif ns.cs_low is not None or ns.cs_high is not None:
        parser.error("--cs-low と --cs-high はセットで指定してください")

    ucs_thresholds: Optional[Tuple[float, float]] = None
    if ns.ucs_low is not None and ns.ucs_high is not None:
        ucs_thresholds = (ns.ucs_low, ns.ucs_high)
    elif ns.ucs_low is not None or ns.ucs_high is not None:
        parser.error("--ucs-low と --ucs-high はセットで指定してください")

    return SearchConfig(
        threshold=ns.threshold,
        cs_loops=ns.cs_loops,
        ucs_loops=ns.ucs_loops,
        seed=ns.seed,
        is_gene=not ns.inhibitory,
        max_total=ns.max_total,
        cs_thresholds=cs_thresholds,
        ucs_thresholds=ucs_thresholds,
        csv_path=ns.csv,
        where_condition=ns.where,
    )


def main() -> None:
    config = parse_args()
    simulator = CSUCSMonteCarlo(config)
    predicate = build_condition_predicate(config.where_condition)

    rows: List[Dict[str, float]] = []
    # Enumerate every contingency table up to the requested size and keep those matching the filter
    for counts in generate_counts(config.max_total):
        total = sum(counts)
        if not predicate(counts):
            continue  # Skip tuples that violate the user-specified --where condition
        cs_val = simulator.cs_generic(counts)
        ucs_val = simulator.ucs_generic(counts)
        rows.append(
            {
                "a": counts[0],
                "b": counts[1],
                "c": counts[2],
                "d": counts[3],
                "total": total,
                "CS_generic": cs_val,
                "UCS_generic": ucs_val,
            }
        )

    if not rows:
        print("条件を満たす (a,b,c,d) が見つかりませんでした。探索範囲や条件式を調整してください。")
        return

    # Use explicit thresholds when provided; otherwise derive terciles from the sampled scores
    cs_thresholds = determine_thresholds(
        np.array([row["CS_generic"] for row in rows]), config.cs_thresholds
    )
    ucs_thresholds = determine_thresholds(
        np.array([row["UCS_generic"] for row in rows]), config.ucs_thresholds
    )

    for row in rows:
        row["CS_label"] = assign_label(row["CS_generic"], *cs_thresholds)
        row["UCS_label"] = assign_label(row["UCS_generic"], *ucs_thresholds)

    picked = pick_label_examples(rows)

    print(f"CS_generic thresholds: low<= {cs_thresholds[0]:.3f}, high>= {cs_thresholds[1]:.3f}")
    print(f"UCS_generic thresholds: low<= {ucs_thresholds[0]:.3f}, high>= {ucs_thresholds[1]:.3f}\n")

    for cs_label in LABEL_ORDER:
        for ucs_label in LABEL_ORDER:
            key = (cs_label, ucs_label)
            row = picked.get(key)
            if row is None:
                print(f"CS={cs_label:>4}, UCS={ucs_label:>4}: 該当なし (探索範囲を広げてください)")
            else:
                counts_repr = (row["a"], row["b"], row["c"], row["d"])
                print(
                    "CS={cs:>4}, UCS={ucs:>4}: counts={cnts} total={tot:>3} CS={cs_val:+.3f} UCS={ucs_val:+.3f}".format(
                        cs=cs_label,
                        ucs=ucs_label,
                        cnts=counts_repr,
                        tot=int(row["total"]),
                        cs_val=row["CS_generic"],
                        ucs_val=row["UCS_generic"],
                    )
                )
        print("")

    if len(picked) < len(LABEL_ORDER) ** 2:
        print("※ 一部の組み合わせが見つかりませんでした。max_total や境界値を調整してください。")

    if config.csv_path is not None:
        write_csv(rows, config.csv_path)
        print(f"\n全探索結果を {config.csv_path} に書き出しました。")


if __name__ == "__main__":
    main()
