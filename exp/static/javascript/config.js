/**
 * config.js - アプリケーション全体の設定モジュール
 */
import { shuffleArray } from './utilities.js';

/**
 * 実験アプリケーションの設定を管理するクラス
 */
export class ExperimentConfig {
  /**
   * コンストラクタ - 設定オブジェクトを初期化
   * @param {Object} options - 設定オプション
   */
  constructor(options = {}) {
    // デフォルト設定
    this.jsonFilePath = options.jsonFilePath || '../static/material1.json';
    this.icons = options.icons || {
      'a': {'type': 'treated_positive'},
      'b': {'type': 'treated_negative'},
      'c': {'type': 'non_treated_positive'},
      'd': {'type': 'non_treated_negative'}
    };
    this.imageTypes = options.imageTypes || [
      "treated_positive", 
      "treated_negative", 
      "non_treated_positive", 
      "non_treated_negative"
    ];
    this.sliderWaitTime = options.sliderWaitTime || 3000;
    
    this.allScenarios = [
      '1', '2', '3', '4', '5', '6', 
      '7', '8', '9', '10', '11', '12'
    ];
    
    // エラー処理とロギングの設定
    this.errorHandling = {
      // エラーレポートエンドポイント
      reportEndpoint: options.errorReportEndpoint || '/api/report-error',
      // グローバルエラーハンドラの有効化
      enableGlobalHandlers: options.enableGlobalHandlers !== false,
      // コンソールへのエラーログ出力
      logToConsole: options.logToConsole !== false,
      // リカバリーパスのマッピング
      recoveryPaths: options.recoveryPaths || {
        'default': '/',
        'data_submission_error': '/examine1',
        'network_error': window.location.pathname
      },
      // 一般的なエラーメッセージのマッピング
      errorMessages: options.errorMessages || {
        'network_error': 'ネットワーク接続に問題があります。インターネット接続を確認してもう一度お試しください。',
        'server_error': 'サーバーエラーが発生しました。しばらく経ってからもう一度お試しください。',
        'data_submission_error': 'データの送信中にエラーが発生しました。もう一度お試しください。',
        'unknown_error': '予期しないエラーが発生しました。ページを再読み込みしてもう一度お試しください。'
      },
      // エラー発生時の自動リトライ回数
      maxRetries: options.maxRetries || 3
    };
    
    // 初期化
    this.init();
  }

  /**
   * 設定を初期化する
   */
  init() {
    this.bgColors = shuffleArray(['#f0ffff','#f0fff0','#f5f5dc','#e0ffff','#fffaf0','#f8f8ff','#fffafa','#f5f5f5','#f0f8ff','#ffe4e1','#d8bfd8']);
    
    // デフォルトでは全シナリオをシャッフル（後で実験タイプに応じて分割）
    this.scenarios = shuffleArray([...this.allScenarios]);
    return this;
  }

  /**
   * 実験タイプに基づいてシナリオを設定
   * @param {string} experimentType - 'examine1' または 'examine1_2'
   * @param {string} userId - ユーザーID
   */
  setExperimentScenarios(experimentType, userId) {
    // ユーザーIDベースでシード値を生成（同じユーザーは同じシナリオセット）
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
      // その他の実験は全シナリオを使用
      this.scenarios = shuffledScenarios.slice(0, 6);
      console.log(`${experimentType}: デフォルトシナリオセットを使用`);
    }
    
    return this.scenarios;
  }

  /**
   * 文字列からシード値を生成
   * @param {string} str - 入力文字列
   * @returns {number} シード値
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
   * シード値に基づく決定論的シャッフル
   * @param {Array} array - シャッフルする配列
   * @param {number} seed - シード値
   * @returns {Array} シャッフルされた配列
   */
  shuffleWithSeed(array, seed) {
    const shuffled = [...array];
    let currentSeed = seed;
    
    // シンプルな線形合同法でランダム値生成
    const random = () => {
      currentSeed = (currentSeed * 1103515245 + 12345) & 0x7fffffff;
      return currentSeed / 0x7fffffff;
    };
    
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    
    return shuffled;
  }

  /**
   * 指定されたインデックスの背景色を取得
   * @param {number} index - シナリオのインデックス
   * @returns {string} 対応する背景色
   */
  getBgColorForIndex(index) {
    return this.bgColors[index % this.bgColors.length];
  }
  
  /**
   * 現在のシナリオ名を取得
   * @param {number} index - シナリオのインデックス
   * @returns {string} シナリオ名
   */
  getScenarioName(index) {
    return this.scenarios[index];
  }

  /**
   * エラータイプに対応するエラーメッセージを取得
   * @param {string} errorType - エラータイプ ('network_error', 'server_error', etc.)
   * @param {string} [defaultMessage] - デフォルトメッセージ（オプション）
   * @returns {string} エラーメッセージ
   */
  getErrorMessage(errorType, defaultMessage = null) {
    return this.errorHandling.errorMessages[errorType] || 
           defaultMessage || 
           this.errorHandling.errorMessages.unknown_error;
  }

  /**
   * エラータイプに対応するリカバリーパスを取得
   * @param {string} errorType - エラータイプ
   * @returns {string} リカバリーパス
   */
  getRecoveryPath(errorType) {
    return this.errorHandling.recoveryPaths[errorType] || 
           this.errorHandling.recoveryPaths.default;
  }
}

// デフォルト設定のエクスポート
export default new ExperimentConfig();