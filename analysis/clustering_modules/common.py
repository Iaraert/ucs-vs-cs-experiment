"""クラスタ分析で共通利用する定数・型・基本関数。

このファイルの役割:
- どの分析でも使う設定値（出力先、パラメータ初期値）を一か所に置く
- 条件分割（Asymmetric/Symmetric × List/Online）を作る
- 相関の共通計算を提供する
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Union

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

ModelParams = Dict[str, Union[float, bool]]

MODEL_VARIANTS: Tuple[str, ...] = ("STRG", "STRC", "SS_STRG", "SS_STRC")

CS_VARIANT_PARAMS: Dict[str, ModelParams] = {
    "STRG": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
    "STRC": {"is_structure": True, "alpha": 0.0, "beta": 0.0},
    "SS_STRG": {"is_structure": False, "alpha": 4.0, "beta": 0.0},
    "SS_STRC": {"is_structure": True, "alpha": 5.0, "beta": 20.0},
}

ISING_VARIANT_PARAMS: Dict[str, ModelParams] = {
    "STRG": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
    "STRC": {"is_structure": True, "alpha": 0.0, "beta": 0.0},
    "SS_STRG": {"is_structure": False, "alpha": 2.0, "beta": 0.0},
    "SS_STRC": {"is_structure": True, "alpha": 1.0, "beta": 10.0},
}


def get_cs_model_name(variant: str) -> str:
    # 出力列名を揃える
    return f"CS_{variant}"


def get_ising_model_name(variant: str) -> str:
    # 出力列名を揃える
    return f"Ising_{variant}"


ALL_MODEL_NAMES: Tuple[str, ...] = (
    *(get_cs_model_name(v) for v in MODEL_VARIANTS),
    *(get_ising_model_name(v) for v in MODEL_VARIANTS),
    "DeltaP",
    "DFH",
    "PCE",
    "PEC",
)

DELTA_P_PARAMS: Dict[str, ModelParams] = {
    "Asymmetric_Online": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
    "Symmetric_Online": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
    "Asymmetric_List": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
    "Symmetric_List": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
}

DFH_PARAMS: Dict[str, ModelParams] = {
    "Asymmetric_Online": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
    "Symmetric_Online": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
    "Asymmetric_List": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
    "Symmetric_List": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
}

PCE_PARAMS: Dict[str, ModelParams] = {
    "Asymmetric_Online": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
    "Symmetric_Online": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
    "Asymmetric_List": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
    "Symmetric_List": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
}

PEC_PARAMS: Dict[str, ModelParams] = {
    "Asymmetric_Online": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
    "Symmetric_Online": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
    "Asymmetric_List": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
    "Symmetric_List": {"is_structure": False, "alpha": 0.0, "beta": 0.0},
}

DEFAULT_INPUT_CSV = "sorted.csv"
DEFAULT_OUTPUT_CSV = Path("out") / "clustering" / "kmeans_clusters.csv"
DEFAULT_CORR_CSV = Path("out") / "clustering" / "cluster_correlations.csv"
DEFAULT_MODEL_MEAN_CSV = Path("out") / "clustering" / "cluster_model_means.csv"
DEFAULT_MODEL_MEAN_RAW_CSV = Path("out") / "clustering" / "cluster_model_means_raw.csv"
DEFAULT_PRED_DIAG_OUTPUT = Path("out") / "clustering" / "cluster_pred_diag_reflection.csv"
DEFAULT_ORDER_EFFECT_OUTPUT = Path("out") / "clustering" / "asymmetric_online_order_effects.csv"
DEFAULT_ORDER_SUMMARY_OUTPUT = Path("out") / "clustering" / "asymmetric_online_order_summary.txt"
DEFAULT_ORDER_PLOT_OUTPUT = Path("out") / "clustering" / "asymmetric_online_order_distribution.png"
DEFAULT_ORDER_COMBO_OUTPUT = Path("out") / "clustering" / "asymmetric_online_order_combo_correlations.csv"
DEFAULT_ORDER_INDIVIDUAL_OUTPUT = Path("out") / "clustering" / "asymmetric_online_order_individual_responses.csv"
DEFAULT_MAX_K = 6
DEFAULT_RANDOM_STATE = 0
DEFAULT_MIN_SILHOUETTE = 0.05
DEFAULT_ISING_THRESHOLD = 1.0
DEFAULT_ISING_INTERVAL = 0.05
MIN_ISING_STRENGTH_INTERVAL = 0.05
DEFAULT_WEIGHT_GRID_STEP = 0.001  # w探索の刻み
DEFAULT_LLFV = (-1.0, 1.0)
DEFAULT_COND_LIKE = True
DEFAULT_SWAP_FE = True
PREDICTIVE_SAMPLE_NUMBERS: Tuple[int, int] = (3, 6)
DIAGNOSTIC_SAMPLE_NUMBERS: Tuple[int, int] = (1, 4)
INTERMEDIATE_SAMPLE_NUMBERS: Tuple[int, int] = (2, 5)
ORDERED_STIMULUS_TYPES: Tuple[str, str, str] = ("predictive", "diagnostic", "intermediate")

ORDERED_CONDITION_TAGS: Tuple[str, ...] = (
    "Asymmetric_Online",
    "Symmetric_Online",
    "Asymmetric_List",
    "Symmetric_List",
)


@dataclass(frozen=True)
class CaseDefinition:
    # 1条件ぶんのデータ束
    label: str
    prefix: str
    experiment: str
    condition: str
    condition_value: int
    data: pd.DataFrame

    @property
    def condition_tag(self) -> str:
        return f"{self.condition}_{self.experiment}"


@dataclass(frozen=True)
class ClusterDecision:
    # k選択の結果
    best_k: int
    best_score: float
    scores: Tuple[Tuple[int, float], ...]


def iter_cases(df: pd.DataFrame) -> Iterable[CaseDefinition]:
    # 4条件(非対称/対称 × List/Online)に切る
    if "Cond" not in df.columns or "user_id" not in df.columns:
        return []

    experiments = [("ex1", "List"), ("ex2", "Online")]
    condition_labels = {0: "Asymmetric", 1: "Symmetric"}
    cases: List[CaseDefinition] = []

    for prefix, experiment_name in experiments:
        flag_col = f"{prefix}_is_first"
        if flag_col not in df.columns:
            continue
        flagged = df[df[flag_col] == 1]
        if flagged.empty:
            continue

        for cond_value, condition_name in condition_labels.items():
            subset = flagged[flagged["Cond"] == cond_value]
            if subset.empty:
                continue
            cases.append(
                CaseDefinition(
                    label=f"Cond{cond_value}_{prefix}",
                    prefix=prefix,
                    experiment=experiment_name,
                    condition=condition_name,
                    condition_value=cond_value,
                    data=subset.copy(),
                )
            )

    cases.sort(
        key=lambda c: ORDERED_CONDITION_TAGS.index(c.condition_tag)
        if c.condition_tag in ORDERED_CONDITION_TAGS
        else len(ORDERED_CONDITION_TAGS)
    )
    return cases


def pearson_corr(a: np.ndarray, b: np.ndarray) -> float:
    # 有効値だけで相関
    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()
    if a.size == 0 or b.size == 0:
        return np.nan
    finite = np.isfinite(a) & np.isfinite(b)
    if finite.sum() < 2:
        return np.nan
    a_valid = a[finite]
    b_valid = b[finite]
    if np.std(a_valid) == 0 or np.std(b_valid) == 0:
        return np.nan
    try:
        corr, _ = pearsonr(a_valid, b_valid)
    except ValueError:
        return np.nan
    return float(corr) if np.isfinite(corr) else np.nan
