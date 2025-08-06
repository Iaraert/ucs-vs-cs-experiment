"""
Phase1とPhase2の共分散行列等質性検定（Box's M test）実装

目的: Phase1とPhase2のデータの共分散構造が同質であるかを確認する
手法: Box's M統計量を用いた多変量等質性検定

手順:
1. データ読み込み（pandas使用）
2. フェーズごとのサブセット抽出（Phase1: ex1_is_first==1, Phase2: ex1_is_first==0）
3. 共分散行列の計算（pandas .cov()使用）
4. Box's M統計量と自由度の算出
5. 検定結果の判断（p値に基づく同質性の評価）
6. 結果の要約と解釈
"""

import pandas as pd
import numpy as np
import scipy.stats as stats
import warnings
warnings.filterwarnings('ignore')


class BoxMTestAnalyzer:
    """
    Phase1とPhase2の共分散行列等質性検定（Box's M test）を実行するクラス
    """
    
    def __init__(self, data_path='final_valid_6_samples.csv'):
        """
        データを読み込み、分析の準備を行う
        
        Parameters:
        -----------
        data_path : str
            データファイルのパス
        """
        print("=== Box's M Test: Phase間共分散行列等質性検定 ===")
        print("データを読み込み中...")
        
        try:
            self.df = pd.read_csv(data_path)
            print(f"データ読み込み完了: {len(self.df)}行, {self.df['user_id'].nunique()}ユーザー")
            self._validate_data()
        except FileNotFoundError:
            print(f"エラー: ファイル '{data_path}' が見つかりません")
            raise
        except Exception as e:
            print(f"データ読み込みエラー: {e}")
            raise
    
    def _validate_data(self):
        """
        データの妥当性をチェック
        """
        required_columns = ['ex1_estimate', 'ex2_estimate', 'ex1_is_first', 'Cond']
        missing_columns = [col for col in required_columns if col not in self.df.columns]
        
        if missing_columns:
            raise ValueError(f"必要な列が不足しています: {missing_columns}")
        
        # Phase分布の確認
        phase1_count = (self.df['ex1_is_first'] == 1).sum()
        phase2_count = (self.df['ex1_is_first'] == 0).sum()
        
        print(f"Phase1 (ex1_is_first==1): {phase1_count}行")
        print(f"Phase2 (ex1_is_first==0): {phase2_count}行")
        
        # 条件別分布の確認
        cond_dist = self.df['Cond'].value_counts().sort_index()
        print(f"条件分布: {dict(cond_dist)}")
        
        if phase1_count < 2 or phase2_count < 2:
            print("警告: 各フェーズのサンプル数が少なすぎます (n<2)")
    
    def extract_phase_subsets(self, variables=None, condition=None):
        """
        フェーズごとのサブセットを抽出（条件指定対応）
        
        Parameters:
        -----------
        variables : list
            検定対象となる数値列（デフォルト: ['ex1_estimate', 'ex2_estimate']）
        condition : int, optional
            特定の条件でフィルタ（Cond列の値）
        
        Returns:
        --------
        tuple : (phase1_data, phase2_data)
            Phase1とPhase2のデータ
        """
        if variables is None:
            variables = ['ex1_estimate', 'ex2_estimate']
        
        print(f"\n--- フェーズごとのサブセット抽出 ---")
        print(f"検定対象変数: {variables}")
        if condition is not None:
            print(f"条件フィルタ: Cond={condition}")
        
        # データのフィルタリング
        df_filtered = self.df.copy()
        if condition is not None:
            df_filtered = df_filtered[df_filtered['Cond'] == condition]
            print(f"条件フィルタ後: {len(df_filtered)}行")
        
        # NaNを含む行を除外
        df_clean = df_filtered.dropna(subset=variables)
        print(f"欠損値除去後: {len(df_clean)}行")
        
        # Phase1とPhase2のデータを抽出
        phase1_data = df_clean[df_clean['ex1_is_first'] == 1][variables]
        phase2_data = df_clean[df_clean['ex1_is_first'] == 0][variables]
        
        print(f"Phase1データ: {len(phase1_data)}行")
        print(f"Phase2データ: {len(phase2_data)}行")
        
        return phase1_data, phase2_data
    
    def calculate_covariance_matrices(self, phase1_data, phase2_data):
        """
        各フェーズの共分散行列を計算
        
        Parameters:
        -----------
        phase1_data : pandas.DataFrame
            Phase1のデータ
        phase2_data : pandas.DataFrame
            Phase2のデータ
        
        Returns:
        --------
        tuple : (cov1, cov2, pooled_cov, n1, n2, p)
            各フェーズと統合の共分散行列、サンプル数、次元数
        """
        print(f"\n--- 共分散行列の計算 ---")
        
        n1, p = phase1_data.shape
        n2, _ = phase2_data.shape
        
        # 各群の共分散行列を計算（pandas .cov()使用）
        cov1 = phase1_data.cov().values
        cov2 = phase2_data.cov().values
        
        # プール共分散行列 Σpool = ((n1-1)Σ1 + (n2-1)Σ2) / (n1 + n2 - 2)
        pooled_cov = ((n1-1) * cov1 + (n2-1) * cov2) / (n1 + n2 - 2)
        
        print(f"Phase1共分散行列 (n1={n1}):")
        print(cov1)
        print(f"\nPhase2共分散行列 (n2={n2}):")
        print(cov2)
        print(f"\nプール共分散行列:")
        print(pooled_cov)
        
        return cov1, cov2, pooled_cov, n1, n2, p
    
    def compute_box_m_statistic(self, cov1, cov2, pooled_cov, n1, n2, p):
        """
        Box's M統計量と自由度を算出
        
        Parameters:
        -----------
        cov1, cov2, pooled_cov : numpy.ndarray
            各フェーズとプールの共分散行列
        n1, n2 : int
            各フェーズのサンプル数
        p : int
            変数の次元数
        
        Returns:
        --------
        dict : 検定結果
        """
        print(f"\n--- Box's M統計量と自由度の算出 ---")
        print(f"サンプル数: n1={n1}, n2={n2}")
        print(f"変数の次元: p={p}")
        
        try:
            # 行列式の計算
            det1 = np.linalg.det(cov1)
            det2 = np.linalg.det(cov2)
            det_pooled = np.linalg.det(pooled_cov)
            
            print(f"行列式: |Σ1|={det1:.6f}, |Σ2|={det2:.6f}, |Σpool|={det_pooled:.6f}")
            
            # 行列式が正でない場合はエラー
            if det1 <= 0 or det2 <= 0 or det_pooled <= 0:
                raise ValueError("共分散行列が正定値ではありません")
            
            # Box's M統計量の計算
            # M = (n1-1)·ln|Σ1| + (n2-1)·ln|Σ2| - (n1+n2-2)·ln|Σpool|
            M = (n1-1) * np.log(det1) + (n2-1) * np.log(det2) - (n1+n2-2) * np.log(det_pooled)
            
            # 自由度 df = p·(p+1)/2
            df = int(p * (p + 1) / 2)
            
            # 補正項 c = (2p²+3p-1) / [6(p+1)] · (1/(n1-1)+1/(n2-1)-1/(n1+n2-2))
            c = (2*p**2 + 3*p - 1) / (6*(p+1)) * (1/(n1-1) + 1/(n2-1) - 1/(n1+n2-2))
            
            # 修正統計量 χ² = M·(1-c)
            chi2_stat = M * (1 - c)
            
            # p値 = 1 - χ²分布の累積分布関数(χ², df)
            p_value = 1 - stats.chi2.cdf(chi2_stat, df)
            
            print(f"M統計量: {M:.6f}")
            print(f"自由度: {df}")
            print(f"補正項 c: {c:.6f}")
            print(f"修正統計量 χ²: {chi2_stat:.6f}")
            print(f"p値: {p_value:.6f}")
            
            return {
                'M_statistic': M,
                'chi2_statistic': chi2_stat,
                'degrees_of_freedom': df,
                'p_value': p_value,
                'correction_factor': c,
                'n1': n1,
                'n2': n2,
                'p': p
            }
            
        except Exception as e:
            print(f"Box's M統計量計算エラー: {e}")
            return None
    
    def interpret_results(self, results, alpha=0.05):
        """
        検定結果の判断と解釈
        
        Parameters:
        -----------
        results : dict
            Box's M検定の結果
        alpha : float
            有意水準（デフォルト: 0.05）
        
        Returns:
        --------
        dict : 解釈結果
        """
        if results is None:
            print("検定結果が無効です")
            return None
        
        print(f"\n--- 検定結果の判断 ---")
        print(f"有意水準α = {alpha}")
        
        # 帰無仮説と対立仮説
        print("帰無仮説 H0: 両フェーズの共分散行列は同質")
        print("対立仮説 H1: 両フェーズの共分散行列は異質")
        
        # 判定
        if results['p_value'] > alpha:
            decision = "帰無仮説を採択"
            interpretation = "共分散行列は同質"
            conclusion = "Phase1とPhase2の共分散構造に有意差は認められません"
        else:
            decision = "帰無仮説を棄却"
            interpretation = "共分散行列は異質"
            conclusion = "Phase1とPhase2の共分散構造に有意差があります"
        
        print(f"\n判定: {decision}")
        print(f"解釈: {interpretation}")
        print(f"結論: {conclusion}")
        
        # 前提条件の確認
        print(f"\n--- 検定の前提条件 ---")
        n_min = min(results['n1'], results['n2'])
        p = results['p']
        print(f"最小サンプル数: {n_min}")
        print(f"変数の次元: {p}")
        print(f"n≫p の条件: {'満たされている' if n_min > 3*p else '注意が必要'}")
        
        return {
            'decision': decision,
            'interpretation': interpretation,
            'conclusion': conclusion,
            'significant': results['p_value'] <= alpha
        }
    
    def create_summary_table(self, results, phase1_data, phase2_data):
        """
        結果の要約と解釈をテーブル形式でまとめる
        
        Parameters:
        -----------
        results : dict
            Box's M検定の結果
        phase1_data, phase2_data : pandas.DataFrame
            各フェーズのデータ
        """
        print(f"\n--- 結果要約テーブル ---")
        
        if results is None:
            print("有効な結果がありません")
            return
        
        # 基本統計量
        print("基本統計量:")
        print(f"  Phase1サンプル数: {results['n1']}")
        print(f"  Phase2サンプル数: {results['n2']}")
        print(f"  変数の次元数: {results['p']}")
        
        print("\nPhase1記述統計:")
        print(phase1_data.describe())
        
        print("\nPhase2記述統計:")
        print(phase2_data.describe())
        
        # 検定結果表形式
        summary_table = pd.DataFrame({
            '統計量': ['χ²統計量', '自由度', 'p値', '判定'],
            '値': [
                f"{results['chi2_statistic']:.4f}",
                f"{results['degrees_of_freedom']}",
                f"{results['p_value']:.6f}",
                '有意' if results['p_value'] < 0.05 else '非有意'
            ]
        })
        
        print("\nBox's M検定結果:")
        print(summary_table.to_string(index=False))
    
    def run_complete_analysis(self, variables=None, alpha=0.05, condition=None):
        """
        完全なBox's M test分析を実行（条件別分析対応）
        
        Parameters:
        -----------
        variables : list
            検定対象変数（デフォルト: ['ex1_estimate', 'ex2_estimate']）
        alpha : float
            有意水準（デフォルト: 0.05）
        condition : int, optional
            特定の条件でのみ分析を実行（Cond列の値）
        
        Returns:
        --------
        dict : 完全な分析結果
        """
        condition_label = f" (条件: Cond={condition})" if condition is not None else " (全体)"
        print(f"=== Box's M Test完全分析を開始{condition_label} ===")
        
        # 1. データ読み込み（既に__init__で実行済み）
        
        # 2. フェーズごとのサブセット抽出
        phase1_data, phase2_data = self.extract_phase_subsets(variables, condition)
        
        if len(phase1_data) < 2 or len(phase2_data) < 2:
            print(f"エラー: サンプル数不足により検定を実行できません{condition_label}")
            return None
        
        # 3. 共分散行列の計算
        cov1, cov2, pooled_cov, n1, n2, p = self.calculate_covariance_matrices(phase1_data, phase2_data)
        
        # 4. Box's M統計量と自由度の算出
        results = self.compute_box_m_statistic(cov1, cov2, pooled_cov, n1, n2, p)
        
        if results is None:
            return None
        
        # 5. 検定結果の判断
        interpretation = self.interpret_results(results, alpha)
        
        # 6. 結果の要約と解釈
        self.create_summary_table(results, phase1_data, phase2_data)
        
        # 完全な結果を返す
        complete_results = {
            'test_results': results,
            'interpretation': interpretation,
            'phase1_data': phase1_data,
            'phase2_data': phase2_data,
            'covariance_matrices': {
                'phase1': cov1,
                'phase2': cov2,
                'pooled': pooled_cov
            },
            'condition': condition
        }
        
        print(f"\n=== Box's M Test分析完了{condition_label} ===")
        return complete_results
    
    def run_condition_analysis(self, variables=None, alpha=0.05):
        """
        2×2要因計画での条件別Box's M test分析を実行
        
        Parameters:
        -----------
        variables : list
            検定対象変数（デフォルト: ['ex1_estimate', 'ex2_estimate']）
        alpha : float
            有意水準（デフォルト: 0.05）
        
        Returns:
        --------
        dict : 条件別分析結果
        """
        print("\n" + "="*60)
        print("2×2要因計画 条件別Box's M Test分析")
        print("="*60)
        
        # 利用可能な条件を確認
        available_conditions = sorted(self.df['Cond'].unique())
        print(f"利用可能な条件: {available_conditions}")
        
        # 各条件での分析を実行
        condition_results = {}
        
        for condition in available_conditions:
            print(f"\n" + "-"*40)
            print(f"条件 {condition} の分析")
            print("-"*40)
            
            result = self.run_complete_analysis(
                variables=variables, 
                alpha=alpha, 
                condition=condition
            )
            
            if result is not None:
                condition_results[condition] = result
            else:
                print(f"条件 {condition} の分析に失敗しました")
        
        # 全体分析も実行
        print(f"\n" + "-"*40)
        print("全体データの分析")
        print("-"*40)
        
        overall_result = self.run_complete_analysis(
            variables=variables, 
            alpha=alpha, 
            condition=None
        )
        
        if overall_result is not None:
            condition_results['overall'] = overall_result
        
        # 条件別サマリーを表示
        self._display_condition_summary(condition_results, alpha)
        
        return condition_results
    
    def _display_condition_summary(self, condition_results, alpha=0.05):
        """
        条件別分析結果のサマリーを表示
        
        Parameters:
        -----------
        condition_results : dict
            条件別分析結果
        alpha : float
            有意水準
        """
        print("\n" + "="*60)
        print("条件別Box's M Test結果サマリー")
        print("="*60)
        
        # サマリーテーブルのデータを準備
        summary_data = []
        
        for condition_key, result in condition_results.items():
            if result is not None:
                test_results = result['test_results']
                interpretation = result['interpretation']
                
                condition_label = f"条件 {condition_key}" if condition_key != 'overall' else "全体"
                
                summary_data.append({
                    '条件': condition_label,
                    'n1 (Phase1)': test_results['n1'],
                    'n2 (Phase2)': test_results['n2'],
                    'χ²統計量': f"{test_results['chi2_statistic']:.4f}",
                    '自由度': test_results['degrees_of_freedom'],
                    'p値': f"{test_results['p_value']:.6f}",
                    '判定': '有意' if test_results['p_value'] < alpha else '非有意',
                    '解釈': interpretation['interpretation']
                })
        
        # サマリーテーブルを作成・表示
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            print(summary_df.to_string(index=False))
            
            print(f"\n【解釈】")
            print(f"有意水準α = {alpha}")
            print("帰無仮説 H0: Phase1とPhase2の共分散行列は同質")
            print("対立仮説 H1: Phase1とPhase2の共分散行列は異質")
            
            # 条件間での比較コメント
            significant_conditions = [row['条件'] for row in summary_data if row['判定'] == '有意']
            non_significant_conditions = [row['条件'] for row in summary_data if row['判定'] == '非有意']
            
            if significant_conditions:
                print(f"\n有意差が検出された条件: {', '.join(significant_conditions)}")
            if non_significant_conditions:
                print(f"有意差が検出されなかった条件: {', '.join(non_significant_conditions)}")
        else:
            print("有効な分析結果がありません")


def main():
    """
    メイン実行関数: Box's M testの完全な実行例（条件別分析対応）
    """
    try:
        # 分析器の初期化（データ読み込み）
        analyzer = BoxMTestAnalyzer('final_valid_6_samples.csv')
        
        # 2×2要因計画での条件別Box's M test分析の実行
        condition_results = analyzer.run_condition_analysis(
            variables=['ex1_estimate', 'ex2_estimate'],
            alpha=0.05
        )
        
        print("\n" + "="*60)
        print("Box's M Test 条件別分析完了")
        print("="*60)
        
        # 結果の要約表示
        if condition_results:
            print(f"\n実行された分析数: {len(condition_results)}")
            for condition_key, result in condition_results.items():
                if result is not None:
                    test_results = result['test_results']
                    interpretation = result['interpretation']
                    condition_label = f"条件 {condition_key}" if condition_key != 'overall' else "全体"
                    
                    print(f"\n【{condition_label}】")
                    print(f"  χ²統計量: {test_results['chi2_statistic']:.3f}")
                    print(f"  p値: {test_results['p_value']:.6f}")
                    print(f"  判定: {interpretation['interpretation']}")
        else:
            print("条件別分析を完了できませんでした")
            
    except Exception as e:
        print(f"分析中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
