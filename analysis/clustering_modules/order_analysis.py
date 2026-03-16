"""オンライン・非対称条件の順序効果を分析するモジュール。

このファイルの役割:
- 参加者ごとに「最初/2番目に見た刺激タイプ」を抽出する
- 回答と (P(E|C), P(C|E)) の相関を個人単位で計算する
- 組合せ要約・検定要約・分布プロットを出力する
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.stats import kruskal, ttest_ind

from .common import (
    DEFAULT_ORDER_COMBO_OUTPUT,
    DEFAULT_ORDER_INDIVIDUAL_OUTPUT,
    DIAGNOSTIC_SAMPLE_NUMBERS,
    ORDERED_STIMULUS_TYPES,
    PREDICTIVE_SAMPLE_NUMBERS,
    pearson_corr,
)
from .model_metrics import calc_predictive_diagnostic_probs, extract_counts_from_row


def classify_stimulus_type(sample_number: int) -> str:
    # 刺激番号を3カテゴリに分ける
    if sample_number in PREDICTIVE_SAMPLE_NUMBERS:
        return "predictive"
    if sample_number in DIAGNOSTIC_SAMPLE_NUMBERS:
        return "diagnostic"
    return "intermediate"


def build_asymmetric_online_model_lookup(df: pd.DataFrame) -> Dict[int, tuple[float, float]]:
    # 刺激ごとのPEC/PCEを引ける辞書
    lookup: Dict[int, tuple[float, float]] = {}
    abcd_cols = ["ex2_a", "ex2_b", "ex2_c", "ex2_d"]
    for sample_number, grp in df.groupby("ex2_sample_number"):
        counts = extract_counts_from_row(grp.iloc[0], abcd_cols)
        if counts is None:
            continue
        try:
            sample_id = int(sample_number)
        except ValueError:
            continue
        lookup[sample_id] = calc_predictive_diagnostic_probs(counts)
    return lookup


def write_order_effect_summary(
    analysis_df: pd.DataFrame,
    combo_df: pd.DataFrame,
    output_path: Path,
) -> None:
    # 結果の読みどころをテキスト化
    lines: List[str] = []
    lines.append("Asymmetric Online (Cond=0, ex2_is_first=1) order effect summary")
    lines.append(f"n_participants={len(analysis_df)}")
    lines.append("")

    first_counts = analysis_df["first_type"].value_counts().to_dict()
    second_counts = analysis_df["second_type"].value_counts().to_dict()
    lines.append(f"first_type_counts={first_counts}")
    lines.append(f"second_type_counts={second_counts}")
    lines.append("")
    if not combo_df.empty:
        lines.append("Combination-level means (first_type x second_type)")
        for _, row in combo_df.iterrows():
            lines.append(
                (
                    f"{row['first_type']} -> {row['second_type']}: "
                    f"n={int(row['n_participants'])}, "
                    f"corr_predictive_mean={float(row['corr_predictive_mean']):.4f}, "
                    f"corr_diagnostic_mean={float(row['corr_diagnostic_mean']):.4f}, "
                    f"corr_diff_mean={float(row['corr_diff_mean']):.4f}"
                )
            )
        lines.append("")
        lines.append("Kruskal-Wallis by first_type x second_type combination")
        analysis_tmp = analysis_df.copy()
        analysis_tmp["combo"] = analysis_tmp["first_type"].astype(str) + "->" + analysis_tmp["second_type"].astype(str)
        for metric in ("corr_predictive", "corr_diagnostic", "corr_diff"):
            group_arrays: List[np.ndarray] = []
            combo_labels: List[str] = []
            for combo, grp in analysis_tmp.groupby("combo"):
                vals = grp[metric].dropna().to_numpy(dtype=float)
                if len(vals) >= 2:
                    group_arrays.append(vals)
                    combo_labels.append(str(combo))
            if len(group_arrays) >= 2:
                stat = kruskal(*group_arrays, nan_policy="omit")
                n_map = {
                    c: int(analysis_tmp.loc[analysis_tmp["combo"] == c, metric].notna().sum())
                    for c in combo_labels
                }
                lines.append(
                    f"{metric}: groups={combo_labels}, n={n_map}, H={float(stat.statistic):.4f}, p={float(stat.pvalue):.4g}"
                )
            else:
                lines.append(f"{metric}: skipped (need >=2 combinations with n>=2)")
        lines.append("")

    target_df = analysis_df[analysis_df["first_type"].isin(("predictive", "diagnostic"))].copy()
    if not target_df.empty:
        lines.append("Welch t-test by first stimulus type (predictive vs diagnostic)")
        for metric in ("corr_predictive", "corr_diagnostic", "corr_diff"):
            pred_vals = target_df.loc[target_df["first_type"] == "predictive", metric].dropna()
            diag_vals = target_df.loc[target_df["first_type"] == "diagnostic", metric].dropna()
            if len(pred_vals) >= 2 and len(diag_vals) >= 2:
                stat = ttest_ind(pred_vals, diag_vals, equal_var=False, nan_policy="omit")
                lines.append(
                    (
                        f"{metric}: mean_pred={pred_vals.mean():.4f}, "
                        f"mean_diag={diag_vals.mean():.4f}, "
                        f"t={float(stat.statistic):.4f}, p={float(stat.pvalue):.4g}, "
                        f"n_pred={len(pred_vals)}, n_diag={len(diag_vals)}"
                    )
                )
            else:
                lines.append(
                    f"{metric}: skipped (need >=2 valid samples in each group, got n_pred={len(pred_vals)}, n_diag={len(diag_vals)})"
                )
        lines.append("")

    lines.append("Kruskal-Wallis by second stimulus type (predictive/diagnostic/intermediate)")
    for metric in ("corr_predictive", "corr_diagnostic", "corr_diff"):
        groups = []
        valid_types: List[str] = []
        for stim_type in ORDERED_STIMULUS_TYPES:
            vals = analysis_df.loc[analysis_df["second_type"] == stim_type, metric].dropna()
            if len(vals) > 0:
                groups.append(vals.to_numpy(dtype=float))
                valid_types.append(stim_type)
        if len(groups) >= 2 and all(len(v) >= 2 for v in groups):
            stat = kruskal(*groups, nan_policy="omit")
            means = {
                stim_type: float(analysis_df.loc[analysis_df["second_type"] == stim_type, metric].mean())
                for stim_type in valid_types
            }
            counts = {
                stim_type: int(analysis_df.loc[analysis_df["second_type"] == stim_type, metric].notna().sum())
                for stim_type in valid_types
            }
            lines.append(
                f"{metric}: means={means}, n={counts}, H={float(stat.statistic):.4f}, p={float(stat.pvalue):.4g}"
            )
        else:
            size_map = {
                stim_type: int(analysis_df.loc[analysis_df["second_type"] == stim_type, metric].notna().sum())
                for stim_type in ORDERED_STIMULUS_TYPES
            }
            lines.append(f"{metric}: skipped (need >=2 groups with each n>=2), n={size_map}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_order_distribution(analysis_df: pd.DataFrame, output_path: Path) -> None:
    # 順序の偏りを図で確認
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))

    first_counts = (
        analysis_df["first_sample_number"]
        .value_counts()
        .reindex([1, 2, 3, 4, 5, 6], fill_value=0)
    )
    axes[0].bar(first_counts.index.astype(str), first_counts.values, color="#4C78A8")
    axes[0].set_title("First Stimulus Number")
    axes[0].set_xlabel("sample_number")
    axes[0].set_ylabel("count")

    combo = pd.crosstab(
        analysis_df["first_type"],
        analysis_df["second_type"],
    ).reindex(index=ORDERED_STIMULUS_TYPES, columns=ORDERED_STIMULUS_TYPES, fill_value=0)
    bottom = np.zeros(len(combo.index), dtype=float)
    colors = {"predictive": "#59A14F", "diagnostic": "#E15759", "intermediate": "#B07AA1"}
    for col in combo.columns:
        vals = combo[col].to_numpy(dtype=float)
        axes[1].bar(combo.index, vals, bottom=bottom, label=col, color=colors.get(str(col), "#9C755F"))
        bottom += vals
    axes[1].set_title("Second Type by First Type")
    axes[1].set_xlabel("first_type")
    axes[1].set_ylabel("count")
    axes[1].legend(loc="upper right", fontsize=8)

    heat = pd.crosstab(
        analysis_df["first_sample_number"],
        analysis_df["second_sample_number"],
    ).reindex(index=[1, 2, 3, 4, 5, 6], columns=[1, 2, 3, 4, 5, 6], fill_value=0)
    im = axes[2].imshow(heat.values, cmap="Blues")
    axes[2].set_title("First -> Second Sample")
    axes[2].set_xlabel("second_sample_number")
    axes[2].set_ylabel("first_sample_number")
    axes[2].set_xticks(np.arange(6))
    axes[2].set_xticklabels([str(x) for x in heat.columns])
    axes[2].set_yticks(np.arange(6))
    axes[2].set_yticklabels([str(x) for x in heat.index])
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            val = int(heat.iloc[i, j])
            axes[2].text(j, i, str(val), ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=axes[2], fraction=0.046, pad=0.04)

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def build_combo_summary(analysis_df: pd.DataFrame) -> pd.DataFrame:
    # 1番目×2番目の組合せ平均
    if analysis_df.empty:
        return pd.DataFrame()
    grouped = (
        analysis_df.groupby(["first_type", "second_type"], as_index=False)
        .agg(
            n_participants=("user_id", "nunique"),
            corr_predictive_mean=("corr_predictive", "mean"),
            corr_predictive_std=("corr_predictive", "std"),
            corr_diagnostic_mean=("corr_diagnostic", "mean"),
            corr_diagnostic_std=("corr_diagnostic", "std"),
            corr_diff_mean=("corr_diff", "mean"),
            corr_diff_std=("corr_diff", "std"),
        )
        .sort_values(["first_type", "second_type"])
        .reset_index(drop=True)
    )
    return grouped


def analyze_asymmetric_online_order_effects(
    csv_path: Path | str,
    analysis_output: Path | str,
    summary_output: Path | str,
    plot_output: Path | str,
    combo_output: Optional[Path | str] = None,
    individual_output: Optional[Path | str] = None,
) -> pd.DataFrame:
    # 順序効果分析の実行入口
    df = pd.read_csv(csv_path)
    required_cols = {
        "user_id",
        "Cond",
        "ex2_is_first",
        "ex2_sample_number",
        "ex2_estimate",
        "ex2_timestamp",
        "ex2_a",
        "ex2_b",
        "ex2_c",
        "ex2_d",
    }
    if not required_cols.issubset(df.columns):
        missing = sorted(required_cols - set(df.columns))
        raise ValueError(f"missing required columns for order analysis: {missing}")

    subset = df[(df["Cond"] == 0) & (df["ex2_is_first"] == 1)].copy()
    combo_path = Path(combo_output) if combo_output is not None else DEFAULT_ORDER_COMBO_OUTPUT
    indiv_path = Path(individual_output) if individual_output is not None else DEFAULT_ORDER_INDIVIDUAL_OUTPUT
    if subset.empty:
        analysis_df = pd.DataFrame()
        out_path = Path(analysis_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        analysis_df.to_csv(out_path, index=False)
        combo_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame().to_csv(combo_path, index=False)
        indiv_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame().to_csv(indiv_path, index=False)
        Path(summary_output).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_output).write_text("No rows for Cond=0 and ex2_is_first=1.\n", encoding="utf-8")
        return analysis_df

    subset["ex2_timestamp"] = pd.to_datetime(subset["ex2_timestamp"], errors="coerce")
    subset = subset.dropna(subset=["ex2_timestamp", "ex2_sample_number", "ex2_estimate"])
    model_lookup = build_asymmetric_online_model_lookup(subset)

    rows: List[Dict[str, float | str | int]] = []
    individual_rows: List[Dict[str, float | str | int]] = []
    for user_id, grp in subset.groupby("user_id"):
        ordered = grp.sort_values("ex2_timestamp")
        if len(ordered) < 2:
            continue
        first_sample = int(float(ordered.iloc[0]["ex2_sample_number"]))
        second_sample = int(float(ordered.iloc[1]["ex2_sample_number"]))
        first_type = classify_stimulus_type(first_sample)
        second_type = classify_stimulus_type(second_sample)

        est_by_sample = (
            grp.groupby("ex2_sample_number", as_index=True)["ex2_estimate"]
            .mean()
            .sort_index()
        )
        common_samples = [
            int(float(sn))
            for sn in est_by_sample.index.tolist()
            if int(float(sn)) in model_lookup
        ]
        if len(common_samples) < 2:
            continue

        human_vals = np.asarray([est_by_sample.loc[sn] for sn in common_samples], dtype=float)
        pred_vals = np.asarray([model_lookup[sn][0] for sn in common_samples], dtype=float)
        diag_vals = np.asarray([model_lookup[sn][1] for sn in common_samples], dtype=float)

        corr_predictive = pearson_corr(human_vals, pred_vals)
        corr_diagnostic = pearson_corr(human_vals, diag_vals)
        corr_diff = (
            float(corr_predictive - corr_diagnostic)
            if np.isfinite(corr_predictive) and np.isfinite(corr_diagnostic)
            else np.nan
        )
        rows.append(
            {
                "user_id": str(user_id),
                "first_sample_number": first_sample,
                "second_sample_number": second_sample,
                "first_type": first_type,
                "second_type": second_type,
                "corr_predictive": corr_predictive,
                "corr_diagnostic": corr_diagnostic,
                "corr_diff": corr_diff,
                "n_trials": int(len(ordered)),
            }
        )

        ordered_min = (
            ordered.groupby("ex2_sample_number", as_index=False)
            .agg(ex2_estimate=("ex2_estimate", "mean"), ex2_timestamp=("ex2_timestamp", "min"))
            .sort_values("ex2_timestamp")
            .reset_index(drop=True)
        )
        for trial_idx, row in ordered_min.iterrows():
            sample_number = int(float(row["ex2_sample_number"]))
            pec, pce = model_lookup.get(sample_number, (np.nan, np.nan))
            individual_rows.append(
                {
                    "user_id": str(user_id),
                    "trial_order": int(trial_idx + 1),
                    "sample_number": sample_number,
                    "stimulus_type": classify_stimulus_type(sample_number),
                    "estimate": float(row["ex2_estimate"]),
                    "predictive_prob_pec": float(pec) if np.isfinite(pec) else np.nan,
                    "diagnostic_prob_pce": float(pce) if np.isfinite(pce) else np.nan,
                    "first_sample_number": first_sample,
                    "second_sample_number": second_sample,
                    "first_type": first_type,
                    "second_type": second_type,
                    "corr_predictive_user": corr_predictive,
                    "corr_diagnostic_user": corr_diagnostic,
                    "corr_diff_user": corr_diff,
                }
            )

    analysis_df = pd.DataFrame(rows)
    combo_df = build_combo_summary(analysis_df)
    individual_df = pd.DataFrame(individual_rows)
    out_path = Path(analysis_output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    analysis_df.to_csv(out_path, index=False)
    combo_path.parent.mkdir(parents=True, exist_ok=True)
    combo_df.to_csv(combo_path, index=False)
    indiv_path.parent.mkdir(parents=True, exist_ok=True)
    individual_df.to_csv(indiv_path, index=False)

    if not analysis_df.empty:
        write_order_effect_summary(analysis_df, combo_df, Path(summary_output))
        plot_order_distribution(analysis_df, Path(plot_output))
    else:
        Path(summary_output).parent.mkdir(parents=True, exist_ok=True)
        Path(summary_output).write_text("No valid participants for correlation analysis.\n", encoding="utf-8")

    return analysis_df
