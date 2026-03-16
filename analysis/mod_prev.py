# %%

import numpy as np
import prior_ss as ssp
import importlib
import math
from scipy import integrate

# importlib.reload(ssp)


def paris(tables, is_gene):
    a = np.float64(tables)[:, 0]
    b = np.float64(tables)[:, 1]
    c = np.float64(tables)[:, 2]
    d = np.float64(tables)[:, 3]
    if is_gene:
        res = a / (a + b + c)
    else:
        res = b / (a + b + d)
    return res


def dfh(tables, is_gene):
    a = np.float64(tables)[:, 0]
    b = np.float64(tables)[:, 1]
    c = np.float64(tables)[:, 2]
    d = np.float64(tables)[:, 3]
    # res = (a / (math.sqrt((a + b) * (a + c))))*2 -1
    if is_gene:
        res = a / (np.sqrt((a + b) * (a + c)))
    else:
        res = b / (np.sqrt((a + b) * (b + d)))
    return res


def CS(tables, is_gene, is_structure, ssp_prams):
    if is_structure:
        return CS_structure_hlu(tables, is_gene, ssp_prams)
    else:
        return CS_strength(tables, is_gene, ssp_prams)


def CS_structure_grif(tables, is_gene, ssp_prams, loop_n=int(1e5)):
    # griffiths and tenenbaum の実装の再現
    # Prior に従う w を大量にサンプリングして近似する
    # スペックに応じて引数のデフォルト値 loop_n を調整すること
    rng = np.random.default_rng()
    alpha, beta = ssp_prams
    use_ssp = alpha != 0
    if use_ssp:
        samples = ssp.g1_rejection_sampling_by_f(loop_n, alpha, beta, is_gene)
        wgts_be_g1 = samples[:, 0]  # wgts_be
        wgts_ce_g1 = samples[:, 1]  # wgts_ce
        samples = ssp.g0_rejection_sampling_by_f(loop_n, alpha, is_gene)
        wgts_be_g0 = samples[:, 0]  # wgts_be
    else:
        wgts_be_g1 = rng.uniform(0, 1, size=loop_n)
        wgts_ce_g1 = rng.uniform(0, 1, size=loop_n)
        wgts_be_g0 = rng.uniform(0, 1, size=loop_n)

    if is_gene:
        like_func_g1 = [
            (1 - (1 - wgts_ce_g1) * (1 - wgts_be_g1)),  # P(E=1|C=1)
            (1 - wgts_ce_g1) * (1 - wgts_be_g1),  # P(E=0|C=1)
            wgts_be_g1,  # P(E=1|C=0)
            (1 - wgts_be_g1),  # P(E=0|C=0)
        ]
    else:
        like_func_g1 = [
            wgts_be_g1 - (wgts_ce_g1 * wgts_be_g1),  # P(E=1|C=1)
            1 - (wgts_be_g1 - (wgts_ce_g1 * wgts_be_g1)),  # P(E=0|C=1)
            wgts_be_g1,  # P(E=1|C=0)
            1 - wgts_be_g1,  # P(E=0|C=0)
        ]
    like_func_g0 = [
        wgts_be_g0,  # P(E=1|C=1)
        (1 - wgts_be_g0),  # P(E=0|C=1)
        wgts_be_g0,  # P(E=1|C=0)
        (1 - wgts_be_g0),  # P(E=0|C=0)
    ]

    res = []
    for table in tables:
        ln_like_val_g1 = np.sum(
            (np.ones((loop_n, 1)) * np.array(table)) * np.log(like_func_g1).T,
            axis=1,
        )  # 多分マルチヌーイの係数は尤度比で打ち消されるから考慮しなくて良いということ
        ln_like_val_g0 = np.sum(
            (np.ones((loop_n, 1)) * np.array(table)) * np.log(like_func_g0).T,
            axis=1,
        )
        like_val_g1 = np.mean(np.exp(ln_like_val_g1))
        like_val_g0 = np.mean(np.exp(ln_like_val_g0))
        logscore = np.log(like_val_g1) - np.log(like_val_g0)
        res.append(logscore)
    return res


