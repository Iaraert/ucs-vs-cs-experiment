"""モデル値を計算するモジュール。

このファイルの役割:
- 刺激ごとの分割表(a,b,c,d)から各モデル値を計算する
- 予測寄り/診断寄りの反映度(w*)推定に必要な値を作る
- 変換（power変換）など、モデル値の後処理を担当する
"""

from __future__ import annotations

import warnings
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.integrate import IntegrationWarning

import transform

import mod_prev as comp

from .common import (
    ALL_MODEL_NAMES,
    MIN_ISING_STRENGTH_INTERVAL,
    MODEL_VARIANTS,
    ModelParams,
    get_cs_model_name,
    get_ising_model_name,
    pearson_corr,
)


def _safe_model_calc(calc_func, *args, **kwargs) -> float:
    # モデル実行の例外を握ってNaNに寄せる
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=IntegrationWarning)
            result = calc_func(*args, **kwargs)
        arr = np.asarray(result, dtype=float).flatten()
        return float(arr[0]) if arr.size else np.nan
    except Exception:
        return np.nan


def calc_cs(counts: Tuple[int, int, int, int], params: ModelParams) -> float:
    # CSを1刺激分だけ計算
    sspp = (float(params["alpha"]), float(params["beta"]))
    return _safe_model_calc(
        comp.CS,
        np.array([counts], dtype=int),
        True,
        bool(params["is_structure"]),
        sspp,
    )


def calc_ising(
    counts: Tuple[int, int, int, int],
    params: ModelParams,
    ising_threshold: float,
    ising_interval: float,
    cond_like: bool,
    swap_fe: bool,
    llfv: Tuple[float, float],
) -> float:
    # Isingを1刺激分だけ計算
    import mod_llm as llm

    tables = np.array([counts], dtype=int)
    sspp = (float(params["alpha"]), float(params["beta"]))
    eff_interval = max(float(ising_interval), MIN_ISING_STRENGTH_INTERVAL)
    use_cond_like = bool(params.get("cond_like", cond_like))
    use_swap_fe = bool(params.get("swap_fe", swap_fe))
    use_llfv = tuple(params.get("llfv", llfv))

    old_defaults = llm.log_linear_strength.__defaults__
    try:
        llm.log_linear_strength.__defaults__ = (eff_interval,)
        return _safe_model_calc(
            llm.ising,
            tables,
            True,
            bool(params["is_structure"]),
            float(ising_threshold),
            False,
            use_llfv,
            sspp,
            use_cond_like,
            use_swap_fe,
        )
    finally:
        llm.log_linear_strength.__defaults__ = old_defaults


def calc_delta_p(counts: Tuple[int, int, int, int]) -> float:
    # ΔP = P(E|C) - P(E|~C)
    a, b, c, d = [float(x) for x in counts]
    if (a + b) <= 0 or (c + d) <= 0:
        return np.nan
    delta_p = a / (a + b) - c / (c + d)
    return float(delta_p) if np.isfinite(delta_p) else np.nan


def calc_dfh(counts: Tuple[int, int, int, int]) -> float:
    # DFH = a / sqrt((a+b)(a+c))
    a, b, c, d = [float(x) for x in counts]
    if (a + b) <= 0 or (a + c) <= 0:
        return np.nan
    res = a / np.sqrt((a + b) * (a + c))
    return float(res) if np.isfinite(res) else np.nan


def calc_predictive_diagnostic_probs(counts: Tuple[int, int, int, int]) -> Tuple[float, float]:
    # (P(E|C), P(C|E)) を返す
    a, b, c, d = [float(x) for x in counts]

    pred_denom = a + b
    diag_denom = a + c

    pec = a / pred_denom if pred_denom > 0 else np.nan
    pce = a / diag_denom if diag_denom > 0 else np.nan

    return (
        float(pec) if np.isfinite(pec) else np.nan,
        float(pce) if np.isfinite(pce) else np.nan,
    )


def calc_pce(counts: Tuple[int, int, int, int]) -> float:
    _, pce = calc_predictive_diagnostic_probs(counts)
    return pce


def calc_pec(counts: Tuple[int, int, int, int]) -> float:
    pec, _ = calc_predictive_diagnostic_probs(counts)
    return pec


def extract_counts_from_row(row: pd.Series, abcd_cols: List[str]) -> Optional[Tuple[int, int, int, int]]:
    counts_series = row[abcd_cols]
    if counts_series.isnull().any():
        return None
    try:
        return tuple(int(float(v)) for v in counts_series.values)
    except ValueError:
        return None


