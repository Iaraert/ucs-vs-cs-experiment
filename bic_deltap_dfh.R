# R - Verson 3.1.0
#

setwd("C:/Users/spira/Desktop/MCP/Project/ucs_vs_cs_experiment-summary")

if (!require(reticulate)) {
  install.packages("reticulate")
  library(reticulate)
}
if (!require(ggplot2)) {
  install.packages("ggplot2")
  library(ggplot2)
}

require(lme4)		# lme4 - ver. 1.1.6
require(lmerTest)	# lmerTest - ver. 2.0.6


Data <- read.csv("final_valid.csv", header=T)


# ex1
# Data$CS_EX1 <- with(Data, ifelse((ex1_a + ex1_b > 0) & (ex1_c + ex1_d > 0),
#                                  ex1_a / (ex1_a + ex1_b) - ex1_c / (ex1_c + ex1_d),
#                                  NA))
# Data$UCS_EX1 <- with(Data, ifelse((ex1_a + ex1_b > 0) & (ex1_a + ex1_c > 0),
#                                   ex1_a / sqrt((ex1_a + ex1_b) * (ex1_a + ex1_c)),
#                                   NA))
# 
# # ex2
# Data$CS_EX2 <- with(Data, ifelse((ex2_a + ex2_b > 0) & (ex2_c + ex2_d > 0),
#                                  ex2_a / (ex2_a + ex2_b) - ex2_c / (ex2_c + ex2_d),
#                                  NA))
# Data$UCS_EX2 <- with(Data, ifelse((ex2_a + ex2_b > 0) & (ex2_a + ex2_c > 0),
#                                   ex2_a / sqrt((ex2_a + ex2_b) * (ex2_a + ex2_c)),
#                                   NA))


# ----- ex1 -----

# pARIs（a / (a + b + c)）
# Data$CS_EX1 <- with(Data, ifelse((ex1_a + ex1_b + ex1_c) > 0,
#                                  ex1_a / (ex1_a + ex1_b + ex1_c),
#                                  NA))
# 
# # P(E|C)（a / (a + b)）
# Data$UCS_EX1 <- with(Data, ifelse((ex1_a + ex1_b) > 0,
#                                   ex1_a / (ex1_a + ex1_b),
#                                   NA))
# 
# 
# # ----- ex2 -----
# 
# # pARIs
# Data$CS_EX2 <- with(Data, ifelse((ex2_a + ex2_b + ex2_c) > 0,
#                                  ex2_a / (ex2_a + ex2_b + ex2_c),
#                                  NA))
# 
# # P(E|C)
# Data$UCS_EX2 <- with(Data, ifelse((ex2_a + ex2_b) > 0,
#                                   ex2_a / (ex2_a + ex2_b),
#                                   NA))

# ----- ex1: Causal Powerとφ係数 -----
Data$CS_EX1 <- mapply(function(a, b, c, d, est) {
  p_e_given_not_c <- ifelse((c + d) > 0, c / (c + d), NA)
  delta_p <- ifelse((a + b) > 0 & (c + d) > 0, a / (a + b) - c / (c + d), NA)

  if (is.na(delta_p) || is.na(p_e_given_not_c)) return(NA)

  if (est >= 0 && p_e_given_not_c < 1) {
    return(delta_p / (1 - p_e_given_not_c))
  } else if (est < 0 && p_e_given_not_c > 0) {
    return(-delta_p / p_e_given_not_c)
  } else {
    return(NA)  # avoid division by zero
  }
}, Data$ex1_a, Data$ex1_b, Data$ex1_c, Data$ex1_d, Data$ex1_estimate)


Data$UCS_EX1 <- mapply(function(a, b, c, d) {
  denom <- sqrt((a + b) * (c + d) * (a + c) * (b + d))
  if (denom > 0) {
    return((a * d - b * c) / denom)
  } else {
    return(NA)
  }
}, Data$ex1_a, Data$ex1_b, Data$ex1_c, Data$ex1_d)

# ----- ex2: Causal Powerとφ係数 -----
Data$CS_EX2 <- mapply(function(a, b, c, d, est) {
  p_e_given_not_c <- ifelse((c + d) > 0, c / (c + d), NA)
  delta_p <- ifelse((a + b) > 0 & (c + d) > 0, a / (a + b) - c / (c + d), NA)

  if (is.na(delta_p) || is.na(p_e_given_not_c)) return(NA)

  if (est >= 0 && p_e_given_not_c < 1) {
    return(delta_p / (1 - p_e_given_not_c))
  } else if (est < 0 && p_e_given_not_c > 0) {
    return(-delta_p / p_e_given_not_c)
  } else {
    return(NA)  # avoid division by zero
  }
}, Data$ex2_a, Data$ex2_b, Data$ex2_c, Data$ex2_d, Data$ex2_estimate)

