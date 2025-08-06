r"""
stimulus_pair_divergence_analysis_improved.py

探索目的
------------
2つの刺激間でCSとUCSが逆の挙動を示すペアを発見する。
具体的には：
1. 刺激Aから刺激Bへの変化で、CSが+閾値以上増加
2. 同時に、UCSが-閾値以上減少
3. またはその逆パターン（CS減少、UCS増加）

改善点
------
- より現実的な閾値設定
- 刺激生成制約の緩和
- 詳細な統計情報の表示
- 発見されたペアの詳細なCSV出力

生成物
--------
- `./results/stimulus_pair_divergence_results.csv` : 異なる挙動を示す刺激ペア
- `./results/stimulus_pair_divergence_plot.png`   : 変化量の可視化
"""

import random
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from CS_UCS import CS, UCS  # ユーザ提供の CS/UCS 実装を利用
import os
import matplotlib
matplotlib.rcParams['font.family'] = ['DejaVu Sans', 'Yu Gothic', 'Hiragino Sans', 'Takao', 'Noto Sans CJK JP']

# -------------------- 設定 --------------------
THRESHOLD   = 1.0   # CS/UCS の閾値
IS_GENE     = True  # True: 生成モデル, False: 抑制モデル
LOOPS       = 10000   # Monte‑Carlo 反復回数
MAX_N       = 100    # 総試行数 N 上限
SAMPLE_SIZE = 2000  # ランダムに生成する刺激数
MIN_DIFF_THRESHOLD = 5.0  # CS・UCSの最小変化量（より現実的な値に調整）
TOP_PAIRS   = 10    # 抽出する上位ペア数
# ----------------------------------------------

def random_stimuli(num_samples: int):
    """(a,b,c,d) のランダム列挙。制約を緩和してより多様な刺激を生成。"""
    count = 0
    while count < num_samples:
        N = random.randint(3, MAX_N)
        if N < 3:
            continue  # Nが3未満だと3点分割できないのでスキップ
        # 0~N の中から 3 点を切り分けて単純形分割
        cuts = sorted(random.sample(range(N + 1), 3))
        a = cuts[0]
        b = cuts[1] - cuts[0]
        c = cuts[2] - cuts[1]
        d = N - cuts[2]
        # 制約を緩和：aが0以上であれば許可
        if a < 0:
            continue
        yield (a, b, c, d)
        count += 1

def compute_scores(stimuli):
    """CS, UCS を DataFrame で返す。"""
    records = []
    print("スコア計算中...")
    for idx, (a, b, c, d) in enumerate(stimuli):
        if (idx + 1) % 500 == 0:
            print(f"進捗: {idx + 1}/{len(stimuli)}")
        
        cs_val  = CS((a, b, c, d), threshold=THRESHOLD, is_gene=IS_GENE, loops=LOOPS)
        ucs_val = UCS((a, b, c, d), threshold=THRESHOLD, is_gene=IS_GENE, loops=LOOPS)
        records.append({
            "stimulus_id": idx,
            "a": a, "b": b, "c": c, "d": d,
            "CS": cs_val, "UCS": ucs_val,
        })
    return pd.DataFrame.from_records(records)

