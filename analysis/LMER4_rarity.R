# R - Verson 3.1.0
#

setwd("C:/Users/spira/Desktop/研究/因果推論/Exp1_Analyses2-HHOTB-2017")
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

Data <- read.csv("Data.csv", header=T)

threshold_cs <- 1.0
threshold_ucs <- 0.01

source_python("CS_UCS.py")

Data$is_geneIV <- Data$IV >= 0
Data$CS_IV <- sapply(1:nrow(Data), function(i) CS(c(Data$a[i], Data$b[i], Data$c[i], Data$d[i]), threshold_cs, is_gene=Data$is_geneIV[i]))
Data$UCS_IV <- sapply(1:nrow(Data), function(i) UCS(c(Data$a[i], Data$b[i], Data$c[i], Data$d[i]), threshold_ucs, is_gene=Data$is_geneIV[i]))

Data$is_geneOB <- Data$OB > 0
Data$CS_OB <- sapply(1:nrow(Data), function(i) CS(c(Data$a[i], Data$b[i], Data$c[i], Data$d[i]), threshold_cs, is_gene=Data$is_geneOB[i]))
Data$UCS_OB <- sapply(1:nrow(Data), function(i) UCS(c(Data$a[i], Data$b[i], Data$c[i], Data$d[i]), threshold_ucs, is_gene=Data$is_geneOB[i]))

######################################################################
# 95% 分位点を閾値として外れ値を Winsorize（上限を設定）
# ucs_iv_max <- quantile(Data$UCS_IV, 0.95)
# cs_ob_max <- quantile(Data$CS_OB, 0.95)
# ucs_ob_max <- quantile(Data$UCS_OB, 0.95)

# cs_iv_max <- quantile(Data$CS_IV[Data$XC == TRUE], 0.95)
# Data$CS_IV[Data$XC == TRUE] <- pmin(Data$CS_IV[Data$XC == TRUE], cs_iv_max)


# # Data$CS_IV <- pmin(Data$CS_IV, cs_iv_max)
# Data$UCS_IV <- pmin(Data$UCS_IV, ucs_iv_max)
# Data$CS_OB <- pmin(Data$CS_OB, cs_ob_max)
# Data$UCS_OB <- pmin(Data$UCS_OB, ucs_ob_max)

# # 再度ヒストグラムを確認
# hist(Data$CS_IV, breaks=20, main="Winsorized CS_IV", xlab="CS_IV")
# hist(Data$UCS_IV, breaks=20, main="Winsorized UCS_IV", xlab="UCS_IV")
# hist(Data$CS_OB, breaks=20, main="Winsorized CS_OB", xlab="CS_OB")
# hist(Data$UCS_OB, breaks=20, main="Winsorized UCS_OB", xlab="UCS_OB")

# Data$CS_IV <- scale(Data$CS_IV)
# Data$UCS_IV <- scale(Data$UCS_IV)
# Data$CS_OB <- scale(Data$CS_OB)
# Data$UCS_OB <- scale(Data$UCS_OB)

# # 再度ヒストグラムを確認
# hist(Data$CS_IV, breaks=20, main="Standardized CS_IV", xlab="CS_IV")
# hist(Data$UCS_IV, breaks=20, main="Standardized UCS_IV", xlab="UCS_IV")
# hist(Data$CS_OB, breaks=20, main="Standardized CS_OB", xlab="CS_OB")
# hist(Data$UCS_OB, breaks=20, main="Standardized UCS_OB", xlab="UCS_OB")

# summary(Data$CS_IV)
# hist(Data$CS_IV)
# summary(Data$CS_OB)
# hist(Data$CS_OB)

# summary(Data$UCS_IV)
# hist(Data$UCS_IV)
# summary(Data$UCS_OB)
# hist(Data$UCS_OB)

data.xc <- Data[Data$Cond=="XC",]
data.fg <- Data[Data$Cond=="FG",]

