# %%

import numpy as np
import prior_ss as ssp
import math
import importlib
from mod_common import joint_dist_to_cp

importlib.reload(ssp)


def log_linear_structure_wow(
    tables,
    is_gene,
    ign_dcell,
    energies_g0,
    energies_g1,
    absent_val,
):
    def eval_ln_like_val(energies_g):
        if absent_val != 0:
            energies_g = np.where(energies_g == 0, absent_val, energies_g)
        if ign_dcell:
            if is_gene:
                energies_g[:, 3] = 0  # dセルは一定に単位元にする
            else:
                energies_g[:, 2] = 0
        energies_g = np.array(energies_g).T  #  convert to (events, energies)
        # exp(sum f_i) を計算するため，イベントごとにエネルギーを合計してから指数を取る
        summed_energy = np.sum(energies_g, axis=1, keepdims=True)
        unnormed_g = np.exp(-summed_energy)  # (events, loop_n)
        prob_dist_g = unnormed_g / unnormed_g.sum(axis=0, keepdims=True)
        like_func_g = joint_dist_to_cp(prob_dist_g)
        ln_like_val_g = np.sum((np.array(table)) * np.log(like_func_g).T, axis=1)
        return ln_like_val_g

    res = []
    for table in tables:
        ln_like_val_g0 = eval_ln_like_val(energies_g0)
        ln_like_val_g1 = eval_ln_like_val(energies_g1)

        like_val_g1 = sum(np.exp(ln_like_val_g1))
        like_val_g0 = sum(np.exp(ln_like_val_g0))
        logscore = np.log(like_val_g1) - np.log(like_val_g0)
        res.append(logscore)
    return res


def log_linear_strength_wow(
    tables,
    is_gene,
    ign_dcell,
    energies_g0,
    energies_g1,
    absent_val,
):
    def eval_ln_like_val(energies_g):
        if absent_val != 0:
            energies_g = np.where(energies_g == 0, absent_val, energies_g)
        if ign_dcell:
            if is_gene:
                energies_g[:, 3] = 0  # dセルは一定に単位元にする
            else:
                energies_g[:, 2] = 0
        energies_g = np.array(energies_g).T  #  convert to (events, energies)
        # exp(sum f_i) を計算するため，イベントごとにエネルギーを合計してから指数を取る
        summed_energy = np.sum(energies_g, axis=1, keepdims=True)
        unnormed_g = np.exp(-summed_energy)  # (events, loop_n)
        prob_dist_g = unnormed_g / unnormed_g.sum(axis=0, keepdims=True)
        like_func_g = joint_dist_to_cp(prob_dist_g)
        ln_like_val_g = np.sum((np.array(table)) * np.log(like_func_g).T, axis=1)
        return ln_like_val_g

    res = []
    for table in tables:
        ln_like_val_g0 = eval_ln_like_val(energies_g0)
        ln_like_val_g1 = eval_ln_like_val(energies_g1)

        like_val_g1 = sum(np.exp(ln_like_val_g1))
        like_val_g0 = sum(np.exp(ln_like_val_g0))
        logscore = np.log(like_val_g1) - np.log(like_val_g0)
        res.append(logscore)
    return res


def ising_wow(
    tables,
    is_gene,
    ign_dcell,
    ign_fe,
    absent_val,
):
    if is_gene:
        # The energy assigned to each of (cpep, cpem, cmep, cmem).
        energy_c = np.array([-1, -1, 0, 0])
        energy_e = np.array([-1, 0, -1, 0])
        energy_be = np.array([-1, 0, -1, 0])
        energy_ce = np.array([-1, 0, 0, -1])
    else:
        energy_c = np.array([-1, -1, 0, 0])
        energy_e = np.array([0, -1, 0, -1])
        energy_be = np.array([0, -1, 0, -1])
        energy_ce = np.array([0, -1, -1, 0])

    energies_g0 = [energy_c, energy_be]
    energies_g1 = [energy_c, energy_be, energy_ce]
    if not ign_fe:
        energies_g0.append(energy_e)
        energies_g1.append(energy_e)
    energies_g0 = np.array(energies_g0)
    energies_g1 = np.array(energies_g1)

    return log_linear_structure_wow(
        tables,
        is_gene,
        ign_dcell,
        energies_g0,
        energies_g1,
        absent_val,
    )