def CS_structure_grid(tables, is_gene, ssp_prams, interval=0.05):
    # グリッド上に w を設定し、Prior の値で重みづけて近似する
    # grifよりも 若干速いが、相対的に近似のズレが大きい
    # スペックに応じて引数のデフォルト値 interval を調整すること
    interval = 0.01
    w_ticks = np.arange(interval, 1, interval)
    # TODO: w_be は本当に分ける必要があるのか？
    wgts_be_g1, wgts_ce_g1 = np.meshgrid(w_ticks, w_ticks)
    wgts_be_g0 = w_ticks
    wgts_be_g0, wgts_be_g1, wgts_ce_g1 = [
        w.flatten() for w in [wgts_be_g0, wgts_be_g1, wgts_ce_g1]
    ]

    if is_gene:
        like_func_g1 = [
            (1 - (1 - wgts_ce_g1) * (1 - wgts_be_g1)),  # P(E=1|C=1)
            (1 - wgts_ce_g1) * (1 - wgts_be_g1),  # P(E=0|C=1)
            wgts_be_g1,  # P(E=1|C=0)
            (1 - wgts_be_g1),  # P(E=0|C=0)
        ]
    else:
        like_func_g1 = [
            wgts_be_g1 - (wgts_ce_g1 * wgts_be_g1),  # P(E=1|C=1)
            1 - (wgts_be_g1 - (wgts_ce_g1 * wgts_be_g1)),  # P(E=0|C=1)
            wgts_be_g1,  # P(E=1|C=0)
            1 - wgts_be_g1,  # P(E=0|C=0)
        ]
    like_func_g0 = [
        wgts_be_g0,  # P(E=1|C=1)
        (1 - wgts_be_g0),  # P(E=0|C=1)
        wgts_be_g0,  # P(E=1|C=0)
        (1 - wgts_be_g0),  # P(E=0|C=0)
    ]

    res = []
    for table in tables:
        ln_like_val_g1 = np.sum(
            (np.ones((len(w_ticks) ** 2, 1)) * np.array(table))
            * np.log(like_func_g1).T,
            axis=1,
        )
        ln_like_val_g0 = np.sum(
            (np.ones((len(w_ticks) ** 1, 1)) * np.array(table))
            * np.log(like_func_g0).T,
            axis=1,
        )

        alpha, beta = ssp_prams
        use_ssp = alpha != 0
        if use_ssp:
            ln_post_g1 = ln_like_val_g1 + np.log(
                ssp.g1_pdf(wgts_be_g1, wgts_ce_g1, alpha, beta, is_gene)
            )
            ln_post_g0 = ln_like_val_g0 + np.log(ssp.g0_pdf(wgts_be_g0, alpha, is_gene))
        else:
            ln_post_g1 = ln_like_val_g1
            ln_post_g0 = ln_like_val_g0

        like_val_g1 = np.mean(np.exp(ln_post_g1))
        like_val_g0 = np.mean(np.exp(ln_post_g0))
        logscore = np.log(like_val_g1) - np.log(like_val_g0)
        res.append(logscore)
    return res


