from numba import njit, prange
import math
import numpy as np
import warnings
import time

# Number of Monte Carlo samples
loop_count = 50000

VALID_CONDITION_VALUES = {0, 1}

def CS(counts, threshold, is_gene, loops=loop_count, counts_loglike0=None):
    rng = np.random.default_rng()
    power = np.zeros((loops, 2))

    for i in range(loops):
      power0 = rng.uniform(0+1e-100, threshold)
      power1 = rng.uniform(0, 1)
      # power1 = threshold
      power[i] = [power0,power1]

    counts_loglike1 = np.array(counts, dtype=float)
    counts_loglike0 = (
        np.array(counts_loglike0, dtype=float) if counts_loglike0 is not None else counts_loglike1
    )

    # power[:, 0] 原因と結果のw
    # power[:, 1] 背景と原因のw

    if is_gene:
      probs1 = [
          (1 - (1 - power[:, 1]) * (1 - power[:, 0])),# P(E=1|C=1)
          (1 - power[:, 1]) * (1 - power[:, 0]),# P(E=0|C=1)
          power[:, 0],# P(E=1|C=0)
          (1 - power[:, 0]),# P(E=0|C=0)
      ]
      # (1 - (1 - wBC) * (1 - wCE))
      # (1 - wBC) * (1 - wCE)
      # wCE
      # (1 - wCE)

    else:
      probs1 = [
          power[:, 0] - (power[:, 1] * power[:, 0]),# P(E=1|C=1)
          1 - (power[:, 0] - (power[:, 1] * power[:, 0])),# P(E=0|C=1)
          power[:, 0],# P(E=1|C=0)
          1 - power[:, 0],# P(E=0|C=0)
      ]

    probs0 = [
        power[:, 0],# P(E=1|C=1)
        (1 - power[:, 0]),# P(E=0|C=1)
        power[:, 0],# P(E=1|C=0)
        (1 - power[:, 0]),# P(E=0|C=0)
    ]
    # wCE
    # (1 - wCE)
    # wCE
    # (1 - wCE)

    loglike1 = np.sum((np.ones((loops, 1)) * counts_loglike1) * np.log(probs1).T, axis=1)
    like1 = sum(np.exp(loglike1)) * (1/loops)

    loglike0 = np.sum((np.ones((loops, 1)) * counts_loglike0) * np.log(probs0).T, axis=1)
    like0 = sum(np.exp(loglike0)) * (1/loops)

    logscore = np.log(like1/like0)
    return logscore

