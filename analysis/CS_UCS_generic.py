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

import argparse
import json
import math
import numpy as np
import pandas as pd
from math import log
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple
from numba import njit, prange
from scipy.special import logsumexp

# 可視化（表をUIに表示）
# from caas_jupyter_tools import display_dataframe_to_user

# 乱数の再現性
np.random.seed(42)

DEFAULT_THRESHOLD = 1.0
DEFAULT_LOOPS = 50000

# ------------------------- 汎用ユーティリティ -------------------------------
def log_mean_exp(log_vals: np.ndarray) -> float:
    """
    数値安定化された log-mean-exp を返す。
    log mean(exp(log_vals)) = m + log( mean(exp(log_vals - m)) ), m=max(log_vals)
    """
    m = np.max(log_vals)
    return m + np.log(np.mean(np.exp(log_vals - m)))

# ------------------------- CS_generic（有向・generic） ----------------------
def CS_generic(counts, threshold, loops):
    rng = np.random.default_rng()  # 乱数ジェネレーター
    power = np.zeros((loops, 2))

    # ループを実行して条件を満たす乱数を生成
    for i in range(loops):
      power0 = rng.uniform(0+1e-100, threshold) # 背景と原因のw
      power1 = rng.uniform(0, 1)                # 原因と結果のw
      # power1 = threshold
      power[i] = [power0,power1]

    a, b, c, d = counts

    # CがEに影響する（P(E|C)を独立に持つ）
    probs1 = [
        power[:, 1],# P(E=1|C=1)
        1 - power[:, 1],# P(E=0|C=1)
        power[:, 0],# P(E=1|C=0)
        1 - power[:, 0],# P(E=0|C=0)
    ]
    # w1
    # (1 - w1)
    # w0
    # (1 - w0)

    # CとEが独立（P(E|C)=P(E)）
    probs0 = [
        power[:, 0],# P(E=1|C=1)
        (1 - power[:, 0]),# P(E=0|C=1)
        power[:, 0],# P(E=1|C=0)
        (1 - power[:, 0]),# P(E=0|C=0)
    ]
    # w0
    # (1 - w0)
    # w0
    # (1 - w0)

    loglike1 = np.sum((np.ones((loops, 1)) * np.array(counts)) * np.log(probs1).T, axis=1)
    like1 = sum(np.exp(loglike1)) * (1/loops)

    loglike0 = np.sum((np.ones((loops, 1)) * np.array(counts)) * np.log(probs0).T, axis=1)
    like0 = sum(np.exp(loglike0)) * (1/loops)

    logscore = np.log(like1/like0)
    return logscore

# ------------------------- UCS_generic（無向・generic） ----------------------
# def UCS_generic(counts, threshold, loops):
#     rng = np.random.default_rng()  # 乱数ジェネレーター
#     power = np.zeros((loops, 3))

#     # ループを実行して条件を満たす乱数を生成
#     for i in range(loops):
#       power0 = rng.uniform(0, 1)
#       power1 = rng.uniform(0+1e-100, threshold)
#       power2 = rng.uniform(0+1e-100, threshold)
#       # power1 = threshold
#       # power2 = threshold
#       power[i] = [power0,power1,power2]
#     a, b, c, d = counts
#     # power[:, 0] 原因と結果のw
#     # power[:, 1] 背景と原因のw
#     # power[:, 2] 背景と結果のw
#     # z = np.sqrt(power[:, 1] * (1 - power[:, 1])) + np.sqrt(power[:, 2] * (1 - power[:, 2])) + np.sqrt(power[:, 0] * (1 - power[:, 0])) + (1 - power[:, 1]) * (1 - power[:, 2]))
#     psi_bc = np.sqrt(power[:, 1] * (1 - power[:, 1]))
#     psi_be = np.sqrt(power[:, 2] * (1 - power[:, 2]))
#     psi_ce = np.sqrt(power[:, 0] * (1 - power[:, 0]))

