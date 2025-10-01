# -*- coding: utf-8 -*-
"""
Optimized correlation and clustering analysis for the UCS vs CS experiments.
- Aggregates responses by experiment/condition using the is_first flags.
- Pre-computes CS/UCS scores per stimulus and threshold to avoid repeated Monte Carlo runs.
- Adds condition-wise participant clustering with silhouette-based model selection.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
import winsound
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from CS_UCS import CS, UCS
from scipy.stats import pearsonr, spearmanr
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, silhouette_samples, pairwise_distances
from sklearn.preprocessing import StandardScaler

STIMULUS_PARAMS: Dict[int, Dict[str, int]] = {
    1: {"a": 6, "b": 6, "c": 0, "d": 12},
    2: {"a": 6, "b": 3, "c": 3, "d": 6},
    3: {"a": 6, "b": 0, "c": 6, "d": 0},
    4: {"a": 7, "b": 6, "c": 0, "d": 13},
    5: {"a": 7, "b": 3, "c": 3, "d": 7},
    6: {"a": 7, "b": 0, "c": 6, "d": 1},
}


class CSUCSCache:
    """Caches CS/UCS scores for (threshold, stimulus, is_gene) combinations.

    Monte Carlo 呼び出しを 12 パターン×閾値分に限定し、繰り返し計算を回避する。
    """

    def __init__(self, stimulus_params: Dict[int, Dict[str, int]]) -> None:
        self.stimulus_params = {int(k): dict(v) for k, v in stimulus_params.items()}
        self.cache: Dict[float, Dict[Tuple[int, bool], Tuple[float, float]]] = {}
        self._cluster_summary_cache: Dict[Tuple[float, int, Tuple[Tuple[int, int], ...]], Dict[str, float]] = {}

    @staticmethod
    def _counts_tuple(params: Dict[str, int]) -> Tuple[int, int, int, int]:
        return int(params["a"]), int(params["b"]), int(params["c"]), int(params["d"])

    @staticmethod
    def _safe_model_call(model_fn, counts: Tuple[int, int, int, int], threshold: float, is_gene: bool) -> float:
        try:
            value = model_fn(counts, threshold, bool(is_gene))
            return float(value) if np.isfinite(value) else np.nan
        except Exception:
            return np.nan

    def precompute_all(self, thresholds: Iterable[float]) -> None:
        """Pre-compute every threshold×stimulus×is_gene combination."""
        for threshold in thresholds:
            threshold = float(threshold)
            th_cache = self.cache.setdefault(threshold, {})
            for sample_num, params in self.stimulus_params.items():
                counts = self._counts_tuple(params)
                for is_gene in (False, True):
                    cache_key = (sample_num, is_gene)
                    if cache_key in th_cache:
                        continue
                    cs_val = self._safe_model_call(CS, counts, threshold, is_gene)
                    ucs_val = self._safe_model_call(UCS, counts, threshold, is_gene)
                    th_cache[cache_key] = (cs_val, ucs_val)

    def get_cs_ucs(self, threshold: float, sample_num: int, is_gene: bool) -> Tuple[float, float]:
        """Return cached CS/UCS scores; fall back to NaN if unavailable."""
        th_cache = self.cache.get(float(threshold))
        if th_cache is None:
            return np.nan, np.nan
        return th_cache.get((int(sample_num), bool(is_gene)), (np.nan, np.nan))

    def aggregate_cluster_scores(
        self,
        threshold: float,
        sample_numbers: Iterable[int],
        is_gene_flags: Iterable[bool],
        cluster_label: int,
    ) -> Dict[str, float]:
        """Aggregate CS/UCS scores for a specific cluster and cache the result."""        
        pairs = tuple(sorted((int(sn), int(bool(flag))) for sn, flag in zip(sample_numbers, is_gene_flags) if not pd.isna(sn)))
        if not pairs:
            return {"cluster_label": int(cluster_label), "CS_mean": np.nan, "UCS_mean": np.nan}

        cache_key = (float(threshold), int(cluster_label), pairs)
        if cache_key not in self._cluster_summary_cache:
            cs_vals: List[float] = []
            ucs_vals: List[float] = []
            for sample_num, flag in pairs:
                cs_val, ucs_val = self.get_cs_ucs(threshold, sample_num, bool(flag))
                cs_vals.append(cs_val)
                ucs_vals.append(ucs_val)
            summary = {
                "cluster_label": int(cluster_label),
                "CS_mean": float(np.nanmean(cs_vals)) if cs_vals else np.nan,
                "UCS_mean": float(np.nanmean(ucs_vals)) if ucs_vals else np.nan,
            }
            self._cluster_summary_cache[cache_key] = summary
        return dict(self._cluster_summary_cache[cache_key])

    def get_counts(self, sample_num: int) -> Tuple[int, int, int, int]:
        params = self.stimulus_params.get(int(sample_num))
        if params is None:
            raise KeyError(sample_num)
        return self._counts_tuple(params)


class ClusterAnalyzer:
    """Handles feature preparation, clustering, and cluster diagnostics per condition."""

    def __init__(
        self,
        min_k: int = 2,
        max_k: int = 8,
        min_participants: int = 10,
        random_state: int = 0,
    ) -> None:
        self.min_k = min_k
        self.max_k = max_k
        self.min_participants = min_participants
        self.random_state = random_state

    def prepare_features_by_condition(
        self, sample_df: pd.DataFrame
    ) -> Dict[Tuple[str, str, int], pd.DataFrame]:
        """Create user×stimulus feature matrices for each condition."""
        features_by_condition: Dict[Tuple[str, str, int], pd.DataFrame] = {}
        if sample_df.empty or "sample_number" not in sample_df.columns:
            return features_by_condition

        group_keys = ["experiment", "condition_label", "condition"]
        for (experiment, condition_label, condition_id), group in sample_df.groupby(group_keys):
            valid = group.dropna(subset=["user_id", "sample_number", "estimate_mean"])
            if valid.empty:
                continue
            pivot = valid.pivot_table(
                index="user_id",
                columns="sample_number",
                values="estimate_mean",
                aggfunc="mean",
            )
            pivot = pivot.reindex(sorted(pivot.columns), axis=1)
            pivot = pivot.dropna(how="all")
            if pivot.empty:
                continue

            pivot = pivot.astype(float)
            col_means = pivot.mean(axis=0)
            pivot = pivot.fillna(col_means).fillna(0.0)

            non_constant_cols = [col for col in pivot.columns if pivot[col].nunique(dropna=False) > 1]
            if non_constant_cols:
                pivot = pivot[non_constant_cols]

            if pivot.shape[0] < 2 or pivot.shape[1] == 0:
                continue

            features_by_condition[(str(experiment), str(condition_label), int(condition_id))] = pivot
        return features_by_condition

    def find_optimal_clusters_silhouette(
        self, features: pd.DataFrame
    ) -> Tuple[int, List[Tuple[int, float]]]:
        """Select the number of clusters that maximizes the silhouette score."""
        n_samples = features.shape[0]
        if n_samples < max(self.min_k, 2):
            return 1, []

        scaler = StandardScaler()
        scaled = scaler.fit_transform(features.values)
        results: List[Tuple[int, float]] = []
        upper_k = min(self.max_k, n_samples - 1)
        if upper_k < self.min_k:
            return 1, []

        for k in range(self.min_k, upper_k + 1):
            try:
                model = KMeans(
                    n_clusters=k,
                    random_state=self.random_state,
                    n_init="auto",
                )
                labels = model.fit_predict(scaled)
                if len(set(labels)) < 2:
                    score = np.nan
                else:
                    score = float(silhouette_score(scaled, labels))
            except Exception:
                score = np.nan
            results.append((k, score))

        finite_scores = [item for item in results if np.isfinite(item[1])]
        if finite_scores:
            optimal_k = max(finite_scores, key=lambda item: item[1])[0]
        else:
            optimal_k = max(self.min_k, 1)
        return optimal_k, results

    def perform_clustering_by_condition(
        self,
        features: pd.DataFrame,
        optimal_k: int,
    ) -> Dict[str, object]:
        """Run K-means (with StandardScaler) for the specified number of clusters."""
        scaler = StandardScaler()
        scaled = scaler.fit_transform(features.values)

        if optimal_k <= 1 or features.shape[0] < max(self.min_k, 2):
            labels = np.zeros(features.shape[0], dtype=int)
            centers_scaled = np.mean(scaled, axis=0, keepdims=True)
            silhouette_avg = np.nan
            silhouette_vals = np.full(features.shape[0], np.nan)
        else:
            model = KMeans(
                n_clusters=optimal_k,
                random_state=self.random_state,
                n_init="auto",
            )
            labels = model.fit_predict(scaled)
            try:
                silhouette_vals = silhouette_samples(scaled, labels)
                silhouette_avg = float(np.nanmean(silhouette_vals))
            except Exception:
                silhouette_vals = np.full(features.shape[0], np.nan)
                silhouette_avg = np.nan
            centers_scaled = model.cluster_centers_

        center_distance = np.linalg.norm(scaled - centers_scaled[labels], axis=1)

        if centers_scaled.shape[0] > 1:
            dist_matrix = pairwise_distances(centers_scaled)
            triu = dist_matrix[np.triu_indices_from(dist_matrix, k=1)]
            cluster_separation = float(np.nanmean(triu)) if triu.size else np.nan
        else:
            cluster_separation = 0.0

        centers_original = scaler.inverse_transform(centers_scaled)

        return {
            "labels": labels,
            "scaled_features": scaled,
            "scaler": scaler,
            "centers_scaled": centers_scaled,
            "centers_original": centers_original,
            "center_distance": center_distance,
            "silhouette_samples": silhouette_vals,
            "silhouette_avg": silhouette_avg,
            "cluster_separation": cluster_separation,
        }

    def analyze_cluster_characteristics(
        self,
        features: pd.DataFrame,
        labels: np.ndarray,
        condition_sample_df: pd.DataFrame,
        cs_ucs_cache: CSUCSCache,
        thresholds: Iterable[float],
    ) -> pd.DataFrame:
        """Summarise mean ratings, stimulus patterns, and CS/UCS scores per cluster."""
        summary_rows: List[Dict[str, float]] = []
        thresholds = list(thresholds)
        unique_labels = sorted(int(label) for label in np.unique(labels))

        for cluster_label in unique_labels:
            mask = labels == cluster_label
            cluster_users = features.index[mask]
            cluster_feature_means = features.iloc[mask].mean(axis=0)
            cluster_samples = condition_sample_df[
                condition_sample_df["user_id"].isin(cluster_users)
            ]

            row: Dict[str, float] = {
                "cluster_label": int(cluster_label),
                "n_users": int(mask.sum()),
                "mean_rating": float(cluster_feature_means.mean())
                if not cluster_feature_means.empty
                else np.nan,
                "mean_estimate": float(cluster_samples["estimate"].mean())
                if not cluster_samples.empty
                else np.nan,
            }

            for stim, value in cluster_feature_means.items():
                row[f"stim_{int(stim)}_mean"] = float(value)

            if not cluster_samples.empty and thresholds:
                sample_col_name = f"{cluster_samples['experiment'].iloc[0]}_sample_number"
                if sample_col_name in cluster_samples.columns:
                    sample_series = pd.to_numeric(cluster_samples[sample_col_name], errors="coerce")
                else:
                    sample_series = pd.to_numeric(cluster_samples.get("sample_number"), errors="coerce")

                valid_mask = sample_series.notna() & cluster_samples["is_gene"].notna()
                if valid_mask.any():
                    sample_numbers = sample_series.loc[valid_mask].astype(int).to_numpy(copy=False)
                    is_gene_flags = cluster_samples.loc[valid_mask, "is_gene"].astype(bool).to_numpy(copy=False)
                    for threshold in thresholds:
                        aggregate = cs_ucs_cache.aggregate_cluster_scores(
                            threshold, sample_numbers, is_gene_flags, cluster_label
                        )
                        row[f"CS_mean_{threshold}"] = aggregate.get("CS_mean", np.nan)
                        row[f"UCS_mean_{threshold}"] = aggregate.get("UCS_mean", np.nan)
            summary_rows.append(row)

        return pd.DataFrame(summary_rows)



@dataclass
class CaseData:
    label: str
    prefix: str
    experiment_label: str
    condition_id: int
    condition_label: str
    df: pd.DataFrame
    metrics_df: pd.DataFrame


def compute_correlations(x: np.ndarray, y: np.ndarray) -> Dict[str, float]:
    """Return Pearson and Spearman correlations with NaN-safe handling."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 2:
        return {method: np.nan for method in UnifiedCorrelationAnalyzerOptimized.CORRELATION_METHODS}

    x_clean = x[mask]
    y_clean = y[mask]

    if np.std(x_clean) == 0 or np.std(y_clean) == 0:
        return {method: 0.0 for method in UnifiedCorrelationAnalyzerOptimized.CORRELATION_METHODS}

    results: Dict[str, float] = {}
    try:
        results["spearman"] = float(spearmanr(x_clean, y_clean)[0])
    except Exception:
        results["spearman"] = np.nan
    try:
        results["pearson"] = float(pearsonr(x_clean, y_clean)[0])
    except Exception:
        results["pearson"] = np.nan

    for method in UnifiedCorrelationAnalyzerOptimized.CORRELATION_METHODS:
        value = results.get(method, np.nan)
        results[method] = value if np.isfinite(value) else np.nan
    return results


