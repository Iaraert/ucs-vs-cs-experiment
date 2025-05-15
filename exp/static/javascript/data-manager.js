/**
 * data-manager.js - 実験データの管理と送信を担当するモジュール
 */
import { getNow, getOrCreateUserId } from './utilities.js';
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
  }

  /**
   * データマネージャーの初期化
   * @returns {Promise} 初期化処理のPromise
   */
  async init() {
    this.startTime = getNow();
    try {
      await this.loadExperimentData();
      this.estimations = [];
      this.loadOrGenerateUserId();
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
      return this.experimentData;
    } catch (error) {
      console.error('実験データの読み込みに失敗しました', error);
      throw error;
    }
  }
  
  /**
   * ユーザーIDの生成または復元
   */
  loadOrGenerateUserId() {
    this.userId = getOrCreateUserId();
    console.log(`ユーザーID: ${this.userId}`);
    
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
    const sampleNumber = this.determineSampleNumber();
    const sampleData = this.experimentData[scenarioKey]['samples'][sampleNumber.toString()];
    
    console.log(`シナリオ ${scenarioKey} ⇒ サンプル${sampleNumber} 使用`);
    
    // サンプルデータを保存
    this.currentSampleData = {
      'a': sampleData.a,
      'b': sampleData.b,
      'c': sampleData.c,
      'd': sampleData.d,
      'sample_type': this.sampleType,
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
  recordResponse(value) {
    let data = {
      'user_id': this.userId,
      'scenario': this.getCurrentScenarioKey(),
      'stimulus_data': this.currentSampleData,
      'response': value,
      'sample_type': this.sampleType,
      'timestamp': getNow()
    };
    
    this.estimations.push(data);
    console.log("回答を記録しました:", data);
    
    // 回答記録イベントを通知（Observerパターン）
    eventBus.emit('response:recorded', { responseData: data });
    
    return data;
  }
  
  /**
   * 次のシナリオに進む
   */
  moveToNextScenario() {
    this.currentScenarioIndex++;
    
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
    return this.currentScenarioIndex >= config.scenarios.length - 1;
  }
  
  /**
   * 実験結果をサーバーに送信
   * @param {string} nextUrl - 送信成功時のリダイレクト先URL
   * @returns {Promise} 送信処理のPromise
   */
  async exportResults(nextUrl) {
    // 送信開始イベントを通知
    eventBus.emit('results:exporting', { userId: this.userId });
    
    const data = {
      'user_id': this.userId,
      'start_time': this.startTime,
      'end_time': getNow(),
      'user_agent': window.navigator.userAgent,
      'sample_type': this.sampleType
    };
    
    this.userData.push(data);

    try {
      const response = await postData('/send', {
        'user_data': JSON.stringify(this.userData),
        'estimations': JSON.stringify(this.estimations),
        'file_name_suffix': 'exp1'
      }, {
        timeout: 50000
      });
      
      // 送信成功イベントを通知（Observerパターン）
      eventBus.emit('results:exported', { 
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
}

// デフォルトインスタンスをエクスポート
export default new DataManager();