# %%

import numpy as np
import prior_ss as ssp
import math
import importlib
from mod_common import joint_dist_to_cp
import math
from scipy import integrate

importlib.reload(ssp)


def ising(
    tables,
    is_gene,
    is_structure,
    threshold,
    ign_fe,
    f_vals,
    ssp_prams,
    cond_like,
    swap_fe,
):
    PRV, ABV = f_vals
    if is_gene:
        # The energy assigned to each of (cpep, cpem, cmep, cmem).
        energy_c = np.array([PRV, PRV, ABV, ABV])
        energy_e = np.array([PRV, ABV, PRV, ABV])
        energy_be = np.array([PRV, ABV, PRV, ABV])
        energy_ce = np.array([PRV, ABV, ABV, PRV])
    else:
        energy_c = np.array([PRV, PRV, ABV, ABV])
        energy_e = np.array([PRV, ABV, PRV, ABV])
        energy_be = np.array([ABV, PRV, ABV, PRV])
        if swap_fe:
            energy_e = energy_be
        energy_ce = np.array([ABV, PRV, PRV, ABV])

    if ign_fe:
        energy_e = np.array([ABV, ABV, ABV, ABV])

    energies_g0 = np.array([energy_c, energy_e, energy_be])
    energies_g1 = np.array([energy_c, energy_e, energy_be, energy_ce])

    if is_structure:
        return log_linear_structure_grif(
            tables,
            is_gene,
            threshold,
            energies_g0,
            energies_g1,
            ssp_prams,
            cond_like,
        )
    else:
        return log_linear_strength(
            tables,
            is_gene,
            energies_g1,
            ssp_prams,
            cond_like,
        )


def boltzmann(
    tables,
    is_gene,
    is_structure,
    threshold,
    ign_fe,
    f_vals,
    ssp_prams,
    cond_like,
    swap_fe,
):
    PRV, ABV = f_vals
    if is_gene:
        # The energy assigned to each of (cpep, cpem, cmep, cmem).
        energy_c = np.array([PRV, PRV, ABV, ABV])
        energy_e = np.array([PRV, ABV, PRV, ABV])
        energy_be = np.array([PRV, ABV, PRV, ABV])
        energy_ce = np.array([PRV, ABV, ABV, ABV])
    else:
        energy_c = np.array([PRV, PRV, ABV, ABV])
        energy_e = np.array([PRV, ABV, PRV, ABV])
        energy_be = np.array([ABV, PRV, ABV, PRV])
        if swap_fe:
            energy_e = energy_be
        energy_ce = np.array([ABV, PRV, ABV, ABV])

    if ign_fe:
        energy_e = np.array([ABV, ABV, ABV, ABV])

    energies_g0 = np.array([energy_c, energy_e, energy_be])
    energies_g1 = np.array([energy_c, energy_e, energy_be, energy_ce])

    if is_structure:
        return log_linear_structure_grif(
            tables,
            is_gene,
            threshold,
            energies_g0,
            energies_g1,
            ssp_prams,
            cond_like,
        )
    else:
        return log_linear_strength(
            tables,
            is_gene,
            energies_g1,
            ssp_prams,
            cond_like,
        )