######################################################################
# OB-FG条件：CS
#
ob.fg.cs_ob.m0 <- lmer(OB ~ 1  + (1 | Subj2), data.fg, REML=FALSE)
ob.fg.cs_ob.m1 <- lmer(OB ~ CS_OB  + (1 | Subj2), data.fg, REML=FALSE)
ob.fg.cs_ob.m2 <- lmer(OB ~ CS_OB  + (1 | Subj2) + (0 + CS_OB | Subj2), data.fg, REML=FALSE)
ob.fg.cs_ob.m3 <- lmer(OB ~ CS_OB  + (1 + CS_OB | Subj2), data.fg, REML=FALSE)

######################################################################
# OB-FG条件：UCS
#
ob.fg.ucs_ob.m0 <- lmer(OB ~ 1  + (1 | Subj2), data.fg, REML=FALSE)
ob.fg.ucs_ob.m1 <- lmer(OB ~ UCS_OB  + (1 | Subj2), data.fg, REML=FALSE)
ob.fg.ucs_ob.m2 <- lmer(OB ~ UCS_OB  + (1 | Subj2) + (0 + UCS_OB | Subj2), data.fg, REML=FALSE)
ob.fg.ucs_ob.m3 <- lmer(OB ~ UCS_OB  + (1 + UCS_OB | Subj2), data.fg, REML=FALSE)

######################################################################
######################################################################
# OB-XC条件：CS
#
ob.xc.cs_ob.m0 <- lmer(OB ~ 1  + (1 | Subj2), data.xc, REML=FALSE)
ob.xc.cs_ob.m1 <- lmer(OB ~ CS_OB  + (1 | Subj2), data.xc, REML=FALSE)
ob.xc.cs_ob.m2 <- lmer(OB ~ CS_OB  + (1 | Subj2) + (0 + CS_OB | Subj2), data.xc, REML=FALSE)
ob.xc.cs_ob.m3 <- lmer(OB ~ CS_OB  + (1 + CS_OB | Subj2), data.xc, REML=FALSE)

######################################################################
# OB-XC条件：UCS
#
ob.xc.ucs_ob.m0 <- lmer(OB ~ 1  + (1 | Subj2), data.xc, REML=FALSE)
ob.xc.ucs_ob.m1 <- lmer(OB ~ UCS_OB  + (1 | Subj2), data.xc, REML=FALSE)
ob.xc.ucs_ob.m2 <- lmer(OB ~ UCS_OB  + (1 | Subj2) + (0 + UCS_OB | Subj2), data.xc, REML=FALSE)
ob.xc.ucs_ob.m3 <- lmer(OB ~ UCS_OB  + (1 + UCS_OB | Subj2), data.xc, REML=FALSE)

######################################################################
######################################################################
# IV-FG条件：CS
#
iv.fg.cs_iv.m0 <- lmer(IV ~ 1  + (1 | Subj1), data.fg, REML=FALSE)
iv.fg.cs_iv.m1 <- lmer(IV ~ CS_IV  + (1 | Subj1), data.fg, REML=FALSE)
iv.fg.cs_iv.m2 <- lmer(IV ~ CS_IV  + (1 | Subj1) + (0 + CS_IV | Subj1), data.fg, REML=FALSE)
iv.fg.cs_iv.m3 <- lmer(IV ~ CS_IV  + (1 + CS_IV | Subj1), data.fg, REML=FALSE)

######################################################################
# IV-FG条件：UCS
#
iv.fg.ucs_iv.m0 <- lmer(IV ~ 1  + (1 | Subj1), data.fg, REML=FALSE)
iv.fg.ucs_iv.m1 <- lmer(IV ~ UCS_IV  + (1 | Subj1), data.fg, REML=FALSE)
iv.fg.ucs_iv.m2 <- lmer(IV ~ UCS_IV  + (1 | Subj1) + (0 + UCS_IV | Subj1), data.fg, REML=FALSE)
iv.fg.ucs_iv.m3 <- lmer(IV ~ UCS_IV  + (1 + UCS_IV | Subj1), data.fg, REML=FALSE)

