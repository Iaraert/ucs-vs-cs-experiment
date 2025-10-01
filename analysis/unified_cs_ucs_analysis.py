# -*- coding: utf-8 -*-
"""
unified_cs_ucs_analysis.py

CS/UCS関連分析の統合版
以下の機能を統合:
1. CS/UCS異なる挙動グループの探索 (cs_ucs_plus.py)
2. 系統的探索による詳細分析 (cs_ucs_systematic_search.py)  
3. 全数探索による網羅的分析 (cs_ucs_exhaustive_search.py)

使用方法:
    python unified_cs_ucs_analysis.py --mode plus
    python unified_cs_ucs_analysis.py --mode systematic
    python unified_cs_ucs_analysis.py --mode exhaustive
    python unified_cs_ucs_analysis.py --mode all
"""

import argparse
import random
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import time
from itertools import combinations
from scipy.stats import pearsonr
from CS_UCS import CS, UCS

# 日本語フォント設定
try:
    import matplotlib_fontja
    matplotlib_fontja.japanize()
except:
    pass

# ==================== 共通設定 ====================
CS_THRESHOLD = 1.0
UCS_THRESHOLDS = [1.0, 0.7, 0.5, 0.3, 0.1]
IS_GENE = True
LOOPS = 10000
GROUP_SIZE = 3
MIN_CORRELATION = -0.8
TOP_GROUPS = 5

# 探索モード別設定
PLUS_SAMPLE_SIZE = 1000
SYSTEMATIC_TARGET_SUM = 32
SYSTEMATIC_MIN_A = 6
EXHAUSTIVE_TARGET_SUM = 32
EXHAUSTIVE_MIN_A = 6

# ==================== 共通ユーティリティ ====================
def random_stimuli(sample_size):
    """ランダム刺激生成"""
    stimuli = []
    max_attempts = sample_size * 10
    attempts = 0
    
    while len(stimuli) < sample_size and attempts < max_attempts:
        attempts += 1
        a, b, c, d = random.randint(1, 30), random.randint(1, 30), random.randint(1, 30), random.randint(1, 30)
        
        try:
            cs_score = CS((a, b, c, d), CS_THRESHOLD, IS_GENE)
            if not np.isnan(cs_score) and not np.isinf(cs_score):
                stimuli.append((a, b, c, d))
        except:
            continue
    
    return stimuli

def is_monotonic_increasing(series):
    """単調増加判定"""
    return all(series[i] <= series[i+1] for i in range(len(series)-1))

def is_monotonic_decreasing(series):
    """単調減少判定"""
    return all(series[i] >= series[i+1] for i in range(len(series)-1))

def compute_all_scores(stimuli, ucs_thresholds=None):
    """全刺激のCS/UCSスコア計算"""
    if ucs_thresholds is None:
        ucs_thresholds = UCS_THRESHOLDS
    
    results = []
    for a, b, c, d in stimuli:
        try:
            cs_score = CS((a, b, c, d), CS_THRESHOLD, IS_GENE)
            if np.isnan(cs_score) or np.isinf(cs_score):
                continue
            
            row = {"a": a, "b": b, "c": c, "d": d, "CS": cs_score}
            
            for ucs_thresh in ucs_thresholds:
                ucs_score = UCS((a, b, c, d), ucs_thresh, IS_GENE)
                row[f"UCS_{ucs_thresh}"] = ucs_score
            
            results.append(row)
        except:
            continue
    
    return pd.DataFrame(results)

