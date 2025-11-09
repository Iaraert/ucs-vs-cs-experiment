import argparse
import json
import math
import numpy as np
import pandas as pd
import warnings
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

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

def UCS(counts, threshold, is_gene=True, loops=100000):
    rng = np.random.default_rng()
    power = np.zeros((loops, 3))

    for i in range(loops):
        power0 = rng.uniform(0+1e-100, threshold)  # wBC
        power1 = rng.uniform(0+1e-100, threshold)  # wBE
        power2 = rng.uniform(0, 1)                 # wCE
        power[i] = [power0, power1, power2]

    a, b, c, d = counts
    wBC = power[:, 0]
    wBE = power[:, 1]
    wCE = power[:, 2]

    # BC / BE
    if is_gene:  # noisy-OR
        sameBC, diffBC = wBC, (1 - wBC)
        sameBE, diffBE = wBE, (1 - wBE)
    else:        # noisy-AND-NOT
        sameBC, diffBC = (1 - wBC), wBC
        sameBE, diffBE = (1 - wBE), wBE

    # --- CE ---
    if is_gene:
        # noisy-OR: P(E=1|C,B=1)
        Pe1_c1 = 1.0 - (1.0 - wBE) * (1.0 - wCE)
        Pe1_c0 = wBE
    else:
        # noisy-AND-NOT: P(E=1|C,B=1)
        Pe1_c1 = wBE * (1.0 - wCE)
        Pe1_c0 = wBE

    Pe0_c1 = 1.0 - Pe1_c1
    Pe0_c0 = 1.0 - Pe1_c0

    # 事前 P(C=1|B=1)=wBC を使って、周辺 P(E|B=1) を作る（分母）
    # P(E=1|B=1) = sum_c P(E=1|c,B=1) P(c|B=1)
    Pe1_b1 = wBC * Pe1_c1 + (1.0 - wBC) * Pe1_c0
    Pe0_b1 = 1.0 - Pe1_b1

    # Bayes: P(C=1|E=e,B=1) = P(E=e|C=1,B=1) P(C=1|B=1) / P(E=e|B=1)
    Pc1_e1 = (Pe1_c1 * wBC) / (Pe1_b1 + 1e-100)
    Pc1_e0 = (Pe0_c1 * wBC) / (Pe0_b1 + 1e-100)
    Pc0_e1 = 1.0 - Pc1_e1
    Pc0_e0 = 1.0 - Pc1_e0

    # セルごとの ψ_CE = sqrt( P(E|C,B=1) * P(C|E,B=1) )
    psi_ce_11 = np.sqrt(Pe1_c1 * Pc1_e1)  # C=1,E=1
    psi_ce_10 = np.sqrt(Pe0_c1 * Pc1_e0)  # C=1,E=0
    psi_ce_01 = np.sqrt(Pe1_c0 * Pc0_e1)  # C=0,E=1
    psi_ce_00 = np.sqrt(Pe0_c0 * Pc0_e0)  # C=0,E=0

    # G1'
    # φ(c,e) = ψ(b,c) ψ(b,e) ψ(c,e)  ; (C,E)=(11,10,01,00)
    phi11 = (sameBC) * (sameBE) * (psi_ce_11)
    phi10 = (sameBC) * (diffBE) * (psi_ce_10)
    phi01 = (diffBC) * (sameBE) * (psi_ce_01)
    phi00 = (diffBC) * (diffBE) * (psi_ce_00)

    Z1 = phi11 + phi10 + phi01 + phi00
    p11 = phi11 / (Z1 + 1e-100)
    p10 = phi10 / (Z1 + 1e-100)
    p01 = phi01 / (Z1 + 1e-100)
    p00 = phi00 / (Z1 + 1e-100)

    probs1 = [p11, p10, p01, p00]

    # G0'
    phi11_0 = (sameBC) * (sameBE)
    phi10_0 = (sameBC) * (diffBE)
    phi01_0 = (diffBC) * (sameBE)
    phi00_0 = (diffBC) * (diffBE)

    Z0 = phi11_0 + phi10_0 + phi01_0 + phi00_0
    q11 = phi11_0 / (Z0 + 1e-100)
    q10 = phi10_0 / (Z0 + 1e-100)
    q01 = phi01_0 / (Z0 + 1e-100)
    q00 = phi00_0 / (Z0 + 1e-100)

    probs0 = [q11, q10, q01, q00]

    # 尤度 → 周辺化
    loglike1 = np.sum((np.ones((loops, 1)) * np.array(counts)) * np.log(np.array(probs1) + 1e-100).T, axis=1)
    like1 = np.sum(np.exp(loglike1)) * (1/loops)

    loglike0 = np.sum((np.ones((loops, 1)) * np.array(counts)) * np.log(np.array(probs0) + 1e-100).T, axis=1)
    like0 = np.sum(np.exp(loglike0)) * (1/loops)

    logscore = np.log(like1/like0)
    return logscore

