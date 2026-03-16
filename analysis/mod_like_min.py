# %%

import numpy as np
import prior_ss as ssp
import importlib
from mod_common import energy_to_prob, joint_dist_to_cp
import math
from scipy import integrate

importlib.reload(ssp)


def boltzmann_like_min(
    tables,
    is_gene,
    is_structure,
    threshold,
    ssp_prams,
    cond_like,
):
    if is_gene:
        # f_. = [φ(cp, ep), φ(cp, em), φ(cm, ep), φ(cm, em)]
        def get_fbe(w):
            return [-w, -(1 - w), -w, -(1 - w)]

        def get_fce(w):
            return [-w, -(1 - w), -(1 - w), -(1 - w)]
    else:
        # f_. = [φ(cp, em), φ(cp, ep), φ(cm, em), φ(cm, ep)]
        def get_fbe(w):
            return [-(1 - w), -w, -(1 - w), -w]

        def get_fce(w):
            return [-(1 - w), -w, -(1 - w), -(1 - w)]

    get_fs = [get_fbe, get_fce]

    if is_structure:
        return log_linear_structure_hlu_min(
            tables, is_gene, threshold, ssp_prams, cond_like, get_fs
        )
    else:
        return inner_w_strength_min(tables, is_gene, ssp_prams, cond_like, get_fs)


def ising_like_min(
    tables,
    is_gene,
    is_structure,
    threshold,
    ssp_prams,
    cond_like,
):
    if is_gene:
        # f_. = [φ(cp, ep), φ(cp, em), φ(cm, ep), φ(cm, em)]
        def get_fbe(w):
            return [-w, -(1 - w), -w, -(1 - w)]

        def get_fce(w):
            return [-w, -(1 - w), -(1 - w), -w]
    else:
        # f_. = [φ(cp, em), φ(cp, ep), φ(cm, em), φ(cm, ep)]
        def get_fbe(w):
            return [-(1 - w), -w, -(1 - w), -w]

        def get_fce(w):
            return [-(1 - w), -w, -w, -(1 - w)]

    get_fs = [get_fbe, get_fce]

    if is_structure:
        return log_linear_structure_hlu_min(
            tables, is_gene, threshold, ssp_prams, cond_like, get_fs
        )
    else:
        return inner_w_strength_min(tables, is_gene, ssp_prams, cond_like, get_fs)


def log_linear_structure_hlu_min(
    tables,
    is_gene,
    threshold,
    ssp_prams,
    cond_like,
    get_fs,
    intprecision=1.0e-8,
):
    # Hluの実装 (自動積分を使用)
    # wbe, wce のみをパラメタとするミニマルなモデル

    alpha, beta = ssp_prams
    use_ssp = alpha != 0

    get_fbe, get_fce = get_fs

    def post_g1(table):
        g1_z = ssp.g1_z(alpha, beta, is_gene)

        def integrand(wbe, wce):
            energies = np.array([get_fbe(wbe), get_fce(wce)]).T  # (events, energies)
            unnormed = np.exp(-1 * np.sum(energies, axis=1))
            prob_dist = unnormed / unnormed.sum(axis=0)  # (events, 1)

            # 同時確率を条件付き確率に変換
            if cond_like:
                like_func = joint_dist_to_cp(prob_dist)
            else:
                like_func = prob_dist

            # eval ln[P(D|w0,w1,Graph1)]
            log_like_val = np.log(like_func) * table
            # eval ln[P(w0,w1|Graph1)]
            log_prior = np.log(ssp.g1_f(wbe, wce, alpha, beta, is_gene)) - np.log(g1_z)
            # eval ln[P(D,w0,w1|Graph1)]
            if use_ssp:
                return np.exp(np.sum(log_like_val) + log_prior)
            else:
                return np.exp(np.sum(log_like_val))

        result, _ = integrate.dblquad(
            integrand, 0, 1, 0, 1, epsabs=intprecision, epsrel=intprecision
        )
        return result

    def post_g0(table):
        g0_z = ssp.g0_z(alpha, is_gene)

        def integrand(wbe):
            energies = np.array([get_fbe(wbe)]).T  # (events, energies)
            unnormed = np.exp(-1 * np.sum(energies, axis=1))
            prob_dist = unnormed / unnormed.sum(axis=0)  # (events, 1)

            # 同時確率を条件付き確率に変換
            if cond_like:
                like_func = joint_dist_to_cp(prob_dist)
            else:
                like_func = prob_dist

            # eval ln[P(D|w0,w1,Graph1)]
            log_like_val = np.log(like_func) * table
            # eval ln[P(w0,w1|Graph1)]
            log_prior = np.log(ssp.g0_f(wbe, alpha, is_gene)) - np.log(g0_z)
            # eval ln[P(D,w0,w1|Graph1)]
            if use_ssp:
                return np.exp(np.sum(log_like_val) + log_prior)
            else:
                return np.exp(np.sum(log_like_val))

        result, _ = integrate.quad(
            integrand, 0, 1, epsabs=intprecision, epsrel=intprecision
        )
        return result

    res = []
    for table in tables:
        post_g1_v = post_g1(table)
        post_g0_v = post_g0(table)
        logscore = np.log(post_g1_v) - np.log(post_g0_v)
        res.append(logscore)
    return res


