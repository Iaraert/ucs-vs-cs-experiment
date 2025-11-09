"""
Python で実装された Sparse-and-Strong (SS) 因果支持モデル。

このモジュールは、`SSmodelmain.m` および関連するヘルパー関数で提供される
MATLAB 実装を模倣しています。目標は、SS 事前分布の下で因果リンク (Graph 1) と
リンクなしのベースライン (Graph 0) に対する事後証拠を計算し、
因果強度パラメータ `w1` の事後分布を要約することです。

SS モデルは、原因と結果の関係を以下の観点から評価します：
- 疎性（Sparseness）: ほとんどの潜在的原因は実際には効果を持たない
- 強さ（Strength）: もし原因が効果を持つなら、その影響は強い

基本的な実行例
--------------
組み込みデータセットを利用する場合:

    python ss_model.py --dataset exp1 --alpha 5 --beta 20 --grid-size 401

CSV ファイル（列: ec, nec, enc, nenc, direction）を読み込む場合:

    python ss_model.py --input ./tables.csv --output ./results.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

import numpy as np

# 対数/指数計算を数値的に安定に保つための小さな定数
# LOG_EPS: 対数計算でゼロを避けるための最小値
# GRID_EPS: グリッド計算で数値オーバーフローを防ぐための最小値
LOG_EPS = 1e-300
GRID_EPS = 1e-12


@dataclass(frozen=True)
class ContingencyTable:
    """単一の分割表（クロス集計表）のカウントデータ。
    
    因果関係の分析において、原因（cause）と結果（effect）の有無による
    4つのセルに分類された観測データを表現します。

    Parameters
    ----------
    ec : int
        結果あり・原因ありの試行回数（Effect present, Cause present）
    nec : int
        結果なし・原因ありの試行回数（No Effect, Cause present）
    enc : int
        結果あり・原因なしの試行回数（Effect present, No Cause）
    nenc : int
        結果なし・原因なしの試行回数（No Effect, No Cause）
    direction : int
        因果方向の指定: 1 (生成的), -1 (抑制的), 0 (不明)
        - 生成的: 原因が結果を促進する
        - 抑制的: 原因が結果を抑制する
        - 不明: 生成的・抑制的両方を考慮
    """

    ec: int
    nec: int
    enc: int
    nenc: int
    direction: int


@dataclass(frozen=True)
class SSResult:
    """分割表に対するSSモデルの出力結果をまとめたデータクラス。
    
    Attributes
    ----------
    prob_g1 : float
        因果リンクが存在するグラフ（Graph 1）の事後確率
    prob_g0 : float 
        因果リンクが存在しないグラフ（Graph 0）の事後確率
    log_support : float
        因果リンクに対する対数サポート値（Graph 1 vs Graph 0の対数尤度比）
    w1_mode : float
        因果強度パラメータw1の事後分布の最頻値（モード）
    w1_mean : float
        因果強度パラメータw1の事後分布の平均値
    w1_entropy : float
        因果強度パラメータw1の事後分布のエントロピー（不確実性の指標）
    """

    prob_g1: float
    prob_g0: float
    log_support: float
    w1_mode: float
    w1_mean: float
    w1_entropy: float


class SSModel:
    """Sparse-and-Strong事前分布の下で分割表を評価するモデル。

    このモデルは、w0（背景生成強度）とw1（候補因果強度）の矩形グリッド上での
    数値積分に依存しています。グリッド解像度は実行時間と精度のトレードオフを
    制御します。
    
    Parameters
    ----------
    alpha : float
        疎性パラメータ。値が大きいほど、因果関係が存在しない（疎性）を強く仮定
    beta : float
        強度パラメータ。値が大きいほど、因果関係が存在する場合は強い効果を仮定
    grid_size : int
        数値積分のためのグリッドサイズ（デフォルト: 401）
    """

    def __init__(self, alpha: float, beta: float, grid_size: int = 401) -> None:
        if grid_size < 2:
            raise ValueError("grid_size must be >= 2 to perform numerical integration.")

        self.alpha = float(alpha)
        self.beta = float(beta)
        self.grid = np.linspace(0.0, 1.0, grid_size)
        self.w0_grid, self.w1_grid = np.meshgrid(self.grid, self.grid, indexing="ij")

        # 複数のケースで再利用するため、事前分布とその正規化定数を事前計算
        self._log_prior_gen = self._prepare_log_prior(self._ss_prior_generative())
        self._log_prior_prev = self._prepare_log_prior(self._ss_prior_preventive())
        self._log_prior0_gen = self._prepare_log_prior1d(self._ss_prior_graph0_generative())
        self._log_prior0_prev = self._prepare_log_prior1d(self._ss_prior_graph0_preventive())

    # ------------------------------------------------------------------
    # パブリック API
    # ------------------------------------------------------------------
    def evaluate_all(self, tables: Sequence[ContingencyTable]) -> List[SSResult]:
        """複数の分割表のコレクションを評価する。"""
        return [self.evaluate_one(table) for table in tables]

    def evaluate_one(self, table: ContingencyTable) -> SSResult:
        """単一の分割表に対してSSモデルを評価する。"""
        if table.direction == 1:
            return self._evaluate_generative(table)
        if table.direction == -1:
            return self._evaluate_preventive(table)
        if table.direction == 0:
            return self._evaluate_unknown(table)
        raise ValueError(f"Unsupported direction flag {table.direction}; expected -1, 0, or 1.")

    # ------------------------------------------------------------------
    # 生成的 / 抑制的評価
    # ------------------------------------------------------------------
    def _evaluate_generative(self, table: ContingencyTable) -> SSResult:
        log_integrand = (
            self._log_likelihood_generative(table)
            + self._log_prior_gen
        )

        evidence_g1, posterior_density = self._integrate_evidence(log_integrand)
        comb_factor = math.exp(self._log_combination(table))
        prob_g1 = comb_factor * evidence_g1
        evidence_g0 = self._integrate_graph0(table, self._log_prior0_gen)
        prob_g0 = comb_factor * evidence_g0
        log_support = math.log(max(evidence_g1, LOG_EPS)) - math.log(max(evidence_g0, LOG_EPS))
        w1_mean, w1_mode, w1_entropy = self._summarise_w1(posterior_density)

        return SSResult(prob_g1=prob_g1, prob_g0=prob_g0, log_support=log_support,
                        w1_mode=w1_mode, w1_mean=w1_mean, w1_entropy=w1_entropy)

    def _evaluate_preventive(self, table: ContingencyTable) -> SSResult:
        log_integrand = (
            self._log_likelihood_preventive(table)
            + self._log_prior_prev
        )

        evidence_g1, posterior_density = self._integrate_evidence(log_integrand)
        comb_factor = math.exp(self._log_combination(table))
        prob_g1 = comb_factor * evidence_g1
        evidence_g0 = self._integrate_graph0(table, self._log_prior0_prev)
        prob_g0 = comb_factor * evidence_g0
        log_support = math.log(max(evidence_g1, LOG_EPS)) - math.log(max(evidence_g0, LOG_EPS))
        w1_mean, w1_mode, w1_entropy = self._summarise_w1(posterior_density)

        return SSResult(prob_g1=prob_g1, prob_g0=prob_g0, log_support=log_support,
                        w1_mode=w1_mode, w1_mean=w1_mean, w1_entropy=w1_entropy)

    def _evaluate_unknown(self, table: ContingencyTable) -> SSResult:
        gen_result = self._evaluate_generative(table)
        prev_result = self._evaluate_preventive(table)

        comb_factor = math.exp(self._log_combination(table))
        evid_g1_gen = gen_result.prob_g1 / comb_factor
        evid_g1_prev = prev_result.prob_g1 / comb_factor
        evid_g0_gen = gen_result.prob_g0 / comb_factor
        evid_g0_prev = prev_result.prob_g0 / comb_factor

        prob_g1 = comb_factor * (evid_g1_gen + evid_g1_prev)
        prob_g0 = comb_factor * (evid_g0_gen + evid_g0_prev)
        log_support = math.log(max(evid_g1_gen + evid_g1_prev, LOG_EPS)) - math.log(max(evid_g0_gen + evid_g0_prev, LOG_EPS))

        # 各因果方向に割り当てられた確率で事後統計を重み付け
        if prob_g1 > 0.0:
            weight_gen = gen_result.prob_g1 / prob_g1
            weight_prev = prev_result.prob_g1 / prob_g1
        else:
            weight_gen = weight_prev = 0.5

        # 抑制的強度は効果を減らすため、MATLABコードに合わせて減算
        w1_mean = weight_gen * gen_result.w1_mean - weight_prev * prev_result.w1_mean
        w1_mode = weight_gen * gen_result.w1_mode - weight_prev * prev_result.w1_mode
        # エントロピーは常に正の寄与として報告
        w1_entropy = weight_gen * gen_result.w1_entropy + weight_prev * prev_result.w1_entropy

        return SSResult(prob_g1=prob_g1, prob_g0=prob_g0, log_support=log_support,
                        w1_mode=w1_mode, w1_mean=w1_mean, w1_entropy=w1_entropy)

    # ------------------------------------------------------------------
    # 尤度関数の構築
    # ------------------------------------------------------------------
    def _log_likelihood_generative(self, table: ContingencyTable) -> np.ndarray:
        """Noisy-OR生成モデルの下での対数尤度を計算する。
        
        生成的因果関係では、原因が結果を促進する。背景要因w0と
        候補原因w1が独立して結果を生成し、両方が失敗した場合のみ
        結果が生じない（Noisy-ORモデル）。
        """
        w0 = self.w0_grid
        w1 = self.w1_grid
        enc = table.enc
        nenc = table.nenc
        ec = table.ec
        nec = table.nec

        log_terms = (
            enc * np.log(np.clip(w0, GRID_EPS, 1.0))
            + nenc * np.log(np.clip(1.0 - w0, GRID_EPS, 1.0))
        )
        term_effect = 1.0 - (1.0 - w0) * (1.0 - w1)
        term_no_effect = (1.0 - w0) * (1.0 - w1)

        log_terms += ec * np.log(np.clip(term_effect, GRID_EPS, 1.0))
        log_terms += nec * np.log(np.clip(term_no_effect, GRID_EPS, 1.0))
        return log_terms

    def _log_likelihood_preventive(self, table: ContingencyTable) -> np.ndarray:
        """Noisy-AND-NOT抑制モデルの下での対数尤度を計算する。
        
        抑制的因果関係では、原因が結果を阻害する。背景要因w0が結果を
        生成するが、候補原因w1がその効果を阻害する（Noisy-AND-NOTモデル）。
        """
        w0 = self.w0_grid
        w1 = self.w1_grid
        enc = table.enc
        nenc = table.nenc
        ec = table.ec
        nec = table.nec

        log_terms = (
            enc * np.log(np.clip(w0, GRID_EPS, 1.0))
            + nenc * np.log(np.clip(1.0 - w0, GRID_EPS, 1.0))
        )
        term_effect = w0 * (1.0 - w1)
        term_no_effect = 1.0 - w0 * (1.0 - w1)

        log_terms += ec * np.log(np.clip(term_effect, GRID_EPS, 1.0))
        log_terms += nec * np.log(np.clip(term_no_effect, GRID_EPS, 1.0))
        return log_terms

    def _log_likelihood_graph0(self, table: ContingencyTable) -> np.ndarray:
        """原因が効果を持たないヌルモデルの対数尤度を計算する。"""
        total_e = table.enc + table.ec
        total_ne = table.nenc + table.nec
        grid = self.grid

        return (
            total_e * np.log(np.clip(grid, GRID_EPS, 1.0))
            + total_ne * np.log(np.clip(1.0 - grid, GRID_EPS, 1.0))
        )

    # ------------------------------------------------------------------
    # 事前分布構築ヘルパー
    # ------------------------------------------------------------------
    def _ss_prior_generative(self) -> np.ndarray:
        """生成的因果リンクに対する正規化されていないSS事前分布。"""
        alpha = self.alpha
        beta = self.beta
        w0 = self.w0_grid
        w1 = self.w1_grid

        term = np.exp(-beta * (1.0 - w1))
        core = np.exp(-alpha * (1.0 - w1) - alpha * w0) + np.exp(-alpha * w1 - alpha * (1.0 - w0))
        return term * core

    def _ss_prior_preventive(self) -> np.ndarray:
        """抑制的因果リンクに対する正規化されていないSS事前分布。"""
        alpha = self.alpha
        beta = self.beta
        w0 = self.w0_grid
        w1 = self.w1_grid

        term = np.exp(-beta * (1.0 - w1))
        core = np.exp(-alpha * (1.0 - w0) - alpha * w1) + np.exp(-alpha * (1.0 - w0) - alpha * (1.0 - w1))
        return term * core

    def _ss_prior_graph0_generative(self) -> np.ndarray:
        """Graph 0における背景パラメータに対する正規化されていない事前分布。"""
        alpha = self.alpha
        grid = self.grid

        if math.isclose(alpha, 0.0):
            return np.ones_like(grid)

        factor = (1.0 - math.exp(-alpha)) / alpha
        return factor * (np.exp(-alpha * grid) + np.exp(-alpha * (1.0 - grid)))

    def _ss_prior_graph0_preventive(self) -> np.ndarray:
        """抑制的仮説を評価する際のGraph 0に対する正規化されていない事前分布。"""
        alpha = self.alpha
        grid = self.grid

        if math.isclose(alpha, 0.0):
            return np.ones_like(grid)

        return np.exp(-alpha * (1.0 - grid))

    def _prepare_log_prior(self, prior: np.ndarray) -> np.ndarray:
        normaliser = self._integrate2d(prior)
        return np.log(np.clip(prior, GRID_EPS, None)) - math.log(max(normaliser, GRID_EPS))

    def _prepare_log_prior1d(self, prior: np.ndarray) -> np.ndarray:
        normaliser = self._integrate1d(prior)
        return np.log(np.clip(prior, GRID_EPS, None)) - math.log(max(normaliser, GRID_EPS))

    # ------------------------------------------------------------------
    # 数値積分ヘルパー関数
    # ------------------------------------------------------------------
    def _integrate2d(self, values: np.ndarray) -> float:
        """w0とw1に対する2次元数値積分を実行する。"""
        return float(np.trapezoid(np.trapezoid(values, self.grid, axis=1), self.grid, axis=0))

    def _integrate1d(self, values: np.ndarray) -> float:
        """共有グリッドに沿った1次元積分を実行する。"""
        return float(np.trapezoid(values, self.grid))

    def _integrate_evidence(self, log_integrand: np.ndarray) -> tuple[float, np.ndarray]:
        """正規化されていない対数密度を積分し、その質量と正規化された密度を返す。"""
        scaled, log_scale = self._stabilise(log_integrand)
        integral_scaled = self._integrate2d(scaled)
        evidence = math.exp(log_scale) * integral_scaled

        if integral_scaled <= 0.0 or not math.isfinite(integral_scaled):
            raise RuntimeError("Failed to compute evidence; integration returned zero or NaN.")

        posterior_density = scaled / integral_scaled
        return evidence, posterior_density

    def _integrate_graph0(self, table: ContingencyTable, log_prior: np.ndarray) -> float:
        log_integrand = self._log_likelihood_graph0(table) + log_prior
        scaled, log_scale = self._stabilise(log_integrand)
        integral_scaled = self._integrate1d(scaled)
        if integral_scaled <= 0.0 or not math.isfinite(integral_scaled):
            raise RuntimeError("Failed to compute Graph 0 evidence; integration returned zero or NaN.")
        return math.exp(log_scale) * integral_scaled

    def _stabilise(self, log_values: np.ndarray) -> tuple[np.ndarray, float]:
        """対数値を最大値で調整して数値的に安定な指数を得る。"""
        max_log = float(np.max(log_values))
        adjusted = np.exp(log_values - max_log)
        return adjusted, max_log

    # ------------------------------------------------------------------
    # 事後分布の要約統計
    # ------------------------------------------------------------------
    def _summarise_w1(self, posterior_density: np.ndarray) -> tuple[float, float, float]:
        """結合密度が与えられた時のw1に対する事後分布を要約する。"""
        density_w1 = np.trapezoid(posterior_density, self.grid, axis=0)
        mass = self._integrate1d(density_w1)
        if mass <= 0.0:
            raise RuntimeError("Posterior mass vanished while summarising w1.")

        density_w1 /= mass
        w1_mean = self._integrate1d(density_w1 * self.grid)
        mode_index = int(np.argmax(density_w1))
        w1_mode = float(self.grid[mode_index])
        entropy = -self._integrate1d(np.where(density_w1 > 0.0, density_w1 * np.log(np.clip(density_w1, GRID_EPS, None)), 0.0))

        return w1_mean, w1_mode, entropy

    def _log_combination(self, table: ContingencyTable) -> float:
        """Graph 0とGraph 1で共有される組み合わせスケーリングの対数値。"""
        enc = table.enc
        nenc = table.nenc
        ec = table.ec
        nec = table.nec

        return (
            math.lgamma(enc + nenc + 1)
            - math.lgamma(enc + 1)
            - math.lgamma(nenc + 1)
            + math.lgamma(ec + nec + 1)
            - math.lgamma(ec + 1)
            - math.lgamma(nec + 1)
        )


# ----------------------------------------------------------------------
# MATLABデータパイプラインと整合させるための便利なラッパー関数
# ----------------------------------------------------------------------
def tables_from_arrays(counts: Iterable[Iterable[int]], directions: Sequence[int]) -> List[ContingencyTable]:
    """生の配列（ec, nec, enc, nenc）から分割表を構築する。
    
    Parameters
    ----------
    counts : Iterable[Iterable[int]]
        各分割表のカウントデータ [ec, nec, enc, nenc] の配列
    directions : Sequence[int]
        各分割表に対応する因果方向フラグの配列
        
    Returns
    -------
    List[ContingencyTable]
        構築された分割表のリスト
    """
    return [
        ContingencyTable(ec=ec, nec=nec, enc=enc, nenc=nenc, direction=dir_flag)
        for (ec, nec, enc, nenc), dir_flag in zip(counts, directions)
    ]


# ----------------------------------------------------------------------
# コマンドライン実行用の補助関数
# ----------------------------------------------------------------------
def _load_builtin_dataset(name: str) -> List[ContingencyTable]:
    """付属している MATLAB デモと同じコンティンジェンシーデータを返す。"""
    if name == "exp1":
        counts = [
            # (8, 0, 0, 8),
            # (8, 0, 2, 6),
            # (16, 48, 0, 64),
            # (12, 4, 16, 0),
            # (0, 16, 4, 12),
            # (4, 12, 16, 0),
            (6, 6, 0, 12),
            (6, 3, 3, 6),
            (6, 0, 6, 0),
            (7, 6, 0, 13),
            (7, 3, 3, 7),
            (7, 0, 6, 1)
        ]
        # directions = [1, 1, 1, -1, -1, -1]
        directions = [1, 1, 1, 1, 1, 1]
        return tables_from_arrays(counts, directions)
    if name == "exp2":
        counts = [
            (6, 18, 6, 6),
            (6, 6, 18, 6),
            (6, 6, 6, 18),
            (4, 4, 0, 8),
            (6, 2, 4, 4),
        ]
        directions = [0, 0, 0, 1, 1]
        return tables_from_arrays(counts, directions)
    raise ValueError(f"Unknown builtin dataset '{name}'.")


def _load_tables_from_csv(path: Path) -> List[ContingencyTable]:
    """CSV ファイルからコンティンジェンシーデータを読み込む。"""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"ec", "nec", "enc", "nenc", "direction"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing columns in CSV: {', '.join(sorted(missing))}")

        rows: List[ContingencyTable] = []
        for row in reader:
            rows.append(
                ContingencyTable(
                    ec=int(row["ec"]),
                    nec=int(row["nec"]),
                    enc=int(row["enc"]),
                    nenc=int(row["nenc"]),
                    direction=int(row["direction"]),
                )
            )
    if not rows:
        raise ValueError("Input CSV did not contain any rows.")
    return rows


def _results_to_dicts(results: Sequence[SSResult]) -> List[dict]:
    """計算結果を CSV/JSON 出力用の辞書リストに変換する。"""
    output = []
    for idx, res in enumerate(results, 1):
        output.append(
            {
                "case": idx,
                "prob_g1": res.prob_g1,
                "prob_g0": res.prob_g0,
                "log_support": res.log_support,
                "w1_mode": res.w1_mode,
                "w1_mean": res.w1_mean,
                "w1_entropy": res.w1_entropy,
            }
        )
    return output


def _run_cli() -> None:
    """CLI エントリーポイント。"""
    parser = argparse.ArgumentParser(
        description="Sparse-and-Strong 因果支持モデルによる評価を行います。",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--input",
        type=Path,
        metavar="CSV",
        help="列 ec, nec, enc, nenc, direction を持つ CSV ファイル。",
    )
    group.add_argument(
        "--dataset",
        choices=["exp1", "exp2"],
        default="exp1",
        help="組み込みのデモデータセットを使用する。",
    )
    parser.add_argument("--alpha", type=float, default=5.0, help="SS 事前分布の alpha パラメータ。")
    parser.add_argument("--beta", type=float, default=20.0, help="十分性選好を表す beta パラメータ。")
    parser.add_argument("--grid-size", type=int, default=401, help="w0/w1 グリッドの分割数。")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="結果を書き出すファイル。拡張子が .json の場合は JSON、それ以外は CSV。",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="標準出力に JSON を表示する（--output 使用時は無効）。",
    )

    args = parser.parse_args()

    if args.input is None:
        tables = _load_builtin_dataset(args.dataset)
        dataset_label = args.dataset
    else:
        tables = _load_tables_from_csv(args.input)
        dataset_label = args.input.name

    model = SSModel(alpha=args.alpha, beta=args.beta, grid_size=args.grid_size)
    results = model.evaluate_all(tables)
    rows = _results_to_dicts(results)

    if args.output:
        if args.output.suffix.lower() == ".json":
            with args.output.open("w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "dataset": dataset_label,
                        "alpha": args.alpha,
                        "beta": args.beta,
                        "grid_size": args.grid_size,
                        "results": rows,
                    },
                    handle,
                    indent=2,
                    ensure_ascii=False,
                )
        else:
            fieldnames = list(rows[0].keys())
            with args.output.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        return

    if args.json:
        print(
            json.dumps(
                {"dataset": dataset_label, "alpha": args.alpha, "beta": args.beta, "grid_size": args.grid_size, "results": rows},
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    # デフォルトはテキスト表を表示
    header = ("case", "prob_g1", "prob_g0", "log_support", "w1_mode", "w1_mean", "w1_entropy")
    width = 13
    print(f"Dataset: {dataset_label} | alpha={args.alpha} beta={args.beta} grid={args.grid_size}")
    print("".join(f"{h:>{width}}" for h in header))
    for row in rows:
        line = []
        for key in header:
            value = row[key]
            if isinstance(value, float):
                line.append(f"{value:>{width}.6f}")
            else:
                line.append(f"{value:>{width}}")
        print("".join(line))


if __name__ == "__main__":
    _run_cli()
