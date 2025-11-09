"""CS/UCS 指標に関する相関解析とクラスタリングを行うモジュール。

    1. CSV を読み込み、条件（実験 × 条件値）ごとにデータを準備する。
    2. 推定値の軌跡でユーザーをクラスタリングする。
    3. CS/UCS を含むモデル指標を算出する。
    4. 全体と各クラスタについて、人間の推定値とモデル指標の相関を計算する。
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from CS_UCS2 import CS, UCS, normalize_condition_value

NUMERIC_EPSILON = 1e-12
DEFAULT_MONTE_CARLO_LOOPS = 40_000
DEFAULT_MAX_CLUSTERS = 2
DEFAULT_RANDOM_STATE = 0
DEFAULT_RESULTS_CSV = "correlation_cluster_results.csv"
DEFAULT_SAMPLE_AVERAGE_CSV = "sample_story_averages_by_condition.csv"
DEFAULT_SAMPLE_PIVOT_CSV = "sample_story_averages_pivot.csv"
DEFAULT_CONDITION_PIVOT_CSV = "sample_condition_averages_pivot.csv"

MODEL_METRIC_COLUMNS = [
    "P(E|C)",
    "P(C|E)",
    "delta_p",
    "CS",
    "UCS",
    "pARIs",
    "DFH",
    "Dice",
    "CS_diff",
    "UCS_diff",
    "CS_ratio",
    "UCS_ratio",
    "CS_single",
    "UCS_single",
]

CONDITION_DEPENDENT_METRICS = [
    "CS_diff",
    "UCS_diff",
    "CS_ratio",
    "UCS_ratio",
    "CS_single",
    "UCS_single",
]

def default_threshold_grid() -> Tuple[float, ...]:
    """Return the default descending threshold grid."""
    values = list(np.arange(1.0, 0.0, -0.1))
    values.append(0.01)
    return tuple(round(float(v), 2) for v in values)


@dataclass(frozen=True)
class CaseDefinition:
    label: str
    prefix: str
    experiment: str
    condition: str
    condition_value: Optional[int]
    data: pd.DataFrame

    @property
    def condition_tag(self) -> str:
        return f"{self.condition}_{self.experiment}"


@dataclass
class ClusterResult:
    matrix: pd.DataFrame

    @property
    def k(self) -> int:
        if self.matrix.empty:
            return 0
        return int(self.matrix["cluster"].max()) + 1

    def members(self, cluster_index: int) -> pd.Index:
        return self.matrix[self.matrix["cluster"] == cluster_index].index

    def size(self, cluster_index: int) -> int:
        return int((self.matrix["cluster"] == cluster_index).sum())


class CorrelationAnalyzer:
    def __init__(
        self,
        csv_path: Path | str,
        max_clusters: int = DEFAULT_MAX_CLUSTERS,
        loops: int = DEFAULT_MONTE_CARLO_LOOPS,
        random_state: int = DEFAULT_RANDOM_STATE,
        debug: bool = False,
    ):
        self.csv_path = Path(csv_path)
        self.max_clusters = int(max_clusters)
        self.loops = int(loops)
        self.random_state = int(random_state)
        self.debug = bool(debug)
        self.df: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def load_data(self) -> pd.DataFrame:
        """Load the CSV file into a pandas DataFrame."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")
        self.df = pd.read_csv(self.csv_path)
        return self.df

    # ------------------------------------------------------------------
    # Cluster and metric helpers
    # ------------------------------------------------------------------
    def _iter_cases(self) -> Iterable[CaseDefinition]:
        """Yield case definitions for each experiment × condition subset."""
        if self.df is None:
            raise RuntimeError("Data frame is not loaded. Call load_data() first.")

        df = self.df
        if "Cond" not in df.columns or "user_id" not in df.columns:
            if self.debug:
                print("[DEBUG] Required columns ('Cond', 'user_id') are missing.")
            return []

        experiments = [
            ("ex1", "Summary"),
            ("ex2", "Online"),
        ]
        condition_labels = {
            0: "Asymmetric",
            1: "Symmetric",
        }

        cases: List[CaseDefinition] = []
        for prefix, experiment_name in experiments:
            flag_col = f"{prefix}_is_first"
            if flag_col not in df.columns:
                if self.debug:
                    print(f"[DEBUG] Missing column '{flag_col}', skipping '{prefix}'.")
                continue

            flagged = df[df[flag_col] == 1].copy()
            if flagged.empty:
                continue

            for cond_value, condition_name in condition_labels.items():
                subset = flagged[flagged["Cond"] == cond_value].copy()
                if subset.empty:
                    continue

                cases.append(
                    CaseDefinition(
                        label=f"Cond{cond_value}_{prefix}",
                        prefix=prefix,
                        experiment=experiment_name,
                        condition=condition_name,
                        condition_value=cond_value,
                        data=subset,
                    )
                )

        return cases

    def _create_cluster_result(
        self,
        df_subset: pd.DataFrame,
        prefix: str,
    ) -> Optional[ClusterResult]:
        """Pivot user estimates and run KMeans clustering."""
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
        if est_col not in df_subset.columns or num_col not in df_subset.columns:
            if self.debug:
                print(
                    f"[DEBUG] Missing columns for clustering ({est_col}, {num_col})."
                )
            return None

        pivot = df_subset.pivot_table(
            index="user_id",
            columns=num_col,
            values=est_col,
            aggfunc="mean",
        ).dropna(how="any")

        if pivot.empty:
            if self.debug:
                print("[DEBUG] Pivot table is empty after dropna; skipping clusters.")
            return None

        X = pivot.to_numpy(dtype=float)
        k = self._find_optimal_k(X)

        if k <= 1:
            labels = np.zeros(len(pivot), dtype=int)
        else:
            model = KMeans(
                n_clusters=k,
                random_state=self.random_state,
                n_init=10,
            )
            labels = model.fit_predict(X)

        cluster_means: Dict[int, float] = {}
        for cluster_idx in range(labels.max() + 1):
            cluster_data = pivot.iloc[labels == cluster_idx]
            if cluster_data.empty:
                cluster_means[cluster_idx] = -np.inf
            else:
                cluster_means[cluster_idx] = float(cluster_data.mean(axis=1).mean())

        order = sorted(cluster_means, key=cluster_means.get, reverse=True)
        remap = {old: new for new, old in enumerate(order)}
        sorted_labels = np.array([remap[label] for label in labels], dtype=int)

        matrix = pivot.copy()
        matrix["cluster"] = sorted_labels
        return ClusterResult(matrix=matrix)

    def _find_optimal_k(self, X: np.ndarray) -> int:
        """Select k using the silhouette score over a reasonable range."""
        n_samples = X.shape[0]
        if n_samples <= 1:
            return 1

        best_k = 1
        best_score = -np.inf
        upper_bound = min(self.max_clusters, n_samples)

        silhouette_scores: List[Tuple[int, float]] = []
        for k in range(2, upper_bound + 1):
            try:
                model = KMeans(
                    n_clusters=k,
                    random_state=self.random_state,
                    n_init=10,
                )
                labels = model.fit_predict(X)
                if len(np.unique(labels)) < 2:
                    continue
                score = silhouette_score(X, labels)
                silhouette_scores.append((k, float(score)))
            except Exception as exc:  # scikit-learn can raise on degenerate data
                if self.debug:
                    print(f"[DEBUG] Unable to evaluate k={k}: {exc}")
                continue

            if score > best_score:
                best_k = k
                best_score = score

        if self.debug and silhouette_scores:
            formatted = ", ".join(f"k={k}: {s:.3f}" for k, s in silhouette_scores)
            print(f"[DEBUG] silhouette scores -> {formatted}")

        return best_k if best_k > 1 else 1

    def _build_model_metrics_table(
        self,
        df_subset: pd.DataFrame,
        prefix: str,
        cs_threshold: float,
        ucs_threshold: float,
        default_cond_value: Optional[int],
    ) -> Optional[pd.DataFrame]:
        """Create a data frame of model metrics per sample number."""
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
        abcd_cols = [f"{prefix}_{c}" for c in ("a", "b", "c", "d")]

        required = set(abcd_cols + [est_col, num_col])
        if not required.issubset(df_subset.columns):
            if self.debug:
                missing = sorted(required.difference(df_subset.columns))
                print(f"[DEBUG] Missing columns for metrics: {missing}")
            return None

        sample_numbers = (
            pd.to_numeric(df_subset[num_col], errors="coerce")
            .dropna()
            .astype(int)
            .unique()
        )
        sample_numbers.sort()

        rows: Dict[int, Dict[str, float]] = {}
        for sample_number in sample_numbers:
            sample_rows = df_subset[df_subset[num_col] == sample_number]
            if sample_rows.empty:
                continue

            counts_series = sample_rows[abcd_cols].iloc[0]
            if counts_series.isnull().any():
                if self.debug:
                    print(f"[DEBUG] Counts missing for sample {sample_number}.")
                continue

            try:
                counts = tuple(int(float(val)) for val in counts_series.values)
            except ValueError:
                if self.debug:
                    print(f"[DEBUG] Non-numeric counts for sample {sample_number}.")
                continue

            is_gene = bool(sample_rows[est_col].mean() >= 0)
            cond_value = default_cond_value
            if "Cond" in sample_rows.columns:
                cond_candidates = (
                    pd.to_numeric(sample_rows["Cond"], errors="coerce")
                    .dropna()
                    .unique()
                )
                if cond_candidates.size > 0:
                    cond_value = int(cond_candidates[0])

            metric_dict = self._metrics_from_counts(
                counts=counts,
                cs_threshold=cs_threshold,
                ucs_threshold=ucs_threshold,
                is_gene=is_gene,
                cond_value=cond_value,
            )
            rows[int(sample_number)] = metric_dict

        if not rows:
            return None

        model_df = pd.DataFrame.from_dict(rows, orient="index")
        model_df = model_df.reindex(columns=MODEL_METRIC_COLUMNS)
        model_df.index.name = "sample_number"
        model_df = model_df.sort_index()
        return model_df

    # ------------------------------------------------------------------
    # Metrics and statistics
    # ------------------------------------------------------------------
    def _metrics_from_counts(
        self,
        counts: Tuple[int, int, int, int],
        cs_threshold: float,
        ucs_threshold: float,
        is_gene: bool,
        cond_value: Optional[int],
    ) -> Dict[str, float]:
        """Compute model metrics from contingency counts."""
        a, b, c, d = counts
        total_a_b = a + b
        total_a_c = a + c
        total_c_d = c + d
        total_a_b_c = a + b + c
        total_2a_b_c = 2 * a + b + c

        metrics = {
            "P(E|C)": a / total_a_b if total_a_b else np.nan,
            "P(C|E)": a / total_a_c if total_a_c else np.nan,
            "delta_p": (a / total_a_b if total_a_b else np.nan)
            - (c / total_c_d if total_c_d else np.nan),
            "CS": self._safe_score(
                CS, counts, cs_threshold, is_gene, label="CS_total"
            ),
            "UCS": self._safe_score(
                UCS, counts, ucs_threshold, is_gene, label="UCS_total"
            ),
            "pARIs": a / total_a_b_c if total_a_b_c else np.nan,
            "DFH": a / np.sqrt(total_a_b * total_a_c)
            if total_a_b and total_a_c
            else np.nan,
            "Dice": (2 * a) / total_2a_b_c if total_2a_b_c else np.nan,
            "CS_diff": np.nan,
            "UCS_diff": np.nan,
            "CS_ratio": np.nan,
            "UCS_ratio": np.nan,
            "CS_single": np.nan,
            "UCS_single": np.nan,
        }

        cond_processed = normalize_condition_value(cond_value)
        if cond_processed == 1:
            cs_ab = self._safe_score(CS, counts, cs_threshold, is_gene, "CS_ab")
            cs_cd = self._safe_score(
                CS, (c, d, a, b), cs_threshold, not is_gene, "CS_cd"
            )
            ucs_ab = self._safe_score(UCS, counts, ucs_threshold, is_gene, "UCS_ab")
            ucs_cd = self._safe_score(
                UCS, (c, d, a, b), ucs_threshold, not is_gene, "UCS_cd"
            )
            cs_single = self._safe_score(
                CS, (a, b, 0, 0), cs_threshold, is_gene, "CS_single"
            )
            ucs_single = self._safe_score(
                UCS, (a, b, 0, 0), ucs_threshold, is_gene, "UCS_single"
            )

            if np.isfinite(cs_ab) and np.isfinite(cs_cd):
                metrics["CS_diff"] = cs_ab - cs_cd
            if np.isfinite(ucs_ab) and np.isfinite(ucs_cd):
                metrics["UCS_diff"] = ucs_ab - ucs_cd

            metrics["CS_ratio"] = self._safe_ratio(cs_ab, cs_cd)
            metrics["UCS_ratio"] = self._safe_ratio(ucs_ab, ucs_cd)
            metrics["CS_single"] = cs_single if np.isfinite(cs_single) else np.nan
            metrics["UCS_single"] = ucs_single if np.isfinite(ucs_single) else np.nan

        return metrics

    def _safe_score(
        self,
        func,
        counts: Tuple[int, int, int, int],
        threshold: float,
        is_gene: bool,
        label: str,
    ) -> float:
        """Safely evaluate CS/UCS scores."""
        try:
            with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
                return float(
                    func(
                        counts,
                        threshold=threshold,
                        is_gene=is_gene,
                        loops=self.loops,
                    )
                )
        except Exception as exc:
            if self.debug:
                print(f"[DEBUG] {label} calculation failed: {exc}")
            return np.nan

    @staticmethod
    def _safe_ratio(numerator: float, denominator: float) -> float:
        if denominator is None or not np.isfinite(denominator):
            return np.nan
        if abs(denominator) < NUMERIC_EPSILON:
            return np.nan
        if numerator is None or not np.isfinite(numerator):
            return np.nan
        return float(numerator / denominator)

    # ------------------------------------------------------------------
    # Correlation helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _round_or_nan(value: float, digits: int = 3) -> float:
        if value is None or not np.isfinite(value):
            return np.nan
        return float(round(value, digits))

    def safe_corr(self, x: np.ndarray, y: np.ndarray) -> float:
        mask = np.isfinite(x) & np.isfinite(y)
        if mask.sum() < 2:
            return np.nan
        x_valid = x[mask]
        y_valid = y[mask]
        if np.nanstd(x_valid) == 0 or np.nanstd(y_valid) == 0:
            return 0.0
        try:
            corr, _ = pearsonr(x_valid, y_valid)
        except Exception:
            return np.nan
        return self._round_or_nan(corr)

    def safe_spearman_corr(self, x: np.ndarray, y: np.ndarray) -> float:
        mask = np.isfinite(x) & np.isfinite(y)
        if mask.sum() < 2:
            return np.nan
        x_valid = x[mask]
        y_valid = y[mask]
        if np.nanstd(x_valid) == 0 or np.nanstd(y_valid) == 0:
            return 0.0
        try:
            corr, _ = spearmanr(x_valid, y_valid)
        except Exception:
            return np.nan
        return self._round_or_nan(corr)

    def _compute_group_correlations(
        self,
        df_subset: pd.DataFrame,
        prefix: str,
        model_df: pd.DataFrame,
        cluster_result: ClusterResult,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Compute correlations for the full group and each cluster."""
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"

        groups: Dict[str, pd.DataFrame] = {"All": df_subset}
        for cluster_index in range(cluster_result.k):
            member_ids = cluster_result.members(cluster_index)
            cluster_df = df_subset[df_subset["user_id"].isin(member_ids)]
            if not cluster_df.empty:
                groups[f"Cluster{cluster_index + 1}"] = cluster_df

        corr_pearson = pd.DataFrame(
            index=groups.keys(), columns=MODEL_METRIC_COLUMNS, dtype=float
        )
        corr_spearman = pd.DataFrame(
            index=groups.keys(), columns=MODEL_METRIC_COLUMNS, dtype=float
        )
        summary = pd.DataFrame(
            index=groups.keys(),
            columns=["estimate_mean", "participants"],
            dtype=float,
        )

        for name, group_df in groups.items():
            if group_df.empty:
                summary.loc[name] = (np.nan, 0)
                corr_pearson.loc[name] = np.nan
                corr_spearman.loc[name] = np.nan
                continue

            summary.loc[name, "estimate_mean"] = float(
                group_df[est_col].mean()
            )
            summary.loc[name, "participants"] = float(
                group_df["user_id"].nunique()
            )

            # Merge group_df with model_df on sample_number to get individual data points
            merged_df = group_df.merge(
                model_df.reset_index(), 
                left_on=num_col, 
                right_on='sample_number', 
                how='inner'
            )
            
            if merged_df.empty:
                corr_pearson.loc[name] = np.nan
                corr_spearman.loc[name] = np.nan
                continue

            y = merged_df[est_col].to_numpy(dtype=float)
            for metric in MODEL_METRIC_COLUMNS:
                x = merged_df[metric].to_numpy(dtype=float)
                corr_pearson.loc[name, metric] = self.safe_corr(x, y)
                corr_spearman.loc[name, metric] = self.safe_spearman_corr(x, y)

        return corr_pearson, corr_spearman, summary

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run_threshold_analysis(
        self,
        thresholds: Optional[Sequence[float]] = None,
        output_path: Optional[Path | str] = None,
    ) -> pd.DataFrame:
        """Run correlation analysis for the requested thresholds."""
        if thresholds is None:
            thresholds = default_threshold_grid()

        if self.df is None:
            self.load_data()

        results: List[Dict[str, float]] = []

        for threshold in thresholds:
            cs_th = float(threshold)
            ucs_th = float(threshold)

            for case in self._iter_cases():
                cluster_result = self._create_cluster_result(case.data, case.prefix)
                if cluster_result is None or cluster_result.k == 0:
                    if self.debug:
                        print(
                            f"[DEBUG] Skipping {case.label} at threshold {threshold}: "
                            "no clusters."
                        )
                    continue

                model_df = self._build_model_metrics_table(
                    df_subset=case.data,
                    prefix=case.prefix,
                    cs_threshold=cs_th,
                    ucs_threshold=ucs_th,
                    default_cond_value=case.condition_value,
                )
                if model_df is None or model_df.empty:
                    if self.debug:
                        print(
                            f"[DEBUG] Skipping {case.label} at threshold {threshold}: "
                            "no model metrics."
                        )
                    continue

                corr_pearson, corr_spearman, summary = self._compute_group_correlations(
                    case.data, case.prefix, model_df, cluster_result
                )

                for group_name in corr_pearson.index:
                    if group_name == "All":
                        continue

                    cluster_index = int(group_name.replace("Cluster", "")) - 1
                    result_row: Dict[str, float] = {
                        "cs_threshold": cs_th,
                        "ucs_threshold": ucs_th,
                        "case_label": case.label,
                        "experiment": case.experiment,
                        "condition": case.condition,
                        "condition_tag": case.condition_tag,
                        "cluster": group_name,
                        "participants": float(cluster_result.size(cluster_index)),
                        "estimate_mean": self._round_or_nan(
                            summary.loc[group_name, "estimate_mean"]
                        ),
                    }

                    for metric in MODEL_METRIC_COLUMNS:
                        result_row[f"{metric}_pearson"] = corr_pearson.loc[
                            group_name, metric
                        ]
                        result_row[f"{metric}_spearman"] = corr_spearman.loc[
                            group_name, metric
                        ]

                    results.append(result_row)

        results_df = pd.DataFrame(results)
        if not results_df.empty:
            # case_labelの順序を指定: Cond0_ex2, Cond1_ex2, Cond0_ex1, Cond1_ex1
            case_order = ["Cond0_ex2", "Cond1_ex2", "Cond0_ex1", "Cond1_ex1"]
            results_df["case_label"] = pd.Categorical(
                results_df["case_label"], 
                categories=case_order, 
                ordered=True
            )
            results_df = results_df.sort_values(
                ["cs_threshold", "case_label", "cluster"],
                ascending=[False, True, True],
            ).reset_index(drop=True)

        if output_path:
            out_path = Path(output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            results_df.to_csv(out_path, index=False)

        return results_df

    def compute_sample_averages(self) -> pd.DataFrame:
        """Compute sample × cover story averages for each condition."""
        if self.df is None:
            self.load_data()

        rows: List[Dict[str, float]] = []
        for case in self._iter_cases():
            est_col = f"{case.prefix}_estimate"
            num_col = f"{case.prefix}_sample_number"
            story_col = f"{case.prefix}_cover_story"

            required = {est_col, num_col, story_col}
            if not required.issubset(case.data.columns):
                if self.debug:
                    missing = sorted(required.difference(case.data.columns))
                    print(f"[DEBUG] Missing columns for averages: {missing}")
                continue

            for sample_number in range(1, 7):
                for story_number in range(1, 13):
                    mask = (case.data[num_col] == sample_number) & (
                        case.data[story_col] == story_number
                    )
                    subset = case.data.loc[mask]

                    if subset.empty:
                        mean_val = np.nan
                        std_val = np.nan
                        count_val = 0
                    else:
                        mean_val = float(subset[est_col].mean())
                        std_val = float(subset[est_col].std(ddof=0))
                        count_val = int(subset.shape[0])

                    rows.append(
                        {
                            "condition_tag": case.condition_tag,
                            "experiment": case.experiment,
                            "condition": case.condition,
                            "sample_number": sample_number,
                            "cover_story": story_number,
                            "mean_estimate": mean_val,
                            "std_estimate": std_val,
                            "count": count_val,
                        }
                    )

        averages_df = pd.DataFrame(rows)
        if averages_df.empty:
            return averages_df

        averages_df = averages_df.sort_values(
            ["condition_tag", "sample_number", "cover_story"]
        ).reset_index(drop=True)
        return averages_df

    def save_sample_averages(
        self,
        averages_df: pd.DataFrame,
        output_dir: Path | str,
    ) -> Dict[str, Path]:
        """Persist sample average tables to CSV files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        outputs: Dict[str, Path] = {}

        rounded_df = averages_df.copy()
        rounded_df["mean_estimate"] = rounded_df["mean_estimate"].round(3)
        rounded_df["std_estimate"] = rounded_df["std_estimate"].round(3)
        outputs["detailed"] = output_dir / DEFAULT_SAMPLE_AVERAGE_CSV
        rounded_df.to_csv(outputs["detailed"], index=False)

        story_pivot = rounded_df.copy()
        story_pivot["condition_story"] = (
            story_pivot["condition_tag"] + "_story" + story_pivot["cover_story"].astype(str)
        )
        story_pivot_table = story_pivot.pivot_table(
            index="sample_number",
            columns="condition_story",
            values="mean_estimate",
        )
        outputs["condition_story_pivot"] = output_dir / DEFAULT_SAMPLE_PIVOT_CSV
        story_pivot_table.to_csv(outputs["condition_story_pivot"])

        condition_pivot = (
            rounded_df.groupby(["condition_tag", "sample_number"])["mean_estimate"]
            .mean()
            .unstack("condition_tag")
        )
        outputs["condition_pivot"] = output_dir / DEFAULT_CONDITION_PIVOT_CSV
        condition_pivot.to_csv(outputs["condition_pivot"])

        return outputs


def parse_thresholds(values: Optional[Sequence[str]]) -> Tuple[float, ...]:
    if not values:
        return default_threshold_grid()

    parsed: List[float] = []
    for value in values:
        try:
            parsed.append(float(value))
        except ValueError as exc:
            raise ValueError(f"Invalid threshold value '{value}'.") from exc
    return tuple(parsed)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run correlation and clustering analysis for CS/UCS metrics."
    )
    parser.add_argument(
        "--csv",
        default="analysis/final_valid_6_samples.csv",
        help="Input CSV file containing experimental data.",
    )
    parser.add_argument(
        "--threshold",
        dest="thresholds",
        action="append",
        help="Threshold value for CS/UCS (use multiple times for several values).",
    )
    parser.add_argument(
        "--max-clusters",
        type=int,
        default=DEFAULT_MAX_CLUSTERS,
        help="Maximum number of clusters to evaluate.",
    )
    parser.add_argument(
        "--loops",
        type=int,
        default=DEFAULT_MONTE_CARLO_LOOPS,
        help="Monte Carlo loops used inside the CS/UCS calculations.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_RESULTS_CSV,
        help="CSV file to store correlation results.",
    )
    parser.add_argument(
        "--averages-dir",
        default=None,
        help="Directory to store sample average tables (defaults to the output directory).",
    )
    parser.add_argument(
        "--skip-sample-averages",
        action="store_true",
        help="Skip generating sample average tables.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging.",
    )

    args = parser.parse_args(argv)

    analyzer = CorrelationAnalyzer(
        csv_path=args.csv,
        max_clusters=args.max_clusters,
        loops=args.loops,
        debug=args.debug,
    )
    analyzer.load_data()

    thresholds = parse_thresholds(args.thresholds)
    results_df = analyzer.run_threshold_analysis(
        thresholds=thresholds,
        output_path=args.output,
    )
    print(
        f"Correlation results saved to {args.output} "
        f"({len(results_df)} rows)."
    )

    if args.skip_sample_averages:
        return 0

    averages_df = analyzer.compute_sample_averages()
    if averages_df.empty:
        print("No sample averages were computed (dataset is empty).")
        return 0

    averages_dir = (
        Path(args.averages_dir)
        if args.averages_dir
        else Path(args.output).resolve().parent
    )

    outputs = analyzer.save_sample_averages(averages_df, averages_dir)
    print("Sample averages saved:")
    for name, path in outputs.items():
        print(f"  - {name}: {path}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