def CS(counts, threshold, is_gene, loops=50000):
    rng = np.random.default_rng()  # 乱数ジェネレーター
    power = np.zeros((loops, 2))

    # ループを実行して条件を満たす乱数を生成
    for i in range(loops):
      power0 = rng.uniform(0+1e-100, threshold)
      power1 = rng.uniform(0, 1)
      # power1 = threshold
      power[i] = [power0,power1]

    a, b, c, d = counts

    wBE = power[:, 0]
    wCE = power[:, 1]

    if is_gene:
      probs1 = [
          (1 - (1 - wCE) * (1 - wBE)),# P(E=1|C=1)
          (1 - wCE) * (1 - wBE),# P(E=0|C=1)
          wBE,# P(E=1|C=0)
          (1 - wBE),# P(E=0|C=0)
      ]
    else:
      probs1 = [
          wBE - (wCE * wBE),# P(E=1|C=1)
          1 - (wBE - (wCE * wBE)),# P(E=0|C=1)
          wBE,# P(E=1|C=0)
          1 - wBE,# P(E=0|C=0)
      ]

    probs0 = [
        wBE,# P(E=1|C=1)
        (1 - wBE),# P(E=0|C=1)
        wBE,# P(E=1|C=0)
        (1 - wBE),# P(E=0|C=0)
    ]

    loglike1 = np.sum((np.ones((loops, 1)) * np.array(counts)) * np.log(probs1).T, axis=1)
    like1 = sum(np.exp(loglike1)) * (1/loops)

    loglike0 = np.sum((np.ones((loops, 1)) * np.array(counts)) * np.log(probs0).T, axis=1)
    like0 = sum(np.exp(loglike0)) * (1/loops)

    logscore = np.log(like1/like0)
    return logscore

