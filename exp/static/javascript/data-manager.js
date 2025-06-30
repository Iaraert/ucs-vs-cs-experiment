/**
 * data-manager.js - 実験データの管理と送信を担当するモジュール
 */
import { getNow, getOrCreateUserId, getProgressToken, isAlreadyParticipated } from './utilities.js';
import { fetchJson, fetchWithRetry, handleAjaxError, postData } from './ajax-utils.js';
import config from './config.js';
import eventBus from './event-bus.js';

/**
 * 実験データを管理するクラス
 */
export class DataManager {
  /**
   * コンストラクタ - データマネージャーを初期化
   */
  constructor() {
    this.experimentData = null;   // JSONから読み込んだ実験データ
    this.userData = [];           // ユーザー情報データ
    this.estimations = [];        // 回答結果データ
    this.currentScenarioIndex = 0; // 現在のシナリオインデックス
    this.currentSampleData = {};   // 現在表示中のサンプルデータ
    this.userId = null;            // ユーザーID
    this.sampleType = null;        // 実験条件（対称/非対称）
    this.startTime = '';           // 実験開始時間
    this.customData = {};          // カスタムデータストレージ
    this.experimentType = '';      // 実験タイプ（eXaMinE1, eXaM1nE_2など）
    this.totalPages = 6;           // 実験の総ページ数（eXaM1nE_2のデフォルト）
    this.sampleNumberList = [];    // examine1用サンプル番号リスト
  }

  /**
   * データマネージャーの初期化
   * @returns {Promise} 初期化処理のPromise
   */
  async init() {
    // ★ ここで必ずstartTimeを初期化する
    this.startTime = getNow();
    try {
      await this.loadExperimentData();
      this.estimations = [];
      this.loadOrGenerateUserId();
      
      // 実験タイプが設定されている場合、シナリオを設定
      if (this.experimentType && this.userId) {
        this.setupExperimentScenarios();
      }
      
      return this;
    } catch (error) {
      handleAjaxError(error, '実験データの読み込みに失敗しました');
      return this;
    }
  }

  /**
   * 実験タイプに基づいてシナリオを設定
   */
  setupExperimentScenarios() {
    if (!this.experimentType || !this.userId) {
      console.warn('実験タイプまたはユーザーIDが設定されていません');
      return;
    }
    
    // シナリオ配布の永続化チェック
    const storageKey = `scenario_assignment_${this.experimentType}_${this.userId}`;
    let assignedScenarios = null;
    
    try {
      assignedScenarios = JSON.parse(localStorage.getItem(storageKey));
    } catch (e) {
      console.warn('保存されたシナリオ配布の読み込みに失敗:', e);
    }
    
    if (assignedScenarios && Array.isArray(assignedScenarios) && assignedScenarios.length === 6) {
      // 既存の配布を使用
      config.scenarios = assignedScenarios;
      console.log(`既存のシナリオ配布を復元: ${assignedScenarios.join(', ')}`);
    } else {
      // 新しい配布を生成
      const scenarios = config.setExperimentScenarios(this.experimentType, this.userId);
      
      // 配布を永続化
      try {
        localStorage.setItem(storageKey, JSON.stringify(scenarios));
        console.log(`シナリオ配布を保存: ${scenarios.join(', ')}`);
      } catch (e) {
        console.warn('シナリオ配布の保存に失敗:', e);
      }
    }
    // examine1の場合のみサンプル番号リストをシャッフルしてセット
    if (this.experimentType === 'eXaMinE1') {
      this.sampleNumberList = shuffleArray([1,2,3,4,5,6]);
      console.log('examine1: サンプル番号リスト（重複なし）:', this.sampleNumberList);
    }
    // シナリオ配布情報をイベントで通知
    eventBus.emit('scenarios:assigned', { 
      experimentType: this.experimentType,
      userId: this.userId,
      scenarios: config.scenarios
    });
  }

