# %%

import numpy as np
import prior_ss as ssp
import math
import importlib
from mod_common import joint_dist_to_cp
from scipy import integrate

importlib.reload(ssp)


def boltzmann_min(
    tables,
    is_gene,
    is_structure,
    threshold,
    f_vals,
    ssp_prams,
    cond_like,
):
    PRV, ABV = f_vals
    if is_gene:
        # The energy assigned to each of (cpep, cpem, cmep, cmem).
        energy_be = np.array([PRV, ABV, PRV, ABV])
        energy_ce = np.array([PRV, ABV, ABV, ABV])
    else:
        energy_be = np.array([ABV, PRV, ABV, PRV])
        energy_ce = np.array([ABV, PRV, ABV, ABV])

    energies_g0 = np.array([energy_be])
    energies_g1 = np.array([energy_be, energy_ce])

    if is_structure:
        return log_linear_structure_hlu_min(
            tables,
            is_gene,
            threshold,
            energies_g0,
            energies_g1,
            ssp_prams,
            cond_like,
        )
    else:
        return log_linear_strength_min(
            tables,
            is_gene,
            energies_g1,
            ssp_prams,
            cond_like,
        )


def ising_min(
    tables,
    is_gene,
    is_structure,
    threshold,
    f_vals,
    ssp_prams,
    cond_like,
):
    PRV, ABV = f_vals
    if is_gene:
        # The energy assigned to each of (cpep, cpem, cmep, cmem).
        energy_be = np.array([PRV, ABV, PRV, ABV])
        energy_ce = np.array([PRV, ABV, ABV, PRV])
    else:
        energy_be = np.array([ABV, PRV, ABV, PRV])
        energy_ce = np.array([ABV, PRV, PRV, ABV])

    energies_g0 = np.array([energy_be])
    energies_g1 = np.array([energy_be, energy_ce])

    if is_structure:
        return log_linear_structure_hlu_min(
            tables,
            is_gene,
            threshold,
            energies_g0,
            energies_g1,
            ssp_prams,
            cond_like,
        )
    else:
        return log_linear_strength_min(
            tables,
            is_gene,
            energies_g1,
            ssp_prams,
            cond_like,
        )


def log_linear_structure_hlu_min(
    tables,
    is_gene,
    threshold,
    energies_g0,
    energies_g1,
    ssp_prams,
    cond_like,
    intprecision=1.0e-8,
):
    # Hluの実装 (自動積分を使用)
    # wbe, wce のみをパラメタとするミニマルなモデル

    alpha, beta = ssp_prams
    use_ssp = alpha != 0

    def post_g1(table):
        g1_z = ssp.g1_z(alpha, beta, is_gene)
        energies = np.array(energies_g1).T  # (events, energies)

        def integrand(wbe, wce):
            weights = [wbe, wce]
            unnormed = np.exp(-np.dot(energies, weights))  # (events, 1)
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
        energies = np.array(energies_g0).T  # (events, energies)

        def integrand(wbe):
            weights = [wbe]  # (events, 1)
            unnormed = np.exp(-np.dot(energies, weights))  # (events, 1)
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


def log_linear_strength_min(
    tables,
    is_gene,
    energies_g1,
    ssp_prams,
    cond_like,
    interval=0.05,
):
    # wbe, wce のみをパラメタとするミニマルなモデル
    alpha, beta = ssp_prams
    use_ssp = alpha != 0
    w_ticks = np.arange(interval, 1, interval)
    wbes, wces = np.meshgrid(w_ticks, w_ticks)
    wbes, wces = [w.flatten() for w in [wbes, wces]]

    ##### energies_g (energies, events) の定義は Wrapper で行う #####
    weights_g1 = np.array([wbes, wces])  # (w_kinds, ticks)
    energies_g1 = np.array(energies_g1).T  #  convert to (event_kinds, energies)

    res = []
    for table in tables:
        cpep, cpem, cmep, cmem = table
        unnormed_g1 = np.exp(-np.dot(energies_g1, weights_g1))  # (event_kinds, loop_n)
        prob_dist_g1 = unnormed_g1 / unnormed_g1.sum(axis=0)
        like_func_g1 = joint_dist_to_cp(prob_dist_g1) if cond_like else prob_dist_g1

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
            ln_prior = np.log(ssp.g1_pdf(wbes, wces, alpha, beta, is_gene))
            post = np.exp(ln_like_val_g1 + ln_prior)
        else:
            post = np.exp(ln_like_val_g1)
        post = post / np.sum(post)
        post_merged_w0 = np.sum(post.reshape((len(w_ticks), len(w_ticks))), axis=1)
        wmean = np.sum(w_ticks * post_merged_w0)
        res.append(wmean)
    return res