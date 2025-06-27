# UCS vs CS 実験データ分析スクリプト
# 可読性重視・R言語

# 必要なパッケージの読み込み
library(tidyverse)
library(lubridate)

# データファイルのパス
estimations_exp1 <- 'data/estimations_exp1.csv'
estimations_exp1_2 <- 'data/estimations_exp1_2.csv'
crt_data_exp3 <- 'data/crt_data_exp3.csv'
imc_data_exp2 <- 'data/imc_data_exp2.csv'
user_data_exp1 <- 'data/user_data_exp1.csv'
user_data_exp1_2 <- 'data/user_data_exp1_2.csv'

# データ読み込み
est1 <- read_csv(estimations_exp1, show_col_types = FALSE)
est2 <- read_csv(estimations_exp1_2, show_col_types = FALSE)
crt <- read_csv(crt_data_exp3, show_col_types = FALSE)
imc <- read_csv(imc_data_exp2, show_col_types = FALSE)
user1 <- read_csv(user_data_exp1, show_col_types = FALSE)
user2 <- read_csv(user_data_exp1_2, show_col_types = FALSE)

# データの基本集計
cat('【実験1 回答数】', nrow(est1), '\n')
cat('【実験1_2 回答数】', nrow(est2), '\n')
cat('【CRTデータ件数】', nrow(crt), '\n')
cat('【IMCデータ件数】', nrow(imc), '\n')

# 実験1_2の推定値分布の可視化
est2 %>%
  ggplot(aes(x = estimation)) +
  geom_histogram(bins = 20, fill = 'skyblue', color = 'gray40') +
  labs(title = '実験1_2: 推定値の分布', x = '推定値', y = '件数')

# サンプルタイプごとの平均・標準偏差
if ('is_symmetric' %in% colnames(est2)) {
  est2 %>%
    group_by(is_symmetric) %>%
    summarise(
      n = n(),
      mean = mean(estimation, na.rm = TRUE),
      sd = sd(estimation, na.rm = TRUE)
    ) %>%
    print()
}

# ユーザーごとの回答数
est2 %>%
  count(user_id, name = '回答数') %>%
  arrange(desc(回答数)) %>%
  print(n = 10)

# CRT合計点の分布（もし列があれば）
if ('total_correct' %in% colnames(crt)) {
  crt %>%
    ggplot(aes(x = total_correct)) +
    geom_bar(fill = 'orange') +
    labs(title = 'CRT合計正答数の分布', x = '正答数', y = '人数')
}

# IMC正答率（True/Falseの割合）
if ('result' %in% colnames(imc)) {
  imc %>%
    count(result) %>%
    mutate(割合 = n / sum(n)) %>%
    print()
}

# 参加者ごとの実験1_2の回答時間（user_data_exp1_2.csvがあれば）
if ('start_time' %in% colnames(user2) && 'end_time' %in% colnames(user2)) {
  user2 %>%
    mutate(
      start = ymd_hms(start_time, quiet = TRUE),
      end = ymd_hms(end_time, quiet = TRUE),
      duration_min = as.numeric(difftime(end, start, units = 'mins'))
    ) %>%
    select(user_id, duration_min) %>%
    print(n = 10)
}

# --- ここに追加分析を記述してください ---

# 保存例: 集計結果をCSVで出力
# write_csv(集計データ, 'analysis/summary_exp1_2.csv')
