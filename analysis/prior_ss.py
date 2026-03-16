# %%
import numpy as np
import matplotlib.pyplot as plt
import time
from scipy import integrate

# from joblib import Parallel, delayed
from prior_misc import find_max_f1, find_max_f2, truncated_exponential


def g1_z(a, b, is_gene):
    def gene_f(w_be, w_ce, a, b):
        factor = np.exp(-b * (1 - w_ce))
        term1 = np.exp(-a * w_be - a * (1 - w_ce))
        term2 = np.exp(-a * (1 - w_be) - a * w_ce)
        return factor * (term1 + term2)

    def prev_f(w_be, w_ce, a, b):
        factor = np.exp(-b * (1 - w_ce))
        term1 = np.exp(-a * (1 - w_be) - a * (1 - w_ce))
        term2 = np.exp(-a * (1 - w_be) - a * w_ce)
        return factor * (term1 + term2)

    if is_gene:
        result, error = integrate.dblquad(lambda y, x: gene_f(x, y, a, b), 0, 1, 0, 1)
        return result
    else:
        result, error = integrate.dblquad(lambda y, x: prev_f(x, y, a, b), 0, 1, 0, 1)
        return result


def g0_z(a, is_gene):
    def gene_f(w_be, a):
        return np.exp(-a * w_be) + np.exp(-a * (1 - w_be))

    def prev_f(w_be, a):
        return np.exp(-a * (1 - w_be))

    if is_gene:
        result, error = integrate.quad(lambda x: gene_f(x, a), 0, 1)
        return result
    else:
        result, error = integrate.quad(lambda x: prev_f(x, a), 0, 1)
        return result


def g1_pdf(w_be, w_ce, a, b, is_gene):
    # 自動積分の結果で正規化
    def gene_f(w_be, w_ce, a, b):
        factor = np.exp(-b * (1 - w_ce))
        term1 = np.exp(-a * w_be - a * (1 - w_ce))
        term2 = np.exp(-a * (1 - w_be) - a * w_ce)
        return factor * (term1 + term2)

    def prev_f(w_be, w_ce, a, b):
        factor = np.exp(-b * (1 - w_ce))
        term1 = np.exp(-a * (1 - w_be) - a * (1 - w_ce))
        term2 = np.exp(-a * (1 - w_be) - a * w_ce)
        return factor * (term1 + term2)

    if is_gene:
        result, error = integrate.dblquad(lambda y, x: gene_f(x, y, a, b), 0, 1, 0, 1)
        return gene_f(w_be, w_ce, a, b) / result
    else:
        result, error = integrate.dblquad(lambda y, x: prev_f(x, y, a, b), 0, 1, 0, 1)
        return prev_f(w_be, w_ce, a, b) / result


def g0_pdf(w_be, a, is_gene):
    # 自動積分の結果で正規化
    def gene_f(w_be, a):
        return np.exp(-a * w_be) + np.exp(-a * (1 - w_be))

    def prev_f(w_be, a):
        return np.exp(-a * (1 - w_be))

    if is_gene:
        result, error = integrate.quad(lambda x: gene_f(x, a), 0, 1)
        return gene_f(w_be, a) / result
    else:
        result, error = integrate.quad(lambda x: prev_f(x, a), 0, 1)
        return prev_f(w_be, a) / result


def g1_f(w_be, w_ce, a, b, is_gene):
    # 正規化なし
    if is_gene:
        factor = np.exp(-b * (1 - w_ce))
        term1 = np.exp(-a * w_be - a * (1 - w_ce))
        term2 = np.exp(-a * (1 - w_be) - a * w_ce)
        return factor * (term1 + term2)
    else:
        factor = np.exp(-b * (1 - w_ce))
        term1 = np.exp(-a * (1 - w_be) - a * (1 - w_ce))
        term2 = np.exp(-a * (1 - w_be) - a * w_ce)
        return factor * (term1 + term2)


