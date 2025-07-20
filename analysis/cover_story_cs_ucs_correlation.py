#!/usr/bin/env python3
# ───────────────────────────────────────────────────────────────────────────────
#  scenario_cs_ucs_analysis_ascii_allrows.py
#  * 全行解析版 *
#
#  1. 日本語列ヘッダを英語化
#  2. 実験タイプ・条件・グループ値を ASCII ラベルに置換（Type1, Cond1, Group1…）
#  3. 行フィルタは一切かけず、CSV の全レコードを解析
#  4. 出力:
#       results/basic_stats.csv
#       results/correlation_patterns.csv
#       results/overview.png  (6 連図)
# ───────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import argparse
import logging
import pathlib
from dataclasses import dataclass, field
from typing import List

import numpy as np
import pandas as pd
from scipy import stats

import matplotlib.pyplot as plt
import seaborn as sns


# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class Config:
    csv_path: str = "cover_story_cs_ucs_correlation_results.csv"
    strong_r_cutoff: float = 0.30
    metrics: List[str] = field(
        default_factory=lambda: [
            "CS",
            "UCS",
            "P(E|C)",
            "P(C|E)",
            "ΔP",
            "pARIs",
            "DFH",
            "Dice",
            "CRT_mean",
        ]
    )
    outdir: pathlib.Path = pathlib.Path("results")
    seaborn_style: str = "whitegrid"


# ═══════════════════════════════════════════════════════════════════════════════
#  ラベル置換ユーティリティ
# ═══════════════════════════════════════════════════════════════════════════════
def ascii_labeler(series: pd.Series, prefix: str) -> pd.Series:
    """ユニーク値を prefix＋連番 の ASCII ラベルに置換し、対応表をログ出力。"""
    uniq = sorted(series.unique())
    mapping = {v: f"{prefix}{i+1}" for i, v in enumerate(uniq)}
    logging.getLogger("Labeler").info("%s mapping: %s", prefix, mapping)
    return series.map(mapping)


