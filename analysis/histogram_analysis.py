"""
histogram_analysis.py

条件・sample_numberごとの回答値のヒストグラムを描画するコード
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib_fontja
from matplotlib import rcParams

class HistogramAnalyzer:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.df: pd.DataFrame = None
        
    def load_data(self):
        """データを読み込み"""
        self.df = pd.read_csv(self.csv_path)
        print(f"データ読み込み完了: {self.csv_path} (shape={self.df.shape})")
        
    def create_condition_histograms(self):
        """4条件（実験タイプ×否定タイプ）でのsample_numberごとのヒストグラムを作成"""
        self.load_data()
        
        # データ準備
        ex1_first = self.df[self.df["ex1_is_first"] == 1].copy()
        ex2_first = self.df[self.df["ex2_is_first"] == 1].copy()
        
        conditions = [
            ("非対称否定_サマリー", ex1_first[ex1_first["Cond"] == 0], "ex1"),
            ("対称否定_サマリー", ex1_first[ex1_first["Cond"] == 1], "ex1"),
            ("非対称否定_オンライン", ex2_first[ex2_first["Cond"] == 0], "ex2"),
            ("対称否定_オンライン", ex2_first[ex2_first["Cond"] == 1], "ex2"),
        ]
        
        # 各条件に対してヒストグラムを作成
        for condition_name, df_subset, prefix in conditions:
            if df_subset.empty:
                continue
                
            self._plot_condition_histogram(condition_name, df_subset, prefix)
            
    def _plot_condition_histogram(self, condition_name: str, df_subset: pd.DataFrame, prefix: str):
        """個別条件のヒストグラム作成"""
        est_col = f"{prefix}_estimate"
        num_col = f"{prefix}_sample_number"
        
        # sample_numberの範囲を取得
        sample_numbers = sorted(df_subset[num_col].unique())
        
        # 図の設定（2行3列で最大6個のsample_number）
        fig = plt.figure(figsize=(15, 10))
        gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)
        
        fig.suptitle(f'回答値分布: {condition_name}', fontsize=16, fontweight='bold')
        
        # 各sample_numberに対してヒストグラムを作成
        for i, sample_num in enumerate(sample_numbers[:6]):  # 最大6個まで
            row = i // 3
            col = i % 3
            ax = fig.add_subplot(gs[row, col])
            
            # 該当するsample_numberのデータを抽出
            data = df_subset[df_subset[num_col] == sample_num][est_col].dropna()
            
            if len(data) == 0:
                ax.text(0.5, 0.5, 'データなし', ha='center', va='center', 
                       transform=ax.transAxes, fontsize=12)
                ax.set_title(f'Sample {sample_num}')
                continue
            
            # ヒストグラムを描画
            ax.hist(data, bins=20, alpha=0.7, edgecolor='black', color='skyblue')
            
            # 統計情報を計算
            mean_val = data.mean()
            std_val = data.std()
            n_val = len(data)
            
            # タイトルと統計情報を設定
            ax.set_title(f'Sample {sample_num} (n={n_val})')
            ax.set_xlabel('回答値')
            ax.set_ylabel('頻度')
            
            # 統計情報をテキストで表示
            stats_text = f'平均: {mean_val:.2f}\n標準偏差: {std_val:.2f}'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   verticalalignment='top', fontsize=10,
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            # 平均値の縦線を描画
            ax.axvline(mean_val, color='red', linestyle='--', alpha=0.8, 
                      label=f'平均: {mean_val:.2f}')
            ax.legend()
            
            # グリッド表示
            ax.grid(True, alpha=0.3)
        
        # ファイル名を作成して保存
        filename = f"histogram_{condition_name.replace('_', '_')}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"→ ヒストグラム保存: {filename}")
        plt.show()
        
    def create_combined_histogram(self):
        """全条件を一つの図にまとめたヒストグラム"""
        self.load_data()
        
        # データ準備
        ex1_first = self.df[self.df["ex1_is_first"] == 1].copy()
        ex2_first = self.df[self.df["ex2_is_first"] == 1].copy()
        
        conditions = [
            ("非対称否定_サマリー", ex1_first[ex1_first["Cond"] == 0], "ex1", 'blue'),
            ("対称否定_サマリー", ex1_first[ex1_first["Cond"] == 1], "ex1", 'red'),
            ("非対称否定_オンライン", ex2_first[ex2_first["Cond"] == 0], "ex2", 'green'),
            ("対称否定_オンライン", ex2_first[ex2_first["Cond"] == 1], "ex2", 'orange'),
        ]
        
        # sample_numberの範囲を決定（全条件から）
        all_sample_nums = set()
        for _, df_subset, prefix, _ in conditions:
            if not df_subset.empty:
                num_col = f"{prefix}_sample_number"
                all_sample_nums.update(df_subset[num_col].unique())
        
        sample_numbers = sorted(list(all_sample_nums))[:6]  # 最大6個
        
        # 図の設定
        fig = plt.figure(figsize=(18, 12))
        gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.4, wspace=0.3)
        
        fig.suptitle('回答値分布比較（全条件）', fontsize=18, fontweight='bold')
        
        # 各sample_numberに対して4条件のヒストグラムを重ねて表示
        for i, sample_num in enumerate(sample_numbers):
            row = i // 3
            col = i % 3
            ax = fig.add_subplot(gs[row, col])
            
            has_data = False
            legend_handles = []
            
            for condition_name, df_subset, prefix, color in conditions:
                if df_subset.empty:
                    continue
                    
                est_col = f"{prefix}_estimate"
                num_col = f"{prefix}_sample_number"
                
                # 該当するsample_numberのデータを抽出
                data = df_subset[df_subset[num_col] == sample_num][est_col].dropna()
                
                if len(data) > 0:
                    has_data = True
                    # ヒストグラムを描画（透明度を付けて重ねる）
                    n, bins, patches = ax.hist(data, bins=15, alpha=0.6, 
                                              label=f'{condition_name} (n={len(data)})',
                                              color=color, edgecolor='black', linewidth=0.5)
                    
                    # 平均値の縦線を描画
                    mean_val = data.mean()
                    ax.axvline(mean_val, color=color, linestyle='--', alpha=0.8, linewidth=2)
            
            if not has_data:
                ax.text(0.5, 0.5, 'データなし', ha='center', va='center', 
                       transform=ax.transAxes, fontsize=12)
            
            ax.set_title(f'Sample {sample_num}', fontsize=14, fontweight='bold')
            ax.set_xlabel('回答値', fontsize=12)
            ax.set_ylabel('頻度', fontsize=12)
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3)
        
        # ファイル名を作成して保存
        filename = "histogram_combined_all_conditions.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"→ 統合ヒストグラム保存: {filename}")
        plt.show()
        
    def create_summary_statistics_table(self):
        """条件・sample_numberごとの要約統計量テーブルを作成"""
        self.load_data()
        
        # データ準備
        ex1_first = self.df[self.df["ex1_is_first"] == 1].copy()
        ex2_first = self.df[self.df["ex2_is_first"] == 1].copy()
        
        conditions = [
            ("非対称否定_サマリー", ex1_first[ex1_first["Cond"] == 0], "ex1"),
            ("対称否定_サマリー", ex1_first[ex1_first["Cond"] == 1], "ex1"),
            ("非対称否定_オンライン", ex2_first[ex2_first["Cond"] == 0], "ex2"),
            ("対称否定_オンライン", ex2_first[ex2_first["Cond"] == 1], "ex2"),
        ]
        
        summary_data = []
        
        for condition_name, df_subset, prefix in conditions:
            if df_subset.empty:
                continue
                
            est_col = f"{prefix}_estimate"
            num_col = f"{prefix}_sample_number"
            
            # 各sample_numberに対して統計量を計算
            for sample_num in sorted(df_subset[num_col].unique()):
                data = df_subset[df_subset[num_col] == sample_num][est_col].dropna()
                
                if len(data) > 0:
                    summary_row = {
                        '条件': condition_name,
                        'sample_number': sample_num,
                        'n': len(data),
                        '平均': round(data.mean(), 3),
                        '標準偏差': round(data.std(), 3),
                        '最小値': round(data.min(), 3),
                        '25%tile': round(data.quantile(0.25), 3),
                        '中央値': round(data.median(), 3),
                        '75%tile': round(data.quantile(0.75), 3),
                        '最大値': round(data.max(), 3)
                    }
                    summary_data.append(summary_row)
        
        # DataFrameに変換
        summary_df = pd.DataFrame(summary_data)
        
        # CSVファイルに保存
        filename = "histogram_summary_statistics.csv"
        summary_df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"→ 要約統計量テーブル保存: {filename}")
        
        # プレビュー表示
        print(f"\n=== 要約統計量テーブル プレビュー ===")
        print(summary_df.head(20).to_string(index=False))
        
        return summary_df
        
    def create_box_plots(self):
        """条件・sample_numberごとの箱ひげ図を作成"""
        self.load_data()
        
        # データ準備
        ex1_first = self.df[self.df["ex1_is_first"] == 1].copy()
        ex2_first = self.df[self.df["ex2_is_first"] == 1].copy()
        
        conditions = [
            ("非対称否定_サマリー", ex1_first[ex1_first["Cond"] == 0], "ex1"),
            ("対称否定_サマリー", ex1_first[ex1_first["Cond"] == 1], "ex1"),
            ("非対称否定_オンライン", ex2_first[ex2_first["Cond"] == 0], "ex2"),
            ("対称否定_オンライン", ex2_first[ex2_first["Cond"] == 1], "ex2"),
        ]
        
        # 全sample_numberを取得
        all_sample_nums = set()
        for _, df_subset, prefix in conditions:
            if not df_subset.empty:
                num_col = f"{prefix}_sample_number"
                all_sample_nums.update(df_subset[num_col].unique())
        
        sample_numbers = sorted(list(all_sample_nums))
        
        # 図の設定
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('回答値分布の箱ひげ図（条件別）', fontsize=16, fontweight='bold')
        
        axes = axes.flatten()
        
        colors = ['blue', 'red', 'green', 'orange']
        condition_names = [name for name, _, _ in conditions]
        
        for i, sample_num in enumerate(sample_numbers[:6]):
            ax = axes[i]
            
            box_data = []
            labels = []
            
            for j, (condition_name, df_subset, prefix) in enumerate(conditions):
                if df_subset.empty:
                    continue
                    
                est_col = f"{prefix}_estimate"
                num_col = f"{prefix}_sample_number"
                
                data = df_subset[df_subset[num_col] == sample_num][est_col].dropna()
                
                if len(data) > 0:
                    box_data.append(data.values)
                    labels.append(f'{condition_name}\n(n={len(data)})')
                else:
                    box_data.append([])
                    labels.append(f'{condition_name}\n(n=0)')
            
            if box_data and any(len(data) > 0 for data in box_data):
                # 箱ひげ図を描画
                bp = ax.boxplot(box_data, labels=labels, patch_artist=True)
                
                # 色を設定
                for patch, color in zip(bp['boxes'], colors[:len(bp['boxes'])]):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.7)
            
            ax.set_title(f'Sample {sample_num}', fontsize=14, fontweight='bold')
            ax.set_ylabel('回答値', fontsize=12)
            ax.tick_params(axis='x', rotation=45, labelsize=10)
            ax.grid(True, alpha=0.3)
        
        # 使用しないサブプロットを非表示
        for i in range(len(sample_numbers), len(axes)):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        
        # ファイル名を作成して保存
        filename = "boxplot_all_conditions.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"→ 箱ひげ図保存: {filename}")
        plt.show()


if __name__ == "__main__":
    print("=== ヒストグラム分析 ===")
    print("=" * 50)
    
    analyzer = HistogramAnalyzer("final_valid_updated.csv")
    
    # 個別条件のヒストグラム作成
    print("\n1. 条件別ヒストグラム作成中...")
    analyzer.create_condition_histograms()
    
    # 統合ヒストグラム作成
    print("\n2. 統合ヒストグラム作成中...")
    analyzer.create_combined_histogram()
    
    # 要約統計量テーブル作成
    print("\n3. 要約統計量テーブル作成中...")
    summary_stats = analyzer.create_summary_statistics_table()
    
    # 箱ひげ図作成
    print("\n4. 箱ひげ図作成中...")
    analyzer.create_box_plots()
    
    print("\n=== 分析完了 ===")