  /**
   * 実験タイプを設定
   * @param {string} experimentType - 実験タイプ
   */
  setExperimentType(experimentType) {
    this.experimentType = experimentType;
    console.log(`実験タイプを設定: ${experimentType}`);
    
    // 既にユーザーIDが設定されている場合、シナリオを設定
    if (this.userId) {
      this.setupExperimentScenarios();
    }
  }

  /**
   * データマネージャーの初期化
   * @param {string|null} userId - 既存のユーザーID（オプション）
   * @returns {Promise} 初期化処理のPromise
   */
  async init(userId = null) {
    // ★ ここでも必ずstartTimeを初期化する
    this.startTime = getNow();
    try {
      await this.loadExperimentData();
      this.estimations = [];
      
      // ユーザーIDが指定されている場合はそれを使用、そうでなければ生成/復元
      if (userId) {
        this.userId = userId;
        console.log(`指定されたユーザーIDを使用: ${this.userId}`);
      } else {
        this.loadOrGenerateUserId();
      }
      
      // 実験タイプが設定されている場合、シナリオを設定
      if (this.experimentType && this.userId) {
        this.setupExperimentScenarios();
      }
      
      return this;
    } catch (error) {
      handleAjaxError(error, '実験データの読み込みに失敗しました');
      return this;
    }
  }
    
  /**
   * 実験用JSONデータを読み込む
   * @returns {Promise} データ読み込みのPromise
   */
  async loadExperimentData() {
    try {
      this.experimentData = await fetchJson(config.jsonFilePath);
      console.log('実験データを読み込みました');
      
      // 共通サンプルデータを読み込み、samples_refを解決
      await this.resolveCommonSamples();
      
      return this.experimentData;
    } catch (error) {
      console.error('実験データの読み込みに失敗しました', error);
      throw error;
    }
  }

  /**
   * 共通サンプルデータを読み込み、samples_refを解決する
   * @returns {Promise} 共通サンプル読み込みのPromise
   */
  async resolveCommonSamples() {
    try {
      // 共通サンプルデータを読み込み
      const commonSamplesData = await fetchJson('../static/samples_common.json');
      console.log('共通サンプルデータを読み込みました');
      
      // 各シナリオのsamples_refを解決
      Object.keys(this.experimentData).forEach(scenarioKey => {
        const scenario = this.experimentData[scenarioKey];
        if (scenario.samples_ref && commonSamplesData[scenario.samples_ref]) {
          // samples_refが指定されている場合、共通データで置き換え
          scenario.samples = commonSamplesData[scenario.samples_ref];
          console.log(`シナリオ ${scenarioKey} のsamples_refを解決しました: ${scenario.samples_ref}`);
        }
      });
    } catch (error) {
      console.warn('共通サンプルデータの読み込みに失敗しました。既存のsamplesデータを使用します。', error);
    }
  }
  
  /**
   * ユーザーIDの生成または復元
   */
  loadOrGenerateUserId() {
    this.userId = getOrCreateUserId();
    console.log(`ユーザーID: ${this.userId}`);
    
    // 実験タイプが設定されている場合、シナリオを設定
    if (this.experimentType) {
      this.setupExperimentScenarios();
    }
    
    // ユーザーID取得イベントを通知（Observerパターン）
    eventBus.emit('user:idLoaded', { userId: this.userId });
  }
  
