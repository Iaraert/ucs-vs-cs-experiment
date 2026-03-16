# %%
import numpy as np
import matplotlib.pyplot as plt
import time
from scipy import integrate
# from joblib import Parallel, delayed


def truncated_exponential(lam, size):
    # 切断指数分布
    u = np.random.uniform(0, 1, size)
    samples = -np.log(1 - u * (1 - np.exp(-lam))) / lam
    return samples


def find_max_f2(pdf, prams, is_gene, n_grid=100):
    # 2変量関数の最大値を Grid-Search
    x_grid = np.linspace(0, 1, n_grid)
    y_grid = np.linspace(0, 1, n_grid)
    X, Y = np.meshgrid(x_grid, y_grid)
    pdf_values = pdf(X.flatten(), Y.flatten(), *prams, is_gene)
    max_pdf = np.max(pdf_values)
    return max_pdf


def find_max_f1(pdf, prams, is_gene, n_grid=100):
    # 1変量関数の最大値を Grid-Search
    x_grid = np.linspace(0, 1, n_grid)
    pdf_values = pdf(x_grid, *prams, is_gene)
    max_pdf = np.max(pdf_values)
    return max_pdf
