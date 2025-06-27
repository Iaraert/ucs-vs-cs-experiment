import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# BIC比較ファイルのパス
bic_csv = 'BIC_comparison.csv'  # または 'analysis/BIC_table_all.csv'

# データ読み込み
bic_df = pd.read_csv(bic_csv)

# Condition列からPresentation, is_symmetricを分離
# 例: 'Symmetric', 'Summary_CS' → is_symmetric:Symmetric, Presentation:Summary, Measure:CS
bic_df[['is_symmetric', 'tmp']] = bic_df['Condition'].str.split(',', n=1, expand=True)
bic_df['is_symmetric'] = bic_df['is_symmetric'].str.strip()
bic_df[['Presentation', 'Measure2']] = bic_df['Measure'].str.split('_', n=1, expand=True)
bic_df['Measure'] = bic_df['Measure2']
bic_df = bic_df.drop(columns=['Condition', 'tmp', 'Measure2'])

# 条件ごとのBIC値の集計
summary = bic_df.groupby(['Presentation', 'is_symmetric', 'Measure', 'Model'])['BIC'].agg(['mean', 'std', 'min', 'max', 'count']).reset_index()
print('--- BIC値の条件別集計 ---')
print(summary)
summary.to_csv('analysis/BIC_summary_by_condition.csv', index=False)

# グラフ描画
sns.set(style="whitegrid")
for pres in bic_df['Presentation'].unique():
    for sym in bic_df['is_symmetric'].unique():
        plt.figure(figsize=(10,6))
        sub = bic_df[(bic_df['Presentation']==pres)&(bic_df['is_symmetric']==sym)]
        if sub.empty:
            continue
        sns.barplot(data=sub, x='Model', y='BIC', hue='Measure', ci=None)
        plt.title(f"BIC値: {pres}, {sym}")
        plt.ylabel('BIC')
        plt.xlabel('モデル')
        plt.legend(title='指標')
        plt.tight_layout()
        fname = f"analysis/BIC_by_{pres}_{sym}.png"
        plt.savefig(fname)
        plt.close()
        # 折れ線グラフも
        plt.figure(figsize=(10,6))
        sns.lineplot(data=sub, x='Model', y='BIC', hue='Measure', marker='o')
        plt.title(f"BIC値(折れ線): {pres}, {sym}")
        plt.ylabel('BIC')
        plt.xlabel('モデル')
        plt.legend(title='指標')
        plt.tight_layout()
        fname = f"analysis/BIC_line_{pres}_{sym}.png"
        plt.savefig(fname)
        plt.close()

print('BIC値の集計表: analysis/BIC_summary_by_condition.csv')
print('BIC値のグラフ: analysis/BIC_by_*_*.png, analysis/BIC_line_*_*.png')