  /**
   * サーバーから条件を取得する
   * @returns {Promise} 条件取得のPromise
   */
  async fetchSampleType() {
    try {
      // 条件を取得前のイベント通知
      eventBus.emit('sampleType:fetching', { userId: this.userId });
      
      // 条件を取得
      const response = await fetchWithRetry({
        type: 'GET',
        url: '/getSampleType',
        data: { user_id: this.userId },
        dataType: 'json'
      });
      
      this.sampleType = response.sampleType;
      console.log(`条件を設定: ${this.sampleType} (ユーザーID: ${this.userId})`);
      
      // 条件取得成功イベントを通知（Observerパターン）
      eventBus.emit('sampleType:fetched', { 
        sampleType: this.sampleType, 
        userId: this.userId 
      });
      
      // 条件設定を通知（エラーがあっても処理を続行）
      try {
        await fetchWithRetry({
          type: 'GET',
          url: '/setSampleType',
          data: { user_id: this.userId, sampleType: this.sampleType },
          dataType: 'json',
          showLoadingUI: false, // ローディングUIを表示しない
          retryCount: 1 // 再試行は1回のみ
        });
      } catch (notifyError) {
        console.log("サーバーへの条件設定通知が失敗しましたが処理を続行します。", notifyError);
        // エラーイベント通知
        eventBus.emit('sampleType:notifyError', { error: notifyError });
      }
      
      return this.sampleType;
    } catch (error) {
      console.log("条件取得に失敗しました。デフォルトで非対称条件を使用します。", error);
      this.sampleType = 'asymmetric';
      
      // エラーイベント通知
      eventBus.emit('sampleType:error', { 
        error: error,
        defaultSampleType: this.sampleType 
      });
      
      return this.sampleType;
    }
  }
  
  /**
   * 現在のシナリオキーを取得
   * @returns {string} 現在のシナリオキー
   */
  getCurrentScenarioKey() {
    return config.getScenarioName(this.currentScenarioIndex);
  }
  
  /**
   * 現在のシナリオデータを取得
   * @returns {Object} 現在のシナリオデータ
   */
  getCurrentScenarioData() {
    return this.experimentData[this.getCurrentScenarioKey()];
  }
  
  /**
   * 表示するサンプル番号を決定
   * @returns {number} 使用するサンプル番号
   */
  determineSampleNumber() {
    return ((this.currentScenarioIndex % 2) + 1) * 3 - Math.floor(Math.random() * 3);
  }
  
  /**
   * サンプルデータを準備
   */
  prepareSampleData() {
    const scenarioKey = this.getCurrentScenarioKey();
    let sampleNumber;
    // examine1は重複なしリストから取得、それ以外は従来ロジック
    if (this.experimentType === 'eXaMinE1' && this.sampleNumberList.length === 6) {
      sampleNumber = this.sampleNumberList[this.currentScenarioIndex];
    } else {
      sampleNumber = this.determineSampleNumber();
    }
    const sampleData = this.experimentData[scenarioKey]['samples'][sampleNumber.toString()];
    console.log(`シナリオ ${scenarioKey} ⇒ サンプル${sampleNumber} 使用`);
    
    // サンプルデータを保存（sample_typeは除外）
    this.currentSampleData = {
      'a': sampleData.a,
      'b': sampleData.b,
      'c': sampleData.c,
      'd': sampleData.d,
      'sample_number': sampleNumber
    };
    
    console.log(`使用するサンプルデータ:`, this.currentSampleData);
    
    // サンプルデータ準備イベントを通知（Observerパターン）
    eventBus.emit('sample:prepared', { 
      scenarioKey: scenarioKey,
      sampleData: this.currentSampleData 
    });
    
    return this.currentSampleData;
  }


  
  /**
   * 回答データを記録
   * @param {number|string} value - 回答値
   */
  async recordResponse(value) {
    // 実験順序を取得
    let experimentOrder = 'order1'; // デフォルト値
    try {
      const { getExperimentOrder } = await import('./utilities.js');
      experimentOrder = await getExperimentOrder(this.userId, false);
    } catch (error) {
      console.warn('実験順序の取得に失敗しました。デフォルト値を使用します:', error);
    }

    // is_first を 0/1 に変換
    // eXaMinE1: order1の場合に最初 (eXaMinE1 → eXaM1nE_2)
    // eXaM1nE_2: order2の場合に最初 (eXaM1nE_2 → eXaMinE1)
    let isFirstNumeric;
    if (this.experimentType === 'eXaMinE1') {
      isFirstNumeric = experimentOrder === 'order1' ? 1 : 0;
    } else if (this.experimentType === 'eXaM1nE_2') {
      isFirstNumeric = experimentOrder === 'order2' ? 1 : 0;
    } else {
      // デフォルト（eXaMinE1のロジック）
      isFirstNumeric = experimentOrder === 'order1' ? 1 : 0;
    }
    
    // is_symmetric を 0/1 に変換
    const isSymmetricNumeric = this.sampleType === 'symmetric' ? 1 : 0;

    // 最適化されたデータ構造：a, b, c, d を個別の列として記録
    let data = {
      'user_id': this.userId,
      'cover_story': this.getCurrentScenarioKey(),
      'a_value': this.currentSampleData ? this.currentSampleData.a : null,
      'b_value': this.currentSampleData ? this.currentSampleData.b : null,
      'c_value': this.currentSampleData ? this.currentSampleData.c : null,
      'd_value': this.currentSampleData ? this.currentSampleData.d : null,
      'estimation': value,
      'is_first': isFirstNumeric,
      'is_symmetric': isSymmetricNumeric,
      'sample_number': this.currentSampleData ? this.currentSampleData.sample_number : null,
      'timestamp': getNow()
    };
    
    this.estimations.push(data);
    console.log("回答を記録しました（最適化済み、is_first/is_symmetric は 0/1 形式）:", data);

    // 回答記録イベントを通知（Observerパターン）
    eventBus.emit('response:recorded', { responseData: data });
    return data;
  }
  