Data$UCS_EX2 <- mapply(function(a, b, c, d) {
  denom <- sqrt((a + b) * (c + d) * (a + c) * (b + d))
  if (denom > 0) {
    return((a * d - b * c) / denom)
  } else {
    return(NA)
  }
}, Data$ex2_a, Data$ex2_b, Data$ex2_c, Data$ex2_d)



######################################################################
# 95% 分位点を閾値として外れ値を Winsorize（上限を設定）
# ucs_ex2_max <- quantile(Data$UCS_EX2, 0.95)
# cs_ex1_max <- quantile(Data$CS_EX1, 0.95)
# ucs_ex1_max <- quantile(Data$UCS_EX1, 0.95)
# cs_ex2_max <- quantile(Data$CS_EX2[Data$SY1 == TRUE], 0.95)
# Data$CS_EX2[Data$SY1 == TRUE] <- pmin(Data$CS_EX2[Data$SY1 == TRUE], cs_ex2_max)


# # Data$CS_EX2 <- pmin(Data$CS_EX2, cs_ex2_max)
# Data$UCS_EX2 <- pmin(Data$UCS_EX2, ucs_ex2_max)
# Data$CS_EX1 <- pmin(Data$CS_EX1, cs_ex1_max)
# Data$UCS_EX1 <- pmin(Data$UCS_EX1, ucs_ex1_max)

# # 再度ヒストグラムを確認
# hist(Data$CS_EX2, breaks=20, main="Winsorized CS_EX2", xlab="CS_EX2")
# hist(Data$UCS_EX2, breaks=20, main="Winsorized UCS_EX2", xlab="UCS_EX2")
# hist(Data$CS_EX1, breaks=20, main="Winsorized CS_EX1", xlab="CS_EX1")
# hist(Data$UCS_EX1, breaks=20, main="Winsorized UCS_EX1", xlab="UCS_EX1")

# Data$CS_EX2 <- scale(Data$CS_EX2)
# Data$UCS_EX2 <- scale(Data$UCS_EX2)
# Data$CS_EX1 <- scale(Data$CS_EX1)
# Data$UCS_EX1 <- scale(Data$UCS_EX1)

# # 再度ヒストグラムを確認
# hist(Data$CS_EX2, breaks=20, main="Standardized CS_EX2", xlab="CS_EX2")
# hist(Data$UCS_EX2, breaks=20, main="Standardized UCS_EX2", xlab="UCS_EX2")
# hist(Data$CS_EX1, breaks=20, main="Standardized CS_EX1", xlab="CS_EX1")
# hist(Data$UCS_EX1, breaks=20, main="Standardized UCS_EX1", xlab="UCS_EX1")

# summary(Data$CS_EX2)
# hist(Data$CS_EX2)
# summary(Data$CS_EX1)
# hist(Data$CS_EX1)

# summary(Data$UCS_EX2)
# hist(Data$UCS_EX2)
# summary(Data$UCS_EX1)
# hist(Data$UCS_EX1)

data.ex1 <- Data[Data$ex1_is_first == 1, ]
data.ex2 <- Data[Data$ex2_is_first == 1, ]

# ex1用
data.ex1.sy0 <- data.ex1[data.ex1$Cond == "0", ]
data.ex1.sy1 <- data.ex1[data.ex1$Cond == "1", ]

# ex2用
data.ex2.sy0 <- data.ex2[data.ex2$Cond == "0", ]
data.ex2.sy1 <- data.ex2[data.ex2$Cond == "1", ]

# SY0
model_cp_sy0 <- lmer(ex1_estimate ~ CS_EX1 + (1 | user_id), data = data.ex1.sy0)
model_phi_sy0 <- lmer(ex1_estimate ~ UCS_EX1 + (1 | user_id), data = data.ex1.sy0)

# SY1
model_cp_sy1 <- lmer(ex1_estimate ~ CS_EX1 + (1 | user_id), data = data.ex1.sy1)
model_phi_sy1 <- lmer(ex1_estimate ~ UCS_EX1 + (1 | user_id), data = data.ex1.sy1)

summary(model_cp_sy0)
summary(model_phi_sy0)
summary(model_cp_sy1)
summary(model_phi_sy1)

BIC(model_cp_sy0, model_phi_sy0)
BIC(model_cp_sy1, model_phi_sy1)


######################################################################
# EX1-SY0条件：CS
#
ex1.sy0.cs_ex1.m0 <- lmer(ex1_estimate ~ 1  + (1 | user_id), data.ex1.sy0, REML=FALSE)
ex1.sy0.cs_ex1.m1 <- lmer(ex1_estimate ~ CS_EX1  + (1 | user_id), data.ex1.sy0, REML=FALSE)
ex1.sy0.cs_ex1.m2 <- lmer(ex1_estimate ~ CS_EX1  + (1 | user_id) + (0 + CS_EX1 | user_id), data.ex1.sy0, REML=FALSE)
ex1.sy0.cs_ex1.m3 <- lmer(ex1_estimate ~ CS_EX1  + (1 + CS_EX1 | user_id), data.ex1.sy0, REML=FALSE)