def inner_w_structure_grif_min(
    tables,
    is_gene,
    threshold,
    ssp_prams,
    cond_like,
    get_fs,
    # loop_n=int(1e7),
    loop_n=int(1e5), # debug
):
    # griffiths and tenenbaum の実装の再現
    # Prior に従う w を大量にサンプリングして近似する
    # スペックに応じて引数のデフォルト値 loop_n を調整すること
    alpha, beta = ssp_prams
    use_ssp = alpha != 0
    rng = np.random.default_rng()
    edge_w_g0 = (
        ssp.g0_rejection_sampling_by_f(loop_n, alpha, is_gene)
        if use_ssp
        else rng.uniform(0, 1, size=(loop_n, 1))
    )
    edge_w_g1 = (
        ssp.g1_rejection_sampling_by_f(loop_n, alpha, beta, is_gene)
        if use_ssp
        else rng.uniform(0, 1, size=(loop_n, 2))
    )
    wbe_g0 = edge_w_g0[:, 0]
    wbe_g1 = edge_w_g1[:, 0]
    wce_g1 = edge_w_g1[:, 1]

    get_fbe, get_fce = get_fs
    fbe_g0 = get_fbe(wbe_g0)
    fbe_g1 = get_fbe(wbe_g1)
    fce_g1 = get_fce(wce_g1)
    # f. = [φ(cp, ep), φ(cp, em), φ(cm, ep), φ(cm, em)]

    # G0 の factors から尤度関数を定義
    f_g0 = [fbe_g0]
    f_g0 = -1 * np.array(f_g0).transpose(1, 0, 2)
    prob_dist_g0 = energy_to_prob(f_g0)
    like_func_g0 = joint_dist_to_cp(prob_dist_g0) if cond_like else prob_dist_g0

    # G1 の factors から尤度関数を定義
    f_g1 = [fbe_g1, fce_g1]
    f_g1 = -1 * np.array(f_g1).transpose(1, 0, 2)
    prob_dist_g1 = energy_to_prob(f_g1)
    like_func_g1 = joint_dist_to_cp(prob_dist_g1) if cond_like else prob_dist_g1

    res = []
    for table in tables:
        ln_like_val_g1 = np.sum(
            (np.ones((loop_n, 1)) * np.array(table)) * np.log(like_func_g1).T, axis=1
        )
        ln_like_val_g0 = np.sum(
            (np.ones((loop_n, 1)) * np.array(table)) * np.log(like_func_g0).T, axis=1
        )
        like_val_g1 = np.mean(np.exp(ln_like_val_g1))
        like_val_g0 = np.mean(np.exp(ln_like_val_g0))
        logscore = np.log(like_val_g1) - np.log(like_val_g0)
        res.append(logscore)
    return res


def inner_w_strength_min(
    tables,
    is_gene,
    ssp_prams,
    cond_like,
    get_fs,
    interval=0.05,
):
    alpha, beta = ssp_prams
    use_ssp = alpha != 0
    w_ticks = np.arange(interval, 1, interval)
    wbes, wces = np.meshgrid(w_ticks, w_ticks)
    wbes, wces = [w.flatten() for w in [wbes, wces]]

    get_fbe, get_fce = get_fs
    fbe = get_fbe(wbes)
    fce = get_fce(wces)
    # f. = [φ(cp, ep), φ(cp, em), φ(cm, ep), φ(cm, em)]

    # G1 の factors から尤度関数を定義
    f_g1 = [fbe, fce]
    f_g1 = -1 * np.array(f_g1).transpose(1, 0, 2)
    prob_dist_g1 = energy_to_prob(f_g1)
    like_func_g1 = joint_dist_to_cp(prob_dist_g1) if cond_like else prob_dist_g1

    res = []
    for table in tables:
        cpep, cpem, cmep, cmem = table
        ln_like_val_g1 = (
            np.log(math.comb(cmep + cmem, cmep))
            + np.log(math.comb(cpep + cpem, cpep))
            + np.sum(
                (np.ones((len(wces), 1)) * np.array(table)) * np.log(like_func_g1).T,
                axis=1,
            )
        )
        if use_ssp:
            ln_prior = np.log(ssp.g1_pdf(wbes, wces, alpha, beta, is_gene))
            post = np.exp(ln_like_val_g1 + ln_prior)
        else:
            post = np.exp(ln_like_val_g1)
        post = post / np.sum(post)
        post_merged_w0 = post.reshape((len(w_ticks), len(w_ticks))).sum(axis=(0,))
        wmean = np.sum(w_ticks * post_merged_w0)
        res.append(wmean)
    return res