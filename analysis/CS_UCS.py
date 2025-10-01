from numba import njit, prange
import math
import numpy as np
import warnings
import time

# Number of Monte Carlo samples
loop_count = 50000

VALID_CONDITION_VALUES = {0, 1}


def normalize_condition_value(cond_value):
    """正規化された条件値 (0 または 1)。無効値は警告を出して None を返す"""
    if cond_value is None:
        return None

    if isinstance(cond_value, (float, np.floating)) and np.isnan(cond_value):
        warnings.warn("Condition value is NaN. Falling back to default behaviour.", UserWarning)
        return None

    if isinstance(cond_value, str):
        stripped = cond_value.strip()
        if stripped == "":
            warnings.warn("Condition value is an empty string. Falling back to default behaviour.", UserWarning)
            return None
        try:
            parsed = float(stripped)
        except ValueError:
            warnings.warn(f"Invalid condition value '{cond_value}'. Falling back to default behaviour.", UserWarning)
            return None
        cond_int = int(parsed)
        if float(cond_int) != parsed:
            warnings.warn(f"Unexpected condition value '{cond_value}'. Falling back to default behaviour.", UserWarning)
            return None
    else:
        try:
            cond_int = int(cond_value)
        except (TypeError, ValueError):
            warnings.warn(f"Invalid condition value '{cond_value}'. Falling back to default behaviour.", UserWarning)
            return None
        try:
            cond_float = float(cond_value)
        except (TypeError, ValueError):
            cond_float = None
        if cond_float is not None and float(cond_int) != cond_float:
            warnings.warn(f"Unexpected condition value '{cond_value}'. Falling back to default behaviour.", UserWarning)
            return None

    if cond_int in VALID_CONDITION_VALUES:
        return cond_int

    warnings.warn(f"Unexpected condition value '{cond_value}'. Falling back to default behaviour.", UserWarning)
    return None

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

    # power[:, 0]
    # power[:, 1]

    if is_gene:
      probs1 = [
          (1 - (1 - power[:, 1]) * (1 - power[:, 0])),# P(E=1|C=1)
          (1 - power[:, 1]) * (1 - power[:, 0]),# P(E=0|C=1)
          power[:, 0],# P(E=1|C=0)
          (1 - power[:, 0]),# P(E=0|C=0)
      ]
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

    loglike1 = np.sum((np.ones((loops, 1)) * counts_loglike1) * np.log(probs1).T, axis=1)
    like1 = sum(np.exp(loglike1)) * (1/loops)

    loglike0 = np.sum((np.ones((loops, 1)) * counts_loglike0) * np.log(probs0).T, axis=1)
    like0 = sum(np.exp(loglike0)) * (1/loops)

    logscore = np.log(like1/like0)
    return logscore

# def UCS(counts, threshold, is_gene, loops=loop_count, counts_loglike0=None):
#     rng = np.random.default_rng()
#     power = np.zeros((loops, 3))

#     for i in range(loops):
#       power0 = rng.uniform(0, 1)
#       power1 = rng.uniform(0+1e-100, threshold)
#       power2 = rng.uniform(0+1e-100, threshold)
#       # power1 = threshold
#       # power2 = threshold
#       power[i] = [power0,power1,power2]

#     counts_loglike1 = np.array(counts, dtype=float)
#     counts_loglike0 = (
#         np.array(counts_loglike0, dtype=float) if counts_loglike0 is not None else counts_loglike1
#     )
#     # power[:, 0]
#     # power[:, 1]
#     # power[:, 2]
#     if is_gene:
#       # z = /(np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2]))) + np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2])))) + np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1])))) + (1 - power[:, 1]) * (1 - power[:, 2]))
#       probs1 = [
#           np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2])))/(np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2]))) + np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2])))) + np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1])))) + (1 - power[:, 1]) * (1 - power[:, 2])),
#           np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2]))))/(np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2]))) + np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2])))) + np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1])))) + (1 - power[:, 1]) * (1 - power[:, 2])),
#           np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1]))))/(np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2]))) + np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2])))) + np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1])))) + (1 - power[:, 1]) * (1 - power[:, 2])),
#           (1 - power[:, 1]) * (1 - power[:, 2])/(np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2]))) + np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2])))) + np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1])))) + (1 - power[:, 1]) * (1 - power[:, 2])),
#       ]
#     else:
#       # z = / (np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0])))) + np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0]))))) + np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2])) + (1 - power[:, 1]) * (1 - power[:, 2]))
#       probs1 = [
#           np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0]))))  / (np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0])))) + np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0]))))) + np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2])) + (1 - power[:, 1]) * (1 - power[:, 2])),
#           np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0])))))  / (np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0])))) + np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0]))))) + np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2])) + (1 - power[:, 1]) * (1 - power[:, 2])),
#           np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2]))  / (np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0])))) + np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0]))))) + np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2])) + (1 - power[:, 1]) * (1 - power[:, 2])),
#           (1 - power[:, 1]) * (1 - power[:, 2])  / (np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0])))) + np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0]))))) + np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2])) + (1 - power[:, 1]) * (1 - power[:, 2])),
#       ]
#     probs0 = [
#         power[:, 1] * power[:, 2],
#         power[:, 1] * (1 - power[:, 2]),
#         (1 - power[:, 1]) * power[:, 2],
#         (1 - power[:, 1]) * (1 - power[:, 2]),
#     ]

