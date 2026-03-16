import numpy as np


def energy_to_prob(energies):
    # energies.shape is (events, nodes/edges, loop_n)
    sum_energies = np.exp(-1 * np.sum(energies, axis=1))  # == prod_factor
    normalization_const = sum_energies.sum(axis=0)
    pr_cont = sum_energies / normalization_const
    return pr_cont


def joint_dist_to_cp(pr_cont):
    prob_a_cell, pr_b_cell, pr_c_cell, prob_d_cell = pr_cont
    pr_cause = prob_a_cell + pr_b_cell
    return np.array(
        [
            prob_a_cell / pr_cause,  # P(E=1|C=1)
            pr_b_cell / pr_cause,  # P(E=0|C=1)
            pr_c_cell / (1 - pr_cause),  # P(E=1|C=0)
            prob_d_cell / (1 - pr_cause),  # P(E=0|C=0)
        ]
    )


def noisy_or(p, q):
    return 1 - (1 - p) * (1 - q)


def noisy_and_not(p, q):
    return p * (1 - q)


def paris(p0, p1, joint):
    retval = joint / (p0 + p1 - joint)
    return retval


def dfh(p0, p1, joint):
    retval = np.sqrt(joint / p0 * joint / p1)
    return retval