######################################################################
# EX1-SY0条件：UCS
#
ex1.sy0.ucs_ex1.m0 <- lmer(ex1_estimate ~ 1  + (1 | user_id), data.ex1.sy0, REML=FALSE)
ex1.sy0.ucs_ex1.m1 <- lmer(ex1_estimate ~ UCS_EX1  + (1 | user_id), data.ex1.sy0, REML=FALSE)
ex1.sy0.ucs_ex1.m2 <- lmer(ex1_estimate ~ UCS_EX1  + (1 | user_id) + (0 + UCS_EX1 | user_id), data.ex1.sy0, REML=FALSE)
ex1.sy0.ucs_ex1.m3 <- lmer(ex1_estimate ~ UCS_EX1  + (1 + UCS_EX1 | user_id), data.ex1.sy0, REML=FALSE)

######################################################################
######################################################################
# EX1-SY1条件：CS
#
ex1.sy1.cs_ex1.m0 <- lmer(ex1_estimate ~ 1  + (1 | user_id), data.ex1.sy1, REML=FALSE)
ex1.sy1.cs_ex1.m1 <- lmer(ex1_estimate ~ CS_EX1  + (1 | user_id), data.ex1.sy1, REML=FALSE)
ex1.sy1.cs_ex1.m2 <- lmer(ex1_estimate ~ CS_EX1  + (1 | user_id) + (0 + CS_EX1 | user_id), data.ex1.sy1, REML=FALSE)
ex1.sy1.cs_ex1.m3 <- lmer(ex1_estimate ~ CS_EX1  + (1 + CS_EX1 | user_id), data.ex1.sy1, REML=FALSE)

######################################################################
# EX1-SY1条件：UCS
#
ex1.sy1.ucs_ex1.m0 <- lmer(ex1_estimate ~ 1  + (1 | user_id), data.ex1.sy1, REML=FALSE)
ex1.sy1.ucs_ex1.m1 <- lmer(ex1_estimate ~ UCS_EX1  + (1 | user_id), data.ex1.sy1, REML=FALSE)
ex1.sy1.ucs_ex1.m2 <- lmer(ex1_estimate ~ UCS_EX1  + (1 | user_id) + (0 + UCS_EX1 | user_id), data.ex1.sy1, REML=FALSE)
ex1.sy1.ucs_ex1.m3 <- lmer(ex1_estimate ~ UCS_EX1  + (1 + UCS_EX1 | user_id), data.ex1.sy1, REML=FALSE)

######################################################################
######################################################################
# EX2-SY0条件：CS
#
ex2.sy0.cs_ex2.m0 <- lmer(ex2_estimate ~ 1  + (1 | user_id), data.ex2.sy0, REML=FALSE)
ex2.sy0.cs_ex2.m1 <- lmer(ex2_estimate ~ CS_EX2  + (1 | user_id), data.ex2.sy0, REML=FALSE)
ex2.sy0.cs_ex2.m2 <- lmer(ex2_estimate ~ CS_EX2  + (1 | user_id) + (0 + CS_EX2 | user_id), data.ex2.sy0, REML=FALSE)
ex2.sy0.cs_ex2.m3 <- lmer(ex2_estimate ~ CS_EX2  + (1 + CS_EX2 | user_id), data.ex2.sy0, REML=FALSE)

######################################################################
# EX2-SY0条件：UCS
#
ex2.sy0.ucs_ex2.m0 <- lmer(ex2_estimate ~ 1  + (1 | user_id), data.ex2.sy0, REML=FALSE)
ex2.sy0.ucs_ex2.m1 <- lmer(ex2_estimate ~ UCS_EX2  + (1 | user_id), data.ex2.sy0, REML=FALSE)
ex2.sy0.ucs_ex2.m2 <- lmer(ex2_estimate ~ UCS_EX2  + (1 | user_id) + (0 + UCS_EX2 | user_id), data.ex2.sy0, REML=FALSE)
ex2.sy0.ucs_ex2.m3 <- lmer(ex2_estimate ~ UCS_EX2  + (1 + UCS_EX2 | user_id), data.ex2.sy0, REML=FALSE)