#     probs1 = [
#         # ダメ
#         # np.sqrt(power[:, 1] * (1 - power[:, 1])) / (np.sqrt(power[:, 1] * (1 - power[:, 1])) + np.sqrt(power[:, 2] * (1 - power[:, 2])) + np.sqrt(power[:, 0] * (1 - power[:, 0])) + (1 - power[:,1]) * (1 - power[:,2])),
#         # np.sqrt(power[:, 2] * (1 - power[:, 2])) / (np.sqrt(power[:, 1] * (1 - power[:, 1])) + np.sqrt(power[:, 2] * (1 - power[:, 2])) + np.sqrt(power[:, 0] * (1 - power[:, 0])) + (1 - power[:,1]) * (1 - power[:,2])),
#         # np.sqrt(power[:, 0] * (1 - power[:, 0])) / (np.sqrt(power[:, 1] * (1 - power[:, 1])) + np.sqrt(power[:, 2] * (1 - power[:, 2])) + np.sqrt(power[:, 0] * (1 - power[:, 0])) + (1 - power[:,1]) * (1 - power[:,2])),
#         # (1 - power[:,1]) * (1 - power[:,2]) / (np.sqrt(power[:, 1] * (1 - power[:, 1])) + np.sqrt(power[:, 2] * (1 - power[:, 2])) + np.sqrt(power[:, 0] * (1 - power[:, 0])) + (1 - power[:,1]) * (1 - power[:,2]))
        
#         # np.sqrt(power[:, 1] * (1 - power[:, 1])) * np.sqrt(power[:, 2] * (1 - power[:, 2])) * np.sqrt(power[:, 0] * (1 - power[:, 0])) / (np.sqrt(power[:, 1] * (1 - power[:, 1])) * np.sqrt(power[:, 2] * (1 - power[:, 2])) * np.sqrt(power[:, 0] * (1 - power[:, 0])) + np.sqrt(power[:, 1] * (1 - power[:, 1])) * (1 - np.sqrt(power[:, 2] * (1 - power[:, 2]))) * np.sqrt(power[:, 0] * (1 - power[:, 0])) + (1 - np.sqrt(power[:, 1] * (1 - power[:, 1]))) * (1 - np.sqrt(power[:, 2] * (1 - power[:, 2]))) * (1 - np.sqrt(power[:, 0] * (1 - power[:, 0])))),
#         # np.sqrt(power[:, 1] * (1 - power[:, 1])) * np.sqrt(power[:, 2] * (1 - power[:, 2])) * (1 - np.sqrt(power[:, 0] * (1 - power[:, 0]))) / (np.sqrt(power[:, 1] * (1 - power[:, 1])) * np.sqrt(power[:, 2] * (1 - power[:, 2])) * np.sqrt(power[:, 0] * (1 - power[:, 0])) + np.sqrt(power[:, 1] * (1 - power[:, 1])) * (1 - np.sqrt(power[:, 2] * (1 - power[:, 2]))) * np.sqrt(power[:, 0] * (1 - power[:, 0])) + (1 - np.sqrt(power[:, 1] * (1 - power[:, 1]))) * (1 - np.sqrt(power[:, 2] * (1 - power[:, 2]))) * (1 - np.sqrt(power[:, 0] * (1 - power[:, 0])))),
#         # np.sqrt(power[:, 1] * (1 - power[:, 1])) * (1 - np.sqrt(power[:, 2] * (1 - power[:, 2]))) * np.sqrt(power[:, 0] * (1 - power[:, 0])) / (np.sqrt(power[:, 1] * (1 - power[:, 1])) * np.sqrt(power[:, 2] * (1 - power[:, 2])) * np.sqrt(power[:, 0] * (1 - power[:, 0])) + np.sqrt(power[:, 1] * (1 - power[:, 1])) * (1 - np.sqrt(power[:, 2] * (1 - power[:, 2]))) * np.sqrt(power[:, 0] * (1 - power[:, 0])) + (1 - np.sqrt(power[:, 1] * (1 - power[:, 1]))) * (1 - np.sqrt(power[:, 2] * (1 - power[:, 2]))) * (1 - np.sqrt(power[:, 0] * (1 - power[:, 0])))),
#         # (1 - np.sqrt(power[:, 1] * (1 - power[:, 1]))) * (1 - np.sqrt(power[:, 2] * (1 - power[:, 2]))) * (1 - np.sqrt(power[:, 0] * (1 - power[:, 0]))) / (np.sqrt(power[:, 1] * (1 - power[:, 1])) * np.sqrt(power[:, 2] * (1 - power[:, 2])) * np.sqrt(power[:, 0] * (1 - power[:, 0])) + np.sqrt(power[:, 1] * (1 - power[:, 1])) * (1 - np.sqrt(power[:, 2] * (1 - power[:, 2]))) * np.sqrt(power[:, 0] * (1 - power[:, 0])) + (1 - np.sqrt(power[:, 1] * (1 - power[:, 1]))) * (1 - np.sqrt(power[:, 2] * (1 - power[:, 2]))) * (1 - np.sqrt(power[:, 0] * (1 - power[:, 0]))))
#         # np.sqrt(power[:,1]*power[:,1]) / (np.sqrt(power[:,1]*power[:,1]) + np.sqrt(power[:,2]*power[:,2]) + np.sqrt(power[:,0]*power[:,0]) + (1 - power[:,1]) * (1 - power[:,2])),
#         # np.sqrt(power[:,2]*power[:,2]) / (np.sqrt(power[:,1]*power[:,1]) + np.sqrt(power[:,2]*power[:,2]) + np.sqrt(power[:,0]*power[:,0]) + (1 - power[:,1]) * (1 - power[:,2])),
#         # np.sqrt(power[:,0]*power[:,0]) / (np.sqrt(power[:,1]*power[:,1]) + np.sqrt(power[:,2]*power[:,2]) + np.sqrt(power[:,0]*power[:,0]) + (1 - power[:,1]) * (1 - power[:,2])),
#         # (1 - power[:,1]) * (1 - power[:,2]) / (np.sqrt(power[:,1]*power[:,1]) + np.sqrt(power[:,2]*power[:,2]) + np.sqrt(power[:,0]*power[:,0]) + (1 - power[:,1]) * (1 - power[:,2])),

