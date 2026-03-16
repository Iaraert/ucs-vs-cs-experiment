"""クラスタ分析の本体処理。

このファイルの役割:
- 回答データを user×刺激行列にして k-means を実行
- クラスタ単位でモデル相関・モデル平均を集計
- 予測/診断どちら寄りかを混合重み w* で推定して保存する
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from .common import (
    ALL_MODEL_NAMES,
    DELTA_P_PARAMS,
    DFH_PARAMS,
    MODEL_VARIANTS,
    PCE_PARAMS,
    PEC_PARAMS,
    CS_VARIANT_PARAMS,
    ISING_VARIANT_PARAMS,
    CaseDefinition,
    ClusterDecision,
    ModelParams,
    get_cs_model_name,
    get_ising_model_name,
    iter_cases,
    pearson_corr,
)
from .model_metrics import (
    build_weight_grid,
    calc_predictive_diagnostic_probs,
    calc_stimulus_model_values,
    empty_model_arrays,
    estimate_pred_diag_reflection,
    extract_counts_from_row,
    power_transform_model,
)


def pivot_estimates(df_subset: pd.DataFrame, prefix: str) -> Optional[pd.DataFrame]:
    # user×刺激番号の行列
    est_col = f"{prefix}_estimate"
    num_col = f"{prefix}_sample_number"
    required = {est_col, num_col}
    if not required.issubset(df_subset.columns):
        return None
    pivot = df_subset.pivot_table(index="user_id", columns=num_col, values=est_col, aggfunc="mean").dropna(how="any")
    return None if pivot.empty else pivot


def find_best_k(X: np.ndarray, max_k: int, min_silhouette: float, random_state: int) -> ClusterDecision:
    # シルエット最大のkを選ぶ
    n_samples = X.shape[0]
    if n_samples <= 1:
        return ClusterDecision(best_k=1, best_score=-np.inf, scores=())

    best_k = 1
    best_score = -np.inf
    scores: List[Tuple[int, float]] = []
    upper = min(max_k, n_samples)
    for k in range(2, upper + 1):
        labels = KMeans(n_clusters=k, random_state=random_state, n_init=10).fit_predict(X)
        if len(np.unique(labels)) < 2:
            continue
        sil = float(silhouette_score(X, labels))
        scores.append((k, sil))
        if sil > best_score:
            best_k, best_score = k, sil

    if best_score < min_silhouette:
        return ClusterDecision(best_k=1, best_score=best_score, scores=tuple(scores))
    return ClusterDecision(best_k=best_k, best_score=best_score, scores=tuple(scores))


def label_clusters(pivot: pd.DataFrame, k: int, random_state: int) -> np.ndarray:
    # 平均回答が高い順に0,1,...へ振り直す
    if k <= 1:
        return np.zeros(len(pivot), dtype=int)
    sample_cols = [c for c in pivot.columns if c != "cluster"]
    X = pivot[sample_cols].to_numpy(dtype=float) if sample_cols else pivot.to_numpy(dtype=float)
    labels = KMeans(n_clusters=k, random_state=random_state, n_init=10).fit_predict(X)
    cluster_means = {}
    for idx in range(k):
        mask = labels == idx
        cluster_means[idx] = float(np.mean(X[mask])) if mask.sum() > 0 else -np.inf
    order = sorted(cluster_means, key=cluster_means.get, reverse=True)
    remap = {old: new for new, old in enumerate(order)}
    return np.array([remap[label] for label in labels], dtype=int)


def _build_cluster_model_vectors(
    case: CaseDefinition,
    cluster_subset: pd.DataFrame,
    cs_variant_params: Dict[str, ModelParams],
    ising_variant_params: Dict[str, ModelParams],
    ising_threshold: float,
    ising_interval: float,
    cond_like: bool,
    swap_fe: bool,
    llfv: Tuple[float, float],
) -> Optional[Tuple[List[int], np.ndarray, Dict[str, np.ndarray], np.ndarray]]:
    # 刺激順を揃えて、人データとモデル値を作る
    if cluster_subset.empty:
        return None

    stimulus_cols = sorted(col for col in cluster_subset.columns if col != "cluster")
    if not stimulus_cols:
        return None

    cluster_mean_responses = cluster_subset[stimulus_cols].mean(axis=0)
    num_col = f"{case.prefix}_sample_number"
    abcd_cols = [f"{case.prefix}_{c}" for c in ("a", "b", "c", "d")]

    sample_numbers: List[int] = []
    human_values: List[float] = []
    contingency_counts: List[Tuple[int, int, int, int]] = []
    model_values = empty_model_arrays()

    for stimulus_num in stimulus_cols:
        stimulus_data = case.data[case.data[num_col] == stimulus_num]
        if stimulus_data.empty:
            continue

        counts = extract_counts_from_row(stimulus_data.iloc[0], abcd_cols)
        if counts is None:
            continue

        try:
            stimulus_id = int(stimulus_num)
        except ValueError:
            continue

        sample_numbers.append(stimulus_id)
        human_values.append(float(cluster_mean_responses.loc[stimulus_num]))
        contingency_counts.append(counts)

        stimulus_models = calc_stimulus_model_values(
            counts,
            cs_variant_params,
            ising_variant_params,
            ising_threshold,
            ising_interval,
            cond_like,
            swap_fe,
            llfv,
        )
        for model_name, value in stimulus_models.items():
            model_values[model_name].append(value)

    if not sample_numbers:
        return None

    human_arr = np.asarray(human_values, dtype=float)
    model_arrays = {name: np.asarray(vals, dtype=float) for name, vals in model_values.items()}
    counts_arr = np.asarray(contingency_counts, dtype=float)
    return sample_numbers, human_arr, model_arrays, counts_arr


def compute_cluster_correlations(
    pivot: pd.DataFrame,
    case: CaseDefinition,
    labels: np.ndarray,
    decision: ClusterDecision,
    cs_variant_params: Dict[str, ModelParams],
    ising_variant_params: Dict[str, ModelParams],
    ising_threshold: float,
    ising_interval: float,
    cond_like: bool,
    swap_fe: bool,
    llfv: Tuple[float, float],
) -> List[Dict[str, float | str]]:
    # クラスタ平均回答と各モデルの相関
    rows: List[Dict[str, float | str]] = []

    pivot_with_labels = pivot.copy()
    pivot_with_labels["cluster"] = labels

    for cid in sorted(np.unique(labels)):
        cluster_subset = pivot_with_labels[pivot_with_labels["cluster"] == cid]
        vectors = _build_cluster_model_vectors(
            case,
            cluster_subset,
            cs_variant_params,
            ising_variant_params,
            ising_threshold,
            ising_interval,
            cond_like,
            swap_fe,
            llfv,
        )
        if vectors is None:
            continue
        _, human_vals, model_values, _ = vectors
        correlations = {model_name: pearson_corr(human_vals, model_arr) for model_name, model_arr in model_values.items()}

        row: Dict[str, float | str] = {
            "condition_tag": case.condition_tag,
            "case_label": case.label,
            "experiment": case.experiment,
            "condition": case.condition,
            "cluster": f"Cluster{cid}",
            "participants": int((labels == cid).sum()),
            "k": int(decision.best_k),
            "silhouette": float(decision.best_score) if decision.best_k > 1 else np.nan,
            "silhouette_grid": decision.scores,
            "corr_delta_p": correlations["DeltaP"],
            "corr_dfh": correlations["DFH"],
            "corr_pce": correlations["PCE"],
            "corr_pec": correlations["PEC"],
        }
        for variant in MODEL_VARIANTS:
            variant_key = variant.lower()
            row[f"corr_cs_{variant_key}"] = correlations[get_cs_model_name(variant)]
            row[f"corr_ising_{variant_key}"] = correlations[get_ising_model_name(variant)]
        row["corr_cs"] = row["corr_cs_ss_strc"]
        row["corr_ising"] = row["corr_ising_ss_strc"]
        rows.append(row)

    return rows


def compute_cluster_pred_diag_reflection(
    pivot: pd.DataFrame,
    case: CaseDefinition,
    labels: np.ndarray,
    decision: ClusterDecision,
    cs_variant_params: Dict[str, ModelParams],
    ising_variant_params: Dict[str, ModelParams],
    ising_threshold: float,
    ising_interval: float,
    cond_like: bool,
    swap_fe: bool,
    llfv: Tuple[float, float],
    weight_grid_step: float,
) -> List[Dict[str, float | str]]:
    # 混合重みw*で予測/診断寄りを推定
    rows: List[Dict[str, float | str]] = []
    weight_grid = build_weight_grid(weight_grid_step)
    target_names = ("Human", *ALL_MODEL_NAMES)

    pivot_with_labels = pivot.copy()
    pivot_with_labels["cluster"] = labels

    for cid in sorted(np.unique(labels)):
        cluster_subset = pivot_with_labels[pivot_with_labels["cluster"] == cid]
        vectors = _build_cluster_model_vectors(
            case,
            cluster_subset,
            cs_variant_params,
            ising_variant_params,
            ising_threshold,
            ising_interval,
            cond_like,
            swap_fe,
            llfv,
        )
        if vectors is None:
            continue
        _, human_vals, model_values, counts_arr = vectors
        if counts_arr.size == 0:
            continue

        probs = np.asarray(
            [
                calc_predictive_diagnostic_probs(
                    tuple(int(v) for v in counts_arr[idx, :])
                )
                for idx in range(counts_arr.shape[0])
            ],
            dtype=float,
        )
        predictive_vals = probs[:, 0]
        diagnostic_vals = probs[:, 1]
        target_map: Dict[str, np.ndarray] = {"Human": human_vals, **model_values}
        participants = int((labels == cid).sum())

        for target_name in target_names:
            reflection = estimate_pred_diag_reflection(
                target_map[target_name],
                predictive_vals,
                diagnostic_vals,
                weight_grid,
            )
            rows.append(
                {
                    "condition_tag": case.condition_tag,
                    "case_label": case.label,
                    "experiment": case.experiment,
                    "condition": case.condition,
                    "cluster": f"Cluster{cid}",
                    "target": target_name,
                    "participants": participants,
                    "n_stimuli": int(counts_arr.shape[0]),
                    "k": int(decision.best_k),
                    "silhouette": float(decision.best_score) if decision.best_k > 1 else np.nan,
                    "silhouette_grid": decision.scores,
                    "weight_grid_step": float(weight_grid_step),
                    "w_star_predictive": reflection["w_star"],
                    "corr_mix_max": reflection["corr_mix_max"],
                    "corr_predictive": reflection["corr_predictive"],
                    "corr_diagnostic": reflection["corr_diagnostic"],
                }
            )

    return rows


def compute_cluster_model_means(
    pivot: pd.DataFrame,
    labels: np.ndarray,
    case: CaseDefinition,
    decision: ClusterDecision,
    cs_variant_params: Dict[str, ModelParams],
    ising_variant_params: Dict[str, ModelParams],
    ising_threshold: float,
    ising_interval: float,
    cond_like: bool,
    swap_fe: bool,
    llfv: Tuple[float, float],
    apply_power_transform: bool,
) -> List[Dict[str, float | str]]:
    # クラスタごとの刺激別モデル平均
    rows: List[Dict[str, float | str]] = []

    pivot_with_labels = pivot.copy()
    pivot_with_labels["cluster"] = labels
    model_params_by_name: Dict[str, ModelParams] = {
        "DeltaP": DELTA_P_PARAMS.get(case.condition_tag, {}),
        "DFH": DFH_PARAMS.get(case.condition_tag, {}),
        "PCE": PCE_PARAMS.get(case.condition_tag, {}),
        "PEC": PEC_PARAMS.get(case.condition_tag, {}),
    }
    for variant in MODEL_VARIANTS:
        model_params_by_name[get_cs_model_name(variant)] = cs_variant_params[variant]
        model_params_by_name[get_ising_model_name(variant)] = ising_variant_params[variant]

    for cid in sorted(np.unique(labels)):
        cluster_subset = pivot_with_labels[pivot_with_labels["cluster"] == cid]
        vectors = _build_cluster_model_vectors(
            case,
            cluster_subset,
            cs_variant_params,
            ising_variant_params,
            ising_threshold,
            ising_interval,
            cond_like,
            swap_fe,
            llfv,
        )
        if vectors is None:
            continue
        sample_numbers, human_vals, model_values, _ = vectors
        participants = int((labels == cid).sum())
        for model_name in ALL_MODEL_NAMES:
            model_arr = model_values[model_name].copy()
            model_params = model_params_by_name[model_name]
            if apply_power_transform and bool(model_params.get("is_structure")):
                model_arr = power_transform_model(model_arr, human_vals)

            row: Dict[str, float | str] = {
                "condition_tag": case.condition_tag,
                "case_label": case.label,
                "experiment": case.experiment,
                "condition": case.condition,
                "cluster": f"Cluster{cid}",
                "model": model_name,
                "participants": participants,
                "k": int(decision.best_k),
                "silhouette": float(decision.best_score) if decision.best_k > 1 else np.nan,
                "silhouette_grid": decision.scores,
            }
            for sn, val in zip(sample_numbers, model_arr):
                row[f"stimulus{sn}"] = float(val)
            rows.append(row)
    return rows


def run_clustering(
    csv_path: Path | str,
    output_csv: Path | str,
    corr_output: Path | str,
    model_mean_output: Path | str,
    model_mean_raw_output: Path | str,
    pred_diag_output: Path | str,
    max_k: int,
    random_state: int,
    min_silhouette: float,
    ising_threshold: float,
    ising_interval: float,
    cond_like: bool,
    swap_fe: bool,
    llfv: Tuple[float, float],
    weight_grid_step: float,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # この分析の実行入口（CSV読込→集計→CSV出力）
    if weight_grid_step <= 0.0 or weight_grid_step > 1.0:
        raise ValueError("weight_grid_step must be in (0, 1].")

    df = pd.read_csv(csv_path)
    cluster_rows: List[Dict[str, float | str]] = []
    corr_rows: List[Dict[str, float | str]] = []
    model_mean_rows: List[Dict[str, float | str]] = []
    model_mean_raw_rows: List[Dict[str, float | str]] = []
    pred_diag_rows: List[Dict[str, float | str]] = []

    for case in iter_cases(df):
        if (
            DELTA_P_PARAMS.get(case.condition_tag) is None
            or DFH_PARAMS.get(case.condition_tag) is None
            or PCE_PARAMS.get(case.condition_tag) is None
            or PEC_PARAMS.get(case.condition_tag) is None
        ):
            continue
        cs_variant_params = {variant: dict(CS_VARIANT_PARAMS[variant]) for variant in MODEL_VARIANTS}
        ising_variant_params = {variant: dict(ISING_VARIANT_PARAMS[variant]) for variant in MODEL_VARIANTS}

        pivot = pivot_estimates(case.data, case.prefix)
        if pivot is None:
            continue

        X = pivot.to_numpy(dtype=float)
        decision = find_best_k(X, max_k, min_silhouette, random_state)
        labels = label_clusters(pivot, decision.best_k, random_state)
        silhouette = decision.best_score if decision.best_k > 1 else np.nan

        corr_rows_case = compute_cluster_correlations(
            pivot,
            case,
            labels,
            decision,
            cs_variant_params,
            ising_variant_params,
            ising_threshold,
            ising_interval,
            cond_like,
            swap_fe,
            llfv,
        )

        for idx, user_id in enumerate(pivot.index):
            cluster_rows.append(
                {
                    "condition_tag": case.condition_tag,
                    "case_label": case.label,
                    "experiment": case.experiment,
                    "condition": case.condition,
                    "user_id": str(user_id),
                    "cluster": int(labels[idx]),
                    "k": int(decision.best_k),
                    "silhouette": float(silhouette) if np.isfinite(silhouette) else np.nan,
                    "silhouette_grid": decision.scores,
                }
            )
        corr_rows.extend(corr_rows_case)

        pred_diag_rows.extend(
            compute_cluster_pred_diag_reflection(
                pivot,
                case,
                labels,
                decision,
                cs_variant_params,
                ising_variant_params,
                ising_threshold,
                ising_interval,
                cond_like,
                swap_fe,
                llfv,
                weight_grid_step,
            )
        )
        model_mean_rows.extend(
            compute_cluster_model_means(
                pivot,
                labels,
                case,
                decision,
                cs_variant_params,
                ising_variant_params,
                ising_threshold,
                ising_interval,
                cond_like,
                swap_fe,
                llfv,
                apply_power_transform=True,
            )
        )
        model_mean_raw_rows.extend(
            compute_cluster_model_means(
                pivot,
                labels,
                case,
                decision,
                cs_variant_params,
                ising_variant_params,
                ising_threshold,
                ising_interval,
                cond_like,
                swap_fe,
                llfv,
                apply_power_transform=False,
            )
        )

    cluster_df = pd.DataFrame(cluster_rows)
    corr_df = pd.DataFrame(corr_rows)
    model_mean_df = pd.DataFrame(model_mean_rows)
    model_mean_raw_df = pd.DataFrame(model_mean_raw_rows)
    pred_diag_df = pd.DataFrame(pred_diag_rows)

    out_path = Path(output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cluster_df.to_csv(out_path, index=False)

    corr_path = Path(corr_output)
    corr_path.parent.mkdir(parents=True, exist_ok=True)
    corr_df.to_csv(corr_path, index=False)

    model_mean_path = Path(model_mean_output)
    model_mean_path.parent.mkdir(parents=True, exist_ok=True)
    model_mean_df.to_csv(model_mean_path, index=False)

    model_mean_raw_path = Path(model_mean_raw_output)
    model_mean_raw_path.parent.mkdir(parents=True, exist_ok=True)
    model_mean_raw_df.to_csv(model_mean_raw_path, index=False)

    pred_diag_path = Path(pred_diag_output)
    pred_diag_path.parent.mkdir(parents=True, exist_ok=True)
    pred_diag_df.to_csv(pred_diag_path, index=False)

    return cluster_df, corr_df, model_mean_df, pred_diag_df