#     loglike1 = np.sum((np.ones((loops, 1)) * counts_loglike1) * np.log(probs1).T, axis=1)
#     like1 = sum(np.exp(loglike1)) * (1/loops)

#     loglike0 = np.sum((np.ones((loops, 1)) * counts_loglike0) * np.log(probs0).T, axis=1)
#     like0 = sum(np.exp(loglike0)) * (1/loops)

#     logscore = np.log(like1/like0)
#     return logscore


# @njit
# def UCS(counts, threshold, is_gene, loops=loop_count):
#     power = np.zeros((loops, 3))
#     for i in range(loops):
#         power0 = np.random.uniform(0.0, 1.0)
#         # 0サンプルの回避，下限に1e-100(最小値)を設定
#         power1 = np.random.uniform(1e-100, threshold)
#         power2 = np.random.uniform(1e-100, threshold)
#         power[i, 0] = power0; power[i, 1] = power1; power[i, 2] = power2

#     probs1 = np.zeros((4, loops))
#     probs0 = np.zeros((4, loops))

#     if is_gene:
#         denom = (
#             np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2])))
#             + np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2]))))
#             + np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1]))))
#             + (1 - power[:, 1]) * (1 - power[:, 2])
#         )
#         probs1[0, :] = np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2]))) / denom
#         probs1[1, :] = np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2])))) / denom
#         probs1[2, :] = np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1])))) / denom
#         probs1[3, :] = (1 - power[:, 1]) * (1 - power[:, 2]) / denom
#     else:
#         denom = (
#             np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0]))))
#             + np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0])))))
#             + np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2]))
#             + (1 - power[:, 1]) * (1 - power[:, 2])
#         )
#         probs1[0, :] = np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0])))) / denom
#         probs1[1, :] = np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0]))))) / denom
#         probs1[2, :] = np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2])) / denom
#         probs1[3, :] = (1 - power[:, 1]) * (1 - power[:, 2]) / denom

#     probs0[0, :] = power[:, 1] * power[:, 2]
#     probs0[1, :] = power[:, 1] * (1 - power[:, 2])
#     probs0[2, :] = (1 - power[:, 1]) * power[:, 2]
#     probs0[3, :] = (1 - power[:, 1]) * (1 - power[:, 2])

#     # 丸め誤差で0になるのを防ぐ
#     eps = 1e-300
#     for j in range(4):
#         probs1[j,:] = np.maximum(probs1[j,:], eps)
#         probs0[j,:] = np.maximum(probs0[j,:], eps)

#     loglike1 = np.zeros(loops)
#     loglike0 = np.zeros(loops)

#     for i in range(loops):
#         for j in range(4):
#             loglike1[i] += counts[j] * np.log(probs1[j, i])
#             loglike0[i] += counts[j] * np.log(probs0[j, i])

#     like1 = 0.0; like0 = 0.0
#     for i in range(loops):
#         like1 += np.exp(loglike1[i])
#         like0 += np.exp(loglike0[i])
#     like1 /= loops; like0 /= loops

#     logscore = np.log(like1 / like0)
#     # 符合反転の取り消し
#     # if not is_gene:
#     #     logscore = -logscore
#     return logscore