######################################################################
######################################################################
# IV-XC条件：CS
#
iv.xc.cs_iv.m0 <- lmer(IV ~ 1  + (1 | Subj1), data.xc, REML=FALSE)
iv.xc.cs_iv.m1 <- lmer(IV ~ CS_IV  + (1 | Subj1), data.xc, REML=FALSE)
iv.xc.cs_iv.m2 <- lmer(IV ~ CS_IV  + (1 | Subj1) + (0 + CS_IV | Subj1), data.xc, REML=FALSE)
iv.xc.cs_iv.m3 <- lmer(IV ~ CS_IV  + (1 + CS_IV | Subj1), data.xc, REML=FALSE)

######################################################################
# IV-XC条件：UCS
#
iv.xc.ucs_iv.m0 <- lmer(IV ~ 1  + (1 | Subj1), data.xc, REML=FALSE)
iv.xc.ucs_iv.m1 <- lmer(IV ~ UCS_IV  + (1 | Subj1), data.xc, REML=FALSE)
iv.xc.ucs_iv.m2 <- lmer(IV ~ UCS_IV  + (1 | Subj1) + (0 + UCS_IV | Subj1), data.xc, REML=FALSE)
iv.xc.ucs_iv.m3 <- lmer(IV ~ UCS_IV  + (1 + UCS_IV | Subj1), data.xc, REML=FALSE)

######################################################################
# 固定効果のみのモデル
# iv.fg.cs_iv.m0 <- lm(IV ~ 1, data.fg)
# iv.xc.cs_iv.m0 <- lm(IV ~ 1, data.xc)
# iv.xc.cs_iv.m1 <- lm(IV ~ CS_IV, data.xc)
# iv.fg.ucs_iv.m0 <- lm(IV ~ 1, data.fg)
# iv.xc.ucs_iv.m0 <- lm(IV ~ 1, data.xc)
# iv.xc.ucs_iv.m1 <- lm(IV ~ UCS_IV, data.xc)

# # ランダム効果を制限したモデル
# iv.xc.cs_iv.m2 <- lmer(IV ~ CS_IV + (1 | Subj1), data.xc, REML=TRUE)
# iv.xc.cs_iv.m3 <- lmer(IV ~ CS_IV + (1 | Subj1), data.xc, REML=TRUE)
# iv.xc.ucs_iv.m2 <- lmer(IV ~ UCS_IV + (1 | Subj1), data.xc, REML=TRUE)
# iv.xc.ucs_iv.m3 <- lmer(IV ~ UCS_IV + (1 | Subj1), data.xc, REML=TRUE)

# # 相関が 1.000 の問題を修正
# ob.fg.cs_ob.m3 <- lmer(OB ~ CS_OB + (1 | Subj2), data.fg, REML=TRUE)
# ob.xc.cs_ob.m3 <- lmer(OB ~ CS_OB + (1 | Subj2), data.xc, REML=TRUE)
# ob.fg.ucs_ob.m3 <- lmer(OB ~ UCS_OB + (1 | Subj2), data.fg, REML=TRUE)

# VarCorr(ob.fg.cs_ob.m0)
# VarCorr(iv.fg.cs_iv.m0)
# VarCorr(ob.xc.cs_ob.m0)
# VarCorr(iv.xc.cs_iv.m0)

# VarCorr(ob.fg.cs_ob.m1)
# VarCorr(iv.fg.cs_iv.m1)
# VarCorr(ob.xc.cs_ob.m1)
# VarCorr(iv.xc.cs_iv.m1)

# VarCorr(ob.fg.cs_ob.m2)
# VarCorr(iv.fg.cs_iv.m2)
# VarCorr(ob.xc.cs_ob.m2)
# VarCorr(iv.xc.cs_iv.m2)

# VarCorr(ob.fg.cs_ob.m3)
# VarCorr(iv.fg.cs_iv.m3)
# VarCorr(ob.xc.cs_ob.m3)
# VarCorr(iv.xc.cs_iv.m3)


# VarCorr(ob.fg.ucs_ob.m0)
# VarCorr(iv.fg.ucs_iv.m0)
# VarCorr(ob.xc.ucs_ob.m0)
# VarCorr(iv.xc.ucs_iv.m0)