#         # np.sqrt(power[:, 1] * power[:, 2] * power[:, 0]) / (np.sqrt(power[:, 1] * power[:, 2] * power[:, 0]) + np.sqrt(power[:, 1] * (1 - power[:, 2] * power[:, 0])) + np.sqrt((1 - power[:, 1]) * power[:, 2] * power[:, 0]) + (1 - power[:, 1]) * (1 - power[:, 2] * power[:, 0])),                # P(E=1|C=1)
#         # np.sqrt(power[:, 1] * (1 - power[:, 2] * power[:, 0]) / (np.sqrt(power[:, 1] * power[:, 2] * power[:, 0]) + np.sqrt(power[:, 1] * (1 - power[:, 2] * power[:, 0])) + np.sqrt((1 - power[:, 1]) * power[:, 2] * power[:, 0]) + (1 - power[:, 1]) * (1 - power[:, 2] * power[:, 0]))),          # P(E=0|C=1)
#         # np.sqrt((1 - power[:, 1]) * power[:, 2] * power[:, 0]) / (np.sqrt(power[:, 1] * power[:, 2] * power[:, 0]) + np.sqrt(power[:, 1] * (1 - power[:, 2] * power[:, 0])) + np.sqrt((1 - power[:, 1]) * power[:, 2] * power[:, 0]) + (1 - power[:, 1]) * (1 - power[:, 2] * power[:, 0])),          # P(E=1|C=0)
#         # (1 - power[:, 1]) * (1 - power[:, 2] * power[:, 0]) / (np.sqrt(power[:, 1] * power[:, 2] * power[:, 0]) + np.sqrt(power[:, 1] * (1 - power[:, 2] * power[:, 0])) + np.sqrt((1 - power[:, 1]) * power[:, 2] * power[:, 0]) + (1 - power[:, 1]) * (1 - power[:, 2] * power[:, 0]))    # P(E=0|C=0)

