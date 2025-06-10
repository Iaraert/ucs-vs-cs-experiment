/**
 * examine1_2.js - 因果関係の強さを推定する実験
 * examine1の堅牢でシンプルな設計パターンを採用
 */
import config from './config.js';
import dataManager from './data-manager.js';
import uiManager from './ui-manager.js';
import eventHandler from './event-handler.js';
import { preventBrowserBack, setupPageLeaveWarning, shuffleArray } from './utilities.js';

/**
 * 実験1.2の管理クラス - examine1のシンプルな設計パターンを採用
 */
class Experiment12Manager {
  constructor() {
    // 実験タイプを設定
    dataManager.setExperimentType('examine1_2');
    
    // examine1_2固有の設定
    this.currentTestPage = 0;
    this.sampleSize = 0;
    this.scenarioIndex = 0;
    this.currentSampleSelection = [];
    this.cellSize = 0;
    this.estimationIndex = 0;
    this.sampleType = 'asymmetric'; // デフォルトは非対称条件
    
    // 画像組み合わせ設定
    this.bgcolors = shuffleArray([
      '#f0ffff','#f0fff0','#f5f5dc','#e0ffff','#fffaf0',
      '#f8f8ff','#fffafa','#f5f5f5','#f0f8ff','#ffe4e1','#d8bfd8'
    ]);
    this.imageType = ["p", "notp", "q", "notq"];
    this.imgCombination = {
      'a': {'cause': 'p', 'effect': 'q'},
      'b': {'cause': 'p', 'effect': 'notq'},
      'c': {'cause': 'notp', 'effect': 'q'},
      'd': {'cause': 'notp', 'effect': 'notq'}
    };
  }
  /**
   * examine1の設計に従った3段階初期化
   * DataManager → UIManager → EventHandler の順序で初期化
   */
  async initialize() {
    try {
      // DataManagerを初期化
      await dataManager.init();
      
      // UIManagerを初期化
      uiManager.init();
      
      // EventHandlerを初期化
      eventHandler.init();
      
      // examine1_2固有の初期化
      await this.initializeExamine12Specific();
      
      // ページ離脱警告を設定
      setupPageLeaveWarning(true);
      
      // 最初のシナリオ説明を表示
      uiManager.displayScenarioDescription(true);
      
      console.log('examine1_2: 初期化完了');
      
    } catch (error) {
      console.error('examine1_2の初期化に失敗しました:', error);
      uiManager.showErrorMessage('実験の準備中にエラーが発生しました。ページを再読み込みしてください。');
    }
  }
      this.displayDetailedError(error);
      
      // エラーレポート送信
      if (window.reportError) {
        window.reportError('examine1_2初期化エラー', error, {
          initializationState: this.initializationState,
          timestamp: new Date().toISOString(),
          userAgent: navigator.userAgent
        });
      }
      