# VarCorr(ob.fg.ucs_ob.m1)
# VarCorr(iv.fg.ucs_iv.m1)
# VarCorr(ob.xc.ucs_ob.m1)
# VarCorr(iv.xc.ucs_iv.m1)

# VarCorr(ob.fg.ucs_ob.m2)
# VarCorr(iv.fg.ucs_iv.m2)
# VarCorr(ob.xc.ucs_ob.m2)
# VarCorr(iv.xc.ucs_iv.m2)

# VarCorr(ob.fg.ucs_ob.m3)
# VarCorr(iv.fg.ucs_iv.m3)
# VarCorr(ob.xc.ucs_ob.m3)
# VarCorr(iv.xc.ucs_iv.m3)

# anova(ob.fg.ucs_ob.m1, iv.fg.ucs_iv.m1)
# anova(ob.xc.ucs_ob.m1, iv.xc.ucs_iv.m1)

# iv.xc.cs_iv_withoutRandom.m1 <- lm(IV ~ CS_IV, data = data.xc)

# AIC(iv.xc.cs_iv_withoutRandom.m1, iv.xc.cs_iv.m1)
# BIC(iv.xc.cs_iv_withoutRandom.m1, iv.xc.cs_iv.m1)

# logLik(iv.xc.cs_iv_withoutRandom.m1)
# logLik(iv.xc.cs_iv.m1)

# LR_stat <- -2 * (logLik(iv.xc.cs_iv_withoutRandom.m1) - logLik(iv.xc.cs_iv.m1))
# p_value <- pchisq(LR_stat, df = 1, lower.tail = FALSE)
# print(p_value)


# BIC(ob.fg.cs_ob.m0, ob.fg.cs_ob.m1, ob.fg.cs_ob.m2, ob.fg.cs_ob.m3)
# BIC(iv.fg.cs_iv.m0, iv.fg.cs_iv.m1, iv.fg.cs_iv.m2, iv.fg.cs_iv.m3)
# BIC(ob.xc.cs_ob.m0, ob.xc.cs_ob.m1, ob.xc.cs_ob.m2, ob.xc.cs_ob.m3)
# BIC(iv.xc.cs_iv.m0, iv.xc.cs_iv.m1, iv.xc.cs_iv.m2, iv.xc.cs_iv.m3)

# BIC(ob.fg.ucs_ob.m0, ob.fg.ucs_ob.m1, ob.fg.ucs_ob.m2, ob.fg.ucs_ob.m3)
# BIC(iv.fg.ucs_iv.m0, iv.fg.ucs_iv.m1, iv.fg.ucs_iv.m2, iv.fg.ucs_iv.m3)
# BIC(ob.xc.ucs_ob.m0, ob.xc.ucs_ob.m1, ob.xc.ucs_ob.m2, ob.xc.ucs_ob.m3)
# BIC(iv.xc.ucs_iv.m0, iv.xc.ucs_iv.m1, iv.xc.ucs_iv.m2, iv.xc.ucs_iv.m3)

######################################################################
summary(ob.fg.cs_ob.m0)
summary(ob.fg.cs_ob.m1)
summary(ob.fg.cs_ob.m2)
summary(ob.fg.cs_ob.m3)

summary(iv.fg.cs_iv.m0)
summary(iv.fg.cs_iv.m1)
summary(iv.fg.cs_iv.m2)
summary(iv.fg.cs_iv.m3)

summary(ob.xc.cs_ob.m0)
summary(ob.xc.cs_ob.m1)
summary(ob.xc.cs_ob.m2)
summary(ob.xc.cs_ob.m3)

summary(iv.xc.cs_iv.m0)
summary(iv.xc.cs_iv.m1)
summary(iv.xc.cs_iv.m2)
summary(iv.xc.cs_iv.m3)

summary(ob.fg.ucs_ob.m0)
summary(ob.fg.ucs_ob.m1)
summary(ob.fg.ucs_ob.m2)
summary(ob.fg.ucs_ob.m3)