  /**
   * 次のシナリオに進む
   */
  moveToNextScenario() {
    // シナリオを1つ進める
    this.currentScenarioIndex++;
    // --- 進捗ログを追加 ---
    console.log(`[moveToNextScenario] currentScenarioIndex=${this.currentScenarioIndex}`);
    // シナリオ変更イベントを通知（Observerパターン）
    eventBus.emit('scenario:changed', { 
      index: this.currentScenarioIndex,
      key: this.getCurrentScenarioKey(),
      isComplete: this.isExperimentComplete() 
    });
    return this.currentScenarioIndex;
  }

  /**
   * シナリオが全て終了したかチェック
   * @returns {boolean} 全シナリオ終了時はtrue
   */
  isExperimentComplete() {
    // --- 進捗ログを追加 ---
    console.log(`[isExperimentComplete] currentScenarioIndex=${this.currentScenarioIndex}, total=${config.scenarios.length}`);
    return this.currentScenarioIndex >= config.scenarios.length;
  }

  /**
   * 配布されたシナリオ情報を取得
   * @returns {Object} シナリオ配布情報
   */
  getScenarioAssignment() {
    return {
      experimentType: this.experimentType,
      userId: this.userId,
      scenarios: config.scenarios,
      currentIndex: this.currentScenarioIndex,
      totalCount: config.scenarios.length
    };
  }

  /**
   * 配布されたシナリオリストを取得
   * @returns {Array} シナリオのリスト
   */
  get scenarios() {
    return config.scenarios || [];
  }