def log_linear_structure_grif(
    tables,
    is_gene,
    threshold,
    energies_g0,
    energies_g1,
    ssp_prams,
    cond_like,
    loop_n=int(1e5),
):
    # griffiths and tenenbaum の実装の再現
    # Prior に従う w を大量にサンプリングして近似する
    # スペックに応じて引数のデフォルト値 loop_n を調整すること
    alpha, beta = ssp_prams
    use_ssp = alpha != 0
    rng = np.random.default_rng()
    edge_wgts_g0 = (
        ssp.g0_rejection_sampling_by_f(loop_n, alpha, is_gene)
        if use_ssp
        else rng.uniform(0, 1, size=(loop_n, 1))
    )
    edge_wgts_g1 = (
        ssp.g1_rejection_sampling_by_f(loop_n, alpha, beta, is_gene)
        if use_ssp
        else rng.uniform(0, 1, size=(loop_n, 2))
    )
    wgts_be_g0 = edge_wgts_g0[:, 0]
    wgts_be_g1 = edge_wgts_g1[:, 0]
    wgts_ce_g1 = edge_wgts_g1[:, 1]
    node_wgts = (
        rng.uniform(0, threshold, size=(loop_n, 3))
        if threshold == 1
        else ssp.truncated_exponential(1 / threshold, size=(loop_n, 3))
    )
    # TODO: likeのようなappend型にする
    wgts_c = node_wgts[:, 1]
    wgts_e = node_wgts[:, 2]

    ##### energies_g (energies, events) の定義は Wrapper で行う #####
    weights_g0 = np.array([wgts_c, wgts_e, wgts_be_g0])  # (wghs, loop_n)
    weights_g1 = np.array([wgts_c, wgts_e, wgts_be_g1, wgts_ce_g1])  # (wgts, loop_n)

    def eval_ln_like_val(energies_g, weights_g):
        energies_g = np.array(energies_g).T  #  convert to (events, energies)
        unnormed_g = np.exp(-np.dot(energies_g, weights_g))  # (events, loop_n)
        prob_dist_g = unnormed_g / unnormed_g.sum(axis=0)
        like_func_g = joint_dist_to_cp(prob_dist_g) if cond_like else prob_dist_g
        ln_like_val_g = np.sum(
            (np.ones((loop_n, 1)) * np.array(table)) * np.log(like_func_g).T, axis=1
        )
        return ln_like_val_g

    res = []
    for table in tables:
        ln_like_val_g0 = eval_ln_like_val(energies_g0, weights_g0)
        ln_like_val_g1 = eval_ln_like_val(energies_g1, weights_g1)

        like_val_g1 = np.mean(np.exp(ln_like_val_g1))
        like_val_g0 = np.mean(np.exp(ln_like_val_g0))
        logscore = np.log(like_val_g1) - np.log(like_val_g0)
        res.append(logscore)

    return res


def log_linear_structure_hlu(
    tables,
    is_gene,
    threshold,
    energies_g0,
    energies_g1,
    ssp_prams,
    cond_like,
):
    # Hluの実装 (自動積分を使用)
    # 多重積分が重すぎてまともに動作しない

    alpha, beta = ssp_prams
    use_ssp = alpha != 0

    def post_g1(table):
        g1_z = ssp.g1_z(alpha, beta, is_gene)
        energies = np.array(energies_g1).T  # (events, energies)

        def integrand(wc, we, wbe, wce):
            weights = [wc, we, wbe, wce]
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

        ranges = [(0, 1), (0, 1), (0, 1), (0, 1)]
        result, _ = integrate.nquad(integrand, ranges)
        return result

    def post_g0(table):
        g0_z = ssp.g0_z(alpha, is_gene)
        energies = np.array(energies_g0).T  # (events, energies)

        def integrand(wc, we, wbe):
            weights = [wc, we, wbe]
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

        ranges = [(0, 1), (0, 1), (0, 1)]
        result, _ = integrate.nquad(integrand, ranges)
        return result

    res = []
    for table in tables:
        post_g1_v = post_g1(table)
        post_g0_v = post_g0(table)
        logscore = np.log(post_g1_v) - np.log(post_g0_v)
        res.append(logscore)
    return res


def log_linear_strength(
    tables,
    is_gene,
    energies_g1,
    ssp_prams,
    cond_like,
    interval=0.05,
):
    alpha, beta = ssp_prams
    use_ssp = alpha != 0
    w_ticks = np.arange(interval, 1, interval)
    wcs, wes, wbes, wces = np.meshgrid(
        w_ticks,
        w_ticks,
        w_ticks,
        w_ticks,
    )
    wcs, wes, wbes, wces = [w.flatten() for w in [wcs, wes, wbes, wces]]

    ##### energies_g (energies, events) の定義は Wrapper で行う #####
    weights_g1 = np.array([wcs, wes, wbes, wces])  # (w_kinds, ticks)
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
                (np.ones((len(w_ticks) ** len(weights_g1), 1)) * np.array(table))
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
        post_merged_w0 = post.reshape(
            (
                len(w_ticks),
                len(w_ticks),
                len(w_ticks),
                len(w_ticks),
            )
        ).sum(axis=(0, 1, 2))
        wmean = np.dot(w_ticks, post_merged_w0)
        res.append(wmean)
    return res

# %%