summary(iv.fg.ucs_iv.m0)
summary(iv.fg.ucs_iv.m1)
summary(iv.fg.ucs_iv.m2)
summary(iv.fg.ucs_iv.m3)

summary(ob.xc.ucs_ob.m0)
summary(ob.xc.ucs_ob.m1)
summary(ob.xc.ucs_ob.m2)
summary(ob.xc.ucs_ob.m3)

summary(iv.xc.ucs_iv.m0)
summary(iv.xc.ucs_iv.m1)
summary(iv.xc.ucs_iv.m2)
summary(iv.xc.ucs_iv.m3)


summary(data.xc$CS_IV)
summary(data.fg$CS_IV)
summary(data.xc$UCS_IV)
summary(data.fg$UCS_IV)

summary(data.xc$CS_OB)
summary(data.fg$CS_OB)
summary(data.xc$UCS_OB)
summary(data.fg$UCS_OB)


######################################################################
######################################################################

ob.fg.cs_ob.m0.sum <- summary(ob.fg.cs_ob.m0)
iv.fg.cs_iv.m0.sum <- summary(iv.fg.cs_iv.m0)
ob.fg.cs_ob.m1.sum <- summary(ob.fg.cs_ob.m1)
iv.fg.cs_iv.m1.sum <- summary(iv.fg.cs_iv.m1)
ob.fg.cs_ob.m2.sum <- summary(ob.fg.cs_ob.m2)
iv.fg.cs_iv.m2.sum <- summary(iv.fg.cs_iv.m2)
ob.fg.cs_ob.m3.sum <- summary(ob.fg.cs_ob.m3)
iv.fg.cs_iv.m3.sum <- summary(iv.fg.cs_iv.m3)
ob.xc.cs_ob.m0.sum <- summary(ob.xc.cs_ob.m0)
iv.xc.cs_iv.m0.sum <- summary(iv.xc.cs_iv.m0)
ob.xc.cs_ob.m1.sum <- summary(ob.xc.cs_ob.m1)
iv.xc.cs_iv.m1.sum <- summary(iv.xc.cs_iv.m1)
ob.xc.cs_ob.m2.sum <- summary(ob.xc.cs_ob.m2)
iv.xc.cs_iv.m2.sum <- summary(iv.xc.cs_iv.m2)
ob.xc.cs_ob.m3.sum <- summary(ob.xc.cs_ob.m3)
iv.xc.cs_iv.m3.sum <- summary(iv.xc.cs_iv.m3)

bic.cs <- c(
BIC(ob.fg.cs_ob.m0), BIC(iv.fg.cs_iv.m0), BIC(ob.fg.cs_ob.m1), BIC(iv.fg.cs_iv.m1),
BIC(ob.fg.cs_ob.m2), BIC(iv.fg.cs_iv.m2), BIC(ob.fg.cs_ob.m3), BIC(iv.fg.cs_iv.m3),
BIC(ob.xc.cs_ob.m0), BIC(iv.xc.cs_iv.m0), BIC(ob.xc.cs_ob.m1), BIC(iv.xc.cs_iv.m1),
BIC(ob.xc.cs_ob.m2), BIC(iv.xc.cs_iv.m2), BIC(ob.xc.cs_ob.m3), BIC(iv.xc.cs_iv.m3)
)

coef.cs <- rbind(
rbind(ob.fg.cs_ob.m0.sum$coefficients, rep(0,5)),
ob.fg.cs_ob.m1.sum$coefficients,
ob.fg.cs_ob.m2.sum$coefficients,
ob.fg.cs_ob.m3.sum$coefficients,
rbind(iv.fg.cs_iv.m0.sum$coefficients, rep(0,5)),
iv.fg.cs_iv.m1.sum$coefficients,
iv.fg.cs_iv.m2.sum$coefficients,
iv.fg.cs_iv.m3.sum$coefficients,
rbind(ob.xc.cs_ob.m0.sum$coefficients, rep(0,5)),
ob.xc.cs_ob.m1.sum$coefficients,
ob.xc.cs_ob.m2.sum$coefficients,
ob.xc.cs_ob.m3.sum$coefficients,
rbind(iv.xc.cs_iv.m0.sum$coefficients, rep(0,5)),
iv.xc.cs_iv.m1.sum$coefficients,
iv.xc.cs_iv.m2.sum$coefficients,
iv.xc.cs_iv.m3.sum$coefficients
)