#         # 良い
#         # power[:,1] / (power[:,1] + power[:,2] + power[:,0] + (1 - power[:,1]) * (1 - power[:,2])),
#         # power[:,2] / (power[:,1] + power[:,2] + power[:,0] + (1 - power[:,1]) * (1 - power[:,2])),
#         # power[:,0] / (power[:,1] + power[:,2] + power[:,0] + (1 - power[:,1]) * (1 - power[:,2])),
#         # (1 - power[:,1]) * (1 - power[:,2]) / (power[:,1] + power[:,2] + power[:,0] + (1 - power[:,1]) * (1 - power[:,2]))

#         psi_bc * psi_be * psi_ce / (psi_bc * psi_be * psi_ce + psi_bc * (1-psi_be) * psi_ce + (1-psi_bc) * psi_be * psi_ce + (1-psi_bc) * (1-psi_be) * (1-psi_ce)),
#         psi_bc * (1-psi_be) * (1-psi_ce) / (psi_bc * psi_be * psi_ce + psi_bc * (1-psi_be) * psi_ce + (1-psi_bc) * psi_be * psi_ce + (1-psi_bc) * (1-psi_be) * (1-psi_ce)),
#         (1-psi_bc) * psi_be * (1-psi_ce) / (psi_bc * psi_be * psi_ce + psi_bc * (1-psi_be) * psi_ce + (1-psi_bc) * psi_be * psi_ce + (1-psi_bc) * (1-psi_be) * (1-psi_ce)),
#         (1-psi_bc) * (1-psi_be) * (1-psi_ce) / (psi_bc * psi_be * psi_ce + psi_bc * (1-psi_be) * psi_ce + (1-psi_bc) * psi_be * psi_ce + (1-psi_bc) * (1-psi_be) * (1-psi_ce)),
#     ]
#     probs0 = [
#         # power[:, 1] * power[:, 2],
#         # power[:, 1] * (1 - power[:, 2]),
#         # (1 - power[:, 1]) * power[:, 2],
#         # (1 - power[:, 1]) * (1 - power[:, 2])
#         psi_bc * psi_be,            # (1,1)
#         psi_bc * (1-psi_be),        # (0,1)
#         (1-psi_bc) * psi_be,        # (1,0)
#         (1-psi_bc) * (1-psi_be)     # (0,0)
#     ]

#     loglike1 = np.sum((np.ones((loops, 1)) * np.array(counts)) * np.log(probs1).T, axis=1)
#     like1 = sum(np.exp(loglike1)) * (1/loops)

#     loglike0 = np.sum((np.ones((loops, 1)) * np.array(counts)) * np.log(probs0).T, axis=1)
#     like0 = sum(np.exp(loglike0)) * (1/loops)

#     logscore = np.log(like1/like0)
#     return logscore

