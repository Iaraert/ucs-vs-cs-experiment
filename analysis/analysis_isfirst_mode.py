import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import seaborn as sns
import sys
from CS_UCS import CS, UCS

# --- モード選択: 'first', 'second', 'all' ---
# コマンドライン引数で指定（なければ'all'）
if len(sys.argv) > 1:
    mode = sys.argv[1].lower()
    assert mode in ['first', 'second', 'all']
else:
    mode = 'all'
print(f"分析モード: {mode}")

# --- データ読み込み ---
summary = pd.read_csv('data/estimations_exp1.csv')
summary['Presentation'] = 'Summary'
online = pd.read_csv('data/estimations_exp1_2.csv')
online['Presentation'] = 'Online'

# 結合
Data = pd.concat([summary, online], ignore_index=True)

# 列名を短く
Data = Data.rename(columns={
    'a_value':'a', 'b_value':'b', 'c_value':'c', 'd_value':'d',
    'estimation':'Est'
})

# --- CS/UCS の計算 ---
Data['CS'] = Data.apply(
    lambda r: CS([r['a'],r['b'],r['c'],r['d']], 1.0, is_gene=r['is_symmetric']),
    axis=1
)
Data['UCS'] = Data.apply(
    lambda r: UCS([r['a'],r['b'],r['c'],r['d']], 0.01, is_gene=r['is_symmetric']),
    axis=1
)

# --- is_first でフィルタ ---
if mode == 'first':
    Data = Data[Data['is_first'] == 1]
elif mode == 'second':
    Data = Data[Data['is_first'] == 0]
# 'all'はそのまま

# --- サブセットを準備 ---
subsets = {}
for sym in [True, False]:
    for pres in ['Summary','Online']:
        key = f"{'Symmetric' if sym else 'Asymmetric'}_{pres}"
        subsets[key] = Data[
            (Data['is_symmetric']==sym) &
            (Data['Presentation']==pres)
        ]

# --- 混合効果モデルを当てはめる関数 ---
def fit_models(df, dv, predictor, subject):
    models = {}
    if len(df) < 10:
        return models
    models['m0'] = smf.mixedlm(f"{dv} ~ 1", df, groups=df[subject], re_formula="~1").fit(reml=False)
    models['m1'] = smf.mixedlm(f"{dv} ~ {predictor}", df, groups=df[subject], re_formula="~1").fit(reml=False)
    return models

# --- 全モデルをフィッティング ---
all_results = {}
bic_records = []
for key, subdf in subsets.items():
    for measure in ['CS', 'UCS']:
        models = fit_models(subdf, 'Est', measure, 'user_id')
        all_results[f"{key}_{measure}"] = models
        # BIC値を記録
        for m, res in models.items():
            pres = 'Summary' if 'Summary' in key else 'Online'
            sym = 'symmetric' if 'Symmetric' in key else 'asymmetric'
            model_name = f"{m}_{sym}"
            bic_records.append({
                'Presentation': pres,
                'is_symmetric': sym,
                'Measure': measure,
                'Model': model_name,
                'BIC': res.bic
            })

# --- BIC値の可視化 ---
bic_df = pd.DataFrame(bic_records)
if not bic_df.empty:
    plt.figure(figsize=(10,6))
    sns.barplot(
        data=bic_df,
        x='Model', y='BIC',
        hue='Measure',
        ci=None
    )
    plt.title(f"BIC値比較 (mode={mode})")
    plt.ylabel('BIC')
    plt.xlabel('モデル')
    plt.legend(title='指標')
    plt.tight_layout()
    plt.savefig(f"analysis/BIC_comparison_{mode}.png")
    plt.close()
    # 条件ごとにも保存
    for (pres, sym), gdf in bic_df.groupby(['Presentation','is_symmetric']):
        plt.figure(figsize=(8,5))
        sns.barplot(
            data=gdf,
            x='Model', y='BIC', hue='Measure', ci=None
        )
        plt.title(f"BIC: {pres}, {sym} (mode={mode})")
        plt.ylabel('BIC')
        plt.xlabel('モデル')
        plt.legend(title='指標')
        plt.tight_layout()
        fname = f"analysis/BIC_{pres}_{sym}_{mode}.png"
        plt.savefig(fname)
        plt.close()
    bic_df.to_csv(f"analysis/BIC_table_{mode}.csv", index=False)
    print(f"BIC値の比較グラフ・表を analysis/ に保存しました。")

# --- 可視化 ---
for key, subdf in subsets.items():
    if len(subdf) < 10:
        continue
    plt.figure(figsize=(8,5))
    sns.boxplot(x='CS', y='Est', data=subdf, color='lightblue')
    plt.title(f"{key} (mode={mode})\nEstimation vs CS")
    plt.xlabel('CS')
    plt.ylabel('Estimation')
    plt.tight_layout()
    plt.savefig(f"analysis/boxplot_{key}_CS_{mode}.png")
    plt.close()
    plt.figure(figsize=(8,5))
    sns.boxplot(x='UCS', y='Est', data=subdf, color='lightgreen')
    plt.title(f"{key} (mode={mode})\nEstimation vs UCS")
    plt.xlabel('UCS')
    plt.ylabel('Estimation')
    plt.tight_layout()
    plt.savefig(f"analysis/boxplot_{key}_UCS_{mode}.png")
    plt.close()

print(f"グラフ画像を analysis/boxplot_*_{mode}.png に保存しました。")