######################################################################
ob.fg.ucs_ob.m0.sum <- summary(ob.fg.ucs_ob.m0)
iv.fg.ucs_iv.m0.sum <- summary(iv.fg.ucs_iv.m0)
ob.fg.ucs_ob.m1.sum <- summary(ob.fg.ucs_ob.m1)
iv.fg.ucs_iv.m1.sum <- summary(iv.fg.ucs_iv.m1)
ob.fg.ucs_ob.m2.sum <- summary(ob.fg.ucs_ob.m2)
iv.fg.ucs_iv.m2.sum <- summary(iv.fg.ucs_iv.m2)
ob.fg.ucs_ob.m3.sum <- summary(ob.fg.ucs_ob.m3)
iv.fg.ucs_iv.m3.sum <- summary(iv.fg.ucs_iv.m3)
ob.xc.ucs_ob.m0.sum <- summary(ob.xc.ucs_ob.m0)
iv.xc.ucs_iv.m0.sum <- summary(iv.xc.ucs_iv.m0)
ob.xc.ucs_ob.m1.sum <- summary(ob.xc.ucs_ob.m1)
iv.xc.ucs_iv.m1.sum <- summary(iv.xc.ucs_iv.m1)
ob.xc.ucs_ob.m2.sum <- summary(ob.xc.ucs_ob.m2)
iv.xc.ucs_iv.m2.sum <- summary(iv.xc.ucs_iv.m2)
ob.xc.ucs_ob.m3.sum <- summary(ob.xc.ucs_ob.m3)
iv.xc.ucs_iv.m3.sum <- summary(iv.xc.ucs_iv.m3)

bic.ucs <- c(
BIC(ob.fg.ucs_ob.m0), BIC(iv.fg.ucs_iv.m0), BIC(ob.fg.ucs_ob.m1), BIC(iv.fg.ucs_iv.m1),
BIC(ob.fg.ucs_ob.m2), BIC(iv.fg.ucs_iv.m2), BIC(ob.fg.ucs_ob.m3), BIC(iv.fg.ucs_iv.m3),
BIC(ob.xc.ucs_ob.m0), BIC(iv.xc.ucs_iv.m0), BIC(ob.xc.ucs_ob.m1), BIC(iv.xc.ucs_iv.m1),
BIC(ob.xc.ucs_ob.m2), BIC(iv.xc.ucs_iv.m2), BIC(ob.xc.ucs_ob.m3), BIC(iv.xc.ucs_iv.m3)
)

#bic.double <- c(
#  BIC(ob.fg.double), BIC(iv.fg.double), BIC(ob.xc.double), BIC(iv.xc.double)
#)


coef.ucs <- rbind(
rbind(ob.fg.ucs_ob.m0.sum$coefficients, rep(0,5)),
ob.fg.ucs_ob.m1.sum$coefficients,
ob.fg.ucs_ob.m2.sum$coefficients,
ob.fg.ucs_ob.m3.sum$coefficients,
rbind(iv.fg.ucs_iv.m0.sum$coefficients, rep(0,5)),
iv.fg.ucs_iv.m1.sum$coefficients,
iv.fg.ucs_iv.m2.sum$coefficients,
iv.fg.ucs_iv.m3.sum$coefficients,
rbind(ob.xc.ucs_ob.m0.sum$coefficients, rep(0,5)),
ob.xc.ucs_ob.m1.sum$coefficients,
ob.xc.ucs_ob.m2.sum$coefficients,
ob.xc.ucs_ob.m3.sum$coefficients,
rbind(iv.xc.ucs_iv.m0.sum$coefficients, rep(0,5)),
iv.xc.ucs_iv.m1.sum$coefficients,
iv.xc.ucs_iv.m2.sum$coefficients,
iv.xc.ucs_iv.m3.sum$coefficients
)