######################################################################
######################################################################
# EX2-SY1条件：CS
#
ex2.sy1.cs_ex2.m0 <- lmer(ex2_estimate ~ 1  + (1 | user_id), data.ex2.sy1, REML=FALSE)
ex2.sy1.cs_ex2.m1 <- lmer(ex2_estimate ~ CS_EX2  + (1 | user_id), data.ex2.sy1, REML=FALSE)
ex2.sy1.cs_ex2.m2 <- lmer(ex2_estimate ~ CS_EX2  + (1 | user_id) + (0 + CS_EX2 | user_id), data.ex2.sy1, REML=FALSE)
ex2.sy1.cs_ex2.m3 <- lmer(ex2_estimate ~ CS_EX2  + (1 + CS_EX2 | user_id), data.ex2.sy1, REML=FALSE)

######################################################################
# EX2-SY1条件：UCS
#
ex2.sy1.ucs_ex2.m0 <- lmer(ex2_estimate ~ 1  + (1 | user_id), data.ex2.sy1, REML=FALSE)
ex2.sy1.ucs_ex2.m1 <- lmer(ex2_estimate ~ UCS_EX2  + (1 | user_id), data.ex2.sy1, REML=FALSE)
ex2.sy1.ucs_ex2.m2 <- lmer(ex2_estimate ~ UCS_EX2  + (1 | user_id) + (0 + UCS_EX2 | user_id), data.ex2.sy1, REML=FALSE)
ex2.sy1.ucs_ex2.m3 <- lmer(ex2_estimate ~ UCS_EX2  + (1 + UCS_EX2 | user_id), data.ex2.sy1, REML=FALSE)

######################################################################
# 固定効果のみのモデル
# ex2.sy0.cs_ex2.m0 <- lm(EX2 ~ 1, data.sy0)
# ex2.sy1.cs_ex2.m0 <- lm(EX2 ~ 1, data.sy1)
# ex2.sy1.cs_ex2.m1 <- lm(EX2 ~ CS_EX2, data.sy1)
# ex2.sy0.ucs_ex2.m0 <- lm(EX2 ~ 1, data.sy0)
# ex2.sy1.ucs_ex2.m0 <- lm(EX2 ~ 1, data.sy1)
# ex2.sy1.ucs_ex2.m1 <- lm(EX2 ~ UCS_EX2, data.sy1)

# # ランダム効果を制限したモデル
# ex2.sy1.cs_ex2.m2 <- lmer(EX2 ~ CS_EX2 + (1 | user_id), data.sy1, REML=TRUE)
# ex2.sy1.cs_ex2.m3 <- lmer(EX2 ~ CS_EX2 + (1 | user_id), data.sy1, REML=TRUE)
# ex2.sy1.ucs_ex2.m2 <- lmer(EX2 ~ UCS_EX2 + (1 | user_id), data.sy1, REML=TRUE)
# ex2.sy1.ucs_ex2.m3 <- lmer(EX2 ~ UCS_EX2 + (1 | user_id), data.sy1, REML=TRUE)

# # 相関が 1.000 の問題を修正
# ex1.sy0.cs_ex1.m3 <- lmer(EX1 ~ CS_EX1 + (1 | user_id), data.sy0, REML=TRUE)
# ex1.sy1.cs_ex1.m3 <- lmer(EX1 ~ CS_EX1 + (1 | user_id), data.sy1, REML=TRUE)
# ex1.sy0.ucs_ex1.m3 <- lmer(EX1 ~ UCS_EX1 + (1 | user_id), data.sy0, REML=TRUE)

# VarCorr(ex1.sy0.cs_ex1.m0)
# VarCorr(ex2.sy0.cs_ex2.m0)
# VarCorr(ex1.sy1.cs_ex1.m0)
# VarCorr(ex2.sy1.cs_ex2.m0)

# VarCorr(ex1.sy0.cs_ex1.m1)
# VarCorr(ex2.sy0.cs_ex2.m1)
# VarCorr(ex1.sy1.cs_ex1.m1)
# VarCorr(ex2.sy1.cs_ex2.m1)

# VarCorr(ex1.sy0.cs_ex1.m2)
# VarCorr(ex2.sy0.cs_ex2.m2)
# VarCorr(ex1.sy1.cs_ex1.m2)
# VarCorr(ex2.sy1.cs_ex2.m2)

# VarCorr(ex1.sy0.cs_ex1.m3)
# VarCorr(ex2.sy0.cs_ex2.m3)
# VarCorr(ex1.sy1.cs_ex1.m3)
# VarCorr(ex2.sy1.cs_ex2.m3)


# VarCorr(ex1.sy0.ucs_ex1.m0)
# VarCorr(ex2.sy0.ucs_ex2.m0)
# VarCorr(ex1.sy1.ucs_ex1.m0)
# VarCorr(ex2.sy1.ucs_ex2.m0)

# VarCorr(ex1.sy0.ucs_ex1.m1)
# VarCorr(ex2.sy0.ucs_ex2.m1)
# VarCorr(ex1.sy1.ucs_ex1.m1)
# VarCorr(ex2.sy1.ucs_ex2.m1)