def UCS_generic(conts, threshold, loops=50_000, or_max=2.0, rng=None):
    """
    生成仮定を外した UCS（3変数のまま）
    ------------------------------------------------------------
    - power[:,0] = wCE ~ Unif(0,1)  -> 連関の強さ（オッズ比に変換）
    - power[:,1] = wBC ~ Unif(0,threshold) -> pC = P(C=1|B=1)
    - power[:,2] = wBE ~ Unif(0,threshold) -> pE = P(E=1|B=1)

    G'0: 独立仮定  p = [pC*pE, pC*(1-pE), (1-pC)*pE, (1-pC)*(1-pE)]
    G'1: 周辺 pC,pE と OR から 2×2 を厳密に復元（方向仮定なし）
         OR = exp(kappa), kappa ∈ [-or_max, +or_max] を wCE から作る
    ------------------------------------------------------------
    conts = (a,b,c,d) = (N(E=1,C=1), N(E=0,C=1), N(E=1,C=0), N(E=0,C=0))
    戻り値: logscore = log P(D|G'1) - log P(D|G'0)
    """
    if rng is None:
        rng = np.random.default_rng()

    a, b, c, d = conts
    N = np.array([a, b, c, d], dtype=float)
    eps = 1e-12

    # --- 3本の乱数は従来どおり ---
    power = np.zeros((loops, 3))
    power[:, 0] = rng.uniform(0.0, 1.0, size=loops)                # wCE
    power[:, 1] = rng.uniform(0.0 + 1e-12, threshold, size=loops)  # wBC -> pC
    power[:, 2] = rng.uniform(0.0 + 1e-12, threshold, size=loops)  # wBE -> pE

    pC = power[:, 1]  # P(C=1 | B=1)
    pE = power[:, 2]  # P(E=1 | B=1)

    # --- wCE -> オッズ比（対称な連関パラメータ）---
    # wCE∈(0,1) を κ∈[-or_max,+or_max] に線形対応させ、OR=exp(κ) に変換
    kappa = (2.0 * power[:, 0] - 1.0) * or_max
    OR = np.exp(kappa)  # OR>0、OR=1 で独立

    # --- G'0: 独立（従来の probs0 と同じ）---
    probs0 = np.vstack([
        pC * pE,               # (E=1,C=1)
        pC * (1.0 - pE),       # (E=0,C=1)
        (1.0 - pC) * pE,       # (E=1,C=0)
        (1.0 - pC) * (1.0 - pE)  # (E=0,C=0)
    ]).T  # shape=(loops,4)

    # --- G'1: 周辺(pC,pE)と OR から 2×2 を再構成 ---
    # 連立:  p11=x, p10=pE-x, p01=pC-x, p00=1-pE-pC+x,
    #        OR = (p11*p00)/(p10*p01)
    # → (θ-1)x^2 + B x + θ pE pC = 0,  θ=OR,
    #    B = -(1 + (θ-1)(pE + pC))
    theta = OR
    A = (theta - 1.0)
    B = -(1.0 + (theta - 1.0) * (pE + pC))
    Cq = theta * pE * pC

    disc = B * B - 4.0 * A * Cq
    # 数値誤差ケア
    disc = np.maximum(disc, 0.0)
    sqrt_disc = np.sqrt(disc)

    # 2解の候補
    denom = 2.0 * A
    with np.errstate(divide='ignore', invalid='ignore'):
        x1 = (-B + sqrt_disc) / (denom + eps)
        x2 = (-B - sqrt_disc) / (denom + eps)

    # OR ≈ 1（A≈0）のときは独立解 x=pE*pC を使う
    indep_x = pE * pC
    near_indep = np.isclose(A, 0.0, atol=1e-10)

    # 妥当域に入る解を選択（max(0, pE+pC-1) ≤ x ≤ min(pE,pC)）
    lower = np.maximum(0.0, pE + pC - 1.0)
    upper = np.minimum(pE, pC)

    def pick_valid(xa, xb):
        xa_ok = (xa >= lower) & (xa <= upper)
        xb_ok = (xb >= lower) & (xb <= upper)
        # 両方OKなら、どちらでも良いが数値的に安定な方（分散が小さい方）を選ぶ
        choice = np.where(xa_ok & ~xb_ok, xa,
                 np.where(~xa_ok & xb_ok, xb,
                 np.where(xa_ok & xb_ok, xa, np.nan)))
        return choice

    x = pick_valid(x1, x2)
    # NaN や近独立は独立解で埋める
    x = np.where(near_indep | ~np.isfinite(x), indep_x, x)
    # 最終クリップ
    x = np.clip(x, lower, upper)

    # G'1 のセル確率（順序は (11,01,10,00)）
    p11 = x
    p01 = pC - x
    p10 = pE - x
    p00 = 1.0 - pE - pC + x
    probs1 = np.vstack([p11, p01, p10, p00]).T

    # --- ログ尤度を log-mean-exp で周辺化 ---
    def log_marginal(probs):
        ll = (N[0] * np.log(probs[:, 0] + eps) +
              N[1] * np.log(probs[:, 1] + eps) +
              N[2] * np.log(probs[:, 2] + eps) +
              N[3] * np.log(probs[:, 3] + eps))
        m = np.max(ll)
        return m + np.log(np.mean(np.exp(ll - m)))

    loglike1 = log_marginal(probs1)
    loglike0 = log_marginal(probs0)

    return loglike1 - loglike0


