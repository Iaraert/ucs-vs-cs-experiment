import numpy as np

# ループ回数
loop_count = 10000

def UCS(conts, threshold, is_gene, loops=loop_count):
    rng = np.random.default_rng()  # 乱数ジェネレーター
    power = np.zeros((loops, 3))

    # ループを実行して条件を満たす乱数を生成
    for i in range(loops):
      power0 = rng.uniform(0, 1)
      power1 = rng.uniform(0+1e-100, threshold)
      power2 = rng.uniform(0+1e-100, threshold)
      # power1 = threshold
      # power2 = threshold
      power[i] = [power0,power1,power2]
    a, b, c, d = conts
    # power[:, 0] 原因と結果のw
    # power[:, 1] 背景と原因のw
    # power[:, 2] 背景と結果のw
    if is_gene:
      # z = /(np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2]))) + np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2])))) + np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1])))) + (1 - power[:, 1]) * (1 - power[:, 2]))
      probs1 = [
          np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2])))/(np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2]))) + np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2])))) + np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1])))) + (1 - power[:, 1]) * (1 - power[:, 2])),
          np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2]))))/(np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2]))) + np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2])))) + np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1])))) + (1 - power[:, 1]) * (1 - power[:, 2])),
          np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1]))))/(np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2]))) + np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2])))) + np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1])))) + (1 - power[:, 1]) * (1 - power[:, 2])),
          (1 - power[:, 1]) * (1 - power[:, 2])/(np.sqrt(power[:, 1] * power[:, 2] * (1 - (1 - power[:, 0]) * (1 - power[:, 1])) * (1 - (1 - power[:, 0]) * (1 - power[:, 2]))) + np.sqrt(power[:, 1] * (1 - power[:, 2]) * (power[:, 1] * ((1 - power[:, 0]) * (1 - power[:, 2])))) + np.sqrt((1 - power[:, 1]) * power[:, 2] * (power[:, 2] * ((1 - power[:, 0]) * (1 - power[:, 1])))) + (1 - power[:, 1]) * (1 - power[:, 2])),
      ]
    else:
      # z = / (np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0])))) + np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0]))))) + np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2])) + (1 - power[:, 1]) * (1 - power[:, 2]))
      probs1 = [
          np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0]))))  / (np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0])))) + np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0]))))) + np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2])) + (1 - power[:, 1]) * (1 - power[:, 2])),
          np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0])))))  / (np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0])))) + np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0]))))) + np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2])) + (1 - power[:, 1]) * (1 - power[:, 2])),
          np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2]))  / (np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0])))) + np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0]))))) + np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2])) + (1 - power[:, 1]) * (1 - power[:, 2])),
          (1 - power[:, 1]) * (1 - power[:, 2])  / (np.sqrt((power[:, 1] * power[:, 2]) * ((power[:, 1] * (1 - power[:, 0])) * (power[:, 2] * (1 - power[:, 0])))) + np.sqrt((power[:, 1] * (1 - power[:, 2])) * (power[:, 1] * (1 - (power[:, 2] * (1 - power[:, 0]))))) + np.sqrt(((1 - power[:, 1]) * power[:, 2]) * ((1 - (power[:, 1] * (1 - power[:, 0]))) * power[:, 2])) + (1 - power[:, 1]) * (1 - power[:, 2])),
      ]
    probs0 = [
        power[:, 1] * power[:, 2],
        power[:, 1] * (1 - power[:, 2]),
        (1 - power[:, 1]) * power[:, 2],
        (1 - power[:, 1]) * (1 - power[:, 2]),
    ]

    loglike1 = np.sum((np.ones((loops, 1)) * np.array(conts)) * np.log(probs1).T, axis=1)
    like1 = sum(np.exp(loglike1)) * (1/loops)

    loglike0 = np.sum((np.ones((loops, 1)) * np.array(conts)) * np.log(probs0).T, axis=1)
    like0 = sum(np.exp(loglike0)) * (1/loops)

    logscore = np.log(like1/like0)
    return logscore


def CS(conts, threshold, is_gene, loops=loop_count):
    rng = np.random.default_rng()  # 乱数ジェネレーター
    power = np.zeros((loops, 2))

    # ループを実行して条件を満たす乱数を生成
    for i in range(loops):
      power0 = rng.uniform(0+1e-100, threshold)
      power1 = rng.uniform(0, 1)
      # power1 = threshold
      power[i] = [power0,power1]

    a, b, c, d = conts

    # power[:, 0] 背景と結果のw
    # power[:, 1] 原因と結果のw

    if is_gene:
      probs1 = [
          (1 - (1 - power[:, 1]) * (1 - power[:, 0])),# P(E=1|C=1)
          (1 - power[:, 1]) * (1 - power[:, 0]),# P(E=0|C=1)
          power[:, 0],# P(E=1|C=0)
          (1 - power[:, 0]),# P(E=0|C=0)
      ]
    else:
      probs1 = [
          power[:, 0] - (power[:, 1] * power[:, 0]),# P(E=1|C=1)
          1 - (power[:, 0] - (power[:, 1] * power[:, 0])),# P(E=0|C=1)
          power[:, 0],# P(E=1|C=0)
          1 - power[:, 0],# P(E=0|C=0)
      ]

    probs0 = [
        power[:, 0],# P(E=1|C=1)
        (1 - power[:, 0]),# P(E=0|C=1)
        power[:, 0],# P(E=1|C=0)
        (1 - power[:, 0]),# P(E=0|C=0)
    ]

    loglike1 = np.sum((np.ones((loops, 1)) * np.array(conts)) * np.log(probs1).T, axis=1)
    like1 = sum(np.exp(loglike1)) * (1/loops)

    loglike0 = np.sum((np.ones((loops, 1)) * np.array(conts)) * np.log(probs0).T, axis=1)
    like0 = sum(np.exp(loglike0)) * (1/loops)

    logscore = np.log(like1/like0)
    return logscore