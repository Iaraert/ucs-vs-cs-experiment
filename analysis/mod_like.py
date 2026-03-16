# %%

import numpy as np
import prior_ss as ssp
import importlib
from mod_common import energy_to_prob, joint_dist_to_cp
import math

importlib.reload(ssp)


def boltzmann_like(
    tables,
    is_gene,
    is_structure,
    threshold,
    ign_fe,
    ssp_prams,
    cond_like,
    swap_fe,
):
    if is_gene:
        # f_. = [φ(cp, ep), φ(cp, em), φ(cm, ep), φ(cm, em)]
        def get_fc(w):
            return [-w, -w, -(1 - w), -(1 - w)]

        def get_fe(w):
            return [-w, -(1 - w), -w, -(1 - w)]

        def get_fbe(w):
            return [-w, -(1 - w), -w, -(1 - w)]

        def get_fce(w):
            return [-w, -(1 - w), -(1 - w), -(1 - w)]
    else:
        # f_. = [φ(cp, em), φ(cp, ep), φ(cm, em), φ(cm, ep)]
        def get_fc(w):
            return [-w, -w, -(1 - w), -(1 - w)]

        def get_fe(w):
            return [-w, -(1 - w), -w, -(1 - w)]

        def get_fbe(w):
            return [-(1 - w), -w, -(1 - w), -w]

        if swap_fe:
            get_fe = get_fbe

        def get_fce(w):
            return [-(1 - w), -w, -(1 - w), -(1 - w)]

    def ignored_f(w):
        return [0 * w, 0 * w, 0 * w, 0 * w]

    if ign_fe:
        get_fe = ignored_f

    get_fs = [get_fc, get_fe, get_fbe, get_fce]

    if is_structure:
        return inner_w_structure_grif(
            tables, is_gene, threshold, ssp_prams, cond_like, get_fs
        )
    else:
        return inner_w_strength(tables, is_gene, ssp_prams, cond_like, get_fs)


def ising_like(
    tables,
    is_gene,
    is_structure,
    threshold,
    ign_fe,
    ssp_prams,
    cond_like,
    swap_fe,
):
    if is_gene:
        # f_. = [φ(cp, ep), φ(cp, em), φ(cm, ep), φ(cm, em)]

        def get_fc(w):
            return [-w, -w, -(1 - w), -(1 - w)]

        def get_fe(w):
            return [-w, -(1 - w), -w, -(1 - w)]

        def get_fbe(w):
            return [-w, -(1 - w), -w, -(1 - w)]

        def get_fce(w):
            return [-w, -(1 - w), -(1 - w), -w]
    else:
        # f_. = [φ(cp, em), φ(cp, ep), φ(cm, em), φ(cm, ep)]

        def get_fc(w):
            return [-w, -w, -(1 - w), -(1 - w)]

        def get_fe(w):
            return [-(1 - w), -w, -(1 - w), -w]

        def get_fbe(w):
            return [-(1 - w), -w, -(1 - w), -w]

        if swap_fe:
            get_fe = get_fbe

        def get_fce(w):
            return [-(1 - w), -w, -w, -(1 - w)]

    def ignored_f(w):
        return [0 * w, 0 * w, 0 * w, 0 * w]

    if ign_fe:
        get_fe = ignored_f

    get_fs = [get_fc, get_fe, get_fbe, get_fce]

    if is_structure:
        return inner_w_structure_grif(
            tables, is_gene, threshold, ssp_prams, cond_like, get_fs
        )
    else:
        return inner_w_strength(tables, is_gene, ssp_prams, cond_like, get_fs)


def inner_w_structure_grif(
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
    node_wgts = (
        rng.uniform(0, threshold, size=(loop_n, 3))
        if threshold == 1
        else ssp.truncated_exponential(1 / threshold, size=(loop_n, 3))
    )
    wc = node_wgts[:, 1]
    we = node_wgts[:, 2]

    get_fc, get_fe, get_fbe, get_fce = get_fs
    fc = get_fc(wc)
    fe = get_fe(we)
    fbe_g0 = get_fbe(wbe_g0)
    fbe_g1 = get_fbe(wbe_g1)
    fce_g1 = get_fce(wce_g1)
    # f. = [φ(cp, ep), φ(cp, em), φ(cm, ep), φ(cm, em)]

    # G0, G1 に共通の factors
    common_fs = [fc, fe]

    # G0 の factors から尤度関数を定義
    f_g0 = common_fs.copy()
    f_g0.append(fbe_g0)  # (f, event, rand)
    f_g0 = np.array(f_g0).transpose(1, 0, 2)  # (event, f, rand)
    prob_dist_g0 = energy_to_prob(f_g0)
    like_func_g0 = joint_dist_to_cp(prob_dist_g0) if cond_like else prob_dist_g0

    # G1 の factors から尤度関数を定義
    f_g1 = common_fs.copy()
    f_g1.append(fbe_g1)
    f_g1.append(fce_g1)  # (f, event, rand)
    f_g1 = np.array(f_g1).transpose(1, 0, 2)  # (event, f, rand)
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


def inner_w_strength(
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
    wcs, wes, wbes, wces = np.meshgrid(
        w_ticks,
        w_ticks,
        w_ticks,
        w_ticks,
    )
    wcs, wes, wbes, wces = [w.flatten() for w in [wcs, wes, wbes, wces]]

    get_fc, get_fe, get_fbe, get_fce = get_fs
    fc = get_fc(wcs)
    fe = get_fe(wes)
    fbe = get_fbe(wbes)
    fce = get_fce(wces)
    # f. = [φ(cp, ep), φ(cp, em), φ(cm, ep), φ(cm, em)]

    # G1 の factors から尤度関数を定義
    f_g1 = [fc, fe, fbe, fce]
    f_g1 = np.array(f_g1).transpose(1, 0, 2)
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
        post_merged_w0 = post.reshape(
            (
                len(w_ticks),
                len(w_ticks),
                len(w_ticks),
                len(w_ticks),
            )
        ).sum(axis=(0, 1, 2))
        wmean = np.sum(w_ticks * post_merged_w0)
        res.append(wmean)
    return res


# %%