def evaluate_counts(named_counts, threshold, loops):
    """Return DataFrame with CS/UCS scores for the provided (a,b,c,d) sets."""
    rows = []
    for label, counts in named_counts:
        cs_val = CS_generic(counts, threshold=threshold, loops=loops)
        ucs_val = UCS_generic(counts, threshold=threshold, loops=loops)
        rows.append({
            "label": label,
            "a": counts[0],
            "b": counts[1],
            "c": counts[2],
            "d": counts[3],
            "CS_generic": cs_val,
            "UCS_generic": ucs_val,
            "CS_minus_UCS": cs_val - ucs_val,
        })
    return pd.DataFrame(rows)


def load_common_samples() -> List[Tuple[str, Tuple[int, int, int, int]]]:
    json_path = Path(__file__).with_name("samples_common.json")
    with json_path.open("r", encoding="utf-8") as f:
        samples = json.load(f)["common_samples"]

    return [
        (
            key,
            (
                int(vals["a"]),
                int(vals["b"]),
                int(vals["c"]),
                int(vals["d"]),
            ),
        )
        for key, vals in samples.items()
    ]


def build_default_tables(threshold: float, loops: int):
    common_counts = load_common_samples()
    df_common = (
        evaluate_counts(common_counts, threshold=threshold, loops=loops)
        .rename(columns={"label": "stimulus"})
        .sort_values("stimulus")
    )

    uniform_samples = [
        ("uniform_1", (1, 1, 1, 1)),
        ("uniform_10", (10, 10, 10, 10)),
        ("uniform_100", (100, 100, 100, 100)),
        ("uniform_1000", (1000, 1000, 1000, 1000)),
    ]

    fivefold_samples = [
        ("a_x5", (5, 1, 1, 1)),
        ("b_x5", (1, 5, 1, 1)),
        ("c_x5", (1, 1, 5, 1)),
        ("d_x5", (1, 1, 1, 5)),
    ]

    df_uniform = evaluate_counts(uniform_samples, threshold=threshold, loops=loops)
    df_uniform["scenario"] = "balanced_size"

    df_fivefold = evaluate_counts(fivefold_samples, threshold=threshold, loops=loops)
    df_fivefold["scenario"] = "single_cell_scaled"

    return df_common, df_uniform, df_fivefold

# def UCS_generic(counts, threshold, is_gene=True, loops=10000):
#     """
#     UCS_generic:
#     無向グラフィカルモデルに基づいたUndirected Causal Support (UCS) を
#     モンテカルロ法により計算する汎用的な関数。

#     Args:
#         counts (tuple): 共起データの2x2分割表 (a, b, c, d)
#                        a: C=1, E=1
#                        b: C=1, E=0
#                        c: C=0, E=1
#                        d: C=0, E=0
#         threshold (float): 稀少性制約を表すパラメータ（例：0.3）
#         is_gene (bool): 原因が生成的かどうか（True:生成的 / False:抑制的）
#         loops (int): サンプリングの繰り返し回数（精度向上用）

#     Returns:
#         float: UCSスコア（G1とG0の対数尤度比）
#     """

#     rng = np.random.default_rng()
#     power = np.zeros((loops, 3))   # wCE, wBC, wBE を保存する行列

