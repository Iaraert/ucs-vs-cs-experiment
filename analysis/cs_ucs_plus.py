r"""
cs_ucs_divergent_behavior_search.py

探索目的
------------
CSとUCSが異なる挙動を示す刺激グループを発見する。
具体的には、複数の刺激において：
1. CSが単調増加しながらUCSが単調減少する
2. CSが単調減少しながらUCSが単調増加する
このような相反する傾向を示す刺激セットを探索します。

アルゴリズム
-----------
1. ランダムに刺激を生成し、CS・UCSスコアを計算
2. スコアでソートし、連続する刺激グループを作成
3. 各グループ内でCS・UCSの相関係数を計算
4. 強い負の相関（異なる挙動）を示すグループを抽出

生成物
--------
- `./results/divergent_behavior_results.csv` : 異なる挙動を示す刺激グループ
- `./results/divergent_behavior_plot.png`   : CS vs UCS の傾向可視化
"""

import random
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import pearsonr
from CS_UCS import CS, UCS  # ユーザ提供の CS/UCS 実装を利用

# -------------------- 設定 --------------------
THRESHOLD   = 1.0   # CS/UCS の閾値
IS_GENE     = True  # True: 生成モデル, False: 抑制モデル
LOOPS       = 10000   # Monte‑Carlo 反復回数
MAX_N       = 30    # 総試行数 N 上限
SAMPLE_SIZE = 4000  # ランダムに生成する刺激数
GROUP_SIZE  = 5     # 分析する刺激グループのサイズ
MIN_CORRELATION = -0.8  # CS-UCS間の最小相関係数（負の値）
TOP_GROUPS  = 3     # 抽出する上位グループ数
# ----------------------------------------------

def random_stimuli(num_samples: int):
    """(a,b,c,d) のランダム列挙。N<=MAX_N かつ a>=6 かつ a+b==c+d を満たす."""
    count = 0
    while count < num_samples:
        N = random.randint(1, MAX_N)
        if N < 3:
            continue  # Nが3未満だと3点分割できないのでスキップ
        # 0~N の中から 3 点を切り分けて単純形分割
        cuts = sorted(random.sample(range(N + 1), 3))
        a = cuts[0]
        b = cuts[1] - cuts[0]
        c = cuts[2] - cuts[1]
        d = N - cuts[2]
        if a < 6:
            continue  # aが6未満ならスキップ
        if (a + b) != (c + d):
            continue  # a+bとc+dが一致しなければスキップ
        yield (a, b, c, d)
        count += 1

def compute_scores(stimuli):
    """CS, UCS を DataFrame で返す。"""
    records = []
    for a, b, c, d in stimuli:
        cs_val  = CS((a, b, c, d), threshold=THRESHOLD, is_gene=IS_GENE, loops=LOOPS)
        ucs_val = UCS((a, b, c, d), threshold=THRESHOLD, is_gene=IS_GENE, loops=LOOPS)
        records.append({
            "a": a, "b": b, "c": c, "d": d,
            "CS": cs_val, "UCS": ucs_val,
        })
    return pd.DataFrame.from_records(records)

def find_divergent_groups(df, group_size=GROUP_SIZE, min_correlation=MIN_CORRELATION):
    """CS と UCS が異なる挙動を示すグループを探索。"""
    
    # CSでソートして連続グループを作成
    df_cs_sorted = df.sort_values("CS").reset_index(drop=True)
    
    # UCSでソートして連続グループを作成  
    df_ucs_sorted = df.sort_values("UCS").reset_index(drop=True)
    
    divergent_groups = []
    
    # CSソート基準でのグループ分析
    for i in range(len(df_cs_sorted) - group_size + 1):
        group = df_cs_sorted.iloc[i:i+group_size]
        if len(group["CS"].unique()) > 1 and len(group["UCS"].unique()) > 1:  # 値に変動がある場合のみ
            corr, p_value = pearsonr(group["CS"], group["UCS"])
            if corr <= min_correlation and p_value < 0.05:  # 強い負の相関
                divergent_groups.append({
                    "group_type": "CS_sorted",
                    "start_index": i,
                    "correlation": corr,
                    "p_value": p_value,
                    "group_data": group.copy()
                })
    
    # UCSソート基準でのグループ分析
    for i in range(len(df_ucs_sorted) - group_size + 1):
        group = df_ucs_sorted.iloc[i:i+group_size]
        if len(group["CS"].unique()) > 1 and len(group["UCS"].unique()) > 1:  # 値に変動がある場合のみ
            corr, p_value = pearsonr(group["CS"], group["UCS"])
            if corr <= min_correlation and p_value < 0.05:  # 強い負の相関
                divergent_groups.append({
                    "group_type": "UCS_sorted", 
                    "start_index": i,
                    "correlation": corr,
                    "p_value": p_value,
                    "group_data": group.copy()
                })
    
    # 相関係数の絶対値でソート（より強い負の相関を上位に）
    divergent_groups.sort(key=lambda x: x["correlation"])
    
    return divergent_groups

