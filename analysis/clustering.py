"""クラスタ分析の実行スクリプト。

このコードでやっていること:
- 参加者の回答パターンを k-means でクラスタに分ける
- 各クラスタで、CS / Ising / ΔP / DFH / P(E|C) / P(C|E) がどれだけ合うかを見る
- オンライン・非対称条件では、刺激提示の順序効果も別で集計する

本体計算は clustering_modules 側にあり、このファイルは実行入口だけを担当する。
"""

from __future__ import annotations

import argparse
from typing import Optional, Sequence

from clustering_modules.cluster_analysis import run_clustering
from clustering_modules.common import (
    DEFAULT_COND_LIKE,
    DEFAULT_CORR_CSV,
    DEFAULT_INPUT_CSV,
    DEFAULT_ISING_INTERVAL,
    DEFAULT_ISING_THRESHOLD,
    DEFAULT_LLFV,
    DEFAULT_MAX_K,
    DEFAULT_MIN_SILHOUETTE,
    DEFAULT_MODEL_MEAN_CSV,
    DEFAULT_MODEL_MEAN_RAW_CSV,
    DEFAULT_ORDER_COMBO_OUTPUT,
    DEFAULT_ORDER_EFFECT_OUTPUT,
    DEFAULT_ORDER_INDIVIDUAL_OUTPUT,
    DEFAULT_ORDER_PLOT_OUTPUT,
    DEFAULT_ORDER_SUMMARY_OUTPUT,
    DEFAULT_OUTPUT_CSV,
    DEFAULT_PRED_DIAG_OUTPUT,
    DEFAULT_RANDOM_STATE,
    DEFAULT_SWAP_FE,
    DEFAULT_WEIGHT_GRID_STEP,
)
from clustering_modules.order_analysis import analyze_asymmetric_online_order_effects


def parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    # ここで、入力CSVや出力先、kの上限など実験条件を受け取る
    parser = argparse.ArgumentParser(description="複数モデル（CS/Ising/DeltaP/DFH/PCE/PEC）の固定パラメータで k-means クラスタリングを実行する。")
    parser.add_argument("--csv", default=DEFAULT_INPUT_CSV, help="入力CSVのパス（例: tomita_data.csv）")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_CSV), help="クラスタリング結果を書き出すCSVパス")
    parser.add_argument("--corr-output", default=str(DEFAULT_CORR_CSV), help="クラスタごとの相関結果を書き出すCSVパス")
    parser.add_argument(
        "--model-mean-output",
        default=str(DEFAULT_MODEL_MEAN_CSV),
        help="クラスタごとのモデル値（刺激別平均）を書き出すCSVパス",
    )
    parser.add_argument(
        "--model-mean-raw-output",
        default=str(DEFAULT_MODEL_MEAN_RAW_CSV),
        help="power変換前のモデル値（刺激別平均）を書き出すCSVパス",
    )
    parser.add_argument(
        "--pred-diag-output",
        default=str(DEFAULT_PRED_DIAG_OUTPUT),
        help="クラスタごとの予測/診断反映度(w*)を書き出すCSVパス",
    )
    parser.add_argument(
        "--order-analysis-output",
        default=str(DEFAULT_ORDER_EFFECT_OUTPUT),
        help="オンライン・非対称 の順序別相関（参加者単位）を書き出すCSVパス",
    )
    parser.add_argument(
        "--order-summary-output",
        default=str(DEFAULT_ORDER_SUMMARY_OUTPUT),
        help="オンライン・非対称 の順序効果サマリを書き出すテキストパス",
    )
    parser.add_argument(
        "--order-plot-output",
        default=str(DEFAULT_ORDER_PLOT_OUTPUT),
        help="オンライン・非対称 の刺激順序分布プロットを書き出すPNGパス",
    )
    parser.add_argument(
        "--order-combo-output",
        default=str(DEFAULT_ORDER_COMBO_OUTPUT),
        help="オンライン・非対称 の1番目×2番目組合せごとの相関要約CSVパス",
    )
    parser.add_argument(
        "--order-individual-output",
        default=str(DEFAULT_ORDER_INDIVIDUAL_OUTPUT),
        help="オンライン・非対称 の個人レベル回答値CSVパス",
    )
    parser.add_argument("--max-k", type=int, default=DEFAULT_MAX_K, help="評価する最大クラスタ数")
    parser.add_argument("--random-state", type=int, default=DEFAULT_RANDOM_STATE, help="KMeansの乱数シード")
    parser.add_argument("--min-silhouette", type=float, default=DEFAULT_MIN_SILHOUETTE, help="この値を下回る場合は k=1 にフォールバックするしきい値")
    parser.add_argument("--ising-threshold", type=float, default=DEFAULT_ISING_THRESHOLD, help="Ising の閾値")
    parser.add_argument("--ising-interval", type=float, default=DEFAULT_ISING_INTERVAL, help="Ising の強度グリッド間隔（小さすぎると計算が重い）")
    parser.add_argument(
        "--weight-grid-step",
        type=float,
        default=DEFAULT_WEIGHT_GRID_STEP,
        help="w 探索の刻み幅（0..1, 例: 0.001）",
    )
    parser.add_argument(
        "--cond-like",
        action=argparse.BooleanOptionalAction,
        default=DEFAULT_COND_LIKE,
        help="cond_like を有効化するか（--no-cond-like で無効化）",
    )
    parser.add_argument(
        "--swap-fe",
        action=argparse.BooleanOptionalAction,
        default=DEFAULT_SWAP_FE,
        help="swap_fe を有効化するか（--no-swap-fe で無効化）",
    )
    parser.add_argument("--llfv", nargs=2, type=float, metavar=("PRV", "ABV"), help="llfv (PRV, ABV) を指定する（例: --llfv -1 1）")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    # 実行フロー: クラスタ分析 -> 順序効果分析 -> 保存先を表示
    args = parse_args(argv)

    # メインのクラスタ分析（参加者クラスタ、モデル相関、モデル平均、w*推定）
    cluster_df, corr_df, model_mean_df, pred_diag_df = run_clustering(
        csv_path=args.csv,
        output_csv=args.output,
        corr_output=args.corr_output,
        model_mean_output=args.model_mean_output,
        model_mean_raw_output=args.model_mean_raw_output,
        pred_diag_output=args.pred_diag_output,
        max_k=args.max_k,
        random_state=args.random_state,
        min_silhouette=args.min_silhouette,
        ising_threshold=args.ising_threshold,
        ising_interval=args.ising_interval,
        cond_like=bool(args.cond_like),
        swap_fe=bool(args.swap_fe),
        llfv=tuple(args.llfv) if args.llfv is not None else DEFAULT_LLFV,
        weight_grid_step=float(args.weight_grid_step),
    )

    # オンライン・非対称条件だけ、刺激提示順が効いているかを追加で集計
    order_df = analyze_asymmetric_online_order_effects(
        csv_path=args.csv,
        analysis_output=args.order_analysis_output,
        summary_output=args.order_summary_output,
        plot_output=args.order_plot_output,
        combo_output=args.order_combo_output,
        individual_output=args.order_individual_output,
    )

    # どこに何行出たかを最後に表示
    print(f"クラスタリング結果を保存しました: {args.output} (行数: {len(cluster_df)})")
    print(f"クラスタ別の相関結果を保存しました: {args.corr_output} (行数: {len(corr_df)})")
    print(f"クラスタ別のモデル平均を保存しました: {args.model_mean_output} (行数: {len(model_mean_df)})")
    print(f"モデル平均（raw）を保存しました: {args.model_mean_raw_output}")
    print(f"予測/診断反映度（w*）を保存しました: {args.pred_diag_output} (行数: {len(pred_diag_df)})")
    print(f"オンライン・非対称の順序効果を保存しました: {args.order_analysis_output} (行数: {len(order_df)})")
    print(f"オンライン・非対称の順序効果サマリを保存しました: {args.order_summary_output}")
    print(f"オンライン・非対称の順序分布プロットを保存しました: {args.order_plot_output}")
    print(f"オンライン・非対称の順序組合せ要約を保存しました: {args.order_combo_output}")
    print(f"オンライン・非対称の個人回答データを保存しました: {args.order_individual_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