# VarCorr(ex1.sy0.ucs_ex1.m2)
# VarCorr(ex2.sy0.ucs_ex2.m2)
# VarCorr(ex1.sy1.ucs_ex1.m2)
# VarCorr(ex2.sy1.ucs_ex2.m2)

# VarCorr(ex1.sy0.ucs_ex1.m3)
# VarCorr(ex2.sy0.ucs_ex2.m3)
# VarCorr(ex1.sy1.ucs_ex1.m3)
# VarCorr(ex2.sy1.ucs_ex2.m3)

# anova(ex1.sy0.ucs_ex1.m1, ex2.sy0.ucs_ex2.m1)
# anova(ex1.sy1.ucs_ex1.m1, ex2.sy1.ucs_ex2.m1)

# ex2.sy1.cs_ex2_withoutRandom.m1 <- lm(EX2 ~ CS_EX2, data = data.sy1)

# AIC(ex2.sy1.cs_ex2_withoutRandom.m1, ex2.sy1.cs_ex2.m1)
# BIC(ex2.sy1.cs_ex2_withoutRandom.m1, ex2.sy1.cs_ex2.m1)

# logLik(ex2.sy1.cs_ex2_withoutRandom.m1)
# logLik(ex2.sy1.cs_ex2.m1)

# LR_stat <- -2 * (logLik(ex2.sy1.cs_ex2_withoutRandom.m1) - logLik(ex2.sy1.cs_ex2.m1))
# p_value <- pchisq(LR_stat, df = 1, lower.tail = FALSE)
# print(p_value)


# BIC(ex1.sy0.cs_ex1.m0, ex1.sy0.cs_ex1.m1, ex1.sy0.cs_ex1.m2, ex1.sy0.cs_ex1.m3)
# BIC(ex2.sy0.cs_ex2.m0, ex2.sy0.cs_ex2.m1, ex2.sy0.cs_ex2.m2, ex2.sy0.cs_ex2.m3)
# BIC(ex1.sy1.cs_ex1.m0, ex1.sy1.cs_ex1.m1, ex1.sy1.cs_ex1.m2, ex1.sy1.cs_ex1.m3)
# BIC(ex2.sy1.cs_ex2.m0, ex2.sy1.cs_ex2.m1, ex2.sy1.cs_ex2.m2, ex2.sy1.cs_ex2.m3)

# BIC(ex1.sy0.ucs_ex1.m0, ex1.sy0.ucs_ex1.m1, ex1.sy0.ucs_ex1.m2, ex1.sy0.ucs_ex1.m3)
# BIC(ex2.sy0.ucs_ex2.m0, ex2.sy0.ucs_ex2.m1, ex2.sy0.ucs_ex2.m2, ex2.sy0.ucs_ex2.m3)
# BIC(ex1.sy1.ucs_ex1.m0, ex1.sy1.ucs_ex1.m1, ex1.sy1.ucs_ex1.m2, ex1.sy1.ucs_ex1.m3)
# BIC(ex2.sy1.ucs_ex2.m0, ex2.sy1.ucs_ex2.m1, ex2.sy1.ucs_ex2.m2, ex2.sy1.ucs_ex2.m3)

######################################################################
summary(ex1.sy0.cs_ex1.m0)
summary(ex1.sy0.cs_ex1.m1)
summary(ex1.sy0.cs_ex1.m2)
summary(ex1.sy0.cs_ex1.m3)

summary(ex2.sy0.cs_ex2.m0)
summary(ex2.sy0.cs_ex2.m1)
summary(ex2.sy0.cs_ex2.m2)
summary(ex2.sy0.cs_ex2.m3)

summary(ex1.sy1.cs_ex1.m0)
summary(ex1.sy1.cs_ex1.m1)
summary(ex1.sy1.cs_ex1.m2)
summary(ex1.sy1.cs_ex1.m3)

summary(ex2.sy1.cs_ex2.m0)
summary(ex2.sy1.cs_ex2.m1)
summary(ex2.sy1.cs_ex2.m2)
summary(ex2.sy1.cs_ex2.m3)

summary(ex1.sy0.ucs_ex1.m0)
summary(ex1.sy0.ucs_ex1.m1)
summary(ex1.sy0.ucs_ex1.m2)
summary(ex1.sy0.ucs_ex1.m3)

summary(ex2.sy0.ucs_ex2.m0)
summary(ex2.sy0.ucs_ex2.m1)
summary(ex2.sy0.ucs_ex2.m2)
summary(ex2.sy0.ucs_ex2.m3)

