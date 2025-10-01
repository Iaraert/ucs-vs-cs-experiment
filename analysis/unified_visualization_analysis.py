"""
unified_visualization_analysis.py

視覚化・統計分析統合版
- ヒストグラム分析（histogram_analysis.py, histogram_analysis_fixed.py）
- 平均値分析（overall_average_analysis.py）
- 平均値関連分析（ave.py, ave_no_first.py, average_answer.py）

統合機能:
1. 条件別ヒストグラム作成（固定軸・可変軸）
2. 全体平均値クラスタリング分析
3. 要約統計量テーブル作成
4. 箱ひげ図作成
5. モデル指標計算・相関分析
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from scipy.stats import pearsonr
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定
import japanize_matplotlib
import matplotlib
matplotlib.rcParams['font.family'] = ['DejaVu Sans', 'Hiragino Sans', 'Yu Gothic', 'Meiryo', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']
matplotlib.rcParams['axes.unicode_minus'] = False


class UnifiedVisualizationAnalyzer:
    """統合視覚化・統計分析クラス"""
    
    def __init__(self, csv_path: str, max_k: int = 5):
        self.csv_path = csv_path
        self.max_k = max_k
        self.df = None
        self.results = {}
        
    def load_data(self):
        """データ読み込み"""
        self.df = pd.read_csv(self.csv_path)
        print(f"データ読み込み完了: {self.csv_path} (shape={self.df.shape})")
        
        # 平均estimate値を計算
        self.df['avg_estimate'] = (self.df['ex1_estimate'] + self.df['ex2_estimate']) / 2
        self.df['sample_number'] = self.df['ex1_sample_number']
        
        print(f"平均estimate値を計算しました")
        print(f"Sample number範囲: {self.df['sample_number'].min()} - {self.df['sample_number'].max()}")
        print(f"ユニークなsample_number: {sorted(self.df['sample_number'].unique())}")
        
        return self.df
        
    def find_optimal_k(self, X: np.ndarray, k_min: int = 2, k_max: int = None) -> int:
        """Silhouette scoreに基づいて最適k値を決定"""
        if k_max is None:
            k_max = self.max_k
        k_max = min(k_max, X.shape[0] - 1)
        
        best_k, best_score = k_min, -np.inf
        for k in range(k_min, k_max + 1):
            labels = KMeans(n_clusters=k, random_state=0).fit_predict(X)
            score = silhouette_score(X, labels)
            print(f"    → k={k}, silhouette={score:.3f}")
            if score > best_score:
                best_k, best_score = k, score
        print(f"  ★ Best k = {best_k} (silhouette={best_score:.3f})\n")
        return best_k
        
    def plot_table(self, df: pd.DataFrame, title: str, fname: str):
        """DataFrameを表画像として保存"""
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.axis("off")
        tbl = ax.table(cellText=df.values,
                       rowLabels=df.index,
                       colLabels=df.columns,
                       cellLoc="center", loc="center")
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(10)
        tbl.scale(1.2, 1.5)
        plt.title(title, pad=20, fontsize=12)
        plt.tight_layout()
        plt.savefig(fname, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"→ 保存: {fname}")
        
    def create_condition_histograms(self, fixed_axis: bool = True):
        """条件別ヒストグラム作成"""
        print("\n" + "="*80)
        print("条件別ヒストグラム分析")
        print("="*80)
        
        if self.df is None:
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
        
        for condition_name, df_subset, prefix in conditions:
            if df_subset.empty:
                print(f"{condition_name}: データが空です → スキップ")
                continue
                
            self._plot_condition_histogram(condition_name, df_subset, prefix, fixed_axis)
            
    def _plot_condition_histogram(self, condition_name: str, df_subset: pd.DataFrame, 
                                 prefix: str, fixed_axis: bool = True):
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
                if fixed_axis:
                    ax.set_xlim(-100, 100)
                continue
                
            # ヒストグラム描画
            hist_range = (-100, 100) if fixed_axis else None
            ax.hist(data, bins=20, alpha=0.7, edgecolor='black', color='skyblue', range=hist_range)
            
            # 軸設定
            if fixed_axis:
                ax.set_xlim(-100, 100)
            
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
            if not fixed_axis or (-100 <= mean_val <= 100):
                ax.axvline(mean_val, color='red', linestyle='--', alpha=0.8, 
                          label=f'平均: {mean_val:.2f}')
                ax.legend()
            
            # グリッド表示
            ax.grid(True, alpha=0.3)
        
        # ファイル名を作成して保存
        axis_suffix = "_fixed" if fixed_axis else ""
        filename = f"histogram_{condition_name}{axis_suffix}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"→ ヒストグラム保存: {filename}")
        plt.close(fig)
        
    def create_combined_histogram(self, fixed_axis: bool = True):
        """全条件統合ヒストグラム作成"""
        print("\n" + "="*80)
        print("統合ヒストグラム分析")
        print("="*80)
        
        if self.df is None:
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
        
        # sample_numberの範囲を決定
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
                    hist_range = (-100, 100) if fixed_axis else None
                    n, bins, patches = ax.hist(data, bins=15, alpha=0.6, 
                                              label=f'{condition_name} (n={len(data)})',
                                              color=color, edgecolor='black', linewidth=0.5,
                                              range=hist_range)
                    
                    # 平均値の縦線を描画
                    mean_val = data.mean()
                    if not fixed_axis or (-100 <= mean_val <= 100):
                        ax.axvline(mean_val, color=color, linestyle='--', alpha=0.8, linewidth=2)
            
            # 軸設定
            if fixed_axis:
                ax.set_xlim(-100, 100)
            
            if not has_data:
                ax.text(0.5, 0.5, 'データなし', ha='center', va='center', 
                       transform=ax.transAxes, fontsize=12)
            
            ax.set_title(f'Sample {sample_num}', fontsize=14, fontweight='bold')
            ax.set_xlabel('回答値', fontsize=12)
            ax.set_ylabel('頻度', fontsize=12)
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3)
        
        # ファイル名を作成して保存
        axis_suffix = "_fixed" if fixed_axis else ""
        filename = f"histogram_combined_all_conditions{axis_suffix}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"→ 統合ヒストグラム保存: {filename}")
        plt.close(fig)
        
    def create_summary_statistics_table(self):
        """要約統計量テーブル作成"""
        print("\n" + "="*80)
        print("要約統計量テーブル作成")
        print("="*80)
        
        if self.df is None:
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
        
        self.results['summary_statistics'] = summary_df
        return summary_df
        
    def create_box_plots(self):
        """箱ひげ図作成"""
        print("\n" + "="*80)
        print("箱ひげ図作成")
        print("="*80)
        
        if self.df is None:
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
        
        # sample_numberの範囲を決定
        all_sample_nums = set()
        for _, df_subset, prefix in conditions:
            if not df_subset.empty:
                num_col = f"{prefix}_sample_number"
                all_sample_nums.update(df_subset[num_col].unique())
        
        sample_numbers = sorted(list(all_sample_nums))[:6]  # 最大6個
        
        # 図の設定
        fig = plt.figure(figsize=(18, 12))
        gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.4, wspace=0.3)
        
        fig.suptitle('回答値分布（箱ひげ図）', fontsize=18, fontweight='bold')
        
        for i, sample_num in enumerate(sample_numbers):
            row = i // 3
            col = i % 3
            ax = fig.add_subplot(gs[row, col])
            
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
                
                # 箱の色設定
                colors = ['lightblue', 'lightcoral', 'lightgreen', 'lightsalmon']
                for patch, color in zip(bp['boxes'], colors):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.7)
            else:
                ax.text(0.5, 0.5, 'データなし', ha='center', va='center', 
                       transform=ax.transAxes, fontsize=12)
            
            ax.set_title(f'Sample {sample_num}', fontsize=14, fontweight='bold')
            ax.set_ylabel('回答値', fontsize=12)
            ax.tick_params(axis='x', rotation=45)
            ax.grid(True, alpha=0.3)
        
        filename = "boxplot_all_conditions.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"→ 箱ひげ図保存: {filename}")
        plt.close(fig)
        
    def overall_average_analysis(self):
        """全体平均値分析"""
        print("\n" + "="*80)
        print("全体平均値分析")
        print("="*80)
        
        if self.df is None:
            self.load_data()
            
        # ピボットテーブル作成
        pivot_df = self.df.pivot(index='user_id', columns='sample_number', values='avg_estimate')
        pivot_df = pivot_df.dropna()
        
        print(f"ピボットテーブル作成完了: {pivot_df.shape}")
        print(f"使用するsample_number: {list(pivot_df.columns)}")
        
        # クラスタリング実行
        print(f"\n=== クラスタリング分析 ===")
        k = self.find_optimal_k(pivot_df.values, k_max=self.max_k)
        
        kmeans = KMeans(n_clusters=k, random_state=0)
        labels = kmeans.fit_predict(pivot_df.values)
        pivot_df['cluster'] = labels
        
        # クラスタサイズの表示
        cluster_counts = pivot_df['cluster'].value_counts().sort_index()
        print("クラスタサイズ:")
        for cluster_id, count in cluster_counts.items():
            print(f"  Cluster {cluster_id + 1}: {count}人")
            
        # 平均値テーブル作成
        sample_columns = [col for col in pivot_df.columns if col != 'cluster']
        avg_table = pd.DataFrame(
            index=sample_columns,
            columns=['All'] + [f'Cluster {i+1}' for i in range(k)]
        )
        avg_table.index.name = 'Sample#'
        
        # 全体平均
        avg_table['All'] = pivot_df[sample_columns].mean().values
        
        # クラスタごとの平均
        for i in range(k):
            cluster_data = pivot_df[pivot_df['cluster'] == i][sample_columns]
            avg_table[f'Cluster {i+1}'] = cluster_data.mean().values
            
        avg_table = avg_table.round(2)
        
        print(f"\n=== クラスタ平均値テーブル ===")
        print(avg_table.to_string())
        
        # テーブルを画像として保存
        self.plot_table(avg_table, "Overall Average Analysis: Cluster Averages", "overall_avg_table.png")
        
        # 結果保存
        avg_table.to_csv('overall_avg_cluster_table.csv')
        
        self.results['overall_analysis'] = {
            'pivot_df': pivot_df,
            'avg_table': avg_table,
            'k': k
        }
        
        return pivot_df, avg_table, k
        
    def safe_corr(self, x: np.ndarray, y: np.ndarray) -> float:
        """安全な相関係数計算"""
        if len(x) == 0 or len(y) == 0:
            return np.nan
        if np.std(x) == 0 or np.std(y) == 0:
            return np.nan
        try:
            corr, _ = pearsonr(x, y)
            return corr
        except:
            return np.nan
            
    def model_metrics_analysis(self):
        """モデル指標分析"""
        print("\n" + "="*80)
        print("モデル指標分析")
        print("="*80)
        
        if self.df is None:
            self.load_data()
            
        # 簡単なモデル指標計算
        sample_numbers = sorted(self.df['sample_number'].unique())
        
        model_df = pd.DataFrame(
            index=sample_numbers,
            columns=['Mean_Estimate', 'Std_Estimate', 'N_Users'],
            dtype=float
        )
        
        for sn in sample_numbers:
            subset = self.df[self.df['sample_number'] == sn]
            model_df.loc[sn, 'Mean_Estimate'] = subset['avg_estimate'].mean()
            model_df.loc[sn, 'Std_Estimate'] = subset['avg_estimate'].std()
            model_df.loc[sn, 'N_Users'] = len(subset['user_id'].unique())
            
        print(f"\n=== モデル指標テーブル ===")
        print(model_df.round(3).to_string())
        
        # 結果保存
        model_df.to_csv('overall_model_metrics.csv')
        
        self.results['model_metrics'] = model_df
        return model_df
        
    def save_results(self, output_dir: str = "visualization_results"):
        """結果保存"""
        os.makedirs(output_dir, exist_ok=True)
        
        # 各結果をCSVとして保存
        for key, data in self.results.items():
            if isinstance(data, pd.DataFrame):
                filename = os.path.join(output_dir, f"{key}.csv")
                data.to_csv(filename)
                print(f"保存: {filename}")
            elif isinstance(data, dict) and 'avg_table' in data:
                filename = os.path.join(output_dir, f"{key}_avg_table.csv")
                data['avg_table'].to_csv(filename)
                print(f"保存: {filename}")
                
        print(f"\n全結果を {output_dir} に保存しました。")


def main():
    parser = argparse.ArgumentParser(description="統合視覚化・統計分析")
    parser.add_argument("--mode", choices=["histogram", "combined", "summary", "boxplot", "overall", "model", "all"], 
                        default="all", help="分析モード選択")
    parser.add_argument("--csv", default="final_valid.csv", help="入力CSVファイル")
    parser.add_argument("--max_k", type=int, default=5, help="最大クラスター数")
    parser.add_argument("--fixed_axis", action="store_true", help="ヒストグラムの軸を-100から100に固定")
    parser.add_argument("--output_dir", default="visualization_results", help="出力ディレクトリ")
    
    args = parser.parse_args()
    
    analyzer = UnifiedVisualizationAnalyzer(args.csv, args.max_k)
    
    try:
        if args.mode in ["histogram", "all"]:
            analyzer.create_condition_histograms(args.fixed_axis)
            
        if args.mode in ["combined", "all"]:
            analyzer.create_combined_histogram(args.fixed_axis)
            
        if args.mode in ["summary", "all"]:
            analyzer.create_summary_statistics_table()
            
        if args.mode in ["boxplot", "all"]:
            analyzer.create_box_plots()
            
        if args.mode in ["overall", "all"]:
            analyzer.overall_average_analysis()
            
        if args.mode in ["model", "all"]:
            analyzer.model_metrics_analysis()
            
        # 結果保存
        analyzer.save_results(args.output_dir)
        
        print("\n統合視覚化・統計分析完了！")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())