def analyze_threshold_results(df, ucs_thresh):
    """閾値別統計分析"""
    ucs_column = f"UCS_{ucs_thresh}"
    
    stats = {
        "threshold": ucs_thresh,
        "total_stimuli": len(df),
        "cs_mean": df["CS"].mean(),
        "cs_std": df["CS"].std(),
        "cs_min": df["CS"].min(),
        "cs_max": df["CS"].max(),
        "ucs_mean": df[ucs_column].mean(),
        "ucs_std": df[ucs_column].std(),
        "ucs_min": df[ucs_column].min(),
        "ucs_max": df[ucs_column].max(),
        "overall_correlation": pearsonr(df["CS"], df[ucs_column])[0] if len(df) > 1 else np.nan
    }
    
    # 分布詳細
    cs_quartiles = df["CS"].quantile([0.25, 0.5, 0.75])
    ucs_quartiles = df[ucs_column].quantile([0.25, 0.5, 0.75])
    
    stats.update({
        "cs_median": cs_quartiles[0.5],
        "ucs_median": ucs_quartiles[0.5],
        "cs_iqr": cs_quartiles[0.75] - cs_quartiles[0.25],
        "ucs_iqr": ucs_quartiles[0.75] - ucs_quartiles[0.25],
        "cs_skewness": df["CS"].skew(),
        "ucs_skewness": df[ucs_column].skew(),
        "cs_kurtosis": df["CS"].kurtosis(),
        "ucs_kurtosis": df[ucs_column].kurtosis()
    })
    
    # 代表刺激
    representatives = {
        "cs_high": df.loc[df["CS"].idxmax()].to_dict(),
        "cs_low": df.loc[df["CS"].idxmin()].to_dict(),
        "ucs_high": df.loc[df[ucs_column].idxmax()].to_dict(),
        "ucs_low": df.loc[df[ucs_column].idxmin()].to_dict()
    }
    
    return stats, representatives