def main():
    print("=== CS と UCS の異なる挙動を示す刺激グループの探索 ===")
    print(f"設定: THRESHOLD={THRESHOLD}, IS_GENE={IS_GENE}, SAMPLE_SIZE={SAMPLE_SIZE}")
    print(f"グループサイズ: {GROUP_SIZE}, 最小相関係数: {MIN_CORRELATION}")
    
    # 1. 刺激をサンプリングしてスコア計算
    print("刺激をサンプリング中...")
    stimuli = list(random_stimuli(SAMPLE_SIZE))
    print(f"有効な刺激数: {len(stimuli)}")
    
    print("CS・UCSスコアを計算中...")
    df = compute_scores(stimuli)
    
    # 2. 異なる挙動を示すグループを探索
    print("異なる挙動を示すグループを探索中...")
    divergent_groups = find_divergent_groups(df)
    
    if not divergent_groups:
        print("異なる挙動を示すグループが見つかりませんでした。")
        print("MIN_CORRELATION を緩和するか、SAMPLE_SIZE を増やしてください。")
        return
        
    print(f"発見されたグループ数: {len(divergent_groups)}")
    
    # 3. 上位グループの結果をCSV出力
    results_data = []
    selected_groups = divergent_groups[:TOP_GROUPS]
    
    for idx, group_info in enumerate(selected_groups):
        group_data = group_info["group_data"]
        for _, row in group_data.iterrows():
            results_data.append({
                "group_id": idx + 1,
                "group_type": group_info["group_type"],
                "correlation": group_info["correlation"],
                "p_value": group_info["p_value"],
                "a": row["a"], "b": row["b"], "c": row["c"], "d": row["d"],
                "CS": row["CS"], "UCS": row["UCS"]
            })
    
    results_df = pd.DataFrame(results_data)
    csv_path = "./results/divergent_behavior_results.csv"
    results_df.to_csv(csv_path, index=False)
    
    # 4. 可視化
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle(f"CS vs UCS 異なる挙動分析 (threshold={THRESHOLD}, is_gene={IS_GENE})", fontsize=14)
    
    # 全体散布図
    axes[0, 0].scatter(df["CS"], df["UCS"], alpha=0.3, s=8, marker=".", label="全刺激")
    axes[0, 0].set_xlabel("CS")
    axes[0, 0].set_ylabel("UCS")
    axes[0, 0].set_title("全刺激の分布")
    axes[0, 0].legend()
    
    # 選択されたグループの散布図
    colors = ['red', 'blue', 'green']
    for idx, group_info in enumerate(selected_groups):
        if idx >= len(colors):
            break
        group_data = group_info["group_data"]
        axes[0, 1].scatter(group_data["CS"], group_data["UCS"], 
                          color=colors[idx], s=50, marker="o", 
                          label=f"Group {idx+1} (r={group_info['correlation']:.3f})")
    axes[0, 1].set_xlabel("CS")
    axes[0, 1].set_ylabel("UCS")
    axes[0, 1].set_title("選択されたグループ")
    axes[0, 1].legend()
    
    # 上位2グループの詳細プロット
    for plot_idx, group_idx in enumerate([0, 1]):
        if group_idx < len(selected_groups):
            ax = axes[1, plot_idx]
            group_info = selected_groups[group_idx]
            group_data = group_info["group_data"]
            
            # CSとUCSの値順序を表示
            stimulus_order = range(len(group_data))
            ax.plot(stimulus_order, group_data["CS"], 'o-', color='red', label='CS', linewidth=2, markersize=8)
            ax.plot(stimulus_order, group_data["UCS"], 's-', color='blue', label='UCS', linewidth=2, markersize=8)
            ax.set_xlabel("刺激順序")
            ax.set_ylabel("スコア")
            ax.set_title(f"Group {group_idx+1} - 相関係数: {group_info['correlation']:.3f}")
            ax.legend()
            ax.grid(True, alpha=0.3)
        else:
            axes[1, plot_idx].axis('off')
    
    plt.tight_layout()
    png_path = "./results/divergent_behavior_plot.png"
    plt.savefig(png_path, dpi=200, bbox_inches='tight')
    plt.close()
    
    # 5. 結果サマリー表示
    print("\n=== 結果サマリー ===")
    for idx, group_info in enumerate(selected_groups):
        print(f"\nGroup {idx+1} ({group_info['group_type']}):")
        print(f"  相関係数: {group_info['correlation']:.4f} (p={group_info['p_value']:.4f})")
        group_data = group_info["group_data"] 
        print(f"  CS範囲: {group_data['CS'].min():.3f} - {group_data['CS'].max():.3f}")
        print(f"  UCS範囲: {group_data['UCS'].min():.3f} - {group_data['UCS'].max():.3f}")
        print("  刺激:")
        for _, row in group_data.iterrows():
            print(f"    ({int(row['a'])}, {int(row['b'])}, {int(row['c'])}, {int(row['d'])}) -> CS:{row['CS']:.3f}, UCS:{row['UCS']:.3f}")
    
    print(f"\nファイル出力:")
    print(f"  {csv_path}")
    print(f"  {png_path}")

if __name__ == "__main__":
    main()