summary(ex1.sy1.ucs_ex1.m0)
summary(ex1.sy1.ucs_ex1.m1)
summary(ex1.sy1.ucs_ex1.m2)
summary(ex1.sy1.ucs_ex1.m3)

summary(ex2.sy1.ucs_ex2.m0)
summary(ex2.sy1.ucs_ex2.m1)
summary(ex2.sy1.ucs_ex2.m2)
summary(ex2.sy1.ucs_ex2.m3)


summary(data.ex2.sy1$CS_EX2)
summary(data.ex2.sy0$CS_EX2)
summary(data.ex2.sy1$UCS_EX2)
summary(data.ex2.sy0$UCS_EX2)

summary(data.ex1.sy1$CS_EX1)
summary(data.ex1.sy0$CS_EX1)
summary(data.ex1.sy1$UCS_EX1)
summary(data.ex1.sy0$UCS_EX1)


######################################################################
######################################################################

ex1.sy0.cs_ex1.m0.sum <- summary(ex1.sy0.cs_ex1.m0)
ex2.sy0.cs_ex2.m0.sum <- summary(ex2.sy0.cs_ex2.m0)
ex1.sy0.cs_ex1.m1.sum <- summary(ex1.sy0.cs_ex1.m1)
ex2.sy0.cs_ex2.m1.sum <- summary(ex2.sy0.cs_ex2.m1)
ex1.sy0.cs_ex1.m2.sum <- summary(ex1.sy0.cs_ex1.m2)
ex2.sy0.cs_ex2.m2.sum <- summary(ex2.sy0.cs_ex2.m2)
ex1.sy0.cs_ex1.m3.sum <- summary(ex1.sy0.cs_ex1.m3)
ex2.sy0.cs_ex2.m3.sum <- summary(ex2.sy0.cs_ex2.m3)
ex1.sy1.cs_ex1.m0.sum <- summary(ex1.sy1.cs_ex1.m0)
ex2.sy1.cs_ex2.m0.sum <- summary(ex2.sy1.cs_ex2.m0)
ex1.sy1.cs_ex1.m1.sum <- summary(ex1.sy1.cs_ex1.m1)
ex2.sy1.cs_ex2.m1.sum <- summary(ex2.sy1.cs_ex2.m1)
ex1.sy1.cs_ex1.m2.sum <- summary(ex1.sy1.cs_ex1.m2)
ex2.sy1.cs_ex2.m2.sum <- summary(ex2.sy1.cs_ex2.m2)
ex1.sy1.cs_ex1.m3.sum <- summary(ex1.sy1.cs_ex1.m3)
ex2.sy1.cs_ex2.m3.sum <- summary(ex2.sy1.cs_ex2.m3)

bic.cs <- c(
BIC(ex1.sy0.cs_ex1.m0), BIC(ex2.sy0.cs_ex2.m0), BIC(ex1.sy0.cs_ex1.m1), BIC(ex2.sy0.cs_ex2.m1),
BIC(ex1.sy0.cs_ex1.m2), BIC(ex2.sy0.cs_ex2.m2), BIC(ex1.sy0.cs_ex1.m3), BIC(ex2.sy0.cs_ex2.m3),
BIC(ex1.sy1.cs_ex1.m0), BIC(ex2.sy1.cs_ex2.m0), BIC(ex1.sy1.cs_ex1.m1), BIC(ex2.sy1.cs_ex2.m1),
BIC(ex1.sy1.cs_ex1.m2), BIC(ex2.sy1.cs_ex2.m2), BIC(ex1.sy1.cs_ex1.m3), BIC(ex2.sy1.cs_ex2.m3)
)

coef.cs <- rbind(
rbind(ex1.sy0.cs_ex1.m0.sum$coefficients, rep(0,5)),
ex1.sy0.cs_ex1.m1.sum$coefficients,
ex1.sy0.cs_ex1.m2.sum$coefficients,
ex1.sy0.cs_ex1.m3.sum$coefficients,
rbind(ex2.sy0.cs_ex2.m0.sum$coefficients, rep(0,5)),
ex2.sy0.cs_ex2.m1.sum$coefficients,
ex2.sy0.cs_ex2.m2.sum$coefficients,
ex2.sy0.cs_ex2.m3.sum$coefficients,
rbind(ex1.sy1.cs_ex1.m0.sum$coefficients, rep(0,5)),
ex1.sy1.cs_ex1.m1.sum$coefficients,
ex1.sy1.cs_ex1.m2.sum$coefficients,
ex1.sy1.cs_ex1.m3.sum$coefficients,
rbind(ex2.sy1.cs_ex2.m0.sum$coefficients, rep(0,5)),
ex2.sy1.cs_ex2.m1.sum$coefficients,
ex2.sy1.cs_ex2.m2.sum$coefficients,
ex2.sy1.cs_ex2.m3.sum$coefficients
)

