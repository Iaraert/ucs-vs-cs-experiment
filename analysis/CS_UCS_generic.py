# CS_generic と UCS_generic（generic版）の実装と、刺激セットでの差分表示
# ----------------------------------------------------------------------------
# 目的：
#  1) CS_generic を「有向・機能形の仮定（noisy-OR等）を置かない generic 版」として実装する。
#     - 構造仮説G1: CがEに影響する（P(E=1|C=1)=θ1, P(E=1|C=0)=θ0 を自由に持つ）
#     - 帰無仮説G0: CとEは独立（P(E=1|C=1)=P(E=1|C=0)=θ 共通）
#     - 事前は一様：θ0 ~ Unif(0,1), θ1 ~ Unif(0,x), θ ~ Unif(0,1)（x=thresholdで稀少性）
#     - モンテカルロで周辺化し、log-mean-exp で数値安定化した対数ベイズ因子を返す
#
#  2) UCS_generic を「無向・対称の generic 版」として実装する。
#     - 構造仮説G1: 無向の従属モデル（極大クリークの幾何平均ポテンシャルに基づくセル重み）
#     - 帰無仮説G0: 独立モデル（直積）
#     - 事前：wBC ~ Unif(0,x), wBE ~ Unif(0,x), wCE ~ Unif(0,1)（x=threshold）
#     - 同様にモンテカルロ＋log-mean-exp で周辺化
#
#  3) /mnt/data/samples_common.json の刺激セット（a,b,c,d）について、
#     CS_generic と UCS_generic を並べ、差分（CS_generic - UCS_generic）を表示する。
#     DataFrame を可視化し、同時にCSVとして保存する。
#
# 注：この実装は「省略なく・可読性重視」でベクトル演算により高速化。
#     乱数のシードを固定して再現可能にする。
# ----------------------------------------------------------------------------

import json
import math
import numpy as np
import pandas as pd
from math import log
from pathlib import Path
from typing import Tuple, Dict
from numba import njit, prange

# 可視化（表をUIに表示）
# from caas_jupyter_tools import display_dataframe_to_user

# 乱数の再現性
np.random.seed(42)

# ------------------------- 汎用ユーティリティ -------------------------------
def log_mean_exp(log_vals: np.ndarray) -> float:
    """
    数値安定化された log-mean-exp を返す。
    log mean(exp(log_vals)) = m + log( mean(exp(log_vals - m)) ), m=max(log_vals)
    """
    m = np.max(log_vals)
    return m + np.log(np.mean(np.exp(log_vals - m)))

# ------------------------- CS_generic（有向・generic） ----------------------
def CS_generic(counts, is_gene, threshold, loops):
    rng = np.random.default_rng()  # 乱数ジェネレーター
    power = np.zeros((loops, 2))

    # ループを実行して条件を満たす乱数を生成
    for i in range(loops):
      power0 = rng.uniform(0, 1)
      power1 = rng.uniform(0+1e-100, threshold)
      # power1 = threshold
      power[i] = [power0,power1]

    a, b, c, d = counts

    # power[:, 0] 背景と結果のw
    # power[:, 1] 原因と結果のw

    probs1 = [
        power[:, 1],# P(E=1|C=1)
        1 - power[:, 1],# P(E=0|C=1)
        power[:, 0],# P(E=1|C=0)
        1 - power[:, 0],# P(E=0|C=0)
    ]

    probs0 = [
        power[:, 0],# P(E=1|C=1)
        (1 - power[:, 0]),# P(E=0|C=1)
        power[:, 0],# P(E=1|C=0)
        (1 - power[:, 0]),# P(E=0|C=0)
    ]

    loglike1 = np.sum((np.ones((loops, 1)) * np.array(counts)) * np.log(probs1).T, axis=1)
    like1 = sum(np.exp(loglike1)) * (1/loops)

    loglike0 = np.sum((np.ones((loops, 1)) * np.array(counts)) * np.log(probs0).T, axis=1)
    like0 = sum(np.exp(loglike0)) * (1/loops)

    logscore = np.log(like1/like0)
    return logscore