def UCS(conts, threshold, is_gene, loops=loop_count):
    rng = np.random.default_rng()  # 乱数ジェネレーター
    power = np.zeros((loops, 3))

    # ループを実行して条件を満たす乱数を生成
    for i in range(loops):
      power0 = rng.uniform(0, 1)
      power1 = rng.uniform(0+1e-100, threshold)
      power2 = rng.uniform(0+1e-100, threshold)
      # power1 = threshold
      # power2 = threshold
      power[i] = [power0,power1,power2]
    a, b, c, d = conts
    # power[:, 0] 原因と結果のw
    # power[:, 1] 背景と原因のw
    # power[:, 2] 背景と結果のw
    if is_gene:
      # z = /(np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2]))) + np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2])))) + np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1])))) + (1 - power[:, 1]) * (1 - power[:, 2]))
      probs1 = [
          np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2])))/(np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2]))) + np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2])))) + np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1])))) + (1 - power[:, 1]) * (1 - power[:, 2])),
          np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2]))))/(np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2]))) + np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2])))) + np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1])))) + (1 - power[:, 1]) * (1 - power[:, 2])),
          np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1]))))/(np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2]))) + np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2])))) + np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1])))) + (1 - power[:, 1]) * (1 - power[:, 2])),
          (1 - power[:, 1]) * (1 - power[:, 2])/(np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2]))) + np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2])))) + np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1])))) + (1 - power[:, 1]) * (1 - power[:, 2])),
      ]
    else:
      # z = / (np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0])))) + np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0]))))) + np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2])) + (1 - power[:, 1]) * (1 - power[:, 2]))
      probs1 = [
          np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0]))))  / (np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0])))) + np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0]))))) + np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2])) + (1 - power[:, 1]) * (1 - power[:, 2])),
          np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0])))))  / (np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0])))) + np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0]))))) + np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2])) + (1 - power[:, 1]) * (1 - power[:, 2])),
          np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2]))  / (np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0])))) + np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0]))))) + np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2])) + (1 - power[:, 1]) * (1 - power[:, 2])),
          (1 - power[:, 1]) * (1 - power[:, 2])  / (np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0])))) + np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0]))))) + np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2])) + (1 - power[:, 1]) * (1 - power[:, 2])),
      ]
    probs0 = [
        power[:, 1] * power[:, 2],
        power[:, 1] * (1 - power[:, 2]),
        (1 - power[:, 1]) * power[:, 2],
        (1 - power[:, 1]) * (1 - power[:, 2]),
    ]

    loglike1 = np.sum((np.ones((loops, 1)) * np.array(conts)) * np.log(probs1).T, axis=1)
    like1 = sum(np.exp(loglike1)) * (1/loops)

    loglike0 = np.sum((np.ones((loops, 1)) * np.array(conts)) * np.log(probs0).T, axis=1)
    like0 = sum(np.exp(loglike0)) * (1/loops)

    logscore = np.log(like1/like0)
    return logscore