def UCS(counts, threshold, is_gene=True, loops=100000):
    rng = np.random.default_rng()  # 乱数ジェネレーター
    power = np.zeros((loops, 3))

    # ループを実行して条件を満たす乱数を生成
    for i in range(loops):
      # power[:, 0] 背景と原因(B–C)のw
      # power[:, 1] 背景と結果(B–E)のw
      # power[:, 2] 原因と結果(C–E)のw
      power0 = rng.uniform(0+1e-100, threshold)  # wBC: 背景リンクは弱め（0～threshold）
      power1 = rng.uniform(0+1e-100, threshold)  # wBE
      power2 = rng.uniform(0, 1)                 # wCE: 相関リンクは 0～1 の一様
      power[i] = [power0, power1, power2]

    a, b, cc, d = counts  # 'c' が変数名と被るので cc に
    wBC = power[:, 0]
    wBE = power[:, 1]
    wCE = power[:, 2]

    # --- BC, BE エッジは従来どおり same/diff（二値ポテンシャル）
    if is_gene:
      sameBC, diffBC = wBC, (1 - wBC)
      sameBE, diffBE = wBE, (1 - wBE)
    else:
      sameBC, diffBC = (1 - wBC), wBC
      sameBE, diffBE = (1 - wBE), wBE

    # CE エッジの ψ は wBE と wCE の両方に依存
    # 幾何平均で対称化：same は C=E、diff は C≠E の場合の代表値
    if is_gene:
        # noisy-OR（生成）
        # P(E=1|C=1,B=1) = 1 - (1-wBE)*(1-wCE)
        Pe1_c1 = 1.0 - (1.0 - wBE) * (1.0 - wCE)
        # P(E=1|C=0,B=1) = 1 - (1-wBE) = wBE
        Pe1_c0 = wBE

        Pe0_c1 = 1.0 - Pe1_c1
        Pe0_c0 = 1.0 - Pe1_c0

        sameCE = np.sqrt(Pe1_c1 * Pe0_c0)  # P(E=1|C=1) * P(E=0|C=0)
        diffCE = np.sqrt(Pe1_c0 * Pe0_c1)  # P(E=1|C=0) * P(E=0|C=1)
    else:
        # noisy-AND-NOT（抑制）
        # P(E=1|C=1,B=1) = wBE * (1 - wCE)
        Pe1_c1 = wBE * (1.0 - wCE)
        # P(E=1|C=0,B=1) = wBE
        Pe1_c0 = wBE

        Pe0_c1 = 1.0 - Pe1_c1
        Pe0_c0 = 1.0 - Pe1_c0

        sameCE = np.sqrt(Pe1_c1 * Pe0_c0) # P(E=1|C=1) * P(E=0|C=0)
        diffCE = np.sqrt(Pe1_c0 * Pe0_c1) # P(E=1|C=0) * P(E=0|C=1)

    # ----- G1'（相関あり：C–E エッジ有効） -----
    # φ(c,e) = ψ(b,c) ψ(b,e) ψ(c,e)
    # (C,E) = (1,1),(1,0),(0,1),(0,0)
    phi11 = (sameBC) * (sameBE) * (sameCE)   # C=1,E=1 → BC: same, BE: same, CE: same
    phi10 = (sameBC) * (diffBE) * (diffCE)   # C=1,E=0 → BC: same, BE: diff, CE: diff
    phi01 = (diffBC) * (sameBE) * (diffCE)   # C=0,E=1 → BC: diff, BE: same, CE: diff
    phi00 = (diffBC) * (diffBE) * (sameCE)   # C=0,E=0 → BC: diff, BE: diff, CE: same

    Z1 = phi11 + phi10 + phi01 + phi00
    p11 = phi11 / (Z1 + 1e-100)
    p10 = phi10 / (Z1 + 1e-100)
    p01 = phi01 / (Z1 + 1e-100)
    p00 = phi00 / (Z1 + 1e-100)

    probs1 = [
        p11,  # P(C=1,E=1)
        p10,  # P(C=1,E=0)
        p01,  # P(C=0,E=1)
        p00,  # P(C=0,E=0)
    ]

    # ----- G0'（独立：C–E エッジ無効 → ψ(c,e)=1）-----
    phi11_0 = (sameBC) * (sameBE)
    phi10_0 = (sameBC) * (diffBE)
    phi01_0 = (diffBC) * (sameBE)
    phi00_0 = (diffBC) * (diffBE)

    Z0 = phi11_0 + phi10_0 + phi01_0 + phi00_0
    q11 = phi11_0 / (Z0 + 1e-100)
    q10 = phi10_0 / (Z0 + 1e-100)
    q01 = phi01_0 / (Z0 + 1e-100)
    q00 = phi00_0 / (Z0 + 1e-100)

    probs0 = [
        q11,  # P(C=1,E=1)
        q10,  # P(C=1,E=0)
        q01,  # P(C=0,E=1)
        q00,  # P(C=0,E=0)
    ]


    loglike1 = np.sum((np.ones((loops, 1)) * np.array(counts)) * np.log(np.array(probs1) + 1e-100).T, axis=1)
    like1 = np.sum(np.exp(loglike1)) * (1/loops)

    loglike0 = np.sum((np.ones((loops, 1)) * np.array(counts)) * np.log(np.array(probs0) + 1e-100).T, axis=1)
    like0 = np.sum(np.exp(loglike0)) * (1/loops)

    logscore = np.log(like1/like0)
    return logscore