# ------------------------- UCS_generic（無向・generic） ----------------------
def UCS_generic(counts, threshold, is_gene=True, loops=10000):
    """
    UCS_generic:
    無向グラフィカルモデルに基づいたUndirected Causal Support (UCS) を
    モンテカルロ法により計算する汎用的な関数。

    Args:
        counts (tuple): 共起データの2x2分割表 (a, b, c, d)
                       a: C=1, E=1
                       b: C=1, E=0
                       c: C=0, E=1
                       d: C=0, E=0
        threshold (float): 稀少性制約を表すパラメータ（例：0.3）
        is_gene (bool): 原因が生成的かどうか（True:生成的 / False:抑制的）
        loops (int): サンプリングの繰り返し回数（精度向上用）

    Returns:
        float: UCSスコア（G1とG0の対数尤度比）
    """

    rng = np.random.default_rng()  # 高速な乱数ジェネレータを生成
    power = np.zeros((loops, 3))   # wCE, wBC, wBE を保存する行列

    # 各サンプルでランダムに確率値を生成
    for i in range(loops):
        power0 = rng.uniform(0, 1)                # 原因→結果（wCE）
        power1 = rng.uniform(1e-100, threshold)   # 背景→原因（wBC）
        power2 = rng.uniform(1e-100, threshold)   # 背景→結果（wBE）
        power[i] = [power0, power1, power2]

    a, b, c, d = counts  # データカウントを展開

    # 各事象に対応する確率の定義
    if is_gene:
        # 生成
        denom = (
            np.sqrt(power[:,1]*power[:,2]*(1 - (1 - power[:,0])*(1 - power[:,1]))*(1 - (1 - power[:,0])*(1 - power[:,2])))
            + np.sqrt(power[:,1]*(1 - power[:,2])*power[:,1]*((1 - power[:,0])*(1 - power[:,2])))
            + np.sqrt((1 - power[:,1])*power[:,2]*power[:,2]*((1 - power[:,0])*(1 - power[:,1])))
            + (1 - power[:,1])*(1 - power[:,2])
        )
        probs1 = [
            np.sqrt(power[:,1]*power[:,2]*(1 - (1 - power[:,0])*(1 - power[:,1]))*(1 - (1 - power[:,0])*(1 - power[:,2]))) / denom,  # P(E=1|C=1)
            np.sqrt(power[:,1]*(1 - power[:,2])*power[:,1]*((1 - power[:,0])*(1 - power[:,2]))) / denom,                           # P(E=0|C=1)
            np.sqrt((1 - power[:,1])*power[:,2]*power[:,2]*((1 - power[:,0])*(1 - power[:,1]))) / denom,                           # P(E=1|C=0)
            (1 - power[:,1])*(1 - power[:,2]) / denom                                                                              # P(E=0|C=0)
        ]
    else:
        # 抑制
        denom = (
            np.sqrt(power[:,1]*power[:,2]*((power[:,1]*(1 - power[:,0]))*(power[:,2]*(1 - power[:,0]))))
            + np.sqrt(power[:,1]*(1 - power[:,2])*power[:,1]*(1 - (power[:,2]*(1 - power[:,0]))))
            + np.sqrt((1 - power[:,1])*power[:,2]*(1 - (power[:,1]*(1 - power[:,0])))*power[:,2])
            + (1 - power[:,1])*(1 - power[:,2])
        )
        probs1 = [
            np.sqrt(power[:,1]*power[:,2]*((power[:,1]*(1 - power[:,0]))*(power[:,2]*(1 - power[:,0])))) / denom,
            np.sqrt(power[:,1]*(1 - power[:,2])*power[:,1]*(1 - (power[:,2]*(1 - power[:,0])))) / denom,
            np.sqrt((1 - power[:,1])*power[:,2]*(1 - (power[:,1]*(1 - power[:,0])))*power[:,2]) / denom,
            (1 - power[:,1])*(1 - power[:,2]) / denom
        ]

    # 非因果構造（G0）の確率：CとEが独立（P(E|C)=P(E)）
    probs0 = [
        power[:,1]*power[:,2],                      # P(E=1|C=1)
        power[:,1]*(1 - power[:,2]),                # P(E=0|C=1)
        (1 - power[:,1])*power[:,2],                # P(E=1|C=0)
        (1 - power[:,1])*(1 - power[:,2])           # P(E=0|C=0)
    ]

    # 尤度計算
    loglike1 = np.sum(np.array([a, b, c, d])[:, np.newaxis] * np.log(probs1), axis=0)
    loglike0 = np.sum(np.array([a, b, c, d])[:, np.newaxis] * np.log(probs0), axis=0)


    like1 = np.mean(np.exp(loglike1))
    like0 = np.mean(np.exp(loglike0))

    logscore = np.log(like1 / like0)  # 対数尤度比
    return logscore

# ------------------------- 刺激セットの読み込みと差分表 ----------------------
# ファイルから (a,b,c,d) を取得
json_path = Path("samples_common.json")
with json_path.open("r", encoding="utf-8") as f:
    samples = json.load(f)["common_samples"]

# 計算条件（必要に応じて変更可）
threshold = 1.0     # 稀少性上限 x（例：0.3）
loops     = 50000   # モンテカルロ試行回数（計算時間と精度のトレードオフ）

# 各刺激について CS_generic と UCS_generic を計算し、差分を表にまとめる
rows = []
for key, vals in samples.items():
    counts = (int(vals["a"]), int(vals["b"]), int(vals["c"]), int(vals["d"]))
    cs = CS_generic(counts, threshold=threshold, is_gene=True, loops=loops)
    ucs = UCS_generic(counts, threshold=threshold, is_gene=True, loops=loops)
    rows.append({
        "stimulus": key,
        "a": counts[0],
        "b": counts[1],
        "c": counts[2],
        "d": counts[3],
        "CS_generic": cs,
        "UCS_generic": ucs,
        "CS_minus_UCS": cs - ucs
    })

df = pd.DataFrame(rows).sort_values("stimulus")
# display_dataframe_to_user("CS_generic vs UCS_generic (common samples)", df)

# CSVとして保存（ダウンロード用）
out_path = Path("CS_UCS_generic_diff2.csv")
df.to_csv(out_path, index=False)

out_path, df.head(10)