def boltzmann_wow(
    tables,
    is_gene,
    ign_dcell,
    ign_fe,
    absent_val,
):
    if is_gene:
        # The energy assigned to each of (cpep, cpem, cmep, cmem).
        energy_c = np.array([-1, -1, 0, 0])
        energy_e = np.array([-1, 0, -1, 0])
        energy_be = np.array([-1, 0, -1, 0])
        energy_ce = np.array([-1, 0, 0, 0])
    else:
        energy_c = np.array([-1, -1, 0, 0])
        energy_e = np.array([0, -1, 0, -1])
        energy_be = np.array([0, -1, 0, -1])
        energy_ce = np.array([0, -1, 0, 0])

    energies_g0 = [energy_c, energy_be]
    energies_g1 = [energy_c, energy_be, energy_ce]
    if not ign_fe:
        energies_g0.append(energy_e)
        energies_g1.append(energy_e)
    energies_g0 = np.array(energies_g0)
    energies_g1 = np.array(energies_g1)

    return log_linear_structure_wow(
        tables,
        is_gene,
        ign_dcell,
        energies_g0,
        energies_g1,
        absent_val,
    )


def pure_ising_gsw(
    tables,
    is_gene,
    ign_dcell,
    ign_fe,
    absent_val,
    wc,
    we,
    wbe,
    wce,
):
    if is_gene:
        # The energy assigned to each of (cpep, cpem, cmep, cmem).
        energy_c = np.array([-1, -1, -1, -1]) * wc
        energy_e = np.array([-1, -1, -1, -1]) * we
        energy_be = np.array([-1, 0, -1, 0]) * wbe
        energy_ce = np.array([-1, 0, 0, -1]) * wce
    else:
        energy_c = np.array([-1, -1, -1, -1]) * wc
        energy_e = np.array([-1, -1, -1, -1]) * we
        energy_be = np.array([0, -1, 0, -1]) * wbe
        energy_ce = np.array([0, -1, -1, 0]) * wce

    energies_g0 = [energy_c, energy_be]
    energies_g1 = [energy_c, energy_be, energy_ce]
    if not ign_fe:
        energies_g0.append(energy_e)
        energies_g1.append(energy_e)
    energies_g0 = np.array(energies_g0)
    energies_g1 = np.array(energies_g1)

    return log_linear_structure_wow(
        tables,
        is_gene,
        ign_dcell,
        energies_g0,
        energies_g1,
        absent_val,
    )


def ising_gsw(
    tables,
    is_gene,
    ign_dcell,
    ign_fe,
    absent_val,
    wc,
    we,
    wbe,
    wce,
):
    if is_gene:
        # The energy assigned to each of (cpep, cpem, cmep, cmem).
        energy_c = np.array([-1, -1, 0, 0]) * wc
        energy_e = np.array([-1, 0, -1, 0]) * we
        energy_be = np.array([-1, 0, -1, 0]) * wbe
        energy_ce = np.array([-1, 0, 0, -1]) * wce
    else:
        energy_c = np.array([-1, -1, 0, 0]) * wc
        energy_e = np.array([-1, 0, -1, 0]) * we
        energy_be = np.array([0, -1, 0, -1]) * wbe
        energy_ce = np.array([0, -1, -1, 0]) * wce

    energies_g0 = [energy_c, energy_be]
    energies_g1 = [energy_c, energy_be, energy_ce]
    if not ign_fe:
        energies_g0.append(energy_e)
        energies_g1.append(energy_e)
    energies_g0 = np.array(energies_g0)
    energies_g1 = np.array(energies_g1)

    return log_linear_structure_wow(
        tables,
        is_gene,
        ign_dcell,
        energies_g0,
        energies_g1,
        absent_val,
    )


def boltzmann_gsw(
    tables,
    is_gene,
    ign_dcell,
    ign_fe,
    absent_val,
    wc,
    we,
    wbe,
    wce,
):
    if is_gene:
        # The energy assigned to each of (cpep, cpem, cmep, cmem).
        energy_c = np.array([-1, -1, 0, 0]) * wc
        energy_e = np.array([-1, 0, -1, 0]) * we
        energy_be = np.array([-1, 0, -1, 0]) * wbe
        energy_ce = np.array([-1, 0, 0, 0]) * wce
    else:
        energy_c = np.array([-1, -1, 0, 0]) * wc
        energy_e = np.array([-1, 0, -1, 0]) * we
        energy_be = np.array([0, -1, 0, -1]) * wbe
        energy_ce = np.array([0, -1, 0, 0]) * wce

    energies_g0 = [energy_c, energy_be]
    energies_g1 = [energy_c, energy_be, energy_ce]
    if not ign_fe:
        energies_g0.append(energy_e)
        energies_g1.append(energy_e)
    energies_g0 = np.array(energies_g0)
    energies_g1 = np.array(energies_g1)

    return log_linear_structure_wow(
        tables,
        is_gene,
        ign_dcell,
        energies_g0,
        energies_g1,
        absent_val,
    )


# %%