def g0_f(w_be, a, is_gene):
    # 正規化なし
    if is_gene:
        return np.exp(-a * w_be) + np.exp(-a * (1 - w_be))
    else:
        return np.exp(-a * (1 - w_be))


def g1_rejection_sampling_by_f(n_samples, a, b, is_gene):
    # 棄却サンプリング
    max_pdf = find_max_f2(g1_f, (a, b), is_gene)
    samples = []

    rng = np.random.default_rng()
    batch_size = 10000  # PCのスペックに応じて決める
    while len(samples) < n_samples:
        x = rng.uniform(0, 1, batch_size)
        y = rng.uniform(0, 1, batch_size)
        u = rng.uniform(0, 1, batch_size)
        accept = u < g1_f(x, y, a, b, is_gene) / max_pdf
        samples.extend(np.column_stack([x[accept], y[accept]]))
    return np.array(samples[:n_samples])


def g0_rejection_sampling_by_f(n_samples, a, is_gene):
    # 棄却サンプリング
    max_pdf = find_max_f1(g0_f, (a,), is_gene)
    samples = []

    rng = np.random.default_rng()
    batch_size = 10000  # PCのスペックに応じて決める
    while len(samples) < n_samples:
        x = rng.uniform(0, 1, batch_size)
        u = rng.uniform(0, 1, batch_size)
        accept = u < g0_f(x, a, is_gene) / max_pdf
        samples.extend(np.column_stack([x[accept]]))
    return np.array(samples[:n_samples])


if __name__ == "__main__":
    # パラメータ設定
    a = 5
    b = 20
    is_gene = True
    n_samples = 100000

    # サンプリング実行
    start = time.time()
    samples = g1_rejection_sampling_by_f(n_samples, a, b, is_gene)
    elapsed = time.time() - start

    print(f"\nサンプル数: {n_samples}")
    print(f"実行時間: {elapsed:.4f} 秒")

    # 統計情報
    print("\n" + "=" * 60)
    print("サンプルの統計:")
    print("=" * 60)
    print(f"x の平均: {samples[:, 0].mean():.4f}")
    print(f"y の平均: {samples[:, 1].mean():.4f}")
    print(f"x の標準偏差: {samples[:, 0].std():.4f}")
    print(f"y の標準偏差: {samples[:, 1].std():.4f}")
    print(f"x の中央値: {np.median(samples[:, 0]):.4f}")
    print(f"y の中央値: {np.median(samples[:, 1]):.4f}")

    # 可視化
    fig = plt.figure(figsize=(15, 5))

    # 散布図
    ax1 = plt.subplot(131)
    ax1.scatter(
        samples[:, 0], samples[:, 1], alpha=0.3, s=5, c="red", edgecolors="none"
    )
    ax1.set_xlabel("x", fontsize=12)
    ax1.set_ylabel("y", fontsize=12)
    ax1.set_title(f"Sample Scatter\n(n={n_samples}, a={a}, b={b})", fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.set_aspect("equal")

    # 2次元ヒストグラム
    ax2 = plt.subplot(132)
    h = ax2.hist2d(samples[:, 0], samples[:, 1], bins=40, cmap="hot", cmin=1)
    ax2.set_xlabel("x", fontsize=12)
    ax2.set_ylabel("y", fontsize=12)
    ax2.set_title("Sample Distribution", fontsize=12)
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.set_aspect("equal")
    plt.colorbar(h[3], ax=ax2, label="Freq")

    # 周辺分布
    ax3 = plt.subplot(133)
    ax3.hist(samples[:, 0], bins=50, alpha=0.5, label="x", density=True)
    ax3.hist(samples[:, 1], bins=50, alpha=0.5, label="y", density=True)
    ax3.set_xlabel("Value", fontsize=12)
    ax3.set_ylabel("Density", fontsize=12)
    ax3.set_title("Merginal Dist.", fontsize=12)
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    # plt.savefig(f"rejection_sampling_a{a}_b{b}.png", dpi=150, bbox_inches="tight")
    plt.show()


# %%
