import pandas as pd
import numpy as np
import scipy.stats as stats
from scipy.stats import bartlett, levene, shapiro
from sklearn.covariance import EmpiricalCovariance
import matplotlib.pyplot as plt
import matplotlib_fontja
import seaborn as sns
from itertools import combinations
import warnings
warnings.filterwarnings('ignore')

class PhaseHomogeneityAnalyzer:
    """
    各条件において異なるPhase(is_first=0, is_first=1)における回答の等質性を分析
    """
    def __init__(self, data_path='final_valid_updated.csv'):
        """
        データを読み込み、分析の準備を行う
        """
        self.df = pd.read_csv(data_path)
        self.results = {}
        self.prepare_data()
    
    def prepare_data(self):
        """
        データの前処理と条件の定義
        """
        # Cond列を使用して条件を定義
        self.df['condition'] = self.df['Cond'].apply(lambda x: f"Condition_{x}")
        
        # Phase情報の追加
        self.df['ex1_phase'] = np.where(self.df['ex1_is_first'] == 1, 'First', 'Second')
        self.df['ex2_phase'] = np.where(self.df['ex2_is_first'] == 1, 'First', 'Second')
        
        # 条件と刺激番号の組み合わせ条件を作成
        self.df['condition_stimulus'] = self.df.apply(
            lambda row: f"Cond{row['Cond']}_Ex1Stim{row['ex1_sample_number']}_Ex2Stim{row['ex2_sample_number']}", 
            axis=1
        )
        
        print(f"データ準備完了: {len(self.df)}行, {self.df['user_id'].nunique()}ユーザー")
        print(f"条件: {sorted(self.df['condition'].unique())}")
        print(f"条件×刺激の組み合わせ: {len(self.df['condition_stimulus'].unique())}種類")
        
        # 刺激番号の分布確認
        print(f"\n刺激番号の分布:")
        print(f"EX1 sample_number: {sorted(self.df['ex1_sample_number'].unique())}")
        print(f"EX2 sample_number: {sorted(self.df['ex2_sample_number'].unique())}")
        
        # Phase分布の確認
        print(f"\nPhase分布:")
        print(f"EX1 - First phase: {(self.df['ex1_is_first'] == 1).sum()}行")
        print(f"EX1 - Second phase: {(self.df['ex1_is_first'] == 0).sum()}行")
        print(f"EX2 - First phase: {(self.df['ex2_is_first'] == 1).sum()}行")
        print(f"EX2 - Second phase: {(self.df['ex2_is_first'] == 0).sum()}行")
        
        # 条件×刺激ごとのサンプル数確認
        print(f"\n各条件×刺激の組み合わせでのデータ数:")
        stimulus_counts = self.df['condition_stimulus'].value_counts().sort_index()
        for stimulus, count in stimulus_counts.head(10).items():
            print(f"  {stimulus}: {count}行")
        if len(stimulus_counts) > 10:
            print(f"  ... (他{len(stimulus_counts)-10}種類)")
    
    def box_m_test(self, group1_data, group2_data):
        """
        Box's M testの実装（共分散行列の等質性検定）
        """
        try:
            n1, p = group1_data.shape
            n2, _ = group2_data.shape
            
            # 各群の共分散行列を計算
            cov1 = EmpiricalCovariance().fit(group1_data).covariance_
            cov2 = EmpiricalCovariance().fit(group2_data).covariance_
            
            # プールされた共分散行列
            pooled_cov = ((n1-1) * cov1 + (n2-1) * cov2) / (n1 + n2 - 2)
            
            # Box's M統計量の計算
            det_pooled = np.linalg.det(pooled_cov)
            det1 = np.linalg.det(cov1)
            det2 = np.linalg.det(cov2)
            
            if det_pooled <= 0 or det1 <= 0 or det2 <= 0:
                return np.nan, np.nan
            
            M = (n1-1) * np.log(det1) + (n2-1) * np.log(det2) - (n1+n2-2) * np.log(det_pooled)
            
            # 自由度とp値の計算
            df = p * (p + 1) / 2
            c = (2*p**2 + 3*p - 1) / (6*(p+1)) * (1/(n1-1) + 1/(n2-1) - 1/(n1+n2-2))
            chi2_stat = M * (1 - c)
            p_value = 1 - stats.chi2.cdf(chi2_stat, df)
            
            return chi2_stat, p_value
            
        except Exception as e:
            print(f"Box's M test error: {e}")
            return np.nan, np.nan
    
    def perform_stimulus_analysis(self, condition, stimulus_num):
        """
        指定された条件と刺激番号でのPhase間等質性分析を実行
        """
        # 条件と刺激番号でフィルタリング
        condition_data = self.df[self.df['condition'] == condition].copy()
        
        results = {
            'condition': condition,
            'stimulus_number': stimulus_num,
            'n_participants': 0,
            'ex1_tests': {},
            'ex2_tests': {}
        }
        
        # EX1の分析（指定された刺激番号）
        ex1_stimulus_data = condition_data[condition_data['ex1_sample_number'] == stimulus_num]
        if len(ex1_stimulus_data) > 0:
            ex1_first = ex1_stimulus_data[ex1_stimulus_data['ex1_is_first'] == 1]['ex1_estimate']
            ex1_second = ex1_stimulus_data[ex1_stimulus_data['ex1_is_first'] == 0]['ex1_estimate']
            
            if len(ex1_first) > 2 and len(ex1_second) > 2:  # 最小サンプル数チェック
                # 正規性検定
                _, ex1_first_normal = shapiro(ex1_first) if len(ex1_first) >= 3 else (np.nan, np.nan)
                _, ex1_second_normal = shapiro(ex1_second) if len(ex1_second) >= 3 else (np.nan, np.nan)
                
                # 等分散性検定
                _, ex1_levene_p = levene(ex1_first, ex1_second)
                
                # T検定（等分散性に応じて選択）
                equal_var = ex1_levene_p > 0.05
                t_stat, p_value = stats.ttest_ind(ex1_first, ex1_second, equal_var=equal_var)
                
                # Cohen's d効果量
                pooled_std = np.sqrt(((len(ex1_first)-1)*ex1_first.var() + 
                                     (len(ex1_second)-1)*ex1_second.var()) / 
                                    (len(ex1_first) + len(ex1_second) - 2))
                cohens_d = (ex1_first.mean() - ex1_second.mean()) / pooled_std if pooled_std > 0 else np.nan
                
                results['ex1_tests'] = {
                    'first_mean': ex1_first.mean(),
                    'first_std': ex1_first.std(),
                    'first_n': len(ex1_first),
                    'second_mean': ex1_second.mean(),
                    'second_std': ex1_second.std(),
                    'second_n': len(ex1_second),
                    't_statistic': t_stat,
                    'p_value': p_value,
                    'cohens_d': cohens_d,
                    'equal_variance': equal_var,
                    'levene_p': ex1_levene_p,
                    'first_normal_p': ex1_first_normal,
                    'second_normal_p': ex1_second_normal
                }
        
        # EX2の分析（指定された刺激番号）
        ex2_stimulus_data = condition_data[condition_data['ex2_sample_number'] == stimulus_num]
        if len(ex2_stimulus_data) > 0:
            ex2_first = ex2_stimulus_data[ex2_stimulus_data['ex2_is_first'] == 1]['ex2_estimate']
            ex2_second = ex2_stimulus_data[ex2_stimulus_data['ex2_is_first'] == 0]['ex2_estimate']
            
            if len(ex2_first) > 2 and len(ex2_second) > 2:  # 最小サンプル数チェック
                # 正規性検定
                _, ex2_first_normal = shapiro(ex2_first) if len(ex2_first) >= 3 else (np.nan, np.nan)
                _, ex2_second_normal = shapiro(ex2_second) if len(ex2_second) >= 3 else (np.nan, np.nan)
                
                # 等分散性検定
                _, ex2_levene_p = levene(ex2_first, ex2_second)
                
                # T検定
                equal_var = ex2_levene_p > 0.05
                t_stat, p_value = stats.ttest_ind(ex2_first, ex2_second, equal_var=equal_var)
                
                # Cohen's d効果量
                pooled_std = np.sqrt(((len(ex2_first)-1)*ex2_first.var() + 
                                     (len(ex2_second)-1)*ex2_second.var()) / 
                                    (len(ex2_first) + len(ex2_second) - 2))
                cohens_d = (ex2_first.mean() - ex2_second.mean()) / pooled_std if pooled_std > 0 else np.nan
                
                results['ex2_tests'] = {
                    'first_mean': ex2_first.mean(),
                    'first_std': ex2_first.std(),
                    'first_n': len(ex2_first),
                    'second_mean': ex2_second.mean(),
                    'second_std': ex2_second.std(),
                    'second_n': len(ex2_second),
                    't_statistic': t_stat,
                    'p_value': p_value,
                    'cohens_d': cohens_d,
                    'equal_variance': equal_var,
                    'levene_p': ex2_levene_p,
                    'first_normal_p': ex2_first_normal,
                    'second_normal_p': ex2_second_normal
                }
        
        # 参加者数の更新
        ex1_users = set(ex1_stimulus_data['user_id'].unique()) if len(ex1_stimulus_data) > 0 else set()
        ex2_users = set(ex2_stimulus_data['user_id'].unique()) if len(ex2_stimulus_data) > 0 else set()
        results['n_participants'] = len(ex1_users.union(ex2_users))
        
        return results

    def perform_t_tests(self, condition):
        """
        指定された条件でのT検定を実行
        """
        condition_data = self.df[self.df['condition'] == condition].copy()
        
        results = {
            'condition': condition,
            'n_participants': condition_data['user_id'].nunique(),
            'ex1_tests': {},
            'ex2_tests': {}
        }
        
        # EX1の分析
        ex1_first = condition_data[condition_data['ex1_is_first'] == 1]['ex1_estimate']
        ex1_second = condition_data[condition_data['ex1_is_first'] == 0]['ex1_estimate']
        
        if len(ex1_first) > 0 and len(ex1_second) > 0:
            # 正規性検定
            _, ex1_first_normal = shapiro(ex1_first)
            _, ex1_second_normal = shapiro(ex1_second)
            
            # 等分散性検定
            _, ex1_levene_p = levene(ex1_first, ex1_second)
            
            # T検定（等分散性に応じて選択）
            equal_var = ex1_levene_p > 0.05
            t_stat, p_value = stats.ttest_ind(ex1_first, ex1_second, equal_var=equal_var)
            
            # Cohen's d効果量
            pooled_std = np.sqrt(((len(ex1_first)-1)*ex1_first.var() + 
                                 (len(ex1_second)-1)*ex1_second.var()) / 
                                (len(ex1_first) + len(ex1_second) - 2))
            cohens_d = (ex1_first.mean() - ex1_second.mean()) / pooled_std
            
            results['ex1_tests'] = {
                'first_mean': ex1_first.mean(),
                'first_std': ex1_first.std(),
                'first_n': len(ex1_first),
                'second_mean': ex1_second.mean(),
                'second_std': ex1_second.std(),
                'second_n': len(ex1_second),
                't_statistic': t_stat,
                'p_value': p_value,
                'cohens_d': cohens_d,
                'equal_variance': equal_var,
                'levene_p': ex1_levene_p,
                'first_normal_p': ex1_first_normal,
                'second_normal_p': ex1_second_normal
            }
        
        # EX2の分析
        ex2_first = condition_data[condition_data['ex2_is_first'] == 1]['ex2_estimate']
        ex2_second = condition_data[condition_data['ex2_is_first'] == 0]['ex2_estimate']
        
        if len(ex2_first) > 0 and len(ex2_second) > 0:
            # 正規性検定
            _, ex2_first_normal = shapiro(ex2_first)
            _, ex2_second_normal = shapiro(ex2_second)
            
            # 等分散性検定
            _, ex2_levene_p = levene(ex2_first, ex2_second)
            
            # T検定
            equal_var = ex2_levene_p > 0.05
            t_stat, p_value = stats.ttest_ind(ex2_first, ex2_second, equal_var=equal_var)
            
            # Cohen's d効果量
            pooled_std = np.sqrt(((len(ex2_first)-1)*ex2_first.var() + 
                                 (len(ex2_second)-1)*ex2_second.var()) / 
                                (len(ex2_first) + len(ex2_second) - 2))
            cohens_d = (ex2_first.mean() - ex2_second.mean()) / pooled_std
            
            results['ex2_tests'] = {
                'first_mean': ex2_first.mean(),
                'first_std': ex2_first.std(),
                'first_n': len(ex2_first),
                'second_mean': ex2_second.mean(),
                'second_std': ex2_second.std(),
                'second_n': len(ex2_second),
                't_statistic': t_stat,
                'p_value': p_value,
                'cohens_d': cohens_d,
                'equal_variance': equal_var,
                'levene_p': ex2_levene_p,
                'first_normal_p': ex2_first_normal,
                'second_normal_p': ex2_second_normal
            }
        
        # Box's M test（多変量等質性検定）
        if len(ex1_first) > 0 and len(ex1_second) > 0 and len(ex2_first) > 0 and len(ex2_second) > 0:
            # First phaseのデータ
            first_data = condition_data[
                (condition_data['ex1_is_first'] == 1) & 
                (condition_data['ex2_is_first'] == 1)
            ][['ex1_estimate', 'ex2_estimate']].dropna()
            
            # Second phaseのデータ
            second_data = condition_data[
                (condition_data['ex1_is_first'] == 0) & 
                (condition_data['ex2_is_first'] == 0)
            ][['ex1_estimate', 'ex2_estimate']].dropna()
            
            if len(first_data) > 2 and len(second_data) > 2:
                box_m_stat, box_m_p = self.box_m_test(first_data.values, second_data.values)
                results['box_m_test'] = {
                    'statistic': box_m_stat,
                    'p_value': box_m_p,
                    'first_n': len(first_data),
                    'second_n': len(second_data)
                }
        
        return results
    
    def analyze_all_conditions(self):
        """
        全ての条件と刺激について分析を実行
        """
        conditions = sorted(self.df['condition'].unique())
        stimulus_numbers = sorted(self.df['ex1_sample_number'].unique())  # 刺激番号（1-6）
        
        print("Phase間等質性分析（刺激別）を開始...")
        print("=" * 80)
        
        all_results = []
        
        for condition in conditions:
            print(f"\n条件: {condition}")
            print("=" * 60)
            
            for stimulus_num in stimulus_numbers:
                print(f"\n  刺激番号: {stimulus_num}")
                print("  " + "-" * 50)
                
                result = self.perform_stimulus_analysis(condition, stimulus_num)
                
                # データが十分にある場合のみ結果を保存・表示
                if (result['ex1_tests'] or result['ex2_tests']) and result['n_participants'] > 0:
                    all_results.append(result)
                    
                    print(f"    参加者数: {result['n_participants']}名")
                    
                    # EX1結果の表示
                    if result['ex1_tests']:
                        ex1 = result['ex1_tests']
                        print(f"    EX1分析:")
                        print(f"      First phase:  平均={ex1['first_mean']:.2f}, SD={ex1['first_std']:.2f}, n={ex1['first_n']}")
                        print(f"      Second phase: 平均={ex1['second_mean']:.2f}, SD={ex1['second_std']:.2f}, n={ex1['second_n']}")
                        print(f"      T検定: t={ex1['t_statistic']:.3f}, p={ex1['p_value']:.4f}, d={ex1['cohens_d']:.3f}")
                        print(f"      等分散性: p={ex1['levene_p']:.4f}")
                        if ex1['p_value'] < 0.05:
                            print(f"      *** 有意差あり (p < 0.05) ***")
                    
                    # EX2結果の表示
                    if result['ex2_tests']:
                        ex2 = result['ex2_tests']
                        print(f"    EX2分析:")
                        print(f"      First phase:  平均={ex2['first_mean']:.2f}, SD={ex2['first_std']:.2f}, n={ex2['first_n']}")
                        print(f"      Second phase: 平均={ex2['second_mean']:.2f}, SD={ex2['second_std']:.2f}, n={ex2['second_n']}")
                        print(f"      T検定: t={ex2['t_statistic']:.3f}, p={ex2['p_value']:.4f}, d={ex2['cohens_d']:.3f}")
                        print(f"      等分散性: p={ex2['levene_p']:.4f}")
                        if ex2['p_value'] < 0.05:
                            print(f"      *** 有意差あり (p < 0.05) ***")
                else:
                    print(f"    刺激{stimulus_num}: データ不足のため分析をスキップ")
        
        self.results = all_results
        return all_results
    
    def create_summary_tables(self):
        """
        分析結果のサマリーテーブルを作成（刺激別）
        """
        # T検定結果のサマリー
        t_test_summary = []
        
        for result in self.results:
            condition = result['condition']
            stimulus_num = result['stimulus_number']
            
            # EX1の結果
            if 'ex1_tests' in result and result['ex1_tests']:
                ex1 = result['ex1_tests']
                t_test_summary.append({
                    'condition': condition,
                    'stimulus_number': stimulus_num,
                    'experiment': 'EX1',
                    'first_mean': ex1['first_mean'],
                    'first_std': ex1['first_std'],
                    'first_n': ex1['first_n'],
                    'second_mean': ex1['second_mean'],
                    'second_std': ex1['second_std'],
                    'second_n': ex1['second_n'],
                    't_statistic': ex1['t_statistic'],
                    'p_value': ex1['p_value'],
                    'significant': ex1['p_value'] < 0.05,
                    'cohens_d': ex1['cohens_d'],
                    'effect_size': self._interpret_cohens_d(ex1['cohens_d']),
                    'equal_variance': ex1['equal_variance'],
                    'levene_p': ex1['levene_p']
                })
            
            # EX2の結果
            if 'ex2_tests' in result and result['ex2_tests']:
                ex2 = result['ex2_tests']
                t_test_summary.append({
                    'condition': condition,
                    'stimulus_number': stimulus_num,
                    'experiment': 'EX2',
                    'first_mean': ex2['first_mean'],
                    'first_std': ex2['first_std'],
                    'first_n': ex2['first_n'],
                    'second_mean': ex2['second_mean'],
                    'second_std': ex2['second_std'],
                    'second_n': ex2['second_n'],
                    't_statistic': ex2['t_statistic'],
                    'p_value': ex2['p_value'],
                    'significant': ex2['p_value'] < 0.05,
                    'cohens_d': ex2['cohens_d'],
                    'effect_size': self._interpret_cohens_d(ex2['cohens_d']),
                    'equal_variance': ex2['equal_variance'],
                    'levene_p': ex2['levene_p']
                })
        
        # DataFrameに変換
        df_t_test = pd.DataFrame(t_test_summary)
        
        # CSVファイルに保存
        df_t_test.to_csv('phase_homogeneity_stimulus_t_tests.csv', index=False, encoding='utf-8')
        
        print("\nサマリーテーブルを保存しました:")
        print("- phase_homogeneity_stimulus_t_tests.csv")
        
        return df_t_test
    
    def _interpret_cohens_d(self, d):
        """
        Cohen's dの効果量を解釈
        """
        abs_d = abs(d)
        if abs_d < 0.2:
            return 'negligible'
        elif abs_d < 0.5:
            return 'small'
        elif abs_d < 0.8:
            return 'medium'
        else:
            return 'large'    
    
    def create_visualizations(self):
        """
        分析結果の可視化（刺激別）
        """
        # フィギュアサイズの設定
        plt.style.use('default')
        
        conditions = sorted(self.df['condition'].unique())
        stimulus_numbers = sorted(self.df['ex1_sample_number'].unique())
        
        # 1. 刺激別Phase間差異のヒートマップ（EX1）
        if hasattr(self, 'results') and self.results:
            df_t_test = self.create_summary_tables()
            
            if len(df_t_test) > 0:
                # EX1のp値ヒートマップ
                ex1_data = df_t_test[df_t_test['experiment'] == 'EX1']
                if len(ex1_data) > 0:
                    pivot_ex1 = ex1_data.pivot(index='condition', columns='stimulus_number', values='p_value')
                    
                    plt.figure(figsize=(12, 6))
                    sns.heatmap(pivot_ex1, annot=True, cmap='RdYlBu_r', center=0.05, 
                                cbar_kws={'label': 'p-value'}, fmt='.3f', vmin=0, vmax=1)
                    plt.title('EX1: p-value of Phase-wise t-test by stimulus')
                    plt.xlabel('Stimulus Number')
                    plt.ylabel('Condition')
                    plt.tight_layout()
                    plt.savefig('phase_homogeneity_stimulus_ex1_pvalues.png', dpi=300, bbox_inches='tight')
                    plt.close()
                
                # EX2のp値ヒートマップ
                ex2_data = df_t_test[df_t_test['experiment'] == 'EX2']
                if len(ex2_data) > 0:
                    pivot_ex2 = ex2_data.pivot(index='condition', columns='stimulus_number', values='p_value')
                    
                    plt.figure(figsize=(12, 6))
                    sns.heatmap(pivot_ex2, annot=True, cmap='RdYlBu_r', center=0.05, 
                                cbar_kws={'label': 'p-value'}, fmt='.3f', vmin=0, vmax=1)
                    plt.title('EX2: p-value of Phase-wise t-test by stimulus')
                    plt.xlabel('Stimulus Number')
                    plt.ylabel('Condition')
                    plt.tight_layout()
                    plt.savefig('phase_homogeneity_stimulus_ex2_pvalues.png', dpi=300, bbox_inches='tight')
                    plt.close()
                
                # 効果量のヒートマップ（EX1）
                if len(ex1_data) > 0:
                    pivot_ex1_d = ex1_data.pivot(index='condition', columns='stimulus_number', values='cohens_d')
                    
                    plt.figure(figsize=(12, 6))
                    sns.heatmap(pivot_ex1_d, annot=True, cmap='RdBu_r', center=0, 
                                cbar_kws={'label': "Cohen's d"}, fmt='.2f')
                    plt.title('EX1: Effect size between phases by stimulus(Cohen\'s d)')
                    plt.xlabel('Stimulus Number')
                    plt.ylabel('Condition')
                    plt.tight_layout()
                    plt.savefig('phase_homogeneity_stimulus_ex1_effect_size.png', dpi=300, bbox_inches='tight')
                    plt.close()
                
                # 効果量のヒートマップ（EX2）
                if len(ex2_data) > 0:
                    pivot_ex2_d = ex2_data.pivot(index='condition', columns='stimulus_number', values='cohens_d')
                    
                    plt.figure(figsize=(12, 6))
                    sns.heatmap(pivot_ex2_d, annot=True, cmap='RdBu_r', center=0, 
                                cbar_kws={'label': "Cohen's d"}, fmt='.2f')
                    plt.title('EX2: Effect size between phases by stimulus(Cohen\'s d)')
                    plt.xlabel('Stimulus Number')
                    plt.ylabel('Condition')
                    plt.tight_layout()
                    plt.savefig('phase_homogeneity_stimulus_ex2_effect_size.png', dpi=300, bbox_inches='tight')
                    plt.close()
        
        # 2. 有意差のある刺激の分布プロット
        if hasattr(self, 'results') and self.results:
            significant_results = [r for r in self.results 
                                 if (r.get('ex1_tests', {}).get('p_value', 1) < 0.05 or 
                                     r.get('ex2_tests', {}).get('p_value', 1) < 0.05)]
            
            if significant_results:
                n_sig = len(significant_results)
                fig, axes = plt.subplots(min(n_sig, 6), 2, figsize=(15, 4*min(n_sig, 6)))
                if n_sig == 1:
                    axes = axes.reshape(1, -1)
                
                for i, result in enumerate(significant_results[:6]):  # 最大6個まで表示
                    condition = result['condition']
                    stimulus_num = result['stimulus_number']
                    
                    # EX1の分布
                    if result.get('ex1_tests'):
                        condition_data = self.df[
                            (self.df['condition'] == condition) & 
                            (self.df['ex1_sample_number'] == stimulus_num)
                        ]
                        
                        ex1_first = condition_data[condition_data['ex1_is_first'] == 1]['ex1_estimate']
                        ex1_second = condition_data[condition_data['ex1_is_first'] == 0]['ex1_estimate']
                        
                        if len(ex1_first) > 0 and len(ex1_second) > 0:
                            axes[i, 0].hist(ex1_first, alpha=0.7, label='First phase', bins=15, density=True, color='skyblue')
                            axes[i, 0].hist(ex1_second, alpha=0.7, label='Second phase', bins=15, density=True, color='lightcoral')
                            axes[i, 0].set_title(f'{condition} EX1 stimulus No.{stimulus_num} (p={result["ex1_tests"]["p_value"]:.3f})')
                            axes[i, 0].set_xlabel('Estimation')
                            axes[i, 0].set_ylabel('Density')
                            axes[i, 0].legend()
                    
                    # EX2の分布
                    if result.get('ex2_tests'):
                        condition_data = self.df[
                            (self.df['condition'] == condition) & 
                            (self.df['ex2_sample_number'] == stimulus_num)
                        ]
                        
                        ex2_first = condition_data[condition_data['ex2_is_first'] == 1]['ex2_estimate']
                        ex2_second = condition_data[condition_data['ex2_is_first'] == 0]['ex2_estimate']
                        
                        if len(ex2_first) > 0 and len(ex2_second) > 0:
                            axes[i, 1].hist(ex2_first, alpha=0.7, label='First phase', bins=15, density=True, color='skyblue')
                            axes[i, 1].hist(ex2_second, alpha=0.7, label='Second phase', bins=15, density=True, color='lightcoral')
                            axes[i, 1].set_title(f'{condition} EX2 stimulus No.{stimulus_num} (p={result["ex2_tests"]["p_value"]:.3f})')
                            axes[i, 1].set_xlabel('Estimation')
                            axes[i, 1].set_ylabel('Density')
                            axes[i, 1].legend()
                
                plt.tight_layout()
                plt.savefig('phase_homogeneity_significant_distributions.png', dpi=300, bbox_inches='tight')
                plt.close()
        
        print("可視化ファイルを保存しました:")
        if hasattr(self, 'results') and self.results:
            print("- phase_homogeneity_stimulus_ex1_pvalues.png")
            print("- phase_homogeneity_stimulus_ex2_pvalues.png")
            print("- phase_homogeneity_stimulus_ex1_effect_size.png")
            print("- phase_homogeneity_stimulus_ex2_effect_size.png")
            print("- phase_homogeneity_significant_distributions.png")
    
    def generate_report(self):
        """
        分析結果のレポートを生成（刺激別）
        """
        df_t_test = self.create_summary_tables()
        
        with open('phase_homogeneity_stimulus_report.txt', 'w', encoding='utf-8') as f:
            f.write("Phase間等質性分析レポート（刺激別）\n")
            f.write("=" * 60 + "\n\n")
            
            # 全体サマリー
            f.write("1. 分析概要\n")
            f.write("-" * 30 + "\n")
            f.write(f"分析対象: {len(self.df)}行, {self.df['user_id'].nunique()}ユーザー\n")
            f.write(f"条件数: {len(self.df['condition'].unique())}\n")
            f.write(f"刺激数: {len(self.df['ex1_sample_number'].unique())}種類\n")
            f.write(f"分析手法: 刺激別T検定, 効果量分析\n\n")
            
            # T検定結果サマリー
            f.write("2. T検定結果サマリー\n")
            f.write("-" * 30 + "\n")
            significant_tests = df_t_test[df_t_test['significant'] == True]
            f.write(f"有意差あり: {len(significant_tests)}/{len(df_t_test)}件\n")
            
            if len(significant_tests) > 0:
                f.write("\n有意差のある条件・刺激・実験:\n")
                for _, row in significant_tests.iterrows():
                    f.write(f"- {row['condition']} 刺激{row['stimulus_number']} {row['experiment']}: ")
                    f.write(f"p={row['p_value']:.4f}, d={row['cohens_d']:.3f} ({row['effect_size']})\n")
            
            # 条件別サマリー
            f.write(f"\n3. 条件別サマリー\n")
            f.write("-" * 30 + "\n")
            for condition in sorted(df_t_test['condition'].unique()):
                cond_data = df_t_test[df_t_test['condition'] == condition]
                cond_significant = cond_data[cond_data['significant'] == True]
                f.write(f"{condition}:\n")
                f.write(f"  総検定数: {len(cond_data)}件\n")
                f.write(f"  有意差あり: {len(cond_significant)}件\n")
                if len(cond_significant) > 0:
                    f.write(f"  有意差のある刺激: ")
                    sig_stimuli = sorted(cond_significant['stimulus_number'].unique())
                    f.write(f"{sig_stimuli}\n")
                f.write("\n")
            
            # 刺激別サマリー
            f.write(f"4. 刺激別サマリー\n")
            f.write("-" * 30 + "\n")
            for stimulus in sorted(df_t_test['stimulus_number'].unique()):
                stim_data = df_t_test[df_t_test['stimulus_number'] == stimulus]
                stim_significant = stim_data[stim_data['significant'] == True]
                f.write(f"刺激{stimulus}:\n")
                f.write(f"  総検定数: {len(stim_data)}件\n")
                f.write(f"  有意差あり: {len(stim_significant)}件\n")
                if len(stim_significant) > 0:
                    f.write(f"  有意差のある条件: ")
                    sig_conditions = sorted(stim_significant['condition'].unique())
                    f.write(f"{sig_conditions}\n")
                f.write("\n")
            
            # 結論
            f.write(f"5. 結論\n")
            f.write("-" * 30 + "\n")
            total_tests = len(df_t_test)
            significant_rate = len(significant_tests) / total_tests if total_tests > 0 else 0
            
            f.write(f"全体の有意差率: {significant_rate:.2%}\n\n")
            
            if significant_rate < 0.1:
                f.write("刺激レベルでのPhase間等質性は概ね保たれていると考えられます。\n")
            elif significant_rate < 0.3:
                f.write("一部の刺激でPhase間に差異が見られますが、全体的には等質性は保たれています。\n")
            else:
                f.write("多くの刺激でPhase間に有意差が見られ、等質性に課題がある可能性があります。\n")
                
            f.write("\n各刺激は参加者が遭遇する具体的な実験条件を表しており、\n")
            f.write("Phase間で差異が見られる刺激については、実験順序効果や\n")
            f.write("学習効果の影響を詳細に検討する必要があります。\n")
        
        print("レポートを保存しました: phase_homogeneity_stimulus_report.txt")


def main():
    """
    メイン実行関数
    """
    
    print("Phase間等質性分析（刺激別）を開始します...")
    
    # 分析器の初期化
    analyzer = PhaseHomogeneityAnalyzer('final_valid_updated.csv')
    
    # 分析の実行
    results = analyzer.analyze_all_conditions()
    
    # サマリーテーブルの作成
    df_t_test = analyzer.create_summary_tables()

    matplotlib_fontja.japanize()

    sns.set_theme(font="IPAexGothic")
    
    # 可視化
    analyzer.create_visualizations()
    
    # レポート生成
    analyzer.generate_report()
    
    print("\n分析完了! 以下のファイルが生成されました:")
    print("- phase_homogeneity_stimulus_t_tests.csv")
    print("- phase_homogeneity_stimulus_ex1_pvalues.png")
    print("- phase_homogeneity_stimulus_ex2_pvalues.png")
    print("- phase_homogeneity_stimulus_ex1_effect_size.png")
    print("- phase_homogeneity_stimulus_ex2_effect_size.png")
    print("- phase_homogeneity_significant_distributions.png")
    print("- phase_homogeneity_stimulus_report.txt")


if __name__ == '__main__':
    main()