######################################################################
ex1.sy0.ucs_ex1.m0.sum <- summary(ex1.sy0.ucs_ex1.m0)
ex2.sy0.ucs_ex2.m0.sum <- summary(ex2.sy0.ucs_ex2.m0)
ex1.sy0.ucs_ex1.m1.sum <- summary(ex1.sy0.ucs_ex1.m1)
ex2.sy0.ucs_ex2.m1.sum <- summary(ex2.sy0.ucs_ex2.m1)
ex1.sy0.ucs_ex1.m2.sum <- summary(ex1.sy0.ucs_ex1.m2)
ex2.sy0.ucs_ex2.m2.sum <- summary(ex2.sy0.ucs_ex2.m2)
ex1.sy0.ucs_ex1.m3.sum <- summary(ex1.sy0.ucs_ex1.m3)
ex2.sy0.ucs_ex2.m3.sum <- summary(ex2.sy0.ucs_ex2.m3)
ex1.sy1.ucs_ex1.m0.sum <- summary(ex1.sy1.ucs_ex1.m0)
ex2.sy1.ucs_ex2.m0.sum <- summary(ex2.sy1.ucs_ex2.m0)
ex1.sy1.ucs_ex1.m1.sum <- summary(ex1.sy1.ucs_ex1.m1)
ex2.sy1.ucs_ex2.m1.sum <- summary(ex2.sy1.ucs_ex2.m1)
ex1.sy1.ucs_ex1.m2.sum <- summary(ex1.sy1.ucs_ex1.m2)
ex2.sy1.ucs_ex2.m2.sum <- summary(ex2.sy1.ucs_ex2.m2)
ex1.sy1.ucs_ex1.m3.sum <- summary(ex1.sy1.ucs_ex1.m3)
ex2.sy1.ucs_ex2.m3.sum <- summary(ex2.sy1.ucs_ex2.m3)

bic.ucs <- c(
BIC(ex1.sy0.ucs_ex1.m0), BIC(ex2.sy0.ucs_ex2.m0), BIC(ex1.sy0.ucs_ex1.m1), BIC(ex2.sy0.ucs_ex2.m1),
BIC(ex1.sy0.ucs_ex1.m2), BIC(ex2.sy0.ucs_ex2.m2), BIC(ex1.sy0.ucs_ex1.m3), BIC(ex2.sy0.ucs_ex2.m3),
BIC(ex1.sy1.ucs_ex1.m0), BIC(ex2.sy1.ucs_ex2.m0), BIC(ex1.sy1.ucs_ex1.m1), BIC(ex2.sy1.ucs_ex2.m1),
BIC(ex1.sy1.ucs_ex1.m2), BIC(ex2.sy1.ucs_ex2.m2), BIC(ex1.sy1.ucs_ex1.m3), BIC(ex2.sy1.ucs_ex2.m3)
)

#bic.double <- c(
#  BIC(ex1.sy0.double), BIC(ex2.sy0.double), BIC(ex1.sy1.double), BIC(ex2.sy1.double)
#)


coef.ucs <- rbind(
rbind(ex1.sy0.ucs_ex1.m0.sum$coefficients, rep(0,5)),
ex1.sy0.ucs_ex1.m1.sum$coefficients,
ex1.sy0.ucs_ex1.m2.sum$coefficients,
ex1.sy0.ucs_ex1.m3.sum$coefficients,
rbind(ex2.sy0.ucs_ex2.m0.sum$coefficients, rep(0,5)),
ex2.sy0.ucs_ex2.m1.sum$coefficients,
ex2.sy0.ucs_ex2.m2.sum$coefficients,
ex2.sy0.ucs_ex2.m3.sum$coefficients,
rbind(ex1.sy1.ucs_ex1.m0.sum$coefficients, rep(0,5)),
ex1.sy1.ucs_ex1.m1.sum$coefficients,
ex1.sy1.ucs_ex1.m2.sum$coefficients,
ex1.sy1.ucs_ex1.m3.sum$coefficients,
rbind(ex2.sy1.ucs_ex2.m0.sum$coefficients, rep(0,5)),
ex2.sy1.ucs_ex2.m1.sum$coefficients,
ex2.sy1.ucs_ex2.m2.sum$coefficients,
ex2.sy1.ucs_ex2.m3.sum$coefficients
)