@njit(parallel=True, cache=True)
def UCS(counts, threshold, is_gene, loops):
    """
    目的（何を狙うか）
    ----------------------------------------------------------------------
    ・UCS（無向CS）のモンテカルロ周辺化を、高速かつ数値安定に計算する。
    ・大域メモリ（4×loopsの確率配列など）の確保・転送を排除して帯域ボトルネックを解消。
    ・ループ内をスカラ演算に寄せ、不要なsqrt/除算/ログ計算の呼び出しを最小化。
    ・平均(exp(loglike)) ではなく log-mean-exp を用いて桁落ちとオーバーフローを回避。

    実装方針（どう実装したか）
    ----------------------------------------------------------------------
    1) 並列化とキャッシュ
       - @njit(parallel=True, cache=True): prangeで各サンプルiの尤度を並列に独立計算。
       - JIT結果をキャッシュして反復実行の起動コストを削減。

    2) 乱数生成の一括化
       - p0s, p1s, p2s をベクトル一括生成し、ループ中はスカラ読み出しのみ。
       - p1, p2 は [1e-100, threshold]（0サンプル回避）でlog(0)を抑制。

    3) メモリ削減と逐次加算
       - probs1/probs0（形状4×loops）の大型配列を廃止。
       - サンプルiごとに4セルの確率を直接スカラで算出し、対数尤度に逐次加算。

    4) 補助変数による重複計算の削減
       - om0, om1, om2 = 1-p を導入し、(1-p) の再計算や一時オブジェクト生成を低減。

    5) 数値安定化
       - ログ直前のスカラクリップ: log(max(p, eps))（配列clipを廃止して分岐最小化）。
       - 周辺化は log-mean-exp: m=最大値で平行移動→expを安定化→平均のlogを復元。

    6) モデルの忠実性
       - G0（独立）: q11=p(C)p(E), q10=p(C)(1-p(E)), q01=(1-p(C))p(E), q00=(1-p(C))(1-p(E))
       - G1（従属, 無向）: 幾何平均のポテンシャル（t11,t10,t01,t00）→ 正規化で p11..p00
       - 生成/予防で式形を分岐するが、結果は常に log P(D|G1) − log P(D|G0) を返す（符号反転なし）。

    7) 複雑度の削減
       - 2重for（4セル×loops）を、スカラ4回のlog加算×loopsへ固定化。
       - ベクトル化は保持せず、NumbaによるJIT+並列で高速化（CPUキャッシュ効率を優先）。
    """

    # --- 入力の展開：間接参照コストを避けるためスカラに展開 ---
    a, b, c, d = counts[0], counts[1], counts[2], counts[3]
    eps = 1e-300  # 極小値：log(0)回避用

    # --- 乱数の一括生成：ループ内の関数呼び出しを削減 ---
    # p0: w_CE（相互作用）に相当 / [0,1]
    # p1: P(C=1) 事前 / [1e-100, threshold]
    # p2: P(E=1) 事前 / [1e-100, threshold]
    p0s = np.random.uniform(0.0, 1.0, size=loops)
    p1s = np.random.uniform(1e-100, threshold, size=loops)
    p2s = np.random.uniform(1e-100, threshold, size=loops)

    # --- 各サンプルの対数尤度を直接バッファに格納（配列確保は1次元のみ） ---
    loglike1 = np.empty(loops)  # 従属モデル G1
    loglike0 = np.empty(loops)  # 独立モデル G0

    # --- サンプルiごとに独立に計算（parallel） ---
    for i in prange(loops):
        p0 = p0s[i]; p1 = p1s[i]; p2 = p2s[i]
        om0 = 1.0 - p0; om1 = 1.0 - p1; om2 = 1.0 - p2  # (1 - p) を再利用

        # ------- 独立モデル G0（同時確率の直積）-------
        q11 = p1 * p2
        q10 = p1 * om2
        q01 = om1 * p2
        q00 = om1 * om2

        # ------- 従属モデル G1（無向：幾何平均ポテンシャル→正規化）-------
        if is_gene:
            # 生成的因果ケース：上位コードと同じ式形をスカラで構成
            t11 = math.sqrt(p1*p2 * (1.0 - om0*om1) * (1.0 - om0*om2))
            t10 = math.sqrt(p1*om2 * (p1 * (om0*om2)))
            t01 = math.sqrt(om1*p2 * (p2 * (om0*om1)))
            t00 = om1*om2
        else:
            # 予防的因果ケース
            t11 = math.sqrt((p1*p2) * ((p1*om0) * (p2*om0)))
            t10 = math.sqrt((p1*om2) * (p1 * (1.0 - (p2*om0))))
            t01 = math.sqrt((om1*p2) * ((1.0 - (p1*om0)) * p2))
            t00 = om1*om2

        denom = t11 + t10 + t01 + t00  # 正規化定数（4セル分子の総和）
        p11 = t11 / denom; p10 = t10 / denom; p01 = t01 / denom; p00 = t00 / denom

        # ------- 対数尤度へ逐次加算（スカラ・クリップで安定化）-------
        ll1 = 0.0
        ll1 += a * math.log(p11 if p11 > eps else eps)
        ll1 += b * math.log(p10 if p10 > eps else eps)
        ll1 += c * math.log(p01 if p01 > eps else eps)
        ll1 += d * math.log(p00 if p00 > eps else eps)
        loglike1[i] = ll1

        ll0 = 0.0
        ll0 += a * math.log(q11 if q11 > eps else eps)
        ll0 += b * math.log(q10 if q10 > eps else eps)
        ll0 += c * math.log(q01 if q01 > eps else eps)
        ll0 += d * math.log(q00 if q00 > eps else eps)
        loglike0[i] = ll0

    # --- 周辺化：log-mean-exp で数値安定かつ高速に平均を取る ---
    # mean(exp(loglike)) = exp(m) * mean(exp(loglike - m))；m=最大値で平行移動
    m1 = np.max(loglike1); m0 = np.max(loglike0)
    s1 = 0.0; s0 = 0.0
    for i in range(loops):
        s1 += math.exp(loglike1[i] - m1)
        s0 += math.exp(loglike0[i] - m0)
    logmean1 = m1 + math.log(s1/loops)
    logmean0 = m0 + math.log(s0/loops)

    # --- 出力：常に log P(D|G1) − log P(D|G0)（予防でも符号反転しない）---
    return (logmean1 - logmean0)

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

    # 各サンプルでランダムに確率値を生成（稀少性を制限）
    for i in range(loops):
        power0 = rng.uniform(0, 1)                # 原因→結果（wCE）
        power1 = rng.uniform(1e-100, threshold)   # 背景→原因（wBC）
        power2 = rng.uniform(1e-100, threshold)   # 背景→結果（wBE）
        power[i] = [power0, power1, power2]

    a, b, c, d = counts  # データカウントを展開

    # 各事象に対応する確率を定義（生成型/抑制型で異なる）
    if is_gene:
        # 生成的原因のケース
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
        # 抑制的原因のケース
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

    # 尤度（log space）計算
    loglike1 = np.sum(np.array([a, b, c, d])[:, np.newaxis] * np.log(probs1), axis=0)
    loglike0 = np.sum(np.array([a, b, c, d])[:, np.newaxis] * np.log(probs0), axis=0)


    like1 = np.mean(np.exp(loglike1))
    like0 = np.mean(np.exp(loglike0))

    logscore = np.log(like1 / like0)  # 対数尤度比
    return logscore