def find_divergent_pairs(df, min_diff=MIN_DIFF_THRESHOLD):
    """CSとUCSが逆の挙動を示す刺激ペアを探索。"""
    
    divergent_pairs = []
    n_stimuli = len(df)
    
    print(f"刺激ペアの組み合わせを分析中... ({n_stimuli} choose 2 = {n_stimuli*(n_stimuli-1)//2} ペア)")
    
    # 全ペアの組み合わせを検証
    for i in range(n_stimuli):
        if i % 200 == 0:
            print(f"進捗: {i}/{n_stimuli}")
            
        for j in range(i + 1, n_stimuli):
            stimulus_1 = df.iloc[i]
            stimulus_2 = df.iloc[j]
            
            cs_diff = stimulus_2["CS"] - stimulus_1["CS"]
            ucs_diff = stimulus_2["UCS"] - stimulus_1["UCS"]
            
            # パターン1: CSが増加(+閾値以上)、UCSが減少(-閾値以下)
            if cs_diff >= min_diff and ucs_diff <= -min_diff:
                divergent_pairs.append({
                    "pair_type": "CS_increase_UCS_decrease",
                    "stimulus_1_id": stimulus_1["stimulus_id"],
                    "stimulus_2_id": stimulus_2["stimulus_id"],
                    "stimulus_1": f"({int(stimulus_1['a'])},{int(stimulus_1['b'])},{int(stimulus_1['c'])},{int(stimulus_1['d'])})",
                    "stimulus_2": f"({int(stimulus_2['a'])},{int(stimulus_2['b'])},{int(stimulus_2['c'])},{int(stimulus_2['d'])})",
                    "a1": stimulus_1["a"], "b1": stimulus_1["b"], "c1": stimulus_1["c"], "d1": stimulus_1["d"],
                    "a2": stimulus_2["a"], "b2": stimulus_2["b"], "c2": stimulus_2["c"], "d2": stimulus_2["d"],
                    "cs_1": stimulus_1["CS"],
                    "cs_2": stimulus_2["CS"],
                    "ucs_1": stimulus_1["UCS"],
                    "ucs_2": stimulus_2["UCS"],
                    "cs_diff": cs_diff,
                    "ucs_diff": ucs_diff,
                    "total_divergence": abs(cs_diff) + abs(ucs_diff)
                })
            
            # パターン2: CSが減少(-閾値以下)、UCSが増加(+閾値以上)
            elif cs_diff <= -min_diff and ucs_diff >= min_diff:
                divergent_pairs.append({
                    "pair_type": "CS_decrease_UCS_increase",
                    "stimulus_1_id": stimulus_1["stimulus_id"],
                    "stimulus_2_id": stimulus_2["stimulus_id"],
                    "stimulus_1": f"({int(stimulus_1['a'])},{int(stimulus_1['b'])},{int(stimulus_1['c'])},{int(stimulus_1['d'])})",
                    "stimulus_2": f"({int(stimulus_2['a'])},{int(stimulus_2['b'])},{int(stimulus_2['c'])},{int(stimulus_2['d'])})",
                    "a1": stimulus_1["a"], "b1": stimulus_1["b"], "c1": stimulus_1["c"], "d1": stimulus_1["d"],
                    "a2": stimulus_2["a"], "b2": stimulus_2["b"], "c2": stimulus_2["c"], "d2": stimulus_2["d"],
                    "cs_1": stimulus_1["CS"],
                    "cs_2": stimulus_2["CS"],
                    "ucs_1": stimulus_1["UCS"],
                    "ucs_2": stimulus_2["UCS"],
                    "cs_diff": cs_diff,
                    "ucs_diff": ucs_diff,
                    "total_divergence": abs(cs_diff) + abs(ucs_diff)
                })
    
    # 総発散量でソート（より大きな差を示すペアを上位に）
    divergent_pairs.sort(key=lambda x: x["total_divergence"], reverse=True)
    
    return divergent_pairs