def CS_structure_hlu(tables, is_gene, ssp_prams, intprecision=1.0e-8):
    # Hluの実装 (自動積分を使用)
    # 高速かつ正確なはず

    def post_g1(table, ssp_prams):
        alpha, beta = ssp_prams
        use_ssp = alpha != 0
        g1_z = ssp.g1_z(alpha, beta, is_gene)

        def integrand(wbe, wce):
            log_likes = (  # ln[P(D|w0,w1,Graph1)]
                np.log(
                    [
                        (1 - (1 - wce) * (1 - wbe)),  # P(E=1|C=1)
                        (1 - wce) * (1 - wbe),  # P(E=0|C=1)
                        wbe,  # P(E=1|C=0)
                        (1 - wbe),  # P(E=0|C=0)
                    ]
                    if is_gene
                    else [
                        wbe - (wce * wbe),  # P(E=1|C=1)
                        1 - (wbe - (wce * wbe)),  # P(E=0|C=1)
                        wbe,  # P(E=1|C=0)
                        1 - wbe,  # P(E=0|C=0)
                    ]
                )
                * table
            )
            log_prior = np.log(  # ln[P(w0,w1|Graph1)]
                ssp.g1_f(wbe, wce, alpha, beta, is_gene)
            ) - np.log(g1_z)
            if use_ssp:
                return np.exp(np.sum(log_likes) + log_prior)
            else:
                return np.exp(np.sum(log_likes))

        result, _ = integrate.dblquad(
            integrand, 0, 1, 0, 1, epsabs=intprecision, epsrel=intprecision
        )
        return result

    def post_g0(table, ssp_prams):
        alpha, _ = ssp_prams
        g0_z = ssp.g0_z(alpha, is_gene)
        use_ssp = alpha != 0

        def integrand(wbe):
            log_likes = (  # ln[P(D|w0,w1,Graph1)]
                np.log(
                    [
                        wbe,  # P(E=1|C=1)
                        (1 - wbe),  # P(E=0|C=1)
                        wbe,  # P(E=1|C=0)
                        (1 - wbe),  # P(E=0|C=0)
                    ]
                )
                * table
            )
            log_prior = np.log(  # ln[P(w0,w1|Graph1)]
                ssp.g0_f(wbe, alpha, is_gene)
            ) - np.log(g0_z)
            if use_ssp:
                return np.exp(np.sum(log_likes) + log_prior)
            else:
                return np.exp(np.sum(log_likes))

        result, _ = integrate.quad(
            integrand, 0, 1, epsabs=intprecision, epsrel=intprecision
        )
        return result

    res = []
    for table in tables:
        post_g1_v = post_g1(table, ssp_prams)
        post_g0_v = post_g0(table, ssp_prams)
        logscore = np.log(post_g1_v) - np.log(post_g0_v)
        res.append(logscore)
    return res


def CS_strength(tables, is_gene, ssp_prams, interval=0.05):
    alpha, beta = ssp_prams
    use_ssp = alpha != 0
    w_ticks = np.arange(interval, 1, interval)
    w0s, w1s = np.meshgrid(w_ticks, w_ticks)
    w0s = w0s.flatten()
    w1s = w1s.flatten()

    if is_gene:
        like_func_g1 = [
            (1 - (1 - w1s) * (1 - w0s)),  # P(E=1|C=1)
            (1 - w1s) * (1 - w0s),  # P(E=0|C=1)
            w0s,  # P(E=1|C=0)
            (1 - w0s),  # P(E=0|C=0)
        ]
    else:
        like_func_g1 = [
            w0s - (w1s * w0s),  # P(E=1|C=1)
            1 - (w0s - (w1s * w0s)),  # P(E=0|C=1)
            w0s,  # P(E=1|C=0)
            1 - w0s,  # P(E=0|C=0)
        ]

    res = []
    for table in tables:
        cpep, cpem, cmep, cmem = table
        ln_like_val_g1 = (
            np.log(math.comb(cmep + cmem, cmep))
            + np.log(math.comb(cpep + cpem, cpep))
            + np.sum(
                (np.ones((len(w_ticks) ** 2, 1)) * np.array(table))
                * np.log(like_func_g1).T,
                axis=1,
            )
        )
        if use_ssp:
            ln_prior = np.log(ssp.g1_pdf(w0s, w1s, alpha, beta, is_gene))
            post = np.exp(ln_like_val_g1 + ln_prior)
        else:
            post = np.exp(ln_like_val_g1)
        post = post / np.sum(post)
        post_merged_w0 = np.sum(post.reshape((len(w_ticks), len(w_ticks))), axis=1)
        wmean = np.sum(w_ticks * post_merged_w0)
        res.append(wmean)
    return res