      return false;
    }
  }

  /**
   * DataManagerの初期化 (段階1) - データ管理基盤の確立
   * examine1の設計に従い、エラーハンドリングを強化
   */
  async initializeDataManager() {
    try {
      console.log('examine1_2: DataManager初期化開始 - データ管理基盤の確立');
      
      // 前提条件の確認
      if (!dataManager) {
        throw new Error('DataManagerが読み込まれていません');
      }
      
      // 基本的なDataManagerの初期化
      await dataManager.init();
      console.log('examine1_2: ✓ DataManager基本初期化完了');
      
      // ユーザー識別情報の設定
      dataManager.userId = getOrCreateUserId({ persistent: true });
      if (!dataManager.userId) {
        throw new Error('ユーザーIDの生成に失敗しました');
      }
      dataManager.startTime = getNow();
      
      // examine1_2固有のデータ構造を初期化
      dataManager.customData = {
        estimations: [],
        sampleType: this.sampleType,
        testResponses: [],
        scenarioData: [],
        participantData: {
          userId: dataManager.userId,
          startTime: dataManager.startTime,
          experimentType: 'examine1_2'
        }
      };
      
      // データ整合性の確認
      if (!dataManager.customData.estimations || !dataManager.customData.participantData) {
        throw new Error('データ構造の初期化に失敗しました');
      }
      
      console.log('examine1_2: ✓ DataManager初期化完了 - ユーザーID:', dataManager.userId);
      
    } catch (error) {
      console.error('❌ DataManagerの初期化に失敗:', error);
      throw new Error(`データ管理システムの初期化に失敗しました: ${error.message}`);
    }
  }

  /**
   * UIManagerの初期化 (段階2) - UI制御システムの確立
   * examine1の設計に従い、UI操作を完全に抽象化
   */
  async initializeUIManager() {
    try {
      console.log('examine1_2: UIManager初期化開始 - UI制御システムの確立');
      
      // 前提条件の確認
      if (!uiManager) {
        throw new Error('UIManagerが読み込まれていません');
      }
      
      // DataManagerの初期化状態を確認
      if (!this.initializationState.dataManager) {
        throw new Error('DataManagerが初期化されていません');
      }
      
      // 基本的なUIManagerの初期化 - awaitを使用
      const initResult = await uiManager.init();
      if (!initResult) {
        throw new Error('UIManagerの基本初期化に失敗しました');
      }
      console.log('examine1_2: ✓ UIManager基本初期化完了');
      
      // examine1_2固有のUI設定
      await this.setupUIConfiguration();
      console.log('examine1_2: ✓ UI設定完了');
      
      console.log('examine1_2: ✓ UIManager初期化完了 - UI制御システム確立');
      
    } catch (error) {
      console.error('❌ UIManagerの初期化に失敗:', error);
      throw new Error(`UI管理システムの初期化に失敗しました: ${error.message}`);
    }
  }

  /**
   * examine1_2固有のUI設定
   */
  async setupUIConfiguration() {
    try {
      console.log('examine1_2: UI設定開始');
      
      // ページスタイルを読み込み
      await loadPageStyles('examine1_2');
      console.log('examine1_2: ✓ ページスタイル読み込み完了');
      
      // UI設定をUIManagerに登録
      const uiConfig = {
        experimentType: 'examine1_2',
        bgcolors: this.bgcolors,
        imageTypes: this.imageType,
        imgCombination: this.imgCombination
      };
      
      if (uiManager.registerExperimentUI) {
        uiManager.registerExperimentUI(uiConfig);
        console.log('examine1_2: ✓ UI設定登録完了');
      } else {
        console.warn('examine1_2: registerExperimentUIメソッドが利用できません - スキップ');
      }
      
    } catch (error) {
      console.error('❌ UI設定に失敗:', error);
      // 致命的ではないため、警告レベルとして処理
      console.warn('examine1_2: UI設定に問題がありましたが、処理を続行します');
    }
  }

  /**
   * EventHandlerの初期化 (段階3) - イベント処理システムの確立
   * examine1の設計に従い、イベント処理を一元化
   */
  async initializeEventHandler() {
    try {
      console.log('examine1_2: EventHandler初期化開始 - イベント処理システムの確立');
      
      // 前提条件の確認
      if (!eventHandler) {
        throw new Error('EventHandlerが読み込まれていません');
      }
      
      // UIManagerの初期化状態を確認
      if (!this.initializationState.uiManager) {
        throw new Error('UIManagerが初期化されていません');
      }
      
      // 基本的なEventHandlerの初期化 - awaitを使用
      await eventHandler.init();
      console.log('examine1_2: ✓ EventHandler基本初期化完了');
      
      // examine1_2固有のイベントハンドラーを設定
      await this.setupExamine12Events();
      console.log('examine1_2: ✓ examine1_2固有イベント設定完了');
      
      console.log('examine1_2: ✓ EventHandler初期化完了 - イベント処理システム確立');
      
    } catch (error) {
      console.error('❌ EventHandlerの初期化に失敗:', error);
      throw new Error(`イベント処理システムの初期化に失敗しました: ${error.message}`);
    }
  }

  /**
   * examine1_2固有のイベント設定
   */
  async setupExamine12Events() {
    try {
      console.log('examine1_2: examine1_2固有のイベント設定を行います');
      
      // ここにexamine1_2固有のイベント設定を記述
      // 例: eventHandler.registerEvent('estimate:complete', this.handleEstimateComplete.bind(this));
      
      // setupExamine12Eventsメソッドが実装されていない場合のダミー実装
      console.log('examine1_2: イベント設定完了');
      return true;
      
    } catch (error) {
      console.error('examine1_2固有のイベント設定に失敗:', error);
      throw new Error(`イベント設定に失敗しました: ${error.message}`);
    }
  }

  /**
   * examine1_2固有の初期化 (段階4) - 実験固有設定の確立
   * examine1の設計に従い、実験固有の設定を段階的に初期化
   */
  async initializeExamine12Specific() {
    try {
      console.log('examine1_2: examine1_2固有初期化開始 - 実験設定確立');
      
      // EventHandlerの初期化状態を確認
      if (!this.initializationState.eventHandler) {
        throw new Error('EventHandlerが初期化されていません');
      }
      
      // 実験データを読み込み
      await this.loadExperimentData();
      console.log('examine1_2: ✓ 実験データ読み込み完了');
      
      // 実験条件を取得
      await this.fetchSampleType();
      console.log('examine1_2: ✓ 実験条件取得完了');
      
      // 画像をプリロード
      await this.preloadImages();
      console.log('examine1_2: ✓ 画像プリロード完了');
      
      // レイジーローディングを設定
      this.setupLazyLoading();
      console.log('examine1_2: ✓ レイジーローディング設定完了');
      
      // シナリオ設定を確認・準備
      await this.ensureScenariosReady();
      console.log('examine1_2: ✓ シナリオ準備完了');
      
      console.log('examine1_2: ✓ examine1_2固有初期化完了 - 実験設定確立');
      
    } catch (error) {
      console.error('❌ examine1_2固有の初期化に失敗:', error);
      throw new Error(`実験固有の設定の初期化に失敗しました: ${error.message}`);
    }
  }

  /**
   * 最終初期化設定 (段階5) - ページ保護と最初の画面表示
   */
  async finalizeInitialization() {
    try {
      console.log('examine1_2: 最終初期化開始 - ページ保護と画面表示');
      
      // examine1_2固有設定の初期化状態を確認
      if (!this.initializationState.examine12Specific) {
        throw new Error('examine1_2固有設定が初期化されていません');
      }
      
      // ページ離脱警告を設定（examine1と同様）
      setupPageLeaveWarning(true);
      console.log('examine1_2: ✓ ページ離脱警告設定完了');
      
      // ブラウザバック防止
      preventBrowserBack();
      console.log('examine1_2: ✓ ブラウザバック防止設定完了');
      
      // 最初のシナリオ説明を表示（UIManagerを通じて）
      await this.displayInitialScenario();
      console.log('examine1_2: ✓ 初期画面表示完了');
      
      console.log('examine1_2: ✓ 最終初期化完了 - 実験開始準備完了');
      
    } catch (error) {
      console.error('❌ 最終初期化設定に失敗:', error);
      throw new Error(`最終初期化設定に失敗しました: ${error.message}`);
    }
  }

  /**
   * 最初のシナリオ説明を表示
   */
  async displayInitialScenario() {
    try {
      // UIManagerを通じて最初の画面を表示
      if (uiManager.displayScenarioDescription) {
        await uiManager.displayScenarioDescription(true);
      } else {
        // フォールバック: 直接DOM操作
        this.toNextScenarioDescription(true);
      }
      
    } catch (error) {
      console.error('❌ 初期画面表示に失敗:', error);
      // フォールバック: 直接DOM操作
      this.toNextScenarioDescription(true);
    }
  }

  /**
   * 初期化エラーのハンドリング - examine1の堅牢なエラー処理を踏襲
   * エラーレベルに応じた適切な対応を実行
   */
  async handleInitializationError(error) {
    const initState = this.initializationState;
    let errorLevel = 'critical';
    let recoveryMessage = '';
    
    // 初期化段階に応じたエラーレベルの判定
    if (!initState.dataManager) {
      errorLevel = 'critical';
      recoveryMessage = 'データ管理システムの初期化に失敗しました。ページを再読み込みしてください。';
    } else if (!initState.uiManager) {
      errorLevel = 'high';
      recoveryMessage = 'UI管理システムの初期化に失敗しました。ページを再読み込みしてください。';
    } else if (!initState.eventHandler) {
      errorLevel = 'high';
      recoveryMessage = 'イベント処理システムの初期化に失敗しました。ページを再読み込みしてください。';
    } else if (!initState.examine12Specific) {
      errorLevel = 'medium';
      recoveryMessage = '実験設定の初期化に失敗しました。ページを再読み込みしてください。';
    } else {
      errorLevel = 'low';
      recoveryMessage = '最終設定で問題が発生しましたが、実験を継続できる可能性があります。';
    }
    
    // エラーログの詳細記録
    console.error('examine1_2 初期化エラー詳細:', {
      error: error,
      errorLevel: errorLevel,
      initializationState: initState,
      timestamp: getNow(),
      userAgent: navigator.userAgent
    });
    
    // UIを通じたエラー表示
    await this.displayErrorMessage(recoveryMessage, errorLevel);
    
    // 必要に応じてリカバリー処理を実行
    if (errorLevel === 'low' || errorLevel === 'medium') {
      await this.attemptErrorRecovery(errorLevel);
    }
  }

  /**
   * エラーメッセージの表示 - UIManagerを優先的に使用
   */
  async displayErrorMessage(message, errorLevel) {
    try {
      if (uiManager && uiManager.showErrorMessage) {
        uiManager.showErrorMessage(message);
      } else {
        // フォールバック: 直接DOM操作
        this.displayDirectErrorMessage(message, errorLevel);
      }
    } catch (error) {
      console.error('エラーメッセージ表示に失敗:', error);
      // 最終フォールバック: アラート
      alert(message);
    }
  }

  /**
   * 直接DOM操作によるエラーメッセージ表示
   */
  displayDirectErrorMessage(message, errorLevel) {
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: ${errorLevel === 'critical' ? '#ffebee' : '#fff3e0'};
      border: 2px solid ${errorLevel === 'critical' ? '#f44336' : '#ff9800'};
      padding: 20px;
      border-radius: 8px;
      z-index: 10000;
      max-width: 400px;
      text-align: center;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    `;
    errorDiv.innerHTML = `
      <h3>エラーが発生しました</h3>
      <p>${message}</p>
      <button onclick="location.reload()">ページを再読み込み</button>
    `;
    document.body.appendChild(errorDiv);
    
    // 5秒後に自動削除
    setTimeout(() => {
      if (errorDiv.parentNode) {
        errorDiv.parentNode.removeChild(errorDiv);
      }
    }, 5000);
  }

  /**
   * エラーリカバリーの試行
   */
  async attemptErrorRecovery(errorLevel) {
    try {
      if (errorLevel === 'low') {
        // 軽微なエラー: 最小限のリカバリー
        console.log('examine1_2: 軽微なエラーのリカバリーを試行中...');
        await this.displayInitialScenario();
      } else if (errorLevel === 'medium') {
        // 中程度のエラー: 部分的な再初期化
        console.log('examine1_2: 中程度のエラーのリカバリーを試行中...');
        await this.initializeExamine12Specific();
        await this.displayInitialScenario();
      }
    } catch (recoveryError) {
      console.error('リカバリー処理に失敗:', recoveryError);
    }
  }

  /**
   * シナリオの準備完了を確認
   */
  async ensureScenariosReady() {
    return new Promise((resolve) => {
      if (config.scenarios && config.scenarios.length === 6) {
        this.scenarios = config.scenarios;
        this.stimuli = shuffle(['1','2','3','4','5','6']);
        resolve();
      } else {
        console.log('examine1_2: シナリオ配布を待機中...');
        
        const checkScenarios = () => {
          if (config.scenarios && config.scenarios.length === 6) {
            this.scenarios = config.scenarios;
            this.stimuli = shuffle(['1','2','3','4','5','6']);
            resolve();
          } else {
            setTimeout(checkScenarios, 100);
          }
        };
        
        // イベントバス経由でのシナリオ配布も監視
        eventBus.on('scenarios:assigned', (data) => {
          console.log('examine1_2: シナリオ配布完了', data);
          this.scenarios = data.scenarios;
          this.stimuli = shuffle(['1','2','3','4','5','6']);
          resolve();
        });
        
        checkScenarios();
      }
    });
  }

  async loadExperimentData() {
    try {
      this.experimentData = await fetchJson('../static/material1.json');
      
      // 共通サンプルデータを読み込み、samples_refを解決
      await this.resolveCommonSamples();
      
      return this.experimentData;
    } catch (error) {
      console.error('実験データの読み込みに失敗しました', error);
      uiManager.showErrorMessage('データの読み込みに失敗しました。ページを再読み込みしてください。');
      throw error;
    }
  }

  /**
   * 共通サンプルデータを読み込み、samples_refを解決する
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
   * サーバーから実験条件を取得
   */
  async fetchSampleType() {
    try {
      const response = await fetch(`/getSampleType?user_id=${encodeURIComponent(dataManager.userId)}`);
      
      if (!response.ok) {
        throw new Error(`サーバーエラー: ${response.status}`);
      }
      
      const data = await response.json();
      this.sampleType = data.sampleType || 'asymmetric';
      dataManager.customData.sampleType = this.sampleType;
      console.log(`実験条件を取得: ${this.sampleType}`);
      
      return this.sampleType;
    } catch (error) {
      console.error('実験条件の取得に失敗しました。デフォルトで非対称条件を使用します。', error);
      this.sampleType = 'asymmetric';
      dataManager.customData.sampleType = this.sampleType;
      return this.sampleType;
    }
  }

  async preloadImages() {
    this.preloadedImages = new Map();
    
    // 必要な画像URLを収集
    const imageUrls = [];
    const basePath = '..';
    
    for (const scenario of this.scenarios) {
      const scenarioData = this.experimentData[scenario];
      
      // 非対称条件の画像
      imageUrls.push(`${basePath}/${scenarioData['images1_2']['arrow']}`);
      for (const type of this.imageType) {
        imageUrls.push(`${basePath}/${scenarioData['images1_2'][type]}`);
      }
      
      // 対称条件の画像（存在する場合）
      if (scenarioData['images_symmetric1_2']) {
        imageUrls.push(`${basePath}/${scenarioData['images_symmetric1_2']['arrow']}`);
        for (const type of this.imageType) {
          imageUrls.push(`${basePath}/${scenarioData['images_symmetric1_2'][type]}`);
        }
      }
    }
    
    // 重複を排除
    const uniqueUrls = [...new Set(imageUrls)];
    
    // プログレスバーUI
    const progressContainer = document.createElement('div');
    progressContainer.style.cssText = 'position:fixed;top:0;left:0;right:0;background:rgba(255,255,255,0.9);padding:20px;text-align:center;z-index:1000;';
    
    const messageEl = document.createElement('div');
    messageEl.textContent = '画像を読み込み中...';
    
    const progressBar = document.createElement('progress');
    progressBar.value = 0;
    progressBar.max = 100;
    progressBar.style.cssText = 'width:80%;margin:10px auto;display:block;';
    
    const progressText = document.createElement('div');
    progressText.textContent = '0%';
    
    progressContainer.appendChild(messageEl);
    progressContainer.appendChild(progressBar);
    progressContainer.appendChild(progressText);
    
    document.body.appendChild(progressContainer);
    
    // 画像のプリロード
    let loaded = 0;
    const total = uniqueUrls.length;
    
    const promises = uniqueUrls.map(url => 
      new Promise(resolve => {
        const img = new Image();
        img.onload = img.onerror = () => {
          loaded++;
          const percent = (loaded / total) * 100;
          progressBar.value = percent;
          progressText.textContent = `${Math.round(percent)}%`;
          resolve();
        };
        img.src = url;
      })
    );
    
    try {
      await Promise.all(promises);
    } catch (e) {
      // エラーは無視して続行
    } finally {
      document.body.removeChild(progressContainer);
      document.getElementById('preload_image').style.display = "none";
    }
  }

  setupLazyLoading() {
    if (!('IntersectionObserver' in window)) {
      // フォールバック
      document.querySelectorAll('img[data-src]').forEach(img => {
        img.src = img.dataset.src;
      });
      return;
    }
    
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          img.src = img.dataset.src;
          observer.unobserve(img);
        }
      });
    }, { rootMargin: '200px' });
    
    document.querySelectorAll('img[data-src]').forEach(img => observer.observe(img));
  }

  clearPage() {
    document.getElementById('estimate_input_area').style.display = "none";
    document.getElementById('check_sentence').style.display = "none";
    document.getElementById('description_area').style.display = "none";
    document.getElementById('show_sample_area').style.display = 'none';
  }

  toNextScenarioDescription(isFirstTime = false) {
    this.clearPage();
    
    if (!isFirstTime) {
      this.scenarioIndex++;
    }
    
    this.resetBackGround();
    
    // 配布されたシナリオを使用
    const scenarios = this.scenarios || config.scenarios;
    document.getElementById('page').innerHTML = "<h4>" + (this.scenarioIndex + 1) + '/' + scenarios.length + "種類目</h4>";
    document.getElementById('scenario_title').innerHTML = "<h2>" + this.experimentData[scenarios[this.scenarioIndex]]['title'] + "</h2>";
    document.getElementById('check_sentence').style.display = "inline-block";
    document.getElementById('description_area').style.display = "inline-block";
    document.getElementById('start_scenario_button').setAttribute("disabled", true);
    
    // 条件に応じた説明文を選択
    let descriptions;
    if (this.sampleType === 'symmetric' && this.experimentData[scenarios[this.scenarioIndex]]['descriptions_symmetric']) {
      descriptions = this.experimentData[scenarios[this.scenarioIndex]]['descriptions_symmetric'];
      console.log('対称条件の説明文を使用');
    } else {
      descriptions = this.experimentData[scenarios[this.scenarioIndex]]['descriptions'];
      console.log('非対称条件の説明文を使用');
    }
    
    const descLen = descriptions.length;
    for (let i = 0; i < descLen; i++) {
      document.getElementById('scenario_description' + String(i + 1)).innerHTML = descriptions[i];
    }
  }

  checkDescription() {
    const checkbox = document.getElementsByClassName("checkbox");
    let count = 0;
    
    for (let i = 0; i < checkbox.length; i++) {
      if (checkbox[i].checked) count++;
    }
    
    if (count == checkbox.length) {
      document.getElementById('start_scenario_button').removeAttribute("disabled");
    } else {
      document.getElementById("start_scenario_button").setAttribute("disabled", true);
    }
  }

  toNextNewSamplePage() {
    this.clearPage();
    
    // チェックボックスをリセット
    const list = document.getElementsByClassName("checkbox");
    for (let index = 0; index < list.length; ++index) {
      list[index].checked = false;
    }
    
    this.currentTestPage = 0;
    document.getElementById('show_sample_area').style.display = "inline";
    document.getElementById('order').innerHTML = "実験の進捗状況";
    this.changeBackGround();

    // 提示するサンプル作成
    this.currentSampleSelection = [];
    this.sampleSize = 0;
    
    const scenarios = this.scenarios || config.scenarios;
    const currentScenario = scenarios[this.scenarioIndex];
    const currentStimulus = this.stimuli[this.scenarioIndex];
    const samples = this.experimentData[currentScenario]['samples'][currentStimulus];
    
    Object.keys(samples).forEach(elm => {
      if (samples[elm] > 0) {
        this.sampleSize += samples[elm];
        this.cellSize = samples[elm];
        
        for (let i = 0; i < this.cellSize; i++) {
          this.currentSampleSelection.push(elm);
        }
      }
    });
    
    this.currentSampleSelection = shuffle(this.currentSampleSelection);
    this.toNextSample();
  }

  toNextSample() {
    const button = document.getElementById('next_sample');
    button.disabled = true;
    
    if (this.currentTestPage >= this.sampleSize) {
      uiManager.showErrorMessage('結果は以上になります。');
      this.drawEstimate('fin');
      return;
    }
    
    this.showStimulation();
    
    // 連打防止
    setTimeout(() => {
      button.disabled = false;
    }, 500);
  }

  showStimulation() {
    const sample = this.currentSampleSelection[this.currentTestPage];
    const scenarios = this.scenarios || config.scenarios;
    const currentScenario = scenarios[this.scenarioIndex];
    
    // 条件に応じて適切な文章を選択
    let sentences;
    if (this.sampleType === 'symmetric' && this.experimentData[currentScenario]['sentences_symmetric']) {
      sentences = this.experimentData[currentScenario]['sentences_symmetric'];
      console.log('対称条件の文章を使用');
    } else {
      sentences = this.experimentData[currentScenario]['sentences'];
      console.log('非対称条件の文章を使用');
    }
    
    const desc = sentences[sample];
    const sentenceParts = desc.split('、');
    document.getElementById('first_sentence').innerHTML = "<h4>" + sentenceParts[0] + "</h4>";
    document.getElementById('last_sentence').innerHTML = "<h4>" + sentenceParts[1] + "</h4>";
    
    document.getElementById('show_sample_area').style.display = "inline";
    document.getElementById('first_sentence').style.display = 'inline-block';
    document.getElementById('last_sentence').style.display = 'inline-block';
    document.getElementById('sample_before').style.display = 'inline';
    document.getElementById('estimate_input_area').style.display = 'none';
    document.getElementById('next_sample').style.display = 'inline';
    
    const combination = this.imgCombination[sample];
    
    // 条件に応じて適切な画像セットを選択
    let imageSet;
    if (this.sampleType === 'symmetric' && this.experimentData[currentScenario]['images_symmetric1_2']) {
      imageSet = this.experimentData[currentScenario]['images_symmetric1_2'];
      console.log('対称条件の画像を使用');
    } else {
      imageSet = this.experimentData[currentScenario]['images1_2'];
      console.log('非対称条件の画像を使用');
    }
    
    document.getElementById('sample_before').src = 
      `../${imageSet[combination['cause']]}`;
    document.getElementById('arrow').src = 
      `../${imageSet['arrow']}`;
    document.getElementById('sample_after').src = 
      `../${imageSet[combination['effect']]}`;
    
    this.updateProgressBar();
    
    this.currentTestPage++;
    document.getElementById('current_page').innerHTML = this.currentTestPage + '/' + this.sampleSize;
  }

  updateProgressBar() {
    document.getElementById('progress_bar').value = this.currentTestPage;
    document.getElementById('progress_bar').max = this.sampleSize - 1;
  }

  drawEstimate(condition) {
    this.clearPage();
    
    document.getElementById("checkbox").setAttribute("disabled", true);
    document.getElementById('next_scenario').style.display = 'none';
    document.getElementById('estimate_input_area').style.display = 'inline-block';
    document.getElementById('next_scenario').setAttribute("disabled", true);
    document.getElementById('continue_scenario').setAttribute("disabled", true);
    document.getElementById('continue_scenario').style.display = 'inline';
    document.getElementById('finish_all_scenarios').setAttribute("disabled", true);
    document.getElementById('estimate_slider').value = 50;
    document.getElementById('estimate').innerHTML = 50;
    document.getElementById("checkbox").checked = false;
    
    if (condition === 'fin') {
      document.getElementById('continue_scenario').style.display = 'none';
      
      const scenarios = this.scenarios || config.scenarios;
      if (this.scenarioIndex === scenarios.length - 1) {
        document.getElementById('finish_all_scenarios').style.display = 'inline';
      } else {
        document.getElementById('next_scenario').style.display = 'inline';
      }
    }

    const scenarios = this.scenarios || config.scenarios;
    const currentScenario = this.experimentData[scenarios[this.scenarioIndex]];
    
    // 実験条件に応じて結果テキストを選択
    let resultText;
    if (this.sampleType === 'symmetric' && currentScenario['result_symmetric']) {
      resultText = currentScenario['result_symmetric'];
      console.log('対称条件の評価文を使用:', resultText);
    } else {
      resultText = currentScenario['result'];
      console.log('非対称条件の評価文を使用:', resultText);
    }
    
    document.getElementById('estimate_description').innerHTML = 
      '<h3>' + resultText + 'と思いますか？</h3>' + 
      '<ul>0：' + currentScenario['min_result'] + '</ul>' + 
      '<ul>100：' + currentScenario['max_result'] + '</ul>' +
      '<ul>として、0から100の値で<b>直感的に</b>回答してください。</ul>' +
      '<p>※スライダーの挙動に不具合が生じた場合、スライダーを直接クリックして値を選択してください。</p>';
  }

  /**
   * 緊急時のフォールバック初期化
   */
  async fallbackInitialization() {
    console.warn('examine1_2: フォールバック初期化を実行中...');
    
    try {
      // 最小限の設定で実験を開始
      this.scenarioIndex = 0;
      this.currentTestPage = 0;
      this.sampleSize = 10; // デフォルト値
      
      // 基本的なDOM要素の確認
      const requiredElements = ['scenario_description1', 'show_sample_area', 'estimate_input_area'];
      const missingElements = requiredElements.filter(id => !document.getElementById(id));
      
      if (missingElements.length > 0) {
        throw new Error(`必要なDOM要素が見つかりません: ${missingElements.join(', ')}`);
      }
      
      // 基本的な画面表示
      document.getElementById('scenario_description1').innerHTML = 
        '<p>実験の準備中です。しばらくお待ちください...</p>';
      
      console.log('examine1_2: フォールバック初期化完了');
      return true;
      
    } catch (error) {
      console.error('examine1_2: フォールバック初期化も失敗:', error);
      return false;
    }
  }

  // EventHandlerから呼び出されるメソッド
  /**
   * 次のシナリオへ進む処理（EventHandler用）
   */
  handleNextScenario() {
    console.log('次のシナリオへ進みます');
    // 推定値を記録
    this.recordEstimation();
    // 次のシナリオ説明に進む
    this.toNextScenarioDescription();
  }

  /**
   * シナリオを継続する処理（EventHandler用）
   */
  handleContinueScenario() {
    console.log('シナリオを継続します');
    // 推定値を記録
    this.recordEstimation();
    // 新しいサンプルページに進む
    this.toNextNewSamplePage();
  }

  /**
   * 結果をエクスポートする処理（EventHandler用）
   */
  async handleExportResults() {
    console.log('結果をエクスポートします');
    
    // ボタンを無効化（連打防止）
    document.getElementById('finish_all_scenarios').disabled = true;
    
    try {
      // 最後の推定値を記録
      this.recordEstimation();
      // 結果をエクスポート
      await this.exportResults();
    } catch (error) {
      console.error('結果エクスポート処理でエラーが発生しました:', error);
      // エラー時はボタンを再有効化
      document.getElementById('finish_all_scenarios').disabled = false;
    }
  }

  /**
   * 推定値を記録
   */
  recordEstimation() {
    const estimation = document.getElementById('estimate_slider').value;
    const scenarios = this.scenarios || config.scenarios;
    const currentScenario = scenarios[this.scenarioIndex];
    
    // DataManagerのカスタムデータに推定結果を追加
    if (!dataManager.customData.estimations) {
      dataManager.customData.estimations = [];
    }
    
    dataManager.customData.estimations.push({
      'user_id': dataManager.userId,
      'number': currentScenario,
      'stimuli': this.stimuli[this.scenarioIndex],
      'estimation': parseInt(estimation)
    });
    
    console.log('推定結果を記録しました:', {
      scenario: currentScenario,
      estimation: estimation,
      stimulus: this.stimuli[this.scenarioIndex]
    });
  }

  async exportResults() {
    try {
      // ページ離脱警告を無効化
      setupPageLeaveWarning(false);
      
      // DataManagerから推定データを取得し、次のページURLを決定
      const nextUrl = await getNextPageUrl('examine1_2', dataManager.userId);
      
      // DataManagerの送信メソッドを使用してデータを送信
      await dataManager.sendExamine12Results(dataManager.customData.estimations, nextUrl);
    } catch (error) {
      console.error("回答送信中にエラーが発生しました", error);
      document.getElementById('finish_all_scenarios').removeAttribute("disabled");
      throw error;
    }
  }

  checkEstimate() {
    if (document.getElementById('checkbox').checked) {
      document.getElementById('next_scenario').removeAttribute("disabled");
      document.getElementById('continue_scenario').removeAttribute("disabled");
      document.getElementById('finish_all_scenarios').removeAttribute("disabled");
    } else {
      document.getElementById("checkbox").removeAttribute("disabled");
      document.getElementById("finish_all_scenarios").setAttribute("disabled", true);
    }
  }

  changeBackGround() {
    document.body.style.backgroundColor = this.bgcolors[this.scenarioIndex];
  }

  resetBackGround() {
    document.body.style.backgroundColor = 'Transparent';
  }

  displayDetailedError(error) {
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
      position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
      background: #ffebee; border: 2px solid #f44336; padding: 20px;
      border-radius: 8px; z-index: 10000; max-width: 600px;
      font-family: Arial, sans-serif; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    `;
    errorDiv.innerHTML = `
      <h3 style="color: #d32f2f; margin-top: 0;">読み込みエラーが発生しました</h3>
      <p><strong>エラー詳細:</strong> ${error.message}</p>
      <p><strong>初期化状態:</strong></p>
      <ul style="text-align: left;">
        <li>DataManager: ${this.initializationState.dataManager ? '✓' : '✗'}</li>
        <li>UIManager: ${this.initializationState.uiManager ? '✓' : '✗'}</li>
        <li>EventHandler: ${this.initializationState.eventHandler ? '✓' : '✗'}</li>
        <li>固有設定: ${this.initializationState.examine12Specific ? '✓' : '✗'}</li>
      </ul>
      <div style="margin-top: 15px;">
        <button onclick="location.reload()" style="background: #f44336; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">ページを再読み込み</button>
        <button onclick="window.history.back()" style="background: #9e9e9e; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-left: 10px;">前のページに戻る</button>
      </div>
    `;
    document.body.appendChild(errorDiv);
  }
}