def main():
    print("=== CSとUCSが逆挙動を示す刺激ペアの探索（改良版） ===")
    print(f"設定: THRESHOLD={THRESHOLD}, IS_GENE={IS_GENE}, SAMPLE_SIZE={SAMPLE_SIZE}")
    print(f"最小変化量: ±{MIN_DIFF_THRESHOLD}, LOOPS={LOOPS}")
    
    # results ディレクトリが存在しない場合は作成
    os.makedirs("./results", exist_ok=True)
    
    # 1. 刺激をサンプリングしてスコア計算
    print("\n刺激をサンプリング中...")
    stimuli = list(random_stimuli(SAMPLE_SIZE))
    print(f"有効な刺激数: {len(stimuli)}")
    
    print("\nCS・UCSスコアを計算中...")
    df = compute_scores(stimuli)
    
    print(f"\nCS範囲: {df['CS'].min():.3f} - {df['CS'].max():.3f}")
    print(f"UCS範囲: {df['UCS'].min():.3f} - {df['UCS'].max():.3f}")
    print(f"CS平均: {df['CS'].mean():.3f} ± {df['CS'].std():.3f}")
    print(f"UCS平均: {df['UCS'].mean():.3f} ± {df['UCS'].std():.3f}")
    
    # 2. 逆挙動を示すペアを探索
    print("\n逆挙動を示すペアを探索中...")
    divergent_pairs = find_divergent_pairs(df)
    
    if not divergent_pairs:
        print("逆挙動を示すペアが見つかりませんでした。")
        print("MIN_DIFF_THRESHOLD を緩和するか、SAMPLE_SIZE を増やしてください。")
        
        # 現在の設定での最大変化量を確認
        all_cs_diffs = []
        all_ucs_diffs = []
        for i in range(len(df)):
            for j in range(i + 1, len(df)):
                cs_diff = df.iloc[j]["CS"] - df.iloc[i]["CS"]
                ucs_diff = df.iloc[j]["UCS"] - df.iloc[i]["UCS"]
                all_cs_diffs.append(abs(cs_diff))
                all_ucs_diffs.append(abs(ucs_diff))
        
        print(f"最大CS変化量: {max(all_cs_diffs):.3f}")
        print(f"最大UCS変化量: {max(all_ucs_diffs):.3f}")
        print(f"推奨閾値: {min(max(all_cs_diffs), max(all_ucs_diffs)) * 0.5:.3f}")
        return
        
    print(f"発見されたペア数: {len(divergent_pairs)}")
    
    # パターン別の統計
    cs_increase_pairs = [p for p in divergent_pairs if p["pair_type"] == "CS_increase_UCS_decrease"]
    cs_decrease_pairs = [p for p in divergent_pairs if p["pair_type"] == "CS_decrease_UCS_increase"]
    
    print(f"CS増加・UCS減少パターン: {len(cs_increase_pairs)}ペア")
    print(f"CS減少・UCS増加パターン: {len(cs_decrease_pairs)}ペア")
    
    # 3. 上位ペアの結果をCSV出力
    selected_pairs = divergent_pairs[:TOP_PAIRS]
    results_df = pd.DataFrame(selected_pairs)
    
    csv_path = "./results/stimulus_pair_divergence_results.csv"
    results_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    # 4. 可視化
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f"刺激ペア間のCS・UCS逆挙動分析 (threshold={THRESHOLD}, is_gene={IS_GENE})", fontsize=14)
    
    # 全体のCS vs UCS分布
    axes[0, 0].scatter(df["CS"], df["UCS"], alpha=0.4, s=12, marker=".", c='gray', label="全刺激")
    if selected_pairs:
        # 選択されたペアの刺激をハイライト
        for pair in selected_pairs[:5]:
            color = 'red' if pair["pair_type"] == "CS_increase_UCS_decrease" else 'blue'
            axes[0, 0].scatter([pair["cs_1"], pair["cs_2"]], [pair["ucs_1"], pair["ucs_2"]], 
                             c=color, s=50, alpha=0.8, edgecolors='black')
    axes[0, 0].set_xlabel("CS")
    axes[0, 0].set_ylabel("UCS")
    axes[0, 0].set_title("全刺激の分布（上位5ペアをハイライト）")
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # 選択されたペアの変化ベクトル
    if selected_pairs:
        for idx, pair in enumerate(selected_pairs[:5]):  # 上位5ペアのみ表示
            color = 'red' if pair["pair_type"] == "CS_increase_UCS_decrease" else 'blue'
            axes[0, 1].arrow(pair["cs_1"], pair["ucs_1"], 
                           pair["cs_diff"], pair["ucs_diff"],
                           head_width=0.02, head_length=0.01, fc=color, ec=color, alpha=0.7,
                           length_includes_head=True)
            axes[0, 1].scatter([pair["cs_1"], pair["cs_2"]], [pair["ucs_1"], pair["ucs_2"]], 
                             c=color, s=50, alpha=0.8, edgecolors='black')
    
    axes[0, 1].set_xlabel("CS")
    axes[0, 1].set_ylabel("UCS")
    axes[0, 1].set_title("上位5ペアの変化ベクトル")
    axes[0, 1].grid(True, alpha=0.3)
    
    # CS変化量 vs UCS変化量
    if divergent_pairs:
        cs_diffs = [p["cs_diff"] for p in divergent_pairs]
        ucs_diffs = [p["ucs_diff"] for p in divergent_pairs]
        colors = ['red' if p["pair_type"] == "CS_increase_UCS_decrease" else 'blue' 
                 for p in divergent_pairs]
        
        axes[1, 0].scatter(cs_diffs, ucs_diffs, c=colors, alpha=0.6, s=30)
        axes[1, 0].axhline(y=0, color='black', linestyle='--', alpha=0.5)
        axes[1, 0].axvline(x=0, color='black', linestyle='--', alpha=0.5)
        axes[1, 0].axhline(y=-MIN_DIFF_THRESHOLD, color='red', linestyle=':', alpha=0.7, 
                          label=f'閾値 (±{MIN_DIFF_THRESHOLD})')
        axes[1, 0].axhline(y=MIN_DIFF_THRESHOLD, color='red', linestyle=':', alpha=0.7)
        axes[1, 0].axvline(x=-MIN_DIFF_THRESHOLD, color='red', linestyle=':', alpha=0.7)
        axes[1, 0].axvline(x=MIN_DIFF_THRESHOLD, color='red', linestyle=':', alpha=0.7)
        axes[1, 0].set_xlabel("CS変化量")
        axes[1, 0].set_ylabel("UCS変化量")
        axes[1, 0].set_title("変化量の分布")
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
    
    # 総発散量のヒストグラム
    if divergent_pairs:
        total_divergences = [p["total_divergence"] for p in divergent_pairs]
        axes[1, 1].hist(total_divergences, bins=20, alpha=0.7, color='green', edgecolor='black')
        axes[1, 1].axvline(x=2*MIN_DIFF_THRESHOLD, color='red', linestyle='--', alpha=0.7, 
                          label=f'最小閾値 ({2*MIN_DIFF_THRESHOLD})')
        axes[1, 1].set_xlabel("総発散量 (|CS変化| + |UCS変化|)")
        axes[1, 1].set_ylabel("頻度")
        axes[1, 1].set_title("総発散量の分布")
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    png_path = "./results/stimulus_pair_divergence_plot.png"
    plt.savefig(png_path, dpi=200, bbox_inches='tight')
    plt.close()
    
    # 5. 結果サマリー表示
    print(f"\n=== 上位{TOP_PAIRS}ペアの詳細 ===")
    
    for idx, pair in enumerate(selected_pairs):
        print(f"\nペア {idx+1} ({pair['pair_type']}):")
        print(f"  刺激1: {pair['stimulus_1']} -> CS: {pair['cs_1']:.4f}, UCS: {pair['ucs_1']:.4f}")
        print(f"  刺激2: {pair['stimulus_2']} -> CS: {pair['cs_2']:.4f}, UCS: {pair['ucs_2']:.4f}")
        print(f"  変化量: CS: {pair['cs_diff']:+.4f}, UCS: {pair['ucs_diff']:+.4f}")
        print(f"  総発散量: {pair['total_divergence']:.4f}")
    
    print(f"\n=== ファイル出力 ===")
    print(f"CSV: {csv_path}")
    print(f"図 : {png_path}")
    
    # 6. 統計サマリー
    if divergent_pairs:
        cs_diffs = [p["cs_diff"] for p in divergent_pairs]
        ucs_diffs = [p["ucs_diff"] for p in divergent_pairs]
        total_divergences = [p["total_divergence"] for p in divergent_pairs]
        
        print(f"\n=== 統計サマリー ===")
        print(f"CS変化量: 平均={np.mean(cs_diffs):.4f}, 標準偏差={np.std(cs_diffs):.4f}")
        print(f"UCS変化量: 平均={np.mean(ucs_diffs):.4f}, 標準偏差={np.std(ucs_diffs):.4f}")
        print(f"総発散量: 平均={np.mean(total_divergences):.4f}, 最大={np.max(total_divergences):.4f}")

if __name__ == "__main__":
    main()