class UnifiedCorrelationAnalyzerOptimized:
    BASE_METRICS = ["P(E|C)", "P(C|E)", "DeltaP", "pARIs", "DFH", "Dice"]
    CS_VARIANTS = ("CS", "CS_diff", "CS_ratio", "CS_dual")
    UCS_VARIANTS = ("UCS", "UCS_diff", "UCS_ratio", "UCS_dual")
    CS_METRICS = CS_VARIANTS + UCS_VARIANTS
    CORRELATION_METHODS = ("spearman", "pearson")

    def __init__(
        self,
        csv_path: str,
        n_jobs: int = 1,
        enable_plots: bool = True,
        cluster_min_k: int = 2,
        cluster_max_k: int = 8,
        cluster_min_participants: int = 10,
        random_state: int = 0,
    ) -> None:
        self.csv_path = csv_path
        self.n_jobs = n_jobs if n_jobs else 1
        self.enable_plots = enable_plots
        self.random_state = random_state

        self.df: Optional[pd.DataFrame] = None
        self.cases: List[CaseData] = []
        self.cs_ucs_cache = CSUCSCache(STIMULUS_PARAMS)
        self.cluster_analyzer = ClusterAnalyzer(
            min_k=cluster_min_k,
            max_k=cluster_max_k,
            min_participants=cluster_min_participants,
            random_state=random_state,
        )
        self._sample_counts_lookup = self._build_sample_counts_lookup()

    @staticmethod
    def default_thresholds() -> List[float]:
        thresholds = [round(th, 1) for th in np.arange(1.0, 0.0, -0.1)]
        thresholds.append(0.01)
        return thresholds

    def _build_sample_counts_lookup(self) -> np.ndarray:
        if not self.cs_ucs_cache.stimulus_params:
            return np.zeros((0, 4), dtype=np.int16)
        max_sample = int(max(self.cs_ucs_cache.stimulus_params))
        lookup = np.zeros((max_sample + 1, 4), dtype=np.int16)
        for sample_num, params in self.cs_ucs_cache.stimulus_params.items():
            lookup[int(sample_num)] = [
                int(params.get("a", 0)),
                int(params.get("b", 0)),
                int(params.get("c", 0)),
                int(params.get("d", 0)),
            ]
        return lookup

    def load_data(self) -> None:
        self.df = pd.read_csv(self.csv_path)
        print(f"Loaded data: {self.csv_path} (shape={self.df.shape})")
        if "user_id" in self.df.columns:
            print(f"Unique participants: {self.df['user_id'].nunique()}")

    def prepare_cases(self) -> None:
        if self.df is None:
            self.load_data()
        assert self.df is not None

        condition_labels = {0: "Asymmetric", 1: "Symmetric"}
        experiment_specs = [
            ("ex1", "ex1"),
            ("ex2", "ex2"),
        ]

        self.cases = []
        for prefix, experiment_label in experiment_specs:
            flag_col = f"{prefix}_is_first"
            if flag_col not in self.df.columns:
                print(f"Skip experiment: {prefix} (missing column: {flag_col})")
                continue

            df_experiment = self.df[self.df.get(flag_col, 0) == 1].copy()
            if df_experiment.empty:
                print(f"Skip experiment: {prefix} (no rows where {flag_col} == 1)")
                continue

            if "Cond" in df_experiment.columns:
                cond_series = pd.to_numeric(df_experiment["Cond"], errors="coerce")
            else:
                cond_series = pd.Series([np.nan] * len(df_experiment), index=df_experiment.index)

            for condition_id, condition_label in condition_labels.items():
                if cond_series.isna().all() and condition_id != 0:
                    continue

                if cond_series.isna().all():
                    df_case = df_experiment.copy()
                else:
                    mask = cond_series == condition_id
                    df_case = df_experiment[mask].copy()

                if df_case.empty:
                    print(f"Skip case: Cond{condition_id}_{prefix} (no rows)")
                    continue

                case = self._build_case(
                    label=f"Cond{condition_id}_{prefix}",
                    df_case=df_case,
                    prefix=prefix,
                    experiment_label=experiment_label,
                    condition_id=condition_id,
                    condition_label=condition_label,
                )
                if case is not None:
                    self.cases.append(case)

        if not self.cases:
            raise ValueError("No valid cases were found.")

        print(f"Number of cases: {len(self.cases)}")

    def _build_case(
        self,
        label: str,
        df_case: pd.DataFrame,
        prefix: str,
        experiment_label: str,
        condition_id: int,
        condition_label: str,
    ) -> Optional[CaseData]:
        metrics_df = self._prepare_metrics_dataframe(
            df_case=df_case,
            prefix=prefix,
            experiment_label=experiment_label,
            condition_id=condition_id,
            condition_label=condition_label,
        )

        if metrics_df.empty:
            print(f"Skip case: {label} (no valid rows after cleaning)")
            return None

        return CaseData(
            label=label,
            prefix=prefix,
            experiment_label=experiment_label,
            condition_id=condition_id,
            condition_label=condition_label,
            df=df_case,
            metrics_df=metrics_df,
        )
    
    def _prepare_metrics_dataframe(
        self,
        df_case: pd.DataFrame,
        prefix: str,
        experiment_label: str,
        condition_id: int,
        condition_label: str,
    ) -> pd.DataFrame:
        estimate_col = f"{prefix}_estimate"
        sample_col = f"{prefix}_sample_number"

        # 優先パス: sample_number から刺激カウントを復元する高速経路。
        if sample_col in df_case.columns:
            required_cols = ["user_id", estimate_col, sample_col]
            missing = [col for col in required_cols if col not in df_case.columns]
            if missing:
                print(f"Missing columns for prefix {prefix}: {missing}")
                return pd.DataFrame()

            data = df_case[required_cols + (["Cond"] if "Cond" in df_case.columns else [])].copy()
            data.rename(columns={estimate_col: "estimate", sample_col: "sample_number"}, inplace=True)
            data[sample_col] = data["sample_number"]
            data["estimate"] = pd.to_numeric(data["estimate"], errors="coerce")            
            data["sample_number"] = pd.to_numeric(data["sample_number"], errors="coerce")
            data = data.dropna(subset=["estimate", "sample_number"])
            if data.empty:
                return pd.DataFrame()

            # sample_numberが有効な整数範囲内にあることを確認
            data = data[data["sample_number"].notna() & (data["sample_number"] >= 1) & (data["sample_number"] <= 6)]
            if data.empty:
                return pd.DataFrame()

            data["sample_number"] = data["sample_number"].astype(int)
            data[sample_col] = data["sample_number"]

            # Expand count columns via sample_number lookup
            merged = data.reset_index(drop=True)
            sample_numbers = merged["sample_number"].to_numpy(dtype=int, copy=False)
            counts_array = self._sample_counts_lookup[sample_numbers]
            merged[["a", "b", "c", "d"]] = counts_array.astype(int, copy=False)
        else:
            # 後方互換用: 旧仕様の a,b,c,d 列から構成する。
            count_cols = [f"{prefix}_{c}" for c in ("a", "b", "c", "d")]
            required = ["user_id", estimate_col] + count_cols
            missing = [col for col in required if col not in df_case.columns]
            if missing:
                print(f"Missing columns for prefix {prefix}: {missing}")
                return pd.DataFrame()

            merged = df_case[required + (["Cond"] if "Cond" in df_case.columns else [])].copy()
            merged.rename(columns={estimate_col: "estimate"}, inplace=True)
            rename_map = {src: dst for src, dst in zip(count_cols, ["a", "b", "c", "d"])}
            merged.rename(columns=rename_map, inplace=True)
            for col in ["estimate", "a", "b", "c", "d"]:
                merged[col] = pd.to_numeric(merged[col], errors="coerce")
            merged = merged.dropna(subset=["estimate", "a", "b", "c", "d"])
            if merged.empty:
                return pd.DataFrame()
            merged[["a", "b", "c", "d"]] = merged[["a", "b", "c", "d"]].astype(int)            
            merged["sample_number"] = merged.apply(
                lambda row: self._match_sample_number((row["a"], row["b"], row["c"], row["d"])),
                axis=1,
            )
            merged = merged.dropna(subset=["sample_number"])
            if merged.empty:
                return pd.DataFrame()
            # sample_numberが有効な整数範囲内にあることを確認
            merged = merged[merged["sample_number"].notna() & (merged["sample_number"] >= 1) & (merged["sample_number"] <= 6)]
            if merged.empty:
                return pd.DataFrame()
            merged["sample_number"] = merged["sample_number"].astype(int)
            merged[sample_col] = merged["sample_number"]

        merged["condition"] = condition_id
        merged["condition_label"] = condition_label
        merged["experiment"] = experiment_label
        merged["is_gene"] = (merged["estimate"] >= 0).astype(int)
        merged["is_sym"] = 1 if condition_label == "Symmetric" else 0
        if "Cond" not in merged.columns:
            merged["Cond"] = condition_id

        # Compute base metrics with vectorized arithmetic
        metrics_values = self._basic_metrics_vectorized(merged[["a", "b", "c", "d"]])
        merged[self.BASE_METRICS] = metrics_values
        merged['estimate_mean'] = merged['estimate']
        merged['rating_pattern_id'] = (
            merged['experiment'].astype(str)
            + '_'
            + merged['condition_label'].astype(str)
            + '_u'
            + merged['user_id'].astype(str)
            + '_s'
            + merged['sample_number'].astype(str)
        )

        return merged.reset_index(drop=True)

    def _basic_metrics(self, a: int, b: int, c: int, d: int) -> Dict[str, float]:
        def safe_div(numerator: float, denominator: float) -> float:
            return numerator / denominator if denominator else np.nan

        pe_c = safe_div(a, a + b)
        pc_e = safe_div(a, a + c)
        p_e_given_not_c = safe_div(c, c + d)
        delta_p = pe_c - p_e_given_not_c if not (np.isnan(pe_c) or np.isnan(p_e_given_not_c)) else np.nan
        paris = safe_div(a, a + b + c)
        dfh = a / math.sqrt((a + b) * (a + c)) if (a + b) and (a + c) else np.nan
        dice = safe_div(2 * a, 2 * a + b + c)

        return {
            "P(E|C)": pe_c,
            "P(C|E)": pc_e,
            "DeltaP": delta_p,
            "pARIs": paris,
            "DFH": dfh,
            "Dice": dice,
        }

    def _basic_metrics_vectorized(self, counts: pd.DataFrame) -> pd.DataFrame:
        if counts.empty:
            return pd.DataFrame(index=counts.index, columns=self.BASE_METRICS, dtype=float)

        counts_array = counts.to_numpy(dtype=float, copy=False)
        a = counts_array[:, 0]
        b = counts_array[:, 1]
        c = counts_array[:, 2]
        d = counts_array[:, 3]

        denom_a_b = a + b
        denom_a_c = a + c
        denom_c_d = c + d
        denom_paris = a + b + c
        denom_dice = 2 * a + b + c
        denom_dfh = np.sqrt((a + b) * (a + c))

        pe_c = np.divide(a, denom_a_b, out=np.full_like(a, np.nan), where=denom_a_b != 0)
        pc_e = np.divide(a, denom_a_c, out=np.full_like(a, np.nan), where=denom_a_c != 0)
        p_e_given_not_c = np.divide(c, denom_c_d, out=np.full_like(c, np.nan), where=denom_c_d != 0)
        delta_p = pe_c - p_e_given_not_c
        paris = np.divide(a, denom_paris, out=np.full_like(a, np.nan), where=denom_paris != 0)
        dfh = np.divide(a, denom_dfh, out=np.full_like(a, np.nan), where=denom_dfh != 0)
        dice = np.divide(2 * a, denom_dice, out=np.full_like(a, np.nan), where=denom_dice != 0)

        return pd.DataFrame(
            {
                "P(E|C)": pe_c,
                "P(C|E)": pc_e,
                "DeltaP": delta_p,
                "pARIs": paris,
                "DFH": dfh,
                "Dice": dice,
            },
            index=counts.index,
        )

    def _compute_base_correlations(self, sample_df: pd.DataFrame, ratings: np.ndarray) -> Dict[str, float]:
        correlations: Dict[str, float] = {}

        if len(ratings) == 0 or len(sample_df) == 0:
            for metric in self.BASE_METRICS:
                for method in self.CORRELATION_METHODS:
                    correlations[f"{metric}_{method}"] = np.nan
            return correlations

        rating_series = sample_df.get("estimate_mean")
        if rating_series is None:
            rating_series = sample_df.get("estimate")
        if rating_series is None:
            for metric in self.BASE_METRICS:
                for method in self.CORRELATION_METHODS:
                    correlations[f"{metric}_{method}"] = np.nan
            return correlations

        rating_array = np.asarray(rating_series, dtype=float)
        valid_mask = ~np.isnan(rating_array)
        if valid_mask.sum() < 2:
            for metric in self.BASE_METRICS:
                for method in self.CORRELATION_METHODS:
                    correlations[f"{metric}_{method}"] = np.nan
            return correlations

        valid_ratings = rating_array[valid_mask]
        valid_sample_df = sample_df.loc[valid_mask].reset_index(drop=True)

        for metric in self.BASE_METRICS:
            if metric in valid_sample_df.columns:
                values = valid_sample_df[metric].to_numpy(dtype=float)
                metric_corrs = compute_correlations(values, valid_ratings)
                for method in self.CORRELATION_METHODS:
                    correlations[f"{metric}_{method}"] = metric_corrs.get(method, np.nan)
            else:
                for method in self.CORRELATION_METHODS:
                    correlations[f"{metric}_{method}"] = np.nan
        return correlations

    def _compute_cs_ucs_vector(
        self,
        sample_df: pd.DataFrame,
        cs_th: float,
        ucs_th: float,
    ) -> Dict[str, np.ndarray]:
        metric_buffers: Dict[str, List[float]] = {key: [] for key in self.CS_METRICS}
        for row in sample_df.itertuples():
            sample_number = getattr(row, "sample_number", None)
            metrics = self._cs_ucs(
                row.a,
                row.b,
                row.c,
                row.d,
                cs_th,
                ucs_th,
                bool(getattr(row, "is_gene", 0)),
                int(getattr(row, "is_sym", 0)),
                sample_number=sample_number,
            )
            for key in self.CS_METRICS:
                metric_buffers[key].append(metrics.get(key, np.nan))
        return {key: np.asarray(values, dtype=float) for key, values in metric_buffers.items()}

    def _cs_ucs(
        self,
        a: int,
        b: int,
        c: int,
        d: int,
        cs_th: float,
        ucs_th: float,
        is_gene: bool,
        is_sym: int,
        sample_number: Optional[int] = None,
    ) -> Dict[str, float]:
        metrics: Dict[str, float] = {key: np.nan for key in self.CS_METRICS}

        cache_sample = sample_number if sample_number is not None else self._match_sample_number((a, b, c, d))
        if cache_sample is not None:
            cs_base, ucs_base = self.cs_ucs_cache.get_cs_ucs(cs_th, cache_sample, is_gene)
        else:
            cs_base = self._safe_cs((a, b, c, d), cs_th, is_gene)
            ucs_base = self._safe_ucs((a, b, c, d), ucs_th, is_gene)
        metrics["CS"] = cs_base
        metrics["UCS"] = ucs_base

        if is_sym == 1:
            pos_counts = (a, b, 0, 0)
            neg_counts = (c, d, 0, 0)

            cs_pos = self._safe_cs(pos_counts, cs_th, is_gene)
            cs_neg = self._safe_cs(neg_counts, cs_th, is_gene)
            metrics["CS_diff"] = cs_pos - cs_neg if np.isfinite(cs_pos) and np.isfinite(cs_neg) else np.nan
            metrics["CS_ratio"] = self._safe_ratio(cs_pos, cs_neg)
            metrics["CS_dual"] = self._safe_cs((a, b, c, d), cs_th, is_gene, alt_counts=pos_counts, null_counts=neg_counts)

            ucs_pos = self._safe_ucs(pos_counts, ucs_th, is_gene)
            ucs_neg = self._safe_ucs(neg_counts, ucs_th, is_gene)
            metrics["UCS_diff"] = ucs_pos - ucs_neg if np.isfinite(ucs_pos) and np.isfinite(ucs_neg) else np.nan
            metrics["UCS_ratio"] = self._safe_ratio(ucs_pos, ucs_neg)
            metrics["UCS_dual"] = self._safe_ucs((a, b, c, d), ucs_th, is_gene, alt_counts=pos_counts, null_counts=neg_counts)
        else:
            metrics["CS_diff"] = np.nan
            metrics["CS_ratio"] = np.nan
            metrics["CS_dual"] = cs_base
            metrics["UCS_diff"] = np.nan
            metrics["UCS_ratio"] = np.nan
            metrics["UCS_dual"] = ucs_base

        return metrics

    @staticmethod
    def _match_sample_number(counts: Tuple[int, int, int, int]) -> Optional[int]:
        for sample_num, params in STIMULUS_PARAMS.items():
            if (params["a"], params["b"], params["c"], params["d"]) == counts:
                return sample_num
        return None

    @staticmethod
    def _safe_ratio(numerator: float, denominator: float) -> float:
        if not np.isfinite(numerator) or not np.isfinite(denominator):
            return np.nan
        if abs(denominator) < 1e-12:
            return np.nan
        try:
            return float(numerator / denominator)
        except ZeroDivisionError:
            return np.nan

    @staticmethod
    def _safe_cs(
        counts: Tuple[int, int, int, int],
        threshold: float,
        is_gene: bool,
        alt_counts: Optional[Tuple[int, int, int, int]] = None,
        null_counts: Optional[Tuple[int, int, int, int]] = None,
    ) -> float:
        try:
            value = CS(counts, threshold, bool(is_gene), alt_counts=alt_counts, null_counts=null_counts)
            return float(value) if np.isfinite(value) else np.nan
        except Exception:
            return np.nan

    @staticmethod
    def _safe_ucs(
        counts: Tuple[int, int, int, int],
        threshold: float,
        is_gene: bool,
        alt_counts: Optional[Tuple[int, int, int, int]] = None,
        null_counts: Optional[Tuple[int, int, int, int]] = None,
    ) -> float:
        try:
            value = UCS(counts, threshold, bool(is_gene), alt_counts=alt_counts, null_counts=null_counts)
            return float(value) if np.isfinite(value) else np.nan
        except Exception:
            return np.nan

    def run(self, thresholds: Iterable[float]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        thresholds = list(thresholds) or self.default_thresholds()
        self.prepare_cases()
        self.cs_ucs_cache.precompute_all(thresholds)

        condition_rows: List[Dict[str, float]] = []
        sample_frames: List[pd.DataFrame] = []

        for case in self.cases:
            metrics_df = case.metrics_df.copy()
            if metrics_df.empty:
                continue

            ratings = metrics_df["estimate"].to_numpy(dtype=float)
            sample_frames.append(metrics_df.assign(case_label=case.label))
            sample_col = f"{case.prefix}_sample_number"
            for threshold in thresholds:
                cs_values: List[float] = []
                ucs_values: List[float] = []
                for row in metrics_df.itertuples():
                    sample_attr = getattr(row, sample_col, np.nan) if hasattr(row, sample_col) else np.nan
                    if pd.isna(sample_attr):
                        sample_attr = getattr(row, "sample_number", np.nan) if hasattr(row, "sample_number") else np.nan
                    is_gene = bool(getattr(row, "is_gene", 0))
                    if pd.isna(sample_attr):
                        counts = (int(row.a), int(row.b), int(row.c), int(row.d))
                        cs_val = self._safe_cs(counts, threshold, is_gene)
                        ucs_val = self._safe_ucs(counts, threshold, is_gene)
                    else:
                        sample_num = int(sample_attr)
                        cs_val, ucs_val = self.cs_ucs_cache.get_cs_ucs(threshold, sample_num, is_gene)
                    cs_values.append(cs_val)
                    ucs_values.append(ucs_val)

                cs_values = np.asarray(cs_values, dtype=float)
                ucs_values = np.asarray(ucs_values, dtype=float)

                cs_corr = compute_correlations(cs_values, ratings)
                ucs_corr = compute_correlations(ucs_values, ratings)

                condition_rows.append(
                    {
                        "Experiment": case.experiment_label,
                        "Condition": case.condition_label,
                        "condition_id": case.condition_id,
                        "CS_threshold": threshold,
                        "UCS_threshold": threshold,
                        "n_trials": float(len(metrics_df)),
                        "n_users": float(metrics_df["user_id"].nunique()),
                        "estimate_mean": float(np.nanmean(ratings)) if ratings.size else np.nan,
                        "CS_spearman": cs_corr.get("spearman", np.nan),
                        "CS_pearson": cs_corr.get("pearson", np.nan),
                        "UCS_spearman": ucs_corr.get("spearman", np.nan),
                        "UCS_pearson": ucs_corr.get("pearson", np.nan),
                    }
                )

        cluster_df = pd.DataFrame()
        condition_df = pd.DataFrame(condition_rows)
        sample_df = pd.concat(sample_frames, ignore_index=True) if sample_frames else pd.DataFrame()

        cluster_records: List[Dict[str, object]] = []
        condition_cluster_metrics: Dict[Tuple[str, str, int], Dict[str, float]] = {}
        sample_cluster_meta: List[Dict[str, object]] = []

        if not sample_df.empty:
            feature_map = self.cluster_analyzer.prepare_features_by_condition(sample_df)
            for key, features in feature_map.items():
                experiment, condition_label, condition_id = key
                if features.shape[0] < self.cluster_analyzer.min_participants:
                    condition_cluster_metrics[key] = {
                        "optimal_n_clusters": 1,
                        "mean_silhouette_score": np.nan,
                        "cluster_separation_index": np.nan,
                    }
                    continue

                optimal_k, _ = self.cluster_analyzer.find_optimal_clusters_silhouette(features)
                clustering_result = self.cluster_analyzer.perform_clustering_by_condition(features, optimal_k)

                condition_sample_df = sample_df[(sample_df["experiment"] == experiment) & (sample_df["condition_label"] == condition_label) & (sample_df["condition"] == condition_id)]

                cluster_summary = self.cluster_analyzer.analyze_cluster_characteristics(
                    features,
                    clustering_result["labels"],
                    condition_sample_df,
                    self.cs_ucs_cache,
                    thresholds,
                )
                summary_dict = {
                    row["cluster_label"]: {k: row[k] for k in cluster_summary.columns if k != "cluster_label"}
                    for row in cluster_summary.to_dict("records")
                }

                assignment_df = pd.DataFrame({
                    "user_id": features.index,
                    "cluster_label": clustering_result["labels"],
                    "cluster_center_distance": clustering_result["center_distance"],
                    "silhouette_score": clustering_result["silhouette_samples"],
                })

                assignment_df["within_cluster_rank"] = assignment_df.groupby("cluster_label")["cluster_center_distance"].rank("dense", ascending=True)
                distance_span = assignment_df.groupby("cluster_label")["cluster_center_distance"].transform(lambda x: x.max() - x.min())
                min_distance = assignment_df.groupby("cluster_label")["cluster_center_distance"].transform("min")
                repr_score = np.where(
                    distance_span > 1e-12,
                    1.0 - ((assignment_df["cluster_center_distance"] - min_distance) / distance_span),
                    1.0,
                )
                assignment_df["cluster_representativeness"] = np.clip(repr_score, 0.0, 1.0)

                for _, row in assignment_df.iterrows():
                    characteristics = summary_dict.get(int(row.cluster_label), {})
                    characteristics_payload = {
                        key_: (None if pd.isna(val) else float(val) if isinstance(val, (np.floating, np.integer)) else val)
                        for key_, val in characteristics.items()
                    }
                    cluster_records.append({
                        "user_id": row.user_id,
                        "experiment": experiment,
                        "condition": condition_label,
                        "condition_id": condition_id,
                        "cluster_label": int(row.cluster_label),
                        "silhouette_score": float(row.silhouette_score) if np.isfinite(row.silhouette_score) else np.nan,
                        "cluster_center_distance": float(row.cluster_center_distance),
                        "cluster_characteristics": json.dumps(characteristics_payload, ensure_ascii=False),
                    })
                    sample_cluster_meta.append({
                        "experiment": experiment,
                        "condition_label": condition_label,
                        "condition": condition_id,
                        "user_id": row.user_id,
                        "cluster_label": int(row.cluster_label),
                        "within_cluster_rank": float(row.within_cluster_rank),
                        "cluster_representativeness": float(row.cluster_representativeness),
                    })

                condition_cluster_metrics[key] = {
                    "optimal_n_clusters": int(max(optimal_k, 1)),
                    "mean_silhouette_score": float(clustering_result["silhouette_avg"]) if np.isfinite(clustering_result["silhouette_avg"]) else np.nan,
                    "cluster_separation_index": float(clustering_result["cluster_separation"]) if np.isfinite(clustering_result["cluster_separation"]) else np.nan,
                }

        if cluster_records:
            cluster_df = pd.DataFrame(cluster_records)
            cluster_df.sort_values(["experiment", "condition", "cluster_label", "user_id"], inplace=True)

        if not condition_df.empty:
            if condition_cluster_metrics:
                metrics_records = [{"Experiment": key[0], "Condition": key[1], "condition_id": key[2], **metrics} for key, metrics in condition_cluster_metrics.items()]
                metrics_df = pd.DataFrame(metrics_records)
                condition_df = condition_df.merge(metrics_df, on=["Experiment", "Condition", "condition_id"], how="left")
            else:
                condition_df["optimal_n_clusters"] = np.nan
                condition_df["mean_silhouette_score"] = np.nan
                condition_df["cluster_separation_index"] = np.nan
            condition_df.sort_values(["Experiment", "condition_id", "CS_threshold"], inplace=True)

        if not sample_df.empty:
            sample_df.sort_values(["experiment", "condition", "user_id", "sample_number"], inplace=True)
            if sample_cluster_meta:
                meta_df = pd.DataFrame(sample_cluster_meta).drop_duplicates(["experiment", "condition_label", "condition", "user_id"])
                sample_df = sample_df.merge(meta_df, on=["experiment", "condition_label", "condition", "user_id"], how="left")
            else:
                sample_df["cluster_label"] = np.nan
                sample_df["within_cluster_rank"] = np.nan
                sample_df["cluster_representativeness"] = np.nan

        return cluster_df, condition_df, sample_df

    def create_visualizations(self, cluster_df: pd.DataFrame, sample_df: pd.DataFrame) -> None:
        if not self.enable_plots:
            return
        print("Visualization step skipped in optimized workflow.")

    @staticmethod
    def save_outputs(
        cluster_df: pd.DataFrame,
        condition_df: pd.DataFrame,
        sample_df: pd.DataFrame,
        cluster_path: str,
        condition_path: str,
        sample_path: str,
    ) -> None:
        if not cluster_df.empty:
            cluster_df.to_csv(cluster_path, index=False, encoding="utf-8-sig")
            print(f"Saved cluster results: {cluster_path}")
        if not condition_df.empty:
            condition_df.to_csv(condition_path, index=False, encoding="utf-8-sig")
            print(f"Saved condition results: {condition_path}")
        if not sample_df.empty:
            sample_df.to_csv(sample_path, index=False, encoding="utf-8-sig")
            print(f"Saved sample results: {sample_path}")


def parse_thresholds(values: Optional[List[float]]) -> List[float]:
    if not values:
        return UnifiedCorrelationAnalyzerOptimized.default_thresholds()
    return sorted(set(values), reverse=True)


def main() -> None:
    start_time = time.perf_counter()

    parser = argparse.ArgumentParser(description="Unified correlation analysis (optimized cache)")
    parser.add_argument("--data", default="final_valid_6_samples.csv", help="Input CSV path")
    parser.add_argument("--thresholds", type=float, nargs="*", help="CS/UCS threshold list")
    parser.add_argument("--n-jobs", type=int, default=1, help="Parallel jobs (unused placeholder)")
    parser.add_argument("--no-plots", action="store_true", help="Disable plot generation")
    parser.add_argument("--cluster-output", default="unified_basic_correlation_results.csv", help="Cluster output")
    parser.add_argument("--condition-output", default="condition_basic_correlation_results.csv", help="Condition output")
    parser.add_argument("--sample-output", default="unified_basic_sample_metrics.csv", help="Sample output")
    args = parser.parse_args()

    thresholds = parse_thresholds(args.thresholds)

    analyzer = UnifiedCorrelationAnalyzerOptimized(
        csv_path=args.data,
        n_jobs=args.n_jobs,
        enable_plots=not args.no_plots,
    )

    cluster_df, condition_df, sample_df = analyzer.run(thresholds)
    analyzer.save_outputs(cluster_df, condition_df, sample_df, args.cluster_output, args.condition_output, args.sample_output)

    elapsed = time.perf_counter() - start_time
    print(f"Elapsed time: {elapsed:.2f} seconds")
    try:
        winsound.MessageBeep()
    except Exception:
        print("", end="", flush=True)


if __name__ == "__main__":
    main()