#     # 各サンプルでランダムに確率値を生成
#     wCE = rng.uniform(0, 1)              # 原因→結果（wCE）
#     wBC = rng.uniform(0+1e-8, threshold) # 背景→原因（wBC）
#     wBE = rng.uniform(0+1e-8, threshold) # 背景→結果（wBE）

#     a, b, c, d = counts  # データカウントを展開

#     # 各事象に対応する確率の定義
#     if is_gene:
#         # 生成
#         denom = (
#             np.sqrt(power[:,1]*power[:,2]*(1 - (1 - power[:,0])*(1 - power[:,1]))*(1 - (1 - power[:,0])*(1 - power[:,2])))
#             + np.sqrt(power[:,1]*(1 - power[:,2])*power[:,1]*((1 - power[:,0])*(1 - power[:,2])))
#             + np.sqrt((1 - power[:,1])*power[:,2]*power[:,2]*((1 - power[:,0])*(1 - power[:,1])))
#             + (1 - power[:,1])*(1 - power[:,2])
#         )
#         probs1 = [
#             np.sqrt(power[:,1]*power[:,2]*(1 - (1 - power[:,0])*(1 - power[:,1]))*(1 - (1 - power[:,0])*(1 - power[:,2]))) / denom,  # P(E=1|C=1)
#             np.sqrt(power[:,1]*(1 - power[:,2])*power[:,1]*((1 - power[:,0])*(1 - power[:,2]))) / denom,                           # P(E=0|C=1)
#             np.sqrt((1 - power[:,1])*power[:,2]*power[:,2]*((1 - power[:,0])*(1 - power[:,1]))) / denom,                           # P(E=1|C=0)
#             (1 - power[:,1])*(1 - power[:,2]) / denom                                                                              # P(E=0|C=0)
#         ]
#     else:
#         # 抑制
#         denom = (
#             np.sqrt(power[:,1]*power[:,2]*((power[:,1]*(1 - power[:,0]))*(power[:,2]*(1 - power[:,0]))))
#             + np.sqrt(power[:,1]*(1 - power[:,2])*power[:,1]*(1 - (power[:,2]*(1 - power[:,0]))))
#             + np.sqrt((1 - power[:,1])*power[:,2]*(1 - (power[:,1]*(1 - power[:,0])))*power[:,2])
#             + (1 - power[:,1])*(1 - power[:,2])
#         )
#         probs1 = [
#             np.sqrt(power[:,1]*power[:,2]*((power[:,1]*(1 - power[:,0]))*(power[:,2]*(1 - power[:,0])))) / denom,
#             np.sqrt(power[:,1]*(1 - power[:,2])*power[:,1]*(1 - (power[:,2]*(1 - power[:,0])))) / denom,
#             np.sqrt((1 - power[:,1])*power[:,2]*(1 - (power[:,1]*(1 - power[:,0])))*power[:,2]) / denom,
#             (1 - power[:,1])*(1 - power[:,2]) / denom
#         ]

#     # 非因果構造（G0）の確率：CとEが独立（P(E|C)=P(E)）
#     probs0 = [
#         power[:,1]*power[:,2],                      # P(E=1|C=1)
#         power[:,1]*(1 - power[:,2]),                # P(E=0|C=1)
#         (1 - power[:,1])*power[:,2],                # P(E=1|C=0)
#         (1 - power[:,1])*(1 - power[:,2])           # P(E=0|C=0)
#     ]

#     # 尤度計算
#     loglike1 = np.sum(np.array([a, b, c, d])[:, np.newaxis] * np.log(probs1), axis=0)
#     loglike0 = np.sum(np.array([a, b, c, d])[:, np.newaxis] * np.log(probs0), axis=0)


#     like1 = np.mean(np.exp(loglike1))
#     like0 = np.mean(np.exp(loglike0))

#     logscore = np.log(like1 / like0)  # 対数尤度比
#     return logscore