# ==================== Plus Mode 探索 ====================
def find_divergent_groups_plus(df, ucs_column, group_size=GROUP_SIZE, min_correlation=MIN_CORRELATION):
    """効率的な異なる挙動グループ探索"""
    divergent_groups = []
    total_stimuli = len(df)
    max_combinations = 1000000
    
    print(f"    Plus探索: 刺激数={total_stimuli}, 最大組み合わせ={max_combinations}")
    
    # 方法1: CSソート順の連続区間
    df_cs_sorted = df.sort_values("CS").reset_index(drop=True)
    for start_idx in range(len(df_cs_sorted) - group_size + 1):
        group = df_cs_sorted.iloc[start_idx:start_idx + group_size]
        
        if len(group["CS"].unique()) <= 1 or len(group[ucs_column].unique()) <= 1:
            continue
        
        cs_values = group["CS"].reset_index(drop=True)
        ucs_values = group[ucs_column].reset_index(drop=True)
        
        # パターン判定
        if is_monotonic_increasing(cs_values) and is_monotonic_decreasing(ucs_values):
            corr, p_value = pearsonr(cs_values, ucs_values)
            if corr <= min_correlation:
                divergent_groups.append({
                    "group_type": "CS_increasing_UCS_decreasing",
                    "correlation": corr,
                    "p_value": p_value,
                    "group_data": group.copy(),
                    "cs_range": f"{cs_values.min():.3f} → {cs_values.max():.3f}",
                    "ucs_range": f"{ucs_values.max():.3f} → {ucs_values.min():.3f}",
                    "pattern_strength": abs(corr),
                    "search_method": "cs_sorted_continuous"
                })
    
    # 方法2: UCSソート順の連続区間
    df_ucs_sorted = df.sort_values(ucs_column).reset_index(drop=True)
    for start_idx in range(len(df_ucs_sorted) - group_size + 1):
        group = df_ucs_sorted.iloc[start_idx:start_idx + group_size]
        
        if len(group["CS"].unique()) <= 1 or len(group[ucs_column].unique()) <= 1:
            continue
        
        cs_sorted_group = group.sort_values("CS")
        cs_values = cs_sorted_group["CS"].reset_index(drop=True)
        ucs_values = cs_sorted_group[ucs_column].reset_index(drop=True)
        
        if is_monotonic_decreasing(cs_values) and is_monotonic_increasing(ucs_values):
            corr, p_value = pearsonr(cs_values, ucs_values)
            if corr <= min_correlation:
                divergent_groups.append({
                    "group_type": "CS_decreasing_UCS_increasing",
                    "correlation": corr,
                    "p_value": p_value,
                    "group_data": cs_sorted_group.copy(),
                    "cs_range": f"{cs_values.max():.3f} → {cs_values.min():.3f}",
                    "ucs_range": f"{ucs_values.min():.3f} → {ucs_values.max():.3f}",
                    "pattern_strength": abs(corr),
                    "search_method": "ucs_sorted_continuous"
                })
    
    # 方法3: ランダムサンプリング
    if total_stimuli > group_size:
        sample_size = min(max_combinations // 2, 100000)
        sampled_combinations = set()
        attempts = 0
        max_attempts = sample_size * 3
        
        while len(sampled_combinations) < sample_size and attempts < max_attempts:
            attempts += 1
            indices = random.sample(range(total_stimuli), group_size)
            combo_tuple = tuple(sorted(indices))
            
            if combo_tuple not in sampled_combinations:
                sampled_combinations.add(combo_tuple)
                group = df.iloc[list(indices)]
                
                if len(group["CS"].unique()) <= 1 or len(group[ucs_column].unique()) <= 1:
                    continue
                
                cs_sorted_group = group.sort_values("CS")
                cs_values = cs_sorted_group["CS"].reset_index(drop=True)
                ucs_values = cs_sorted_group[ucs_column].reset_index(drop=True)
                
                # 両パターンをチェック
                if is_monotonic_increasing(cs_values) and is_monotonic_decreasing(ucs_values):
                    corr, p_value = pearsonr(cs_values, ucs_values)
                    if corr <= min_correlation:
                        divergent_groups.append({
                            "group_type": "CS_increasing_UCS_decreasing",
                            "correlation": corr,
                            "p_value": p_value,
                            "group_data": cs_sorted_group.copy(),
                            "cs_range": f"{cs_values.min():.3f} → {cs_values.max():.3f}",
                            "ucs_range": f"{ucs_values.max():.3f} → {ucs_values.min():.3f}",
                            "pattern_strength": abs(corr),
                            "search_method": "random_sampling"
                        })
                
                elif is_monotonic_decreasing(cs_values) and is_monotonic_increasing(ucs_values):
                    corr, p_value = pearsonr(cs_values, ucs_values)
                    if corr <= min_correlation:
                        divergent_groups.append({
                            "group_type": "CS_decreasing_UCS_increasing",
                            "correlation": corr,
                            "p_value": p_value,
                            "group_data": cs_sorted_group.copy(),
                            "cs_range": f"{cs_values.max():.3f} → {cs_values.min():.3f}",
                            "ucs_range": f"{ucs_values.min():.3f} → {ucs_values.max():.3f}",
                            "pattern_strength": abs(corr),
                            "search_method": "random_sampling"
                        })
    
    # 重複除去
    unique_groups = []
    seen_stimuli_sets = set()
    
    for group in divergent_groups:
        stimuli_set = frozenset([
            (row['a'], row['b'], row['c'], row['d']) 
            for _, row in group['group_data'].iterrows()
        ])
        
        if stimuli_set not in seen_stimuli_sets:
            seen_stimuli_sets.add(stimuli_set)
            unique_groups.append(group)
    
    # 強度順ソート
    unique_groups.sort(key=lambda x: x["pattern_strength"], reverse=True)
    
    return unique_groups

# ==================== Systematic Mode 探索 ====================
def generate_systematic_stimuli(target_sum=SYSTEMATIC_TARGET_SUM, min_a=SYSTEMATIC_MIN_A):
    """系統的刺激生成 (a+b+c+d=target_sum, a>=min_a, a+b=c+d)"""
    stimuli = []
    
    for a in range(min_a, target_sum):
        for b in range(1, target_sum - a):
            remainder = target_sum - a - b
            for c in range(1, remainder):
                d = remainder - c
                if d >= 1 and a + b == c + d:
                    stimuli.append((a, b, c, d))
    
    return stimuli

def systematic_group_search(df, ucs_column, group_size=GROUP_SIZE, min_correlation=MIN_CORRELATION):
    """系統的グループ探索"""
    divergent_groups = []
    total_stimuli = len(df)
    
    print(f"    系統的探索: 総刺激数={total_stimuli}")
    
    # 全組み合わせ探索
    for combo in combinations(range(total_stimuli), group_size):
        group = df.iloc[list(combo)]
        
        if len(group["CS"].unique()) <= 1 or len(group[ucs_column].unique()) <= 1:
            continue
        
        cs_sorted_group = group.sort_values("CS")
        cs_values = cs_sorted_group["CS"].reset_index(drop=True)
        ucs_values = cs_sorted_group[ucs_column].reset_index(drop=True)
        
        # CS単調増加 & UCS単調減少
        if is_monotonic_increasing(cs_values) and is_monotonic_decreasing(ucs_values):
            corr, p_value = pearsonr(cs_values, ucs_values)
            if corr <= min_correlation:
                cs_var = cs_values.std()
                ucs_var = ucs_values.std()
                
                divergent_groups.append({
                    "group_type": "CS_increasing_UCS_decreasing",
                    "correlation": corr,
                    "p_value": p_value,
                    "group_data": cs_sorted_group.copy(),
                    "cs_variation": cs_var,
                    "ucs_variation": ucs_var,
                    "pattern_strength": abs(corr),
                    "search_method": "systematic_exhaustive"
                })
        
        # CS単調減少 & UCS単調増加
        elif is_monotonic_decreasing(cs_values) and is_monotonic_increasing(ucs_values):
            corr, p_value = pearsonr(cs_values, ucs_values)
            if corr <= min_correlation:
                cs_var = cs_values.std()
                ucs_var = ucs_values.std()
                
                divergent_groups.append({
                    "group_type": "CS_decreasing_UCS_increasing",
                    "correlation": corr,
                    "p_value": p_value,
                    "group_data": cs_sorted_group.copy(),
                    "cs_variation": cs_var,
                    "ucs_variation": ucs_var,
                    "pattern_strength": abs(corr),
                    "search_method": "systematic_exhaustive"
                })
    
    return sorted(divergent_groups, key=lambda x: x["pattern_strength"], reverse=True)

# ==================== Exhaustive Mode 探索 ====================
def generate_all_valid_stimuli(target_sum=EXHAUSTIVE_TARGET_SUM, min_a=EXHAUSTIVE_MIN_A):
    """全数探索用刺激生成"""
    stimuli = []
    
    for a in range(min_a, target_sum):
        for b in range(1, target_sum - a + 1):
            for c in range(1, target_sum - a - b + 1):
                d = target_sum - a - b - c
                if d >= 1:
                    stimuli.append((a, b, c, d))
    
    return stimuli

def exhaustive_group_search(df, ucs_column, group_size=GROUP_SIZE, min_correlation=MIN_CORRELATION):
    """全数探索によるグループ検索"""
    divergent_groups = []
    total_stimuli = len(df)
    total_combinations = 1
    
    for i in range(group_size):
        total_combinations *= (total_stimuli - i)
        total_combinations //= (i + 1)
    
    print(f"    全数探索: 総刺激数={total_stimuli}, 総組み合わせ数={total_combinations}")
    
    if total_combinations > 10000000:  # 制限
        print(f"    組み合わせ数が多すぎるため、最初の10,000,000組み合わせのみ探索")
        max_combinations = 10000000
    else:
        max_combinations = total_combinations
    
    count = 0
    for combo in combinations(range(total_stimuli), group_size):
        count += 1
        if count > max_combinations:
            break
        
        group = df.iloc[list(combo)]
        
        if len(group["CS"].unique()) <= 1 or len(group[ucs_column].unique()) <= 1:
            continue
        
        cs_sorted_group = group.sort_values("CS")
        cs_values = cs_sorted_group["CS"].reset_index(drop=True)
        ucs_values = cs_sorted_group[ucs_column].reset_index(drop=True)
        
        # パターン判定
        if is_monotonic_increasing(cs_values) and is_monotonic_decreasing(ucs_values):
            corr, p_value = pearsonr(cs_values, ucs_values)
            if corr <= min_correlation:
                divergent_groups.append({
                    "group_type": "CS_increasing_UCS_decreasing",
                    "correlation": corr,
                    "p_value": p_value,
                    "group_data": cs_sorted_group.copy(),
                    "pattern_strength": abs(corr),
                    "search_method": "exhaustive"
                })
        
        elif is_monotonic_decreasing(cs_values) and is_monotonic_increasing(ucs_values):
            corr, p_value = pearsonr(cs_values, ucs_values)
            if corr <= min_correlation:
                divergent_groups.append({
                    "group_type": "CS_decreasing_UCS_increasing",
                    "correlation": corr,
                    "p_value": p_value,
                    "group_data": cs_sorted_group.copy(),
                    "pattern_strength": abs(corr),
                    "search_method": "exhaustive"
                })
    
    return sorted(divergent_groups, key=lambda x: x["pattern_strength"], reverse=True)

# ==================== 統合実行器 ====================
class UnifiedCSUCSAnalyzer:
    def __init__(self, mode="plus"):
        self.mode = mode
        self.results_dir = "./results"
        os.makedirs(self.results_dir, exist_ok=True)
    
    def run_plus_mode(self):
        """Plus Mode実行"""
        print("=== Plus Mode: 効率的探索 ===")
        print(f"サンプルサイズ: {PLUS_SAMPLE_SIZE}")
        
        # 刺激生成
        stimuli = list(random_stimuli(PLUS_SAMPLE_SIZE))
        print(f"有効刺激数: {len(stimuli)}")
        
        if len(stimuli) == 0:
            print("有効な刺激が生成されませんでした")
            return
        
        # スコア計算
        df = compute_all_scores(stimuli)
        
        # 基本統計
        threshold_stats = []
        for ucs_thresh in UCS_THRESHOLDS:
            stats, representatives = analyze_threshold_results(df, ucs_thresh)
            threshold_stats.append(stats)
            print(f"\nUCS閾値 {ucs_thresh}:")
            print(f"  CS: 平均={stats['cs_mean']:.3f}, 標準偏差={stats['cs_std']:.3f}")
            print(f"  UCS: 平均={stats['ucs_mean']:.3f}, 標準偏差={stats['ucs_std']:.3f}")
            print(f"  全体相関: {stats['overall_correlation']:.3f}")
        
        # 異なる挙動グループ探索
        all_results = []
        group_summary = {}
        
        for ucs_thresh in UCS_THRESHOLDS:
            ucs_column = f"UCS_{ucs_thresh}"
            divergent_groups = find_divergent_groups_plus(df, ucs_column)
            group_summary[ucs_thresh] = len(divergent_groups)
            
            if divergent_groups:
                print(f"\nUCS閾値 {ucs_thresh}: {len(divergent_groups)}グループ発見")
                selected_groups = divergent_groups[:TOP_GROUPS]
                
                for idx, group_info in enumerate(selected_groups):
                    group_data = group_info["group_data"]
                    group_id = f"{ucs_thresh}_{idx+1}"
                    
                    for _, row in group_data.iterrows():
                        result_row = {
                            "ucs_threshold": ucs_thresh,
                            "group_id": group_id,
                            "group_type": group_info["group_type"],
                            "correlation": group_info["correlation"],
                            "p_value": group_info["p_value"],
                            "search_method": group_info["search_method"],
                            "a": int(row["a"]),
                            "b": int(row["b"]),
                            "c": int(row["c"]),
                            "d": int(row["d"]),
                            "CS": row["CS"],
                            "UCS": row[ucs_column]
                        }
                        all_results.append(result_row)
        
        # 結果保存
        if all_results:
            results_df = pd.DataFrame(all_results)
            results_df.to_csv(f"{self.results_dir}/plus_mode_results.csv", index=False)
            print(f"\n結果保存: {self.results_dir}/plus_mode_results.csv")
        
        return all_results, threshold_stats
    
    def run_systematic_mode(self):
        """Systematic Mode実行"""
        print("=== Systematic Mode: 系統的探索 ===")
        print(f"制約: a+b+c+d={SYSTEMATIC_TARGET_SUM}, a>={SYSTEMATIC_MIN_A}, a+b=c+d")
        
        # 刺激生成
        start_time = time.time()
        stimuli = generate_systematic_stimuli()
        print(f"生成時間: {time.time() - start_time:.2f}秒")
        print(f"総刺激数: {len(stimuli)}")
        
        # スコア計算
        df = compute_all_scores(stimuli)
        
        # 基本統計
        threshold_stats = []
        for ucs_thresh in UCS_THRESHOLDS:
            stats, _ = analyze_threshold_results(df, ucs_thresh)
            threshold_stats.append(stats)
            print(f"\nUCS閾値 {ucs_thresh}: 相関={stats['overall_correlation']:.3f}")
        
        # グループ探索
        all_results = []
        group_summary = {}
        
        for ucs_thresh in UCS_THRESHOLDS:
            ucs_column = f"UCS_{ucs_thresh}"
            start_time = time.time()
            divergent_groups = systematic_group_search(df, ucs_column)
            search_time = time.time() - start_time
            
            group_summary[ucs_thresh] = len(divergent_groups)
            print(f"\nUCS閾値 {ucs_thresh}: {len(divergent_groups)}グループ発見 ({search_time:.1f}秒)")
            
            if divergent_groups:
                selected_groups = divergent_groups[:TOP_GROUPS]
                for idx, group_info in enumerate(selected_groups):
                    group_data = group_info["group_data"]
                    group_id = f"{ucs_thresh}_{idx+1}"
                    
                    for _, row in group_data.iterrows():
                        result_row = {
                            "ucs_threshold": ucs_thresh,
                            "group_id": group_id,
                            "group_type": group_info["group_type"],
                            "correlation": group_info["correlation"],
                            "p_value": group_info["p_value"],
                            "cs_variation": group_info["cs_variation"],
                            "ucs_variation": group_info["ucs_variation"],
                            "search_method": group_info["search_method"],
                            "a": int(row["a"]),
                            "b": int(row["b"]),
                            "c": int(row["c"]),
                            "d": int(row["d"]),
                            "CS": row["CS"],
                            "UCS": row[ucs_column]
                        }
                        all_results.append(result_row)
        
        # 結果保存
        if all_results:
            results_df = pd.DataFrame(all_results)
            results_df.to_csv(f"{self.results_dir}/systematic_mode_results.csv", index=False)
            print(f"\n結果保存: {self.results_dir}/systematic_mode_results.csv")
        
        return all_results, threshold_stats
    
    def run_exhaustive_mode(self):
        """Exhaustive Mode実行"""
        print("=== Exhaustive Mode: 全数探索 ===")
        print(f"制約: a+b+c+d={EXHAUSTIVE_TARGET_SUM}, a>={EXHAUSTIVE_MIN_A}")
        
        # 刺激生成
        start_time = time.time()
        stimuli = generate_all_valid_stimuli()
        print(f"生成時間: {time.time() - start_time:.2f}秒")
        print(f"総刺激数: {len(stimuli)}")
        
        # スコア計算
        df = compute_all_scores(stimuli)
        
        # 基本統計
        threshold_stats = []
        for ucs_thresh in UCS_THRESHOLDS:
            stats, _ = analyze_threshold_results(df, ucs_thresh)
            threshold_stats.append(stats)
            print(f"\nUCS閾値 {ucs_thresh}: 相関={stats['overall_correlation']:.3f}")
        
        # グループ探索
        all_results = []
        group_summary = {}
        
        for ucs_thresh in UCS_THRESHOLDS:
            ucs_column = f"UCS_{ucs_thresh}"
            start_time = time.time()
            divergent_groups = exhaustive_group_search(df, ucs_column)
            search_time = time.time() - start_time
            
            group_summary[ucs_thresh] = len(divergent_groups)
            print(f"\nUCS閾値 {ucs_thresh}: {len(divergent_groups)}グループ発見 ({search_time:.1f}秒)")
            
            if divergent_groups:
                selected_groups = divergent_groups[:TOP_GROUPS]
                for idx, group_info in enumerate(selected_groups):
                    group_data = group_info["group_data"]
                    group_id = f"{ucs_thresh}_{idx+1}"
                    
                    for _, row in group_data.iterrows():
                        result_row = {
                            "ucs_threshold": ucs_thresh,
                            "group_id": group_id,
                            "group_type": group_info["group_type"],
                            "correlation": group_info["correlation"],
                            "p_value": group_info["p_value"],
                            "search_method": group_info["search_method"],
                            "a": int(row["a"]),
                            "b": int(row["b"]),
                            "c": int(row["c"]),
                            "d": int(row["d"]),
                            "CS": row["CS"],
                            "UCS": row[ucs_column]
                        }
                        all_results.append(result_row)
        
        # 結果保存
        if all_results:
            results_df = pd.DataFrame(all_results)
            results_df.to_csv(f"{self.results_dir}/exhaustive_mode_results.csv", index=False)
            print(f"\n結果保存: {self.results_dir}/exhaustive_mode_results.csv")
        
        return all_results, threshold_stats
    
    def create_visualizations(self, all_results, threshold_stats, mode_name):
        """可視化作成"""
        if not all_results:
            return
        
        n_thresholds = len(UCS_THRESHOLDS)
        fig, axes = plt.subplots(2, n_thresholds, figsize=(6*n_thresholds, 12))
        if n_thresholds == 1:
            axes = axes.reshape(2, 1)
        
        fig.suptitle(f"{mode_name} Mode: CS vs UCS 異なる挙動分析", fontsize=14)
        
        # 閾値別可視化
        results_df = pd.DataFrame(all_results)
        
        for i, ucs_thresh in enumerate(UCS_THRESHOLDS):
            # 全体散布図
            threshold_data = results_df[results_df["ucs_threshold"] == ucs_thresh]
            
            axes[0, i].scatter(threshold_data["CS"], threshold_data["UCS"], 
                             alpha=0.7, s=30, c='red', label="発見グループ")
            axes[0, i].set_xlabel("CS")
            axes[0, i].set_ylabel(f"UCS (threshold={ucs_thresh})")
            axes[0, i].set_title(f"UCS threshold={ucs_thresh}")
            axes[0, i].legend()
            axes[0, i].grid(True, alpha=0.3)
            
            # グループ別詳細
            unique_groups = threshold_data["group_id"].unique()
            colors = plt.cm.Set3(np.linspace(0, 1, len(unique_groups)))
            
            for j, group_id in enumerate(unique_groups[:5]):  # 上位5グループ
                group_data = threshold_data[threshold_data["group_id"] == group_id]
                axes[1, i].scatter(group_data["CS"], group_data["UCS"], 
                                 color=colors[j], s=50, label=f"Group {group_id}")
                
                # 線で接続
                sorted_group = group_data.sort_values("CS")
                axes[1, i].plot(sorted_group["CS"], sorted_group["UCS"], 
                               color=colors[j], alpha=0.7, linewidth=2)
            
            axes[1, i].set_xlabel("CS")
            axes[1, i].set_ylabel(f"UCS (threshold={ucs_thresh})")
            axes[1, i].set_title(f"発見グループ詳細 (threshold={ucs_thresh})")
            axes[1, i].legend()
            axes[1, i].grid(True, alpha=0.3)
        
        plt.tight_layout()
        filename = f"{self.results_dir}/{mode_name.lower()}_mode_visualization.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"可視化保存: {filename}")
    
    def run(self):
        """メイン実行"""
        if self.mode == "plus":
            results, stats = self.run_plus_mode()
            self.create_visualizations(results, stats, "Plus")
        
        elif self.mode == "systematic":
            results, stats = self.run_systematic_mode()
            self.create_visualizations(results, stats, "Systematic")
        
        elif self.mode == "exhaustive":
            results, stats = self.run_exhaustive_mode()
            self.create_visualizations(results, stats, "Exhaustive")
        
        elif self.mode == "all":
            print("=== 全モード実行 ===\n")
            for mode in ["plus", "systematic", "exhaustive"]:
                print(f"\n{'='*20} {mode.upper()} MODE {'='*20}")
                self.mode = mode
                self.run()
        
        else:
            print(f"未知のモード: {self.mode}")

def main():
    parser = argparse.ArgumentParser(description="統合CS/UCS分析")
    parser.add_argument("--mode", choices=["plus", "systematic", "exhaustive", "all"], 
                       default="plus", help="実行モード選択")
    
    args = parser.parse_args()
    
    analyzer = UnifiedCSUCSAnalyzer(mode=args.mode)
    analyzer.run()

if __name__ == "__main__":
    main()