// 実験マネージャーのインスタンスを作成
const experimentManager = new Experiment12Manager();

// グローバルスコープに公開する必要がある関数（HTMLから呼び出し可能）
window.experiment12Manager = null;

// ページ読み込み時に実験マネージャーを初期化
window.addEventListener('DOMContentLoaded', async () => {
  window.experiment12Manager = experimentManager;
  await experimentManager.initialize();
});

// グローバル関数の公開（HTMLから呼び出し可能にする）
window.checkDescription = function() {
  if (window.experiment12Manager && window.experiment12Manager.checkDescription) {
    window.experiment12Manager.checkDescription();
  } else {
    eventHandler.checkDescription();
  }
};

window.to_next_new_sample_page = function() {
  if (window.experiment12Manager && window.experiment12Manager.toNextNewSamplePage) {
    window.experiment12Manager.toNextNewSamplePage();
  }
};

window.checkEstimate = function() {
  if (window.experiment12Manager && window.experiment12Manager.checkEstimate) {
    window.experiment12Manager.checkEstimate();
  }
};

window.enableEstimateCheckbox = function() {
  // スライダー操作時の処理
  let sliderMoved = true;
  document.getElementById('checkbox').disabled = false;
};

// ページ読み込み完了時の初期化
document.addEventListener('DOMContentLoaded', () => {
  console.log('examine1_2: DOMContentLoaded - 初期化開始');
});