# ------------------------- 刺激セットの読み込みと差分表 ----------------------
# ファイルから (a,b,c,d) を取得
json_path = Path(__file__).with_name("samples_common.json")
with json_path.open("r", encoding="utf-8") as f:
    samples = json.load(f)["common_samples"]

# 計算条件（必要に応じて変更可）
threshold = 1.0     # 稀少性上限 x（例：0.3）
loops     = 50000   # モンテカルロ試行回数（計算時間と精度のトレードオフ）

# 各刺激について CS_generic と UCS_generic を計算し、差分を表にまとめる
common_counts = []
for key, vals in samples.items():
    counts = (int(vals["a"]), int(vals["b"]), int(vals["c"]), int(vals["d"]))
    common_counts.append((key, counts))

df_common = evaluate_counts(common_counts, threshold=threshold, loops=loops)
df_common = df_common.rename(columns={"label": "stimulus"}).sort_values("stimulus")

uniform_samples = [
    ("uniform_1", (1, 1, 1, 1)),
    ("uniform_10", (10, 10, 10, 10)),
    ("uniform_100", (100, 100, 100, 100)),
    ("uniform_1000", (1000, 1000, 1000, 1000)),
]

fivefold_samples = [
    ("a_x5", (5, 1, 1, 1)),
    ("b_x5", (1, 5, 1, 1)),
    ("c_x5", (1, 1, 5, 1)),
    ("d_x5", (1, 1, 1, 5)),
]

fivefold2_samples = [
    ("a_x50", (50, 10, 10, 10)),
    ("b_x50", (10, 50, 10, 10)),
    ("c_x50", (10, 10, 50, 10)),
    ("d_x50", (10, 10, 10, 50)),
]

fivefold3_samples = [
    ("a_x500", (500, 100, 100, 100)),
    ("b_x500", (100, 500, 100, 100)),
    ("c_x500", (100, 100, 500, 100)),
    ("d_x500", (100, 100, 100, 500)),
]

fivefold4_samples = [
    ("a_x5000", (5000, 1000, 1000, 1000)),
    ("b_x5000", (1000, 5000, 1000, 1000)),
    ("c_x5000", (1000, 1000, 5000, 1000)),
    ("d_x5000", (1000, 1000, 1000, 5000)),
]

df_uniform = evaluate_counts(uniform_samples, threshold=threshold, loops=loops)
df_uniform["scenario"] = "balanced_size"

df_fivefold = evaluate_counts(fivefold_samples, threshold=threshold, loops=loops)
df_fivefold["scenario"] = "single_cell_scaled"

df_fivefold2 = evaluate_counts(fivefold2_samples, threshold=threshold, loops=loops)
df_fivefold2["scenario"] = "single_cell_scaled_2"

df_fivefold3 = evaluate_counts(fivefold3_samples, threshold=threshold, loops=loops)
df_fivefold3["scenario"] = "single_cell_scaled_3"

df_fivefold4 = evaluate_counts(fivefold4_samples, threshold=threshold, loops=loops)
df_fivefold4["scenario"] = "single_cell_scaled_4"

# display_dataframe_to_user("CS_generic vs UCS_generic (common samples)", df_common)

# CSVとして保存（ダウンロード用）
out_path = Path("CS_UCS_generic_diff2.csv")
df_common.to_csv(out_path, index=False)

if __name__ == "__main__":
    print("Common samples saved to:", out_path)
    print("\nCommon samples (first 10 rows):")
    print(df_common.head(10).to_string(index=False))

    print("\nBalanced sample-size scaling:")
    print(df_uniform.to_string(index=False))

    print("\nSingle-cell fivefold scaling:")
    print(df_fivefold.to_string(index=False))

    print("\nSingle-cell fivefold scaling 2:")
    print(df_fivefold2.to_string(index=False))

    print("\nSingle-cell fivefold scaling 3:")
    print(df_fivefold3.to_string(index=False))

    print("\nSingle-cell fivefold scaling 4:")
    print(df_fivefold4.to_string(index=False))