def build_weight_grid(step: float) -> np.ndarray:
    # 0..1のw候補を作る
    if not np.isfinite(step) or step <= 0.0 or step > 1.0:
        raise ValueError("weight_grid_step must be in (0, 1].")
    grid = np.arange(0.0, 1.0 + (step * 0.5), step, dtype=float)
    if grid.size == 0 or grid[-1] < 1.0:
        grid = np.append(grid, 1.0)
    grid = np.clip(grid, 0.0, 1.0)
    return np.unique(np.round(grid, 12))


def estimate_pred_diag_reflection(
    y_vals: np.ndarray,
    predictive_vals: np.ndarray,
    diagnostic_vals: np.ndarray,
    weight_grid: np.ndarray,
) -> Dict[str, float]:
    # yが予測寄りか診断寄りかをwで当てる
    y_arr = np.asarray(y_vals, dtype=float)
    pred_arr = np.asarray(predictive_vals, dtype=float)
    diag_arr = np.asarray(diagnostic_vals, dtype=float)
    corr_pred = pearson_corr(y_arr, pred_arr)
    corr_diag = pearson_corr(y_arr, diag_arr)
    best_w = np.nan
    best_corr = -np.inf
    for w in np.asarray(weight_grid, dtype=float):
        mix_vals = (w * pred_arr) + ((1.0 - w) * diag_arr)
        corr = pearson_corr(y_arr, mix_vals)
        if np.isfinite(corr) and (not np.isfinite(best_corr) or corr > best_corr):
            best_corr = float(corr)
            best_w = float(w)
    if not np.isfinite(best_corr):
        best_corr = np.nan
    return {
        "w_star": float(best_w) if np.isfinite(best_w) else np.nan,
        "corr_mix_max": float(best_corr),
        "corr_predictive": float(corr_pred) if np.isfinite(corr_pred) else np.nan,
        "corr_diagnostic": float(corr_diag) if np.isfinite(corr_diag) else np.nan,
    }


def power_transform_model(model_vals: np.ndarray, human_vals: np.ndarray) -> np.ndarray:
    # 人データにレンジを合わせる
    model_arr = np.asarray(model_vals, dtype=float)
    human_arr = np.asarray(human_vals, dtype=float)
    if model_arr.size == 0 or human_arr.size == 0:
        return model_arr
    if not np.all(np.isfinite(human_arr)) or not np.any(np.isfinite(model_arr)):
        return model_arr

    trans_vals, _ = transform.power_optimize(human_arr, model_arr)
    if np.all(np.isnan(trans_vals)):
        return model_arr

    h_min, h_max = np.nanmin(human_arr), np.nanmax(human_arr)
    t_min, t_max = np.nanmin(trans_vals), np.nanmax(trans_vals)
    if not np.all(np.isfinite([h_min, h_max, t_min, t_max])):
        return trans_vals
    if (h_max - h_min) <= 0 or (t_max - t_min) <= 0:
        return trans_vals

    scaled = (h_max - h_min) / (t_max - t_min) * (trans_vals - t_min) + h_min
    return scaled


def calc_stimulus_model_values(
    counts: Tuple[int, int, int, int],
    cs_variant_params: Dict[str, ModelParams],
    ising_variant_params: Dict[str, ModelParams],
    ising_threshold: float,
    ising_interval: float,
    cond_like: bool,
    swap_fe: bool,
    llfv: Tuple[float, float],
) -> Dict[str, float]:
    # 1刺激ぶんの全モデル値
    model_values: Dict[str, float] = {}

    for variant in MODEL_VARIANTS:
        model_values[get_cs_model_name(variant)] = calc_cs(counts, cs_variant_params[variant])
        model_values[get_ising_model_name(variant)] = calc_ising(
            counts,
            ising_variant_params[variant],
            ising_threshold,
            ising_interval,
            cond_like,
            swap_fe,
            llfv,
        )

    model_values["DeltaP"] = calc_delta_p(counts)
    model_values["DFH"] = calc_dfh(counts)
    model_values["PCE"] = calc_pce(counts)
    model_values["PEC"] = calc_pec(counts)
    return model_values


def empty_model_arrays() -> Dict[str, List[float]]:
    return {name: [] for name in ALL_MODEL_NAMES}