# ═══════════════════════════════════════════════════════════════════════════════
#  解析クラス
# ═══════════════════════════════════════════════════════════════════════════════
class ScenarioAnalyzer:
    JP2EN_COLS = {
        "実験タイプ": "ExperimentType",
        "条件": "Condition",
        "ストーリー": "Story",
        "グループ": "Group",
        # CS, UCS などの列名はそのまま
    }

    def __init__(self, cfg: Config, log: logging.Logger):
        self.cfg = cfg
        self.log = log
        self.df: pd.DataFrame
        self.work: pd.DataFrame

        cfg.outdir.mkdir(exist_ok=True, parents=True)

    # ── データ読み込み ───────────────────────────────────────────────────────
    def load(self):
        self.df = pd.read_csv(self.cfg.csv_path)
        self.log.info("Loaded %d rows from %s", len(self.df), self.cfg.csv_path)

        # 日本語ヘッダ→英語
        self.df.rename(columns=self.JP2EN_COLS, inplace=True)

        # 実験タイプ・条件・グループを ASCII ラベル化
        self.df["ExperimentType"] = ascii_labeler(self.df["ExperimentType"], "Type")
        self.df["Condition"] = ascii_labeler(self.df["Condition"], "Cond")
        self.df["Group"] = ascii_labeler(self.df["Group"], "Group")

        # 全行そのまま解析対象
        self.work = self.df.copy()
        self.log.info("Analysis target rows: %d (no filtering)", len(self.work))

    # ── 基本統計 ───────────────────────────────────────────────────────────
    def basic_stats(self) -> pd.DataFrame:
        g = self.work.groupby(["ExperimentType", "Condition"])
        stats_df = (
            g[self.cfg.metrics]
            .agg(["mean", "std", "min", "max", "count"])
            .stack(level=0, future_stack=True)
        )
        out = self.cfg.outdir / "basic_stats.csv"
        stats_df.to_csv(out)
        self.log.info("Wrote %s", out)
        return stats_df

    # ── 相関パターン集計 ───────────────────────────────────────────────────
    def correlation_patterns(self) -> pd.DataFrame:
        cut = self.cfg.strong_r_cutoff

        def label(r):
            strong_cs = abs(r.CS) >= cut
            strong_ucs = abs(r.UCS) >= cut
            if strong_cs and strong_ucs:
                return "CS+UCS strong"
            if strong_cs:
                return "CS strong"
            if strong_ucs:
                return "UCS strong"
            return "weak"

        self.work["Pattern"] = self.work.apply(label, axis=1)
        patt_df = (
            self.work.groupby(["ExperimentType", "Condition", "Pattern"])
            .size()
            .unstack(fill_value=0)
        )
        out = self.cfg.outdir / "correlation_patterns.csv"
        patt_df.to_csv(out)
        self.log.info("Wrote %s", out)
        return patt_df

    # ── 可視化 ─────────────────────────────────────────────────────────────
    def overview_plot(self):
        sns.set_style(self.cfg.seaborn_style)
        fig, ax = plt.subplots(3, 2, figsize=(14, 16))

        # 1: 平均 CS / UCS
        m = (
            self.work.groupby(["ExperimentType", "Condition"])[["CS", "UCS"]]
            .mean()
            .reset_index()
        )
        sns.barplot(
            data=m, x="ExperimentType", y="CS", hue="Condition",
            palette="Blues", ax=ax[0, 0]
        )
        sns.barplot(
            data=m, x="ExperimentType", y="UCS", hue="Condition",
            palette="Reds", alpha=0.7, dodge=True, ax=ax[0, 0]
        )
        ax[0, 0].set_title("Mean CS / UCS by type & cond")

        # 2: CRT ヒストグラム
        sns.histplot(
            data=self.work, x="CRT_mean", hue="Condition",
            multiple="stack", bins=12, ax=ax[0, 1]
        )
        ax[0, 1].set_title("CRT mean distribution")

        # 3: 散布図 CS vs UCS
        sns.scatterplot(
            data=self.work, x="CS", y="UCS",
            hue="Condition", style="ExperimentType",
            ax=ax[1, 0]
        )
        ax[1, 0].axhline(0, ls="--", c="k", alpha=0.4)
        ax[1, 0].axvline(0, ls="--", c="k", alpha=0.4)

        # 4: CS ヒートマップ (Story × Type×Cond)
        pivot = self.work.pivot_table(
            index="Story", columns=["ExperimentType", "Condition"], values="CS"
        )
        sns.heatmap(pivot.T, cmap="RdBu_r", center=0, ax=ax[1, 1])

        # 5: |r| ヒストグラム
        sns.histplot(abs(self.work["CS"]), bins=15, ax=ax[2, 0], label="|CS|")
        sns.histplot(abs(self.work["UCS"]), bins=15, ax=ax[2, 0],
                     color="salmon", label="|UCS|")
        ax[2, 0].axvline(self.cfg.strong_r_cutoff, ls="--", c="k")
        ax[2, 0].legend()

        # 6: CRT vs (CS, UCS)
        sns.regplot(data=self.work, x="CRT_mean", y="CS",
                    scatter_kws={"alpha": 0.5}, ax=ax[2, 1])
        sns.regplot(data=self.work, x="CRT_mean", y="UCS",
                    color="r", scatter_kws={"alpha": 0.5}, ax=ax[2, 1])

        fig.tight_layout()
        out_img = self.cfg.outdir / "overview.png"
        fig.savefig(out_img, dpi=300)
        self.log.info("Saved %s", out_img)

    # ── 実行 ───────────────────────────────────────────────────────────────
    def run(self):
        self.load()
        self.basic_stats()
        self.correlation_patterns()
        self.overview_plot()


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI エントリポイント
# ═══════════════════════════════════════════════════════════════════════════════
def cli(argv: List[str] | None = None):
    parser = argparse.ArgumentParser(description="CS/UCS analysis (all rows)")
    parser.add_argument("--csv", default="cover_story_cs_ucs_correlation_results.csv")
    parser.add_argument(
        "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s:%(name)s:%(message)s",
    )

    cfg = Config(csv_path=args.csv)
    ScenarioAnalyzer(cfg, logging.getLogger("ScenarioAnalyzer")).run()
    logging.info("Analysis complete – outputs in %s", cfg.outdir)


if __name__ == "__main__":
    cli()
