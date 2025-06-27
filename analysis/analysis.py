import pandas as pd
import statsmodels.formula.api as smf
from CS_UCS import CS, UCS

# 閾値設定
threshold_cs = 1.0
threshold_ucs = 0.01

# --- データの読み込み・ラベリング ---
summary = pd.read_csv('data/estimations_exp1.csv')
summary['Presentation'] = 'Summary'         # 一括提示
online   = pd.read_csv('data/estimations_exp1_2.csv')
online['Presentation']   = 'Online'    # 逐次提示

# 結合
Data = pd.concat([summary, online], ignore_index=True)

# 列名を短く
Data = Data.rename(columns={
    'a_value':'a', 'b_value':'b', 'c_value':'c', 'd_value':'d',
    'estimation':'Est'
})

# --- CS/UCS の計算 ---
Data['CS'] = Data.apply(
    lambda r: CS([r['a'],r['b'],r['c'],r['d']], threshold_cs, is_gene=r['is_symmetric']),
    axis=1
)
Data['UCS'] = Data.apply(
    lambda r: UCS([r['a'],r['b'],r['c'],r['d']], threshold_ucs, is_gene=r['is_symmetric']),
    axis=1
)

# --- サブセットを準備 ---
# is_symmetric: True/False, Presentation: Summary/Online の4つ
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
    """
    dv: 従属変数列名 (ここでは 'Est')
    predictor: 説明変数列名 ('CS' または 'UCS')
    subject: 被験者ID 列名 ('user_id')
    """
    models = {}
    # m0: ランダム切片のみ
    models['m0'] = smf.mixedlm(f"{dv} ~ 1", df, groups=df[subject], re_formula="~1").fit(reml=False)
    # m1: 固定効果 + ランダム切片
    models['m1'] = smf.mixedlm(f"{dv} ~ {predictor}", df, groups=df[subject], re_formula="~1").fit(reml=False)
    # m2: 固定効果 + 切片ランダム + 傾きランダム（非相関）
    models['m2'] = smf.mixedlm(
        f"{dv} ~ {predictor}",
        df,
        groups=df[subject],
        re_formula="~1",
        vc_formula={predictor: f"0 + {predictor}"}
    ).fit(reml=False)
    # m3: 固定効果 + 切片・傾きランダム（相関あり）
    models['m3'] = smf.mixedlm(f"{dv} ~ {predictor}", df, groups=df[subject], re_formula=f"~{predictor}").fit(reml=False)
    return models

# --- 全モデルをフィッティング ---
all_results = {}
for key, subdf in subsets.items():
    all_results[f"{key}_CS"] = fit_models(subdf, 'Est', 'CS', 'user_id')
    all_results[f"{key}_UCS"] = fit_models(subdf, 'Est', 'UCS', 'user_id')

# --- サマリー表示 ---
for name, models in all_results.items():
    print(f"\n===== {name} =====")
    for m, res in models.items():
        print(f"\n--- {m} ---")
        print(res.summary())

# --- BIC 比較表の作成・保存 ---
bic_records = []
for name, models in all_results.items():
    cond, measure = name.split('_', 1)
    for m, res in models.items():
        bic_records.append({
            'Condition': cond,
            'Measure': measure,
            'Model': m,
            'BIC': res.bic
        })
bic_df = pd.DataFrame(bic_records)
bic_df.to_csv('BIC_comparison.csv', index=False)

# --- 係数表の作成・保存 ---
coef_records = []
for name, models in all_results.items():
    cond, measure = name.split('_', 1)
    for m, res in models.items():
        fe = res.fe_params
        se = res.bse_fe
        # 切片
        coef_records.append({
            'Condition': cond,
            'Measure': measure,
            'Model': m,
            'Parameter': 'Intercept',
            'Estimate': fe['Intercept'],
            'SE': se['Intercept']
        })
        # 効果変数の係数（ある場合のみ）
        if len(fe) > 1:
            var = fe.index[1]
            coef_records.append({
                'Condition': cond,
                'Measure': measure,
                'Model': m,
                'Parameter': var,
                'Estimate': fe[var],
                'SE': se[var]
            })
coef_df = pd.DataFrame(coef_records)
coef_df.to_csv('coefficients.csv', index=False)

print("=> 結果ファイル BIC_comparison.csv, coefficients.csv を出力しました。")