  /**
   * 実験結果をサーバーに送信（eXaMinE1用）
   * @param {string} nextUrl - 送信成功時のリダイレクト先URL
   * @returns {Promise} 送信処理のPromise
   */
  async exportResults(nextUrl) {
    // 送信開始イベントを通知
    eventBus.emit('results:exporting', { userId: this.userId });
    
    console.log('exportResults: 開始 - ユーザーID:', this.userId);
    console.log('exportResults: 遷移先URL:', nextUrl);
    
    const data = {
      'user_id': this.userId,
      'start_time': this.startTime,
      'end_time': getNow(),
      'user_agent': window.navigator.userAgent,
      'sample_type': this.sampleType
    };
    
    this.userData.push(data);

    try {
      // eXaM1nE_2の場合はfile_name_suffixをexp1_2にする
      let fileNameSuffix = 'exp1';
      if (this.experimentType === 'eXaM1nE_2') {
        fileNameSuffix = 'exp1_2';
      }
      // --- ここでlocalStorageに6件分のデータを保存 ---
      try {
        if (this.experimentType === 'eXaMinE1') {
          localStorage.setItem(`estimations_eXaMinE1_${this.userId}`, JSON.stringify(this.estimations));
        } else if (this.experimentType === 'eXaM1nE_2') {
          localStorage.setItem(`estimations_eXaM1nE_2_${this.userId}`, JSON.stringify(this.estimations));
        }
      } catch (e) {
        // 保存失敗時は何もしない
        console.warn('estimationsのlocalStorage保存に失敗:', e);
      }
      const response = await postData('/send', {
        'user_data': JSON.stringify(this.userData),
        'estimations': JSON.stringify(this.estimations),
        'file_name_suffix': fileNameSuffix,
        'progress_token': getProgressToken()
      }, {
        timeout: 50000
      });
      // 送信成功時にフラグ保存
      if (this.experimentType === 'eXaMinE1') {
        localStorage.setItem(`eXaMinE1_sent_${this.userId}`, 'sent');
      } else if (this.experimentType === 'eXaM1nE_2') {
        localStorage.setItem(`eXaM1nE_2_sent_${this.userId}`, 'sent');
      }
      // 実験完了時に参加済みフラグをセット
      try {
        localStorage.setItem('already_participated', '1');
      } catch (e) {
        console.warn('already_participatedフラグのlocalStorage保存に失敗:', e);
      }
      
      // 送信成功イベントを通知（Observerパターン）
      eventBus.emit('results:exported', { 
        userId: this.userId,
        response: response,
        nextUrl: nextUrl
      });
      
      console.log(`exportResults: リダイレクト先URL: ${nextUrl}`);
      console.log(`exportResults: 現在のユーザーID: ${this.userId}`);
      
      if (nextUrl) {
        console.log(`exportResults: ページ遷移実行 - ${nextUrl}`);
        location.href = nextUrl;
      }
      
      return response;
    } catch (error) {
      handleAjaxError(error, '回答送信中にエラーが発生しました。もう一度送信ボタンを押してください。');
      
      // エラーイベントを通知
      eventBus.emit('results:exportError', { error: error });
      
      throw error;
    }
  }
  
  /**
   * CRT/IMC テスト結果を送信する
   * @param {Object} data - 送信するデータ
   * @param {string} suffix - ファイル名のサフィックス
   * @param {string} nextUrl - 送信成功時のリダイレクト先URL
   * @returns {Promise} 送信処理のPromise
   */
  async sendTestResults(data, suffix, nextUrl) {
    // テスト結果送信開始イベントを通知
    eventBus.emit('testResults:sending', { 
      testType: suffix === 'exp3' ? 'CRT' : 'IMC',
      userId: this.userId 
    });
    
    try {
      const response = await postData('/send_imc', {
        [suffix === 'exp3' ? 'crt_data' : 'user_data']: JSON.stringify(data),
        'file_name_suffix': suffix
      }, {
        timeout: 50000
      });
      // 送信成功時にフラグ保存
      if (suffix === 'exp2') {
        localStorage.setItem(`examine2_sent_${this.userId}`, 'sent');
      } else if (suffix === 'exp3') {
        localStorage.setItem(`examine3_sent_${this.userId}`, 'sent');
      }
      
      // テスト結果送信成功イベントを通知（Observerパターン）
      eventBus.emit('testResults:sent', { 
        testType: suffix === 'exp3' ? 'CRT' : 'IMC',
        userId: this.userId,
        response: response,
        nextUrl: nextUrl
      });
      
      if (nextUrl) {
        location.href = nextUrl;
      }
      
      return response;
    } catch (error) {
      handleAjaxError(error, '回答送信中にエラーが発生しました。もう一度送信ボタンを押してください。');
      
      // エラーイベントを通知
      eventBus.emit('testResults:error', { 
        testType: suffix === 'exp3' ? 'CRT' : 'IMC',
        error: error 
      });
      
      throw error;
    }
  }
  
