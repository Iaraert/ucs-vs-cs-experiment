#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_cs_ucs_bic.py

縦長データ → CS / UCS 計算（行ごとに再計算）→ wide → MixedLM → BIC / プロット

* **is_gene** は各行で `estimation > 0` から判定。
* CRT での除外は行わず、IMC・slider 回数・定数回答のみ除外。
* コードを最後まで実装し、出力ファイルが生成されるようにした。
"""
from __future__ import annotations

import itertools
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd
from tqdm import tqdm
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt

# --------------------------------------------------
# 0. 刺激テーブル（sample_number → a,b,c,d）
# --------------------------------------------------
STIMS: Dict[int, Dict[str, int]] = {
    1: dict(a=6, b=6, c=0, d=12),
    2: dict(a=6, b=3, c=3, d=6),
    3: dict(a=6, b=0, c=6, d=0),
    4: dict(a=7, b=6, c=0, d=13),
    5: dict(a=7, b=3, c=3, d=7),
    6: dict(a=7, b=0, c=6, d=1),
}

# --------------------------------------------------
# 1. パス設定
# --------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent
HONBAN: Path = BASE_DIR / "honban"

EST1: Path = HONBAN / "estimations_exp1.csv"
EST2: Path = HONBAN / "estimations_exp1_2.csv"
IMC: Path  = HONBAN / "imc_data_exp2.csv"
PARTICIPANT_ID: Path = HONBAN / "participant_id.csv"

OUT_DIR: Path = (HONBAN / "outputs").resolve()
OUT_DIR.mkdir(parents=True, exist_ok=True)

LONG_CSV = OUT_DIR / "completed_valid_participants_long.csv"
WIDE_CSV = OUT_DIR / "wide_with_cs_ucs.csv"
BIC_CSV  = OUT_DIR / "bic_summary.csv"
PIC_CS   = OUT_DIR / "bic_cs.png"
PIC_UCS  = OUT_DIR / "bic_ucs.png"

# --------------------------------------------------
# 2. CS / UCS 計算パラメータ
# --------------------------------------------------
THRESHOLDS = [round(x, 2) for x in list(np.arange(1.0, 0.0, -0.1)) + [0.01]]  # 1.0, 0.9, …, 0.1, 0.01
LOOPS = 10_000  # モンテカルロ試行回数

# --------------------------------------------------
# 3. CS / UCS 実装をインポート
# --------------------------------------------------
from honban.CS_UCS import CS, UCS  # type: ignore

# --------------------------------------------------
# 4. データ読み込み & 除外
# --------------------------------------------------

def load_and_filter() -> pd.DataFrame:
    """CSV 読み込みと除外処理。CRT は無視。"""
    participant_ids = pd.read_csv(PARTICIPANT_ID, dtype=str)["user_id"].tolist()

    def _load(path: Path) -> pd.DataFrame:
        df = pd.read_csv(path)
        df["user_id"] = df["user_id"].astype(str)
        return df.query("user_id in @participant_ids").copy()

    df1, df2 = _load(EST1), _load(EST2)
    imc      = _load(IMC)

    # 除外 ID 集合
    excl: set[str] = set()
    # IMC fail
    excl |= set(imc.loc[imc.get("result", 1) == 0, "user_id"])
    # slider 回数 != 12
    both = pd.concat([df1, df2])
    excl |= set(both.groupby("user_id").size().loc[lambda s: s != 12].index)
    # estimation が定数
    excl |= set(both.groupby("user_id").estimation.nunique().loc[lambda s: s <= 1].index)

    def to_long(df: pd.DataFrame, block: str) -> pd.DataFrame:
        cols = [
            "user_id", "a_value", "b_value", "c_value", "d_value",
            "estimation", "is_first", "is_symmetric",
            "sample_number", "timestamp",
        ]
        out = df[cols].copy()
        out["block"] = block
        return out

    long_df = pd.concat([
        to_long(df1, "examine1"),
        to_long(df2, "examine1_2"),
    ])

    valid_long = long_df.query("user_id not in @excl").copy()
    valid_long.to_csv(LONG_CSV, index=False, encoding="utf-8")
    print(f"[OK] long CSV saved → {LONG_CSV.relative_to(BASE_DIR)}  (n={valid_long.user_id.nunique()} participants)")
    return valid_long

# --------------------------------------------------
# 5. CS / UCS 計算を行ごとに付加
# --------------------------------------------------

def attach_cs_ucs(df_long: pd.DataFrame) -> pd.DataFrame:
    print("[INFO] Calculating CS / UCS per row …")

    def _calc(row: pd.Series) -> pd.Series:
        flag = bool(row["estimation"] > 0)  # is_gene 判定
        vec = [row["a_value"], row["b_value"], row["c_value"], row["d_value"]]
        res: Dict[str, Any] = {}
        for th in THRESHOLDS:
            res[f"CS_{th}"]  = CS(vec, th, flag, loops=LOOPS)
            res[f"UCS_{th}"] = UCS(vec, th, flag, loops=LOOPS)
        return pd.Series(res)

    csucs = df_long.apply(_calc, axis=1)
    return pd.concat([df_long, csucs], axis=1)

# --------------------------------------------------
# 6. wide 形式へ
# --------------------------------------------------

def make_wide(valid_long: pd.DataFrame) -> pd.DataFrame:
    with_cs = attach_cs_ucs(valid_long)

    dfs: Dict[str, pd.DataFrame] = {}
    for blk in ["examine1", "examine1_2"]:
        tmp = with_cs.query("block == @blk").copy()
        pref = "ex1_" if blk == "examine1" else "ex1_2_"
        rename = {
            "a_value": pref + "a",
            "b_value": pref + "b",
            "c_value": pref + "c",
            "d_value": pref + "d",
            "estimation": pref + "estimation",
            "is_first": pref + "is_first",
            "is_symmetric": pref + "is_symmetric",
        }
        rename.update({c: pref + c for c in tmp.filter(regex=r"^(CS_|UCS_)").columns})
        dfs[blk] = (
            tmp.rename(columns=rename)
               .drop(columns=["timestamp", "block"])
        )

    wide = dfs["examine1"].merge(
        dfs["examine1_2"],
        on=["user_id", "sample_number"],
        how="outer",
    )

    wide["Cond"] = wide["ex1_is_symmetric"].map({1: "SY1", 0: "SY0"})
    col_order = ["Cond", "user_id", "sample_number"] + [c for c in wide.columns if c not in ("Cond", "user_id", "sample_number")]
    wide = wide[col_order]
    wide.to_csv(WIDE_CSV, index=False, encoding="utf-8")
    print(f"[OK] wide CSV saved → {WIDE_CSV.relative_to(BASE_DIR)}")
    return wide

# --------------------------------------------------
# 7. MixedLM & BIC
# --------------------------------------------------

def fit_mixedlm(wide_df: pd.DataFrame) -> pd.DataFrame:
    print("[INFO] Fitting MixedLM models …")
    recs: list[Dict[str, Any]] = []

    for blk, pref in [("ex1", "ex1_"), ("ex1_2", "ex1_2_")]:
        for cond in ["SY0", "SY1"]:
            sub = wide_df.query("Cond == @cond").copy()
            if sub.empty:
                continue
            sub["est"] = sub[f"{pref}estimation"]

            for meas in ["CS", "UCS"]:
                for th in THRESHOLDS:
                    feat = f"{pref}{meas}_{th}"
                    if feat not in sub.columns:
                        continue

                    for mid, spec in {
                        "m0": ("est ~ 1", None),
                        "m1": (f"est ~ {feat}", None),
                        "m2": (f"est ~ {feat}", f"0 + {feat}"),
                        "m3": (f"est ~ {feat}", f"1 + {feat}"),
                    }.items():
                        formula, re_form = spec
                        try:
                            mdl = smf.mixedlm(formula, sub, groups=sub["user_id"], re_formula=re_form)
                            res = mdl.fit(reml=False, method="lbfgs", maxiter=1024, disp=False)
                            bic_val = res.bic
                        except Exception as e:
                            bic_val = np.nan
                            print(f"[WARN] {blk}-{cond}-{meas}-{th}-{mid}: {e}")
                        recs.append({
                            "block": blk,
                            "cond": cond,
                            "measure": meas,
                            "threshold": th,
                            "model": mid,
                            "BIC": bic_val,
                        })

    bic_df = pd.DataFrame.from_records(recs)
    bic_df.to_csv(BIC_CSV, index=False, encoding="utf-8")
    print(f"[OK] BIC CSV saved → {BIC_CSV.relative