def evaluate_counts(named_counts, threshold, loops):
    """Return DataFrame with CS/UCS scores for the provided (a,b,c,d) sets."""
    rows = []
    for label, counts in named_counts:
        cs_val = CS(counts, threshold=threshold, loops=loops)
        ucs_val = UCS(counts, threshold=threshold, loops=loops)
        rows.append({
            "label": label,
            "a": counts[0],
            "b": counts[1],
            "c": counts[2],
            "d": counts[3],
            "CS": cs_val,
            "UCS": ucs_val,
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

# ------------------------- 刺激セットの読み込みと差分表 ----------------------
# ファイルから (a,b,c,d) を取得
# json_path = Path(__file__).with_name("samples_common.json")
# with json_path.open("r", encoding="utf-8") as f:
#     samples = json.load(f)["common_samples"]

# # 計算条件（必要に応じて変更可）
# threshold = 1.0     # 稀少性上限 x（例：0.3）
# loops     = 50000   # モンテカルロ試行回数（計算時間と精度のトレードオフ）

# # 各刺激について CS と UCS を計算し、差分を表にまとめる
# common_counts = []
# for key, vals in samples.items():
#     counts = (int(vals["a"]), int(vals["b"]), int(vals["c"]), int(vals["d"]))
#     common_counts.append((key, counts))

# df_common = evaluate_counts(common_counts, threshold=threshold, loops=loops)
# df_common = df_common.rename(columns={"label": "stimulus"}).sort_values("stimulus")

# uniform_samples = [
#     ("uniform_1", (1, 1, 1, 1)),
#     ("uniform_10", (10, 10, 10, 10)),
#     ("uniform_100", (100, 100, 100, 100)),
#     ("uniform_1000", (1000, 1000, 1000, 1000)),
# ]

# fivefold_samples = [
#     ("a_x5", (5, 1, 1, 1)),
#     ("b_x5", (1, 5, 1, 1)),
#     ("c_x5", (1, 1, 5, 1)),
#     ("d_x5", (1, 1, 1, 5)),
# ]

# fivefold2_samples = [
#     # ("a_x50", (50, 10, 10, 10)),
#     # ("b_x50", (10, 50, 10, 10)),
#     # ("c_x50", (10, 10, 50, 10)),
#     # ("d_x50", (10, 10, 10, 50)),
#     ("a_x50", (60, 60, 0, 120)),
#     ("b_x50", (60, 30, 30, 60)),
#     ("c_x50", (60, 0, 60, 0)),
#     ("d_x50", (70, 0, 60, 10)),
# ]

# fivefold3_samples = [
#     ("a_x500", (500, 100, 100, 100)),
#     ("b_x500", (100, 500, 100, 100)),
#     ("c_x500", (100, 100, 500, 100)),
#     ("d_x500", (100, 100, 100, 500)),
# ]

# fivefold4_samples = [
#     ("a_x5000", (5000, 1000, 1000, 1000)),
#     ("b_x5000", (1000, 5000, 1000, 1000)),
#     ("c_x5000", (1000, 1000, 5000, 1000)),
#     ("d_x5000", (1000, 1000, 1000, 5000)),
# ]

# df_uniform = evaluate_counts(uniform_samples, threshold=threshold, loops=loops)
# df_uniform["scenario"] = "balanced_size"

# df_fivefold = evaluate_counts(fivefold_samples, threshold=threshold, loops=loops)
# df_fivefold["scenario"] = "single_cell_scaled"

# df_fivefold2 = evaluate_counts(fivefold2_samples, threshold=threshold, loops=loops)
# df_fivefold2["scenario"] = "single_cell_scaled_2"

# df_fivefold3 = evaluate_counts(fivefold3_samples, threshold=threshold, loops=loops)
# df_fivefold3["scenario"] = "single_cell_scaled_3"

# df_fivefold4 = evaluate_counts(fivefold4_samples, threshold=threshold, loops=loops)
# df_fivefold4["scenario"] = "single_cell_scaled_4"

# # display_dataframe_to_user("CS vs UCS (common samples)", df_common)

# # CSVとして保存（ダウンロード用）
# out_path = Path("CS_UCS_diff.csv")
# df_common.to_csv(out_path, index=False)

# if __name__ == "__main__":
#     print("Common samples saved to:", out_path)
#     print("\nCommon samples (first 10 rows):")
#     print(df_common.head(10).to_string(index=False))

#     print("\nBalanced sample-size scaling:")
#     print(df_uniform.to_string(index=False))

#     print("\nSingle-cell fivefold scaling:")
#     print(df_fivefold.to_string(index=False))

#     print("\nSingle-cell fivefold scaling 2:")
#     print(df_fivefold2.to_string(index=False))

#     print("\nSingle-cell fivefold scaling 3:")
#     print(df_fivefold3.to_string(index=False))

#     print("\nSingle-cell fivefold scaling 4:")
#     print(df_fivefold4.to_string(index=False))