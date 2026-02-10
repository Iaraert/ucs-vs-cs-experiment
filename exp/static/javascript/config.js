/**
 * config.js - 実験全体の設定管理モジュール
 * シナリオ配布、エラー処理、画像タイプなどの設定を一元管理
 */
import { shuffleArray } from './utilities.js';

/**
 * 実験設定クラス
 */
export class ExperimentConfig {
  constructor(options = {}) {
    // JSONデータファイルのパス
    this.jsonFilePath = options.jsonFilePath || '../static/material1.json';
    
    // 画像アイコンの定義（a/b/c/d → treated_positive等のマッピング）
    this.icons = options.icons || {
      'a': {'type': 'treated_positive'},     // 処置群・ポジティブ結果
      'b': {'type': 'treated_negative'},     // 処置群・ネガティブ結果
      'c': {'type': 'non_treated_positive'}, // 非処置群・ポジティブ結果
      'd': {'type': 'non_treated_negative'}  // 非処置群・ネガティブ結果
    };
    
    // 画像タイプの一覧
    this.imageTypes = options.imageTypes || [
      "treated_positive", 
      "treated_negative", 
      "non_treated_positive", 
      "non_treated_negative"
    ];
    
    // スライダー待機時間（ミリ秒）- ユーザーがすぐに回答を変更できないようにする
    this.sliderWaitTime = options.sliderWaitTime || 3000;
    
    // 全シナリオ番号（1-12）
    this.allScenarios = [
      '1', '2', '3', '4', '5', '6', 
      '7', '8', '9', '10', '11', '12'
    ];
    
    // エラー処理設定（あまり使用されていないが残しておく）
    this.errorHandling = {
      reportEndpoint: options.errorReportEndpoint || '/api/report-error',
      enableGlobalHandlers: options.enableGlobalHandlers !== false,
      logToConsole: options.logToConsole !== false,
      recoveryPaths: options.recoveryPaths || {
        'default': '/',
        'data_submission_error': '/examine1',
        'network_error': window.location.pathname
      },
      errorMessages: options.errorMessages || {
        'network_error': 'ネットワーク接続に問題があります。インターネット接続を確認してもう一度お試しください。',
        'server_error': 'サーバーエラーが発生しました。しばらく経ってからもう一度お試しください。',
        'data_submission_error': 'データの送信中にエラーが発生しました。もう一度お試しください。',
        'unknown_error': '予期しないエラーが発生しました。ページを再読み込みしてもう一度お試しください。'
      },
      maxRetries: options.maxRetries || 3
    };
    
    this.init();
  }

  init() {
    // デフォルトで全シナリオをシャッフル（後で実験タイプに応じて分割）
    this.scenarios = shuffleArray([...this.allScenarios]);
    return this;
  }

  /**
   * 実験タイプに基づいてシナリオを6個ずつ割り当て
   * @param {string} experimentType - 'examine1'（1-6番）または 'examine1_2'（7-12番）
   * @param {string} userId - ユーザーID（同じユーザーには同じシナリオセットを割り当てる）
   */
  setExperimentScenarios(experimentType, userId) {
    // ユーザーIDから決定論的なシード値を生成
    const userSeed = this.generateSeed(userId);
    const shuffledScenarios = this.shuffleWithSeed([...this.allScenarios], userSeed);
    
    if (experimentType === 'examine1') {
      // examine1: 最初の6シナリオ
      this.scenarios = shuffledScenarios.slice(0, 6);
      console.log(`examine1: シナリオセット ${this.scenarios.join(', ')} を使用`);
    } else if (experimentType === 'examine1_2') {
      // examine1_2: 残りの6シナリオ
      this.scenarios = shuffledScenarios.slice(6, 12);
      console.log(`examine1_2: シナリオセット ${this.scenarios.join(', ')} を使用`);
    } else {
      // その他の実験は最初の6シナリオを使用
      this.scenarios = shuffledScenarios.slice(0, 6);
      console.log(`${experimentType}: デフォルトシナリオセットを使用`);
    }
    
    return this.scenarios;
  }

  /**
   * 文字列からシード値を生成（同じ文字列からは同じシード値）
   */
  generateSeed(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // 32bit整数に変換
    }
    return Math.abs(hash);
  }

  /**
   * シード値に基づく決定論的シャッフル（同じシードからは同じ順序）
   * 線形合同法でランダム値を生成し、Fisher-Yatesアルゴリズムでシャッフル
   */
  shuffleWithSeed(array, seed) {
    const shuffled = [...array];
    let currentSeed = seed;
    
    // 線形合同法でランダム値生成
    const random = () => {
      currentSeed = (currentSeed * 1103515245 + 12345) & 0x7fffffff;
      return currentSeed / 0x7fffffff;
    };
    
    // Fisher-Yatesシャッフル
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    
    return shuffled;
  }

  /**
   * 指定インデックスのシナリオ名を取得
   */
  getScenarioName(index) {
    return this.scenarios[index];
  }

  /**
   * エラータイプからエラーメッセージを取得
   */
  getErrorMessage(errorType, defaultMessage = null) {
    return this.errorHandling.errorMessages[errorType] || 
           defaultMessage || 
           this.errorHandling.errorMessages.unknown_error;
  }

  /**
   * エラータイプからリカバリーパスを取得
   */
  getRecoveryPath(errorType) {
    return this.errorHandling.recoveryPaths[errorType] || 
           this.errorHandling.recoveryPaths.default;
  }
}

// デフォルト設定のエクスポート
export default new ExperimentConfig();