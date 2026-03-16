import numpy as np
from scipy.optimize import minimize_scalar


# # sign(x) * abs(x)^c を計算する関数
# def transform_with_c(x, c):
#     return np.sign(x) * np.abs(x) ** c


# # sign(x) * abs(x)^c の変換を行う際，人間の判断との相関が最も高いc を見つける関数
# def find_best_c_and_corr(rating, model_values):
#     def negative_corr(c):
#         transformed_values = transform_with_c(model_values, c)
#         return -np.corrcoef(rating, transformed_values)[
#             0, 1
#         ]  # 負の相関を返す（最小化のため）

#     result = minimize_scalar(negative_corr, bounds=(0.1, 10), method="bounded")
#     best_c = result.x
#     max_corr = -result.fun  # minimize_scalarの結果なので符号を反転
#     return best_c, max_corr


def power_transform(gamma, model, data):
    y = np.sign(model) * np.abs(model) ** gamma

    inds = np.where(~np.isnan(y))[0]

    if len(inds) > 0 and np.var(y[inds]) > np.finfo(float).eps and 0.1 < gamma < 10:
        # Calculate correlation coefficient
        cc = np.corrcoef(y[inds], data[inds])
        r = -cc[0, 1]
    else:
        r = 1.0

    return r


def power_optimize(human, model):
    res = minimize_scalar(
        lambda g: power_transform(g, model, human),
        bounds=(0.1, 10),
        method="bounded",
    )
    gamma = res.x
    value = np.sign(model) * np.abs(model) ** res.x
    r = -power_transform(res.x, model, human)
    raw = model
    return value, r