// 初期化処理の改善
let initializationAttempted = false;

// モジュール読み込み完了後の初期化
setTimeout(async () => {
  if (initializationAttempted) return;
  initializationAttempted = true;
  
  try {
    console.log('examine1_2: 初期化開始');
    
    // 依存関係の確認
    const dependencies = ['config', 'dataManager', 'uiManager', 'eventHandler'];
    for (const dep of dependencies) {
      if (typeof window[dep] === 'undefined') {
        throw new Error(`${dep} モジュールが読み込まれていません`);
      }
    }
    
    const manager = new Experiment12Manager();
    const success = await manager.initialize();
    
    if (!success) {
      console.warn('examine1_2: 通常初期化に失敗、フォールバックを試行');
      await manager.fallbackInitialization();
    }
    
    // グローバルスコープに公開
    window.experiment12Manager = manager;
    console.log('examine1_2: 初期化完了');
    
  } catch (error) {
    console.error('examine1_2: 初期化処理でエラーが発生:', error);
    
    // 最終手段: 基本的なエラーページを表示
    document.body.innerHTML = `
      <div style="text-align: center; padding: 50px; font-family: Arial, sans-serif;">
        <h2 style="color: #d32f2f;">実験ページの読み込みに失敗しました</h2>
        <p>技術的な問題が発生しています。以下の方法をお試しください：</p>
        <ol style="text-align: left; max-width: 400px; margin: 20px auto;">
          <li>ページを再読み込みする</li>
          <li>ブラウザを再起動する</li>
          <li>異なるブラウザを使用する</li>
        </ol>
        <button onclick="location.reload()" style="background: #1976d2; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">ページを再読み込み</button>
      </div>
    `;
  }
}, 1000); // 1秒待機してから初期化

export default experimentManager;