  /**
   * eXaM1nE_2実験の結果を送信
   * @param {Array} estimations - 推定値データ
   * @param {string} nextUrl - 送信成功時のリダイレクト先URL
   * @returns {Promise} 送信処理のPromise
   */
  async sendExamine12Results(estimations, nextUrl) {
    // 実験結果送信開始イベントを通知
    eventBus.emit('examine12Results:sending', { 
      userId: this.userId,
      dataCount: estimations.length
    });
    
    try {
      console.log('sendExamine12Results: 開始 - ユーザーID:', this.userId);
      console.log('sendExamine12Results: 遷移先URL:', nextUrl);
      
      // ユーザーデータを準備
      const userData = [{
        'user_id': this.userId,
        'start_time': this.startTime,
        'end_time': getNow(),
        'user_agent': window.navigator.userAgent
      }];
      
      // --- ここでlocalStorageに6件分のデータを保存 ---
      try {
        localStorage.setItem(`estimations_eXaM1nE_2_${this.userId}`, JSON.stringify(estimations));
      } catch (e) {
        console.warn('estimations_eXaM1nE_2のlocalStorage保存に失敗:', e);
      }
      const response = await postData('/send', {
        'user_data': JSON.stringify(userData),
        'estimations': JSON.stringify(estimations),
        'file_name_suffix': 'exp1_2',
        'progress_token': getProgressToken()
      }, {
        timeout: 50000
      });
      // 送信成功時にフラグ保存
      localStorage.setItem(`eXaM1nE_2_sent_${this.userId}`, 'sent');
      // 実験完了時に参加済みフラグをセット
      try {
        localStorage.setItem('already_participated', '1');
      } catch (e) {
        console.warn('already_participatedフラグのlocalStorage保存に失敗:', e);
      }
      
      // 実験結果送信成功イベントを通知
      eventBus.emit('examine12Results:sent', { 
        userId: this.userId,
        response: response,
        nextUrl: nextUrl
      });
      
      console.log(`sendExamine12Results: リダイレクト先URL: ${nextUrl}`);
      console.log(`sendExamine12Results: 現在のユーザーID: ${this.userId}`);
      
      if (nextUrl) {
        console.log(`sendExamine12Results: ページ遷移実行 - ${nextUrl}`);
        location.href = nextUrl;
      }
      
      return response;
    } catch (error) {
      handleAjaxError(error, '回答送信中にエラーが発生しました。もう一度終了ボタンを押してください。');
      
      // エラーイベントを通知
      eventBus.emit('examine12Results:error', { 
        error: error,
        userId: this.userId
      });
      
      throw error;
    }
  }
  
  /**
   * 指定ページで進捗条件を満たしているか判定
   * @param {string} page - 'eXaMinE1' | 'eXaM1nE_2' | 'Ex2' | 'examine3'
   * @returns {boolean}
   */
  isPageSubmissionValid(page) {
    try {
      // 6つ目のシナリオで送信時のみ、orderに従った次ページへの進入許可を判定
      // それ以外の判定方法は削除
      if (page === 'eXaMinE1' || page === 'eXaM1nE_2') {
        // 6件目の回答時のみ許可
        return this.estimations.length === 6;
      }
      // Ex2, examine3はorderに従った進入許可のみ（送信済みフラグ等は判定しない）
      if (page === 'Ex2' || page === 'examine3') {
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }
}

// デフォルトインスタンスをエクスポート
export default new DataManager();

// ページロード時に参加済み判定
window.addEventListener('DOMContentLoaded', function() {
  if (isAlreadyParticipated()) {
    const btn = document.getElementById('participate_btn');
    if (btn) btn.style.display = 'none';
    const msg = document.getElementById('already_participated_msg');
    if (msg) msg.style.display = 'block';
  }
});

/**
 * 配列をシャッフルするユーティリティ関数
 * @param {Array} array - シャッフル対象の配列
 * @returns {Array} シャッフルされた配列
 */
function shuffleArray(array) {
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
  }
  return array;
}