bic_sorted_table <- data.frame(
  Model = c(
    "EX1-SY0.m0", "EX2-SY0.m0", "EX1-SY0.m1", "EX2-SY0.m1", 
    "EX1-SY0.m2", "EX2-SY0.m2", "EX1-SY0.m3", "EX2-SY0.m3",
    "EX1-SY1.m0", "EX2-SY1.m0", "EX1-SY1.m1", "EX2-SY1.m1",
    "EX1-SY1.m2", "EX2-SY1.m2", "EX1-SY1.m3", "EX2-SY1.m3",
    "EX1-SY0.m0", "EX2-SY0.m0", "EX1-SY0.m1", "EX2-SY0.m1", 
    "EX1-SY0.m2", "EX2-SY0.m2", "EX1-SY0.m3", "EX2-SY0.m3",
    "EX1-SY1.m0", "EX2-SY1.m0", "EX1-SY1.m1", "EX2-SY1.m1",
    "EX1-SY1.m2", "EX2-SY1.m2", "EX1-SY1.m3", "EX2-SY1.m3"
  ),
  BIC_value = c(
    bic.cs[1], bic.cs[2], bic.cs[3], bic.cs[4], 
    bic.cs[5], bic.cs[6], bic.cs[7], bic.cs[8], 
    bic.cs[9], bic.cs[10], bic.cs[11], bic.cs[12], 
    bic.cs[13], bic.cs[14], bic.cs[15], bic.cs[16],
    bic.ucs[1], bic.ucs[2], bic.ucs[3], bic.ucs[4], 
    bic.ucs[5], bic.ucs[6], bic.ucs[7], bic.ucs[8], 
    bic.ucs[9], bic.ucs[10], bic.ucs[11], bic.ucs[12], 
    bic.ucs[13], bic.ucs[14], bic.ucs[15], bic.ucs[16]
  )
)

for (i in 1:16){
  print(bic_sorted_table$BIC_value[i])
}

for (i in 17:36){
  print(bic_sorted_table$BIC_value[i])
}

bic_table_name <- paste0("BICsorted_DeltaP_DFH.csv")
write.table(bic_sorted_table, file=bic_table_name, sep=",", row.names=FALSE)

######################################################################
######################################################################
cs.all <- cbind(c(rbind(bic.cs, rep(0, 16))), coef.cs)

rownames(cs.all) <- c(
"EX1-SY0.m0.int", "EX1-SY0.m0.CS",  
"EX2-SY0.m0.int", "EX2-SY0.m0.CS",
"EX1-SY0.m1.int", "EX1-SY0.m1.CS",
"EX2-SY0.m1.int", "EX2-SY0.m1.CS",
"EX1-SY0.m2.int", "EX1-SY0.m2.CS",
"EX2-SY0.m2.int", "EX2-SY0.m2.CS",
"EX1-SY0.m3.int", "EX1-SY0.m3.CS",
"EX2-SY0.m3.int", "EX2-SY0.m3.CS",
"EX1-SY1.m0.int", "EX1-SY1.m0.CS",
"EX2-SY1.m0.int", "EX2-SY1.m0.CS",
"EX1-SY1.m1.int", "EX1-SY1.m1.CS",
"EX2-SY1.m1.int", "EX2-SY1.m1.CS",
"EX1-SY1.m2.int", "EX1-SY1.m2.CS",
"EX2-SY1.m2.int", "EX2-SY1.m2.CS",
"EX1-SY1.m3.int", "EX1-SY1.m3.CS",
"EX2-SY1.m3.int", "EX2-SY1.m3.CS"
)

ucs.all <- cbind(c(rbind(bic.ucs, rep(0, 16))), coef.ucs)

rownames(ucs.all) <- c(
"EX1-SY0.m0.int", "EX1-SY0.m0.UCS",  
"EX2-SY0.m0.int", "EX2-SY0.m0.UCS",
"EX1-SY0.m1.int", "EX1-SY0.m1.UCS",
"EX2-SY0.m1.int", "EX2-SY0.m1.UCS",
"EX1-SY0.m2.int", "EX1-SY0.m2.UCS",
"EX2-SY0.m2.int", "EX2-SY0.m2.UCS",
"EX1-SY0.m3.int", "EX1-SY0.m3.UCS",
"EX2-SY0.m3.int", "EX2-SY0.m3.UCS",
"EX1-SY1.m0.int", "EX1-SY1.m0.UCS",
"EX2-SY1.m0.int", "EX2-SY1.m0.UCS",
"EX1-SY1.m1.int", "EX1-SY1.m1.UCS",
"EX2-SY1.m1.int", "EX2-SY1.m1.UCS",
"EX1-SY1.m2.int", "EX1-SY1.m2.UCS",
"EX2-SY1.m2.int", "EX2-SY1.m2.UCS",
"EX1-SY1.m3.int", "EX1-SY1.m3.UCS",
"EX2-SY1.m3.int", "EX2-SY1.m3.UCS"
)

cs_filename <- paste0("bic_delta_p.csv")
ucs_filename <- paste0("bic_dfh.csv")

write.table(cs.all, file=cs_filename, sep=",", row.names=T)
write.table(ucs.all, file=ucs_filename, sep=",", row.names=T)