bic_sorted_table <- data.frame(
  Model = c(
    "OB-FG.m0", "IV-FG.m0", "OB-FG.m1", "IV-FG.m1", 
    "OB-FG.m2", "IV-FG.m2", "OB-FG.m3", "IV-FG.m3",
    "OB-XC.m0", "IV-XC.m0", "OB-XC.m1", "IV-XC.m1",
    "OB-XC.m2", "IV-XC.m2", "OB-XC.m3", "IV-XC.m3",
    "OB-FG.m0", "IV-FG.m0", "OB-FG.m1", "IV-FG.m1", 
    "OB-FG.m2", "IV-FG.m2", "OB-FG.m3", "IV-FG.m3",
    "OB-XC.m0", "IV-XC.m0", "OB-XC.m1", "IV-XC.m1",
    "OB-XC.m2", "IV-XC.m2", "OB-XC.m3", "IV-XC.m3"
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

bic_table_name <- paste0("BICsorted_CS_rarity", threshold_cs , "UCS_rarity", threshold_ucs, ".csv")
write.table(bic_sorted_table, file=bic_table_name, sep=",", row.names=FALSE)

######################################################################
######################################################################
cs.all <- cbind(c(rbind(bic.cs, rep(0, 16))), coef.cs)

rownames(cs.all) <- c(
"OB-FG.m0.int", "OB-FG.m0.CS",  
"IV-FG.m0.int", "IV-FG.m0.CS",
"OB-FG.m1.int", "OB-FG.m1.CS",
"IV-FG.m1.int", "IV-FG.m1.CS",
"OB-FG.m2.int", "OB-FG.m2.CS",
"IV-FG.m2.int", "IV-FG.m2.CS",
"OB-FG.m3.int", "OB-FG.m3.CS",
"IV-FG.m3.int", "IV-FG.m3.CS",
"OB-XC.m0.int", "OB-XC.m0.CS",
"IV-XC.m0.int", "IV-XC.m0.CS",
"OB-XC.m1.int", "OB-XC.m1.CS",
"IV-XC.m1.int", "IV-XC.m1.CS",
"OB-XC.m2.int", "OB-XC.m2.CS",
"IV-XC.m2.int", "IV-XC.m2.CS",
"OB-XC.m3.int", "OB-XC.m3.CS",
"IV-XC.m3.int", "IV-XC.m3.CS"
)

ucs.all <- cbind(c(rbind(bic.ucs, rep(0, 16))), coef.ucs)

rownames(ucs.all) <- c(
"OB-FG.m0.int", "OB-FG.m0.UCS",  
"IV-FG.m0.int", "IV-FG.m0.UCS",
"OB-FG.m1.int", "OB-FG.m1.UCS",
"IV-FG.m1.int", "IV-FG.m1.UCS",
"OB-FG.m2.int", "OB-FG.m2.UCS",
"IV-FG.m2.int", "IV-FG.m2.UCS",
"OB-FG.m3.int", "OB-FG.m3.UCS",
"IV-FG.m3.int", "IV-FG.m3.UCS",
"OB-XC.m0.int", "OB-XC.m0.UCS",
"IV-XC.m0.int", "IV-XC.m0.UCS",
"OB-XC.m1.int", "OB-XC.m1.UCS",
"IV-XC.m1.int", "IV-XC.m1.UCS",
"OB-XC.m2.int", "OB-XC.m2.UCS",
"IV-XC.m2.int", "IV-XC.m2.UCS",
"OB-XC.m3.int", "OB-XC.m3.UCS",
"IV-XC.m3.int", "IV-XC.m3.UCS"
)

cs_filename <- paste0("CS_rarity", threshold_cs, ".csv")
ucs_filename <- paste0("UCS_rarity", threshold_ucs, ".csv")

write.table(cs.all, file=cs_filename, sep=",", row.names=T)
write.table(ucs.all, file=ucs_filename, sep=",", row.names=T)