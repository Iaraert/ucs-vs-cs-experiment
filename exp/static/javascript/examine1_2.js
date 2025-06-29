/**
 * examine1_2.js - 因果関係の強さを推定する実験
 * モジュラー構造に対応し、examine1との互換性を確保
 */

// 共有モジュールのインポート
import config from './config.js';
import dataManager from './data-manager.js';
import uiManager from './ui-manager.js';
import eventHandler from './event-handler.js';
import { preventBrowserBack, setupPageLeaveWarning, shuffleArray, zeroPadding, getNow, getNextPageUrl, getExperimentOrder, isAlreadyParticipated } from './utilities.js';
import { 
  validateCheckboxes, 
  validateCheckboxesRobust,
  validateDataStructure, 
  validateScenarioData,
  setImagePaths,
  createImageMapping,
  setElementsDisplay,
  setButtonStates,
  setElementTexts,
  setElementHTMLs,
  setElementAttributes
} from './common-utils.js';

// 依存関係の読み込み状態を管理
let modulesLoaded = false;
let initializationAttempts = 0;
const MAX_INIT_ATTEMPTS = 5;

/**
 * 依存モジュールの読み込み状態をチェック
 */
function checkModulesLoaded() {
  try {
    // 必要なモジュールが正しく読み込まれているかチェック
    const requiredModules = {
      config: config,
      dataManager: dataManager,
      uiManager: uiManager,
      eventHandler: eventHandler,
      utilities: { preventBrowserBack, setupPageLeaveWarning, shuffleArray, zeroPadding, getNow, getNextPageUrl, getExperimentOrder, isAlreadyParticipated },
      commonUtils: { validateCheckboxes, validateCheckboxesRobust, validateDataStructure, validateScenarioData, setImagePaths, createImageMapping, setElementsDisplay, setButtonStates, setElementTexts, setElementHTMLs, setElementAttributes }
    };
    
    for (const [moduleName, moduleObj] of Object.entries(requiredModules)) {
      if (!moduleObj || (typeof moduleObj === 'object' && Object.keys(moduleObj).length === 0)) {
        console.warn(`Module ${moduleName} is not properly loaded`);
        return false;
      }
    }
    
    console.log('✅ All required modules are loaded successfully');
    return true;
  } catch (error) {
    console.error('❌ Error checking module dependencies:', error);
    return false;
  }
}

/**
 * 初期化のリトライ機能付き実行
 */
async function initializeWithRetry() {
  return new Promise((resolve, reject) => {
    const attemptInit = () => {
      initializationAttempts++;
      console.log(`🔄 Initialization attempt ${initializationAttempts}/${MAX_INIT_ATTEMPTS}`);
      
      if (checkModulesLoaded()) {
        modulesLoaded = true;
        console.log('✅ Modules loaded successfully, proceeding with initialization');
        resolve();
      } else if (initializationAttempts < MAX_INIT_ATTEMPTS) {
        console.log(`⏳ Modules not ready, retrying in ${1000 * initializationAttempts}ms...`);
        setTimeout(attemptInit, 1000 * initializationAttempts);
      } else {
        const error = new Error(`Failed to load modules after ${MAX_INIT_ATTEMPTS} attempts`);
        console.error('❌ Module loading failed:', error);
        reject(error);
      }
    };
    
    attemptInit();
  });
}

/**
 * 実験1.2を管理するクラス
 */
class Experiment12Manager {  
  constructor() {
    // 初期化状態管理
    this.initialized = false;
    this.initializationInProgress = false;
    
    // 実験タイプを新しい名称に変更
    dataManager.setExperimentType('eXaM1nE_2');
    
    // examine1_2固有の設定
    this.file = '../static/material1.json';
    this.userData = [];
    this.testOrder = {};  // オブジェクトとして初期化
    this.currentSampleSelection = [];
    this.estimations = [];
      // シナリオはconfig.jsから取得（ハードコードしない）
    this.scenarios = null;  // 初期化時に設定される
    
    // 刺激データの初期化（安全にチェック）
    try {
      this.stimuli = shuffleArray(['1','2','3','4','5','6']);
      console.log('examine1_2: stimuli初期化完了:', this.stimuli);
    } catch (error) {
      console.error('examine1_2: stimuli初期化エラー:', error);
      this.stimuli = ['1','2','3','4','5','6']; // フォールバック
    }
    // 背景色を2色交互に設定（アイコンの色と被らないように）
    this.bgcolors = ['#f8f9fa', '#fff8f0']; // 淡いグレーと淡いベージュ
    
    this.imageType = ["p", "notp", "q", "notq"];
    this.imgCombination = {
        'a': {'cause': 'p', 'effect': 'q'},
        'b': {'cause': 'p', 'effect': 'notq'},
        'c': {'cause': 'notp', 'effect': 'q'},
        'd': {'cause': 'notp', 'effect': 'notq'}
    };
      // 実験状態管理
    this.currentTestPage = 0;
    this.sampleSize = 0;
    this.userId = 0;
    this.startTime = getNow();
    dataManager.startTime = this.startTime; // ← 追加: dataManagerにもコピー
    this.sceIdx = 0;
    this.estI = 0;
    this.cellSize = 0;
    
    // 初期化を非同期で開始
    this.initializeAsync();
  }  /**
   * 非同期初期化（リトライ機能付き）
   */
  async initializeAsync() {
    if (this.initializationInProgress) {
      console.log('⏳ Initialization already in progress...');
      return;
    }
    this.initializationInProgress = true;
    try {
      // ★ ここで必ずstartTimeを初期化する
      this.startTime = getNow();
      dataManager.startTime = this.startTime; // ← 追加: dataManagerにもコピー
      // 依存モジュールの読み込み完了を待機
      await initializeWithRetry();
      // utilities.jsから統一されたユーザーID取得関数を使用
      const { getOrCreateUserId } = await import('./utilities.js');
      this.userId = getOrCreateUserId({ 
        urlParam: true, 
        persistent: false 
      });
      // 実際の初期化処理を実行
      await this.initialize();
      this.initialized = true;
      this.initializationInProgress = false;
      console.log('✅ Experiment12Manager initialized successfully');
    } catch (error) {
      console.error('❌ Failed to initialize Experiment12Manager:', error);
      this.initializationInProgress = false;
      // エラー時のフォールバック処理
      this.showInitializationError();
    }
  }

  /**
   * 初期化エラー時の処理
   */
  showInitializationError() {
    const errorMessage = document.createElement('div');
    errorMessage.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: #fff;
      border: 2px solid #dc3545;
      border-radius: 8px;
      padding: 20px;
      text-align: center;
      z-index: 10000;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    `;
    errorMessage.innerHTML = `
      <h3 style="color: #dc3545; margin-top: 0;">初期化エラー</h3>
      <p>実験システムの初期化に失敗しました。</p>
      <p>ページを再読み込みしてください。</p>
      <button onclick="location.reload()" style="
        background: #dc3545;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 4px;
        cursor: pointer;
        margin-top: 10px;
      ">ページを再読み込み</button>
    `;
    document.body.appendChild(errorMessage);
  }

  /**
   * 実験を初期化
   */  async initialize() {
    try {
      // utilities.jsから統一されたユーザーID取得関数を使用
      const { getOrCreateUserId } = await import('./utilities.js');
      this.userId = getOrCreateUserId({ 
        urlParam: true, 
        persistent: false 
      });
      // 進捗/order検証は削除（ページ表示時は判定しない）
      if (!this.userId) {
        console.error('examine1_2: ユーザーIDの取得に失敗しました');
        alert('ユーザー識別情報の取得に失敗しました。最初のページからやり直してください。');
        window.location.href = '/';
        return;
      }
      
      console.log('examine1_2: ユーザーID:', this.userId);
      
      // DataManagerにユーザーIDを設定 - 重要: 確実に同じIDを使用
      dataManager.userId = this.userId;
      
      // サーバーから実験条件（対称/非対称）を取得
      await dataManager.fetchSampleType();
      console.log('examine1_2: 実験条件:', dataManager.sampleType);
      
      // config.jsからexamine1_2用のシナリオを取得
      this.scenarios = config.setExperimentScenarios('examine1_2', this.userId);
      console.log('examine1_2: 配布されたシナリオ:', this.scenarios.join(', '));
        // データの読み込み
      console.log('examine1_2: データファイルの読み込みを開始:', this.file);
      this.testOrder = await this.readJson(this.file);
      console.log('examine1_2: データファイルの読み込み完了、キー数:', Object.keys(this.testOrder).length);
      this.estimations = new Array();
      
      // 共通サンプルデータの解決
      console.log('examine1_2: 共通サンプルデータの解決を開始');
      await this.resolveCommonSamples();
      console.log('examine1_2: 共通サンプルデータの解決完了');
      
      // 画像のプリロード
      console.log('examine1_2: 画像のプリロードを開始');
      this.getImages();
      console.log('examine1_2: 画像のプリロード完了');
      
      // 最初のシナリオ表示
      console.log('examine1_2: 最初のシナリオ表示を開始');
      this.toNextScenarioDescription(true);
      
      // ページ離脱警告の設定
      setupPageLeaveWarning();
      
      // ブラウザバック防止
      preventBrowserBack();
      
      console.log('examine1_2: 初期化完了');
    } catch (error) {
      console.error('examine1_2の初期化に失敗しました:', error);
      console.error('エラーの詳細:', error.stack);
      uiManager.showErrorMessage('実験の準備中にエラーが発生しました。ページを再読み込みしてください。');
    }
  }/**
   * JSONファイルを読み込む
   */
  async readJson(filename) {
    try {
      const response = await fetch(filename);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const json = await response.json();
      console.log('examine1_2: JSONデータ読み込み完了');
      return json;
    } catch (error) {
      console.error('JSONファイルの読み込みに失敗しました:', error);
      throw error;
    }
  }

  /**
   * 共通サンプルデータを読み込み、samples_refを解決する
   */
  async resolveCommonSamples() {
    try {
      // 共通サンプルデータを読み込み
      const response = await fetch('../static/samples_common.json');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const commonSamplesData = await response.json();
      console.log('examine1_2: 共通サンプルデータを読み込みました');
      
      // 各シナリオのsamples_refを解決
      Object.keys(this.testOrder).forEach(scenarioKey => {
        const scenario = this.testOrder[scenarioKey];
        if (scenario.samples_ref && commonSamplesData[scenario.samples_ref]) {
          // samples_refが指定されている場合、共通データで置き換え
          scenario.samples = commonSamplesData[scenario.samples_ref];
          console.log(`examine1_2: シナリオ ${scenarioKey} のsamples_refを解決しました: ${scenario.samples_ref}`);
        }
      });
    } catch (error) {
      console.warn('examine1_2: 共通サンプルデータの読み込みに失敗しました。既存のsamplesデータを使用します。', error);
    }
  }  /**
   * 画像のプリロード（最適化版）
   */
  getImages() {
    // データ構造の基本チェック
    if (!validateDataStructure(this.testOrder, 'testOrder')) {
      console.warn('testOrderが初期化されていません。画像プリロードをスキップします。');
      return;
    }
    
    try {
      // 画像プリロード設定のマッピング
      const preloadTasks = this.scenarios.map(scenarioKey => ({
        scenarioKey,
        requiredPaths: ['images1_2'],
        imageTypes: this.imageType
      }));
      
      // 並列でプリロード処理を実行
      this.executeImagePreload(preloadTasks);
      
      // 対称条件の画像もプリロード
      if (dataManager.sampleType === 'symmetric') {
        const symmetricPreloadTasks = this.scenarios.map(scenarioKey => ({
          scenarioKey,
          requiredPaths: ['images_symmetric1_2'],
          imageTypes: this.imageType
        }));
        this.executeSymmetricImagePreload(symmetricPreloadTasks);
      }
      
      // プリロード表示を非表示
      setElementsDisplay({ 'preload_image': 'none' });
      
      console.log('examine1_2: 画像プリロード完了');
    } catch (error) {
      console.error('画像プリロード中にエラーが発生しました:', error);
    }
  }
    /**
   * 画像プリロードの実行（ヘルパーメソッド）
   * @param {Array} preloadTasks - プリロードタスクの配列
   */
  executeImagePreload(preloadTasks) {
    preloadTasks.forEach(({ scenarioKey, requiredPaths, imageTypes }) => {
      // データ構造の存在確認
      if (!validateScenarioData(this.testOrder, scenarioKey, requiredPaths)) {
        console.warn(`シナリオ ${scenarioKey} の画像データが見つかりません`);
        return;
      }
      
      // 画像タイプごとにプリロード
      const images = this.testOrder[scenarioKey]['images1_2'];
      imageTypes.forEach(imageType => {
        const imagePath = images[imageType];
        if (imagePath) {
          this.preloadSingleImage(imagePath);
        }
      });
    });
  }
  
  /**
   * 対称条件画像プリロードの実行（ヘルパーメソッド）
   * @param {Array} preloadTasks - プリロードタスクの配列
   */
  executeSymmetricImagePreload(preloadTasks) {
    preloadTasks.forEach(({ scenarioKey, requiredPaths, imageTypes }) => {
      // データ構造の存在確認
      if (!validateScenarioData(this.testOrder, scenarioKey, requiredPaths)) {
        console.warn(`シナリオ ${scenarioKey} の対称条件画像データが見つかりません`);
        return;
      }
      
      // 画像タイプごとにプリロード
      const images = this.testOrder[scenarioKey]['images_symmetric1_2'];
      imageTypes.forEach(imageType => {
        const imagePath = images[imageType];
        if (imagePath) {
          this.preloadSingleImage(imagePath);
        }
      });
    });
  }
  
  /**
   * 単一画像のプリロード
   * @param {string} imagePath - 画像のパス
   */
  preloadSingleImage(imagePath) {
    const img = document.createElement('img');
    img.src = `../${imagePath}`;
    img.onerror = () => console.warn(`画像の読み込みに失敗: ${imagePath}`);
    return img;
  }

  /**
   * ページをクリアする
   */
  clearPage() {
    document.getElementById('estimate_input_area').style.display = "none";
    document.getElementById('check_sentence').style.display = "none";
    document.getElementById('description_area').style.display = "none";
    document.getElementById('show_sample_area').style.display = 'none';
  }  /**
   * 次のシナリオの説明を表示
   */
  async toNextScenarioDescription(isFirstTime = false) {
    if (!validateScenarioData(this.testOrder, null)) {
      console.error('testOrderが初期化されていません');
      return;
    }
    
    this.clearPage();
    if (!isFirstTime) {
      this.sceIdx++;
      // --- 進捗ログを追加 ---
      if (window.dataManager) {
        console.log(`[examine1_2.toNextScenarioDescription] ページ移動: sceIdx=${this.sceIdx}, currentScenarioIndex=${window.dataManager.currentScenarioIndex}`);
      } else {
        console.log(`[examine1_2.toNextScenarioDescription] ページ移動: sceIdx=${this.sceIdx}`);
      }
    }
    
    // 境界チェック: 配列アクセス前の安全性確認
    if (this.sceIdx < 0 || this.sceIdx >= this.scenarios.length) {
      console.error(`シナリオインデックスが不正です: ${this.sceIdx}/${this.scenarios.length}`);
      alert('シナリオデータエラーが発生しました。管理者にお問い合わせください。');
      return;
    }
    
    this.resetBackGround();
    
    const scenarioKey = this.scenarios[this.sceIdx];
    console.log(`シナリオ表示: インデックス=${this.sceIdx}, キー=${scenarioKey}`);
    
    // シナリオデータの存在確認を7つ目のチェックボックス処理前に実行
    if (!validateScenarioData(this.testOrder, scenarioKey)) {
      console.error(`シナリオデータが見つかりません: ${scenarioKey}`);
      alert(`シナリオ "${scenarioKey}" のデータが見つかりません。管理者にお問い合わせください。`);
      return;
    }

    // シナリオデータの必須プロパティ確認
    const requiredProperties = ['title', 'descriptions'];
    for (const prop of requiredProperties) {
      if (!this.testOrder[scenarioKey][prop]) {
        console.error(`シナリオ "${scenarioKey}" に必要なプロパティ "${prop}" がありません`);
        alert(`シナリオデータが不完全です。管理者にお問い合わせください。`);
        return;
      }
    }

    // --- 通し番号の計算 ---
    let displayIndex = this.sceIdx + 1;
    let total = 12;
    (async () => {
      let experimentOrder = 'order1';
      try {
        const { getExperimentOrder } = await import('./utilities.js');
        experimentOrder = await getExperimentOrder(this.userId, false);
      } catch (e) {}
      if (dataManager.experimentType === 'eXaM1nE_2') {
        displayIndex = (experimentOrder === 'order1') ? (this.sceIdx + 7) : (this.sceIdx + 1);
      } else if (dataManager.experimentType === 'eXaMinE1') {
        displayIndex = (experimentOrder === 'order1') ? (this.sceIdx + 1) : (this.sceIdx + 7);
      }
      document.getElementById('page').innerHTML = `<h4>${displayIndex}/${total}種類目</h4>`;
    })();

    document.getElementById('scenario_title').innerHTML = "<h2>" + this.testOrder[scenarioKey]['title'] + "</h2>";

    setElementsDisplay({
      'check_sentence': 'inline-block',
      'description_area': 'inline-block',
      'start_scenario_button': 'inline'
    });

    setButtonStates({
      'start_scenario_button': false
    });

    // 明示的にボタンを無効化
    const startButton = document.getElementById('start_scenario_button');
    if (startButton) {
      startButton.setAttribute('disabled', true);
    }    // 条件に応じて説明文を選択
    let descriptions;
    if (dataManager.sampleType === 'symmetric' && this.testOrder[scenarioKey]['descriptions_symmetric']) {
      descriptions = this.testOrder[scenarioKey]['descriptions_symmetric'];
      console.log('対称条件の説明文を使用');
    } else {
      descriptions = this.testOrder[scenarioKey]['descriptions'];
      console.log('非対称条件の説明文を使用');
    }

    // シナリオ説明文の表示
    const scenarioDescriptionsContainer = document.getElementById('scenario_descriptions');
    scenarioDescriptionsContainer.innerHTML = '';
    // 5文以上でも対応できるようにループで生成
    descriptions.forEach((desc, idx) => {
      const p = document.createElement('p');
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = 'checkbox';
      checkbox.id = `desc_check_${idx}`;
      checkbox.style.marginRight = '8px';
      checkbox.addEventListener('change', () => {
        validateCheckboxes('checkbox', 'start_scenario_button');
      });
      p.appendChild(checkbox);
      const label = document.createElement('label');
      label.htmlFor = checkbox.id;
      label.textContent = desc;
      p.appendChild(label);
      scenarioDescriptionsContainer.appendChild(p);
    });

    // DOM更新の同期化: チェックボックス動的生成後のsetTimeout待機時間を200ms以上に延長
    setTimeout(async () => {
      console.log(`toNextScenarioDescription: DOM更新完了 - シナリオ${this.sceIdx + 1}, チェックボックス数: ${descriptions.length}`);
      
      // DOM更新完了の確認処理を追加
      const checkboxes = document.getElementsByClassName("checkbox");
      if (checkboxes.length !== descriptions.length) {
        console.warn(`DOM更新完了確認: チェックボックス数が不一致 - 期待: ${descriptions.length}, 実際: ${checkboxes.length}`);
        
        // DOM更新が不完全な場合の追加待機
        setTimeout(() => {
          const recheckBoxes = document.getElementsByClassName("checkbox");
          console.log(`追加確認後のチェックボックス数: ${recheckBoxes.length}`);            this.resetCheckboxes(recheckBoxes, descriptions.length);
        }, 100);
      } else {
        this.resetCheckboxes(checkboxes, descriptions.length);
      }

      // --- ここでorder1かつsceIdx===0のときのみ通知表示 ---
      try {
        const { getExperimentOrder, checkAndShowFormatChangeNotification } = await import('./utilities.js');
        const experimentOrder = await getExperimentOrder(this.userId, false);
        if (experimentOrder === 'order1' && this.sceIdx === 0) {
          await checkAndShowFormatChangeNotification(this.userId, 0, 'eXaM1nE_2');
        }
      } catch (e) {
        console.warn('実験形式変更通知の表示に失敗:', e);
      }
      // --- ここまで ---
    }, 250); // DOM更新完了を確実に待機（200ms以上に延長）
  }
    /**
   * チェックボックスのリセット処理（ヘルパーメソッド）
   */
  resetCheckboxes(checkboxes, expectedCount) {
    for (let i = 0; i < checkboxes.length; i++) {
      checkboxes[i].checked = false;
    }
    console.log(`toNextScenarioDescription: チェックボックスリセット完了 - 実際の要素数: ${checkboxes.length}`);
  }
    /**
   * フォールバック時のシナリオ表示処理（ヘルパーメソッド）
   */
  handleFallbackScenarioDisplay(descriptions) {
    if (descriptions && descriptions.length > 0) {
      for (let i = 0; i < descriptions.length; i++) {
        const element = document.getElementById('scenario_description' + String(i + 1));
        if (element) {
          element.innerHTML = descriptions[i];
        }
      }
    }
    
    // フォールバック時もチェックボックスをリセット
    setTimeout(() => {
      const checkboxes = document.getElementsByClassName("checkbox");
      for (let i = 0; i < checkboxes.length; i++) {
        checkboxes[i].checked = false;
      }
      console.log(`フォールバック: チェックボックスリセット完了 - 要素数: ${checkboxes.length}`);
    }, 200);
  }
    /**
   * 実験終了処理（ヘルパーメソッド）
   */
  endExperiment() {
    console.log('実験終了処理を開始します');
    // 実験終了時の適切な処理をここに実装
    // 必要に応じて結果送信や次のページへの遷移処理を追加
  }  /**
   * チェックボックスの確認
   */
  async checkDescription() {
    console.log('checkDescription: 開始');
    console.log('checkDescription: 現在のsceIdx:', this.sceIdx);
    console.log('checkDescription: scenarios:', this.scenarios);
    
    // this.sceIdxの境界チェックを追加して、配列範囲外アクセスを防止
    if (this.sceIdx < 0 || this.sceIdx >= this.scenarios.length) {
      console.error(`checkDescription: シナリオインデックスが範囲外です: ${this.sceIdx}/${this.scenarios.length}`);
      alert('シナリオデータエラーが発生しました。管理者にお問い合わせください。');
      return;
    }
    
    try {
      // 通常のチェックボックス検証
      console.log('checkDescription: validateCheckboxes実行前');
      validateCheckboxes("checkbox", "start_scenario_button");
      console.log('checkDescription: validateCheckboxes実行後');
      
      // 実験形式変更通知のチェック（全チェックボックス完了時に実行）
      console.log('checkDescription: 実験形式変更通知チェック開始');
      await this.checkFormatChangeNotification();
      console.log('checkDescription: 実験形式変更通知チェック完了');
    } catch (error) {
      console.error('checkDescription: 検証中にエラーが発生しました:', error);
      alert('チェックボックスの確認中にエラーが発生しました。ページを再読み込みしてください。');
    }
  }
    /**
   * 実験形式変更通知をチェックする
   * 1つ目のシナリオで全チェックボックス完了時に通知を表示
   */
  async checkFormatChangeNotification() {
    try {
      console.log('checkFormatChangeNotification: 通知チェック開始');
      console.log('checkFormatChangeNotification: 現在のsceIdx:', this.sceIdx);
      console.log('checkFormatChangeNotification: scenarios:', this.scenarios);
      
      // シナリオ説明用のチェックボックスが全て完了しているかチェック
      const checkboxes = document.getElementsByClassName("checkbox");
      console.log('checkFormatChangeNotification: チェックボックス数:', checkboxes.length);
      
      let allChecked = true;
      
      // チェックボックスが存在しない場合は処理しない
      if (checkboxes.length === 0) {
        console.log('checkFormatChangeNotification: チェックボックスが存在しないため処理をスキップ');
        return;
      }
      
      // 各チェックボックスの状態をログ出力
      for (let i = 0; i < checkboxes.length; i++) {
        console.log(`checkFormatChangeNotification: チェックボックス${i + 1}: ${checkboxes[i].checked}`);
        if (!checkboxes[i].checked) {
          allChecked = false;
        }
      }
      
      console.log('checkFormatChangeNotification: 全チェックボックス完了状態:', allChecked);
      
      // 全チェックボックスが完了していない場合は処理しない
      if (!allChecked) {
        console.log('checkFormatChangeNotification: 全チェックボックスが完了していないため通知をスキップ');
        return;
      }
      
      // 1つ目のシナリオでない場合は処理しない
      if (this.sceIdx !== 0) {
        console.log(`checkFormatChangeNotification: 1つ目のシナリオではないため通知をスキップ (現在のインデックス: ${this.sceIdx})`);
        return;
      }
      
      console.log(`checkFormatChangeNotification: 通知処理開始 - ユーザーID: ${this.userId}, シナリオ: ${this.sceIdx}, ページ: examine1_2`);
      
      // 実験形式変更通知を呼び出し
      const { checkAndShowFormatChangeNotification } = await import('./utilities.js');
      await checkAndShowFormatChangeNotification(this.userId, this.sceIdx, 'examine1_2');
      
      console.log('checkFormatChangeNotification: 通知処理完了');
      
    } catch (error) {
      console.error('checkFormatChangeNotification: エラーが発生しました:', error);
    }
  }/**
   * 次のサンプル表示ページへ遷移
   */
  toNextNewSamplePage() {
    try {
      // 初期化チェック
      if (!this.testOrder || Object.keys(this.testOrder).length === 0) {
        console.error('toNextNewSamplePage: testOrderが初期化されていません');
        alert('実験データの読み込みが完了していません。しばらく待ってから再度お試しください。');
        return;
      }
      
      if (!this.scenarios || this.scenarios.length === 0) {
        console.error('toNextNewSamplePage: scenariosが初期化されていません');
        alert('シナリオデータが読み込まれていません。ページを再読み込みしてください。');
        return;
      }
        if (!this.stimuli || this.stimuli.length === 0) {
        console.error('toNextNewSamplePage: stimuliが初期化されていません');
        console.error('toNextNewSamplePage: 現在のstimuliの状態:', this.stimuli);
        
        // 緊急時フォールバック: 刺激データを再初期化
        try {
          this.stimuli = shuffleArray(['1','2','3','4','5','6']);
          console.log('toNextNewSamplePage: stimuli緊急再初期化完了:', this.stimuli);
        } catch (error) {
          console.error('toNextNewSamplePage: 緊急再初期化も失敗:', error);
          this.stimuli = ['1','2','3','4','5','6']; // 最終フォールバック
          console.log('toNextNewSamplePage: 最終フォールバック適用:', this.stimuli);
        }
        
        // 再度チェック
        if (!this.stimuli || this.stimuli.length === 0) {
          alert('刺激データが初期化されていません。ページを再読み込みしてください。');
          return;
        }
      }
      
      // 境界チェック強化
      if (this.sceIdx < 0 || this.sceIdx >= this.scenarios.length) {
        console.error(`toNextNewSamplePage: シナリオインデックスが範囲外です: ${this.sceIdx}/${this.scenarios.length}`);
        alert('シナリオデータエラーが発生しました。管理者にお問い合わせください。');
        return;
      }    
    this.clearPage();
    let list = document.getElementsByClassName("checkbox");
    for (let index = 0; index < list.length; ++index) {
      list[index].checked = false;
    }
    this.currentTestPage = 0;
    document.getElementById('show_sample_area').style.display = "inline";
    document.getElementById('order').innerHTML = "実験の進捗状況";
    this.changeBackGround();    // 提示するサンプルのリストを作り、サンプルサイズを求める
    this.currentSampleSelection = [];
    this.sampleSize = 0;
    
    const scenarioKey = this.scenarios[this.sceIdx];
    const stimulusKey = this.stimuli[this.sceIdx];
    
    console.log(`サンプル表示準備: シナリオ=${scenarioKey}, 刺激=${stimulusKey}, sampleType=${dataManager.sampleType}`);
    
    // データ構造の存在確認
    if (!this.testOrder[scenarioKey]) {
      console.error(`toNextNewSamplePage: シナリオ ${scenarioKey} のデータが存在しません`);
      alert('シナリオデータが見つかりません。ページを再読み込みしてください。');
      return;
    }
    
    if (!this.testOrder[scenarioKey]['samples']) {
      console.error(`toNextNewSamplePage: シナリオ ${scenarioKey} にsamplesデータが存在しません`);
      alert('サンプルデータが見つかりません。ページを再読み込みしてください。');
      return;
    }
    
    // examine1_2では、samplesの構造が{stimulusKey: {a, b, c, d}}の形式
    if (!this.testOrder[scenarioKey]['samples'][stimulusKey]) {
      console.error(`toNextNewSamplePage: 刺激キー ${stimulusKey} のサンプルデータが存在しません`);
      console.log('toNextNewSamplePage: 利用可能なstimulusKeys:', Object.keys(this.testOrder[scenarioKey]['samples']));
      alert('刺激データが見つかりません。ページを再読み込みしてください。');
      return;
    }
    
    // 刺激データから{a, b, c, d}の値を取得
    const stimulusData = this.testOrder[scenarioKey]['samples'][stimulusKey];
    console.log(`toNextNewSamplePage: 刺激データ=`, stimulusData);
    
    // a,b,c,dの各値に基づいてサンプルを生成
    Object.keys(stimulusData).forEach((elm) => {
      const count = stimulusData[elm];
      if (count > 0) {
        this.sampleSize += count;
        this.cellSize = count;
        for (let i = 0; i < count; i++) {
          this.currentSampleSelection.push(elm);
        }
      }
    });
    
    // サンプルをシャッフル
    this.currentSampleSelection = shuffleArray(this.currentSampleSelection);
    
    console.log(`toNextNewSamplePage: サンプル数=${this.sampleSize}, サンプル配列の最初の3つ=[${this.currentSampleSelection.slice(0, 3).join(', ')}]...`);

    this.toNextSample();
    
    } catch (error) {
      console.error('toNextNewSamplePage: エラーが発生しました:', error);
      alert('サンプル表示の準備中にエラーが発生しました。ページを再読み込みしてください。');
    }
  }

  /**
   * 次のサンプルを表示
   */
  toNextSample() {
    const button1 = document.getElementById('next_sample');
    button1.disabled = true;
    if (this.currentTestPage >= this.sampleSize) {
      alert('結果は以上になります。');
      this.drawEstimate('fin');
      return;
    }
    this.showStimulation();
    setTimeout(() => {
      button1.disabled = false;
    }, 10);
  }  /**
   * スライダーの質問文を設定
   */
  initializeSlider() {
    // 境界チェック強化
    if (this.sceIdx < 0 || this.sceIdx >= this.scenarios.length) {
      console.error(`initializeSlider: シナリオインデックスが範囲外です: ${this.sceIdx}/${this.scenarios.length}`);
      alert('シナリオデータエラーが発生しました。管理者にお問い合わせください。');
      return;
    }
    
    const scenarioKey = this.scenarios[this.sceIdx];
    const scenarioData = this.testOrder[scenarioKey];
    
    if (!scenarioData) {
      console.error('initializeSlider: シナリオデータが見つかりません:', scenarioKey);
      alert(`シナリオ "${scenarioKey}" のデータが見つかりません。管理者にお問い合わせください。`);
      return;
    }
    
    // 条件に応じて評価文を選択（ui-manager.jsと同様のロジック）
    let resultText;
    if (dataManager.sampleType === 'symmetric' && scenarioData['result_symmetric']) {
      resultText = scenarioData['result_symmetric'];
      console.log('対称条件の評価文を使用:', resultText);
    } else {
      resultText = scenarioData['result'];
      console.log('非対称条件の評価文を使用:', resultText);
    }
    
    // スライダーの質問文を設定
    const sliderResultElement = document.getElementById('slider_scenario_result');
    if (sliderResultElement && resultText) {
      sliderResultElement.innerHTML = resultText;
      console.log('評価文をDOM要素に設定しました:', resultText);
    } else {
      console.error('slider_scenario_result要素が見つからないか、評価文が空です');
    }
    
    // 最小値と最大値の設定
    const minResultElement = document.getElementById('slider_min_result');
    if (minResultElement) {
      if ( dataManager.sampleType === 'symmetric') {
        minResultElement.textContent = '0：差はない';
      } else {
        minResultElement.textContent = '0：' + (scenarioData['min_result'] || '全く引き起こさない');
      }
    }
    
    const maxResultElement = document.getElementById('slider_max_result');
    if (maxResultElement) {
      if (dataManager.sampleType === 'symmetric') {
        // symmetric条件用のmax_result_symmetricがあれば優先、なければデフォルト文言
        maxResultElement.textContent = '100：' + (scenarioData['max_result_symmetric'] || 'より確実に引き起こす');
      } else {
        maxResultElement.textContent = '100：' + (scenarioData['max_result'] || '確実に引き起こす');
      }
    }
  }  /**
   * 刺激を表示
   */
  showStimulation() {
    if (!this.currentSampleSelection || this.currentTestPage >= this.currentSampleSelection.length) {
      console.error('サンプル選択データが不正です');
      return;
    }

    // 境界チェック強化
    if (this.sceIdx < 0 || this.sceIdx >= this.scenarios.length) {
      console.error(`showStimulation: シナリオインデックスが範囲外です: ${this.sceIdx}/${this.scenarios.length}`);
      alert('シナリオデータエラーが発生しました。管理者にお問い合わせください。');
      return;
    }

    const sample = this.currentSampleSelection[this.currentTestPage];
    const scenarioKey = this.scenarios[this.sceIdx];

    console.log(`刺激表示: シナリオ=${scenarioKey}, サンプル=${sample}, ページ=${this.currentTestPage + 1}/${this.currentSampleSelection.length}`);

    // 条件に応じて文章セットを選択
    let sentencesKey = 'sentences';
    let imagesKey = 'images1_2';

    if (dataManager.sampleType === 'symmetric') {
      if (this.testOrder[scenarioKey]['sentences_symmetric']) {
        sentencesKey = 'sentences_symmetric';
        console.log('対称条件の文章を使用');
      }
      if (this.testOrder[scenarioKey]['images_symmetric1_2']) {
        imagesKey = 'images_symmetric1_2';
        console.log('対称条件の画像を使用');
      }
    } else {
      console.log('非対称条件の文章・画像を使用');
    }

    // データ構造の存在確認
    if (!validateScenarioData(this.testOrder, scenarioKey, [`${sentencesKey}.${sample}`, imagesKey])) {
      return;
    }

    const desc = this.testOrder[scenarioKey][sentencesKey][sample];
    console.log("showStimulation_in - 使用文章:", desc);
    const descParts = desc.split('、');

    document.getElementById('first_sentence').innerHTML = "<h4>" + descParts[0] + "</h4>";
    document.getElementById('last_sentence').innerHTML = "<h4>" + descParts[1] + "</h4>";

    setElementsDisplay({
      'show_sample_area': 'inline',
      'first_sentence': 'inline-block',
      'last_sentence': 'inline-block',
      'sample_before': 'inline',
      'estimate_input_area': 'none',
      'next_sample': 'inline'
    });

    // 条件に応じた画像セットの設定
    const images = this.testOrder[scenarioKey][imagesKey];
    const imageMapping = createImageMapping(images, this.imgCombination, sample);
    setImagePaths(imageMapping);

    // 進捗バー更新
    this.progressBar();
    this.currentTestPage++;
    document.getElementById('current_page').innerHTML = this.currentTestPage + '/' + this.sampleSize;
  }

  /**
   * 進捗バーを更新
   */
  progressBar() {
    document.getElementById('progress_bar').value = this.currentTestPage;
    document.getElementById('progress_bar').max = this.sampleSize - 1;
  }  /**
   * 推定画面を描画
   */
  drawEstimate(c) {

    // 境界チェック強化
    if (this.sceIdx < 0 || this.sceIdx >= this.scenarios.length) {
      console.error(`drawEstimate: シナリオインデックスが範囲外です: ${this.sceIdx}/${this.scenarios.length}`);
      alert('シナリオデータエラーが発生しました。管理者にお問い合わせください。');
      return;
    }

    const scenarioKey = this.scenarios[this.sceIdx];
    console.log(`推定画面描画: シナリオ=${scenarioKey}, モード=${c}`);

    // 共通化されたデータ構造存在確認
    if (!validateScenarioData(this.testOrder, scenarioKey, ['result', 'min_result', 'max_result'])) {
      console.error(`drawEstimate: シナリオ "${scenarioKey}" の必要データが不足しています`);
      alert('シナリオデータが不完全です。管理者にお問い合わせください。');
      return;
    }

    this.clearPage();

    // UI要素の状態を一括設定
    setElementsDisplay({
      'estimate_input_area': 'inline-block',
      'next_scenario': 'none',
      'continue_scenario': 'inline'
    });
    
    setButtonStates({
      'next_scenario': true,
      'continue_scenario': true, 
      'finish_all_scenarios': true
    });    // フォーム要素の初期化
    setElementAttributes('checkbox', { 'disabled': true, 'checked': false });
    setElementAttributes('estimate_slider', { 'value': 50, 'disabled': true });
    setElementHTMLs({ 'estimate': '50' });
    
    // スライダーの質問文を設定
    this.initializeSlider();
    
    // 待機メッセージを表示し、3秒後にスライダーを有効化
    const waitMessage = document.getElementById('slider_wait_message');
    if (waitMessage) {
      waitMessage.style.display = 'block';
    }
    
    setTimeout(() => {
      const slider = document.getElementById('estimate_slider');
      if (slider && waitMessage) {
        slider.disabled = false;
        waitMessage.style.display = 'none';
      }
    }, 3000);      if (c == 'fin') {
      setElementsDisplay({ 'continue_scenario': 'none' });
      
      // 最後のシナリオの場合のみ「回答を送信する」ボタンを表示
      if (this.sceIdx == this.scenarios.length - 1) {
        setElementsDisplay({ 'finish_all_scenarios': 'inline' });
        console.log(`drawEstimate(): 最終シナリオ (${this.sceIdx + 1}/${this.scenarios.length}) - 送信ボタンを表示`);
      } else {
        setElementsDisplay({ 'next_scenario': 'inline' });
        console.log(`drawEstimate(): 中間シナリオ (${this.sceIdx + 1}/${this.scenarios.length}) - 次へボタンを表示`);
      }
    }
    
    // HTMLのリセット関数を呼び出し
    if (window.resetResponseFlow) {
      window.resetResponseFlow();
    }
  }/**
   * 推定値を取得
   */
  async getValue() {
    console.log(`getValue(): シナリオ ${this.sceIdx + 1}/${this.scenarios.length} の回答を記録開始`);
    await this.appendEstimation(
      document.getElementById('estimate_slider').value
    );
    console.log(`getValue(): 回答記録完了 - 総記録数: ${this.estimations.length} 件`);
  }
  /**
   * 推定画面のチェック確認
   * HTMLのonclick呼び出しを無効化し、スライダー操作に基づく自動処理のみを行う
   */
  checkEstimate() {
    // この関数は後方互換性のために残しているが、実際の処理はHTMLのイベントリスナーに移行
    console.log('checkEstimate() called - now handled by HTML event listeners');
  }  /**
   * 推定データを追加
   */
  async appendEstimation(estimation) {
    // 現在のサンプルデータを取得
    const currentSample = this.currentSampleSelection[this.currentTestPage - 1];
    const scenarioKey = this.scenarios[this.sceIdx];
    const stimulusKey = this.stimuli[this.sceIdx];
    
    console.log(`appendEstimation: currentSample=${currentSample}, scenarioKey=${scenarioKey}, stimulusKey=${stimulusKey}`);
    
    // examine1_2では、currentSampleが'a', 'b', 'c', 'd'のいずれかの文字列
    // 対応するサンプル数を刺激データから取得
    const stimulusData = this.testOrder[scenarioKey]['samples'][stimulusKey];
    let a_value = 0, b_value = 0, c_value = 0, d_value = 0;
    
    if (stimulusData) {
      a_value = stimulusData.a || 0;
      b_value = stimulusData.b || 0;
      c_value = stimulusData.c || 0;
      d_value = stimulusData.d || 0;
    } else {
      console.error(`appendEstimation: 刺激データが見つかりません - scenarioKey=${scenarioKey}, stimulusKey=${stimulusKey}`);
    }
    
    console.log(`appendEstimation: 刺激データ a=${a_value}, b=${b_value}, c=${c_value}, d=${d_value}`);
      // 実験順序を取得
    let experimentOrder = 'order1'; // デフォルト値
    try {
      const { getExperimentOrder } = await import('./utilities.js');
      experimentOrder = await getExperimentOrder(this.userId, false);
    } catch (error) {
      console.warn('実験順序の取得に失敗しました。デフォルト値を使用します:', error);
    }
      // is_first を 0/1 に変換
    // order2の場合にexamine1_2が最初の実験となる
    const isFirstNumeric = experimentOrder === 'order2' ? 1 : 0;
    
    // is_symmetric を 0/1 に変換
    const isSymmetricNumeric = dataManager.sampleType === 'symmetric' ? 1 : 0;
      // 最適化されたデータ構造：a, b, c, d を個別の列として記録
    let data = {
      'user_id': this.userId,
      'cover_story': scenarioKey,
      'a_value': a_value,
      'b_value': b_value,
      'c_value': c_value,
      'd_value': d_value,
      'estimation': estimation,
      'is_first': isFirstNumeric,
      'is_symmetric': isSymmetricNumeric,
      'sample_number': this.currentTestPage,
      'timestamp': getNow()
    };
      this.estimations.push(data);
    console.log(`推定データを記録しました（最適化済み、is_first/is_symmetric は 0/1 形式）- 記録数: ${this.estimations.length}/${this.scenarios.length}:`, data);
  }/**
   * 結果をエクスポート
   */
  async exportResults() {
    try {
      let data = {};
      data['user_id'] = this.userId;
      data['start_time'] = this.startTime;
      data['end_time'] = getNow();
      data['user_agent'] = window.navigator.userAgent;
      this.userData.push(data);
      
      // 実験順序に基づいて次のページURLを決定
      console.log('examine1_2: exportResults - ユーザーID:', this.userId);
      const nextUrl = await getNextPageUrl('eXaM1nE_2', this.userId);
      console.log('examine1_2: 次のページURL:', nextUrl);
      console.log('examine1_2: 現在のユーザーID（確認）:', this.userId);

      // DataManagerのsendExamine12Resultsメソッドを使用
      await dataManager.sendExamine12Results(this.estimations, nextUrl);
      
    } catch (error) {
      console.error('結果送信に失敗しました:', error);
      alert("回答送信中にエラーが発生しました。もう一度送信ボタンを押してください。");
      
      // エラー時はボタンを再度有効化
      setButtonStates({ 'finish_all_scenarios': false });
    }
  }  /**
   * 背景色を2色交互に変更（アイコンの色と被らないように）
   */
  changeBackGround() {
    // シナリオインデックスに基づいて2色を交互に選択
    const colorIndex = this.sceIdx % 2;
    const bgColor = this.bgcolors[colorIndex] || 'Transparent';
    document.body.style.backgroundColor = bgColor;
    console.log(`背景色変更: シナリオ${this.sceIdx + 1} -> ${bgColor}`);
  }

  /**
   * 背景色をリセット
   */
  resetBackGround() {
    document.body.style.backgroundColor = 'Transparent';
  }
}

// グローバル変数として実験インスタンスを保持
let experimentManager;

// 安全なアクセスのためのヘルパー関数（エラーハンドリング強化版）
function safeCall(methodName, ...args) {
  if (!experimentManager) {
    console.error(`experimentManager not initialized when calling ${methodName}`);
    alert('実験システムの初期化が完了していません。ページを再読み込みしてください。');
    return;
  }
  if (typeof experimentManager[methodName] !== 'function') {
    console.error(`Method ${methodName} not found on experimentManager`);
    alert('実験システムにエラーが発生しました。ページを再読み込みしてください。');
    return;
  }
  
  // 初期化状態のチェック（toNextNewSamplePageの場合）
  if (methodName === 'toNextNewSamplePage') {
    if (!experimentManager.testOrder || Object.keys(experimentManager.testOrder).length === 0) {
      console.error('safeCall: testOrderが初期化されていません');
      alert('実験データの読み込みが完了していません。しばらく待ってから再度お試しください。');
      return;
    }
    if (!experimentManager.scenarios || experimentManager.scenarios.length === 0) {
      console.error('safeCall: scenariosが初期化されていません');
      alert('シナリオデータが読み込まれていません。ページを再読み込みしてください。');
      return;
    }
  }
  
  try {
    return experimentManager[methodName](...args);
  } catch (error) {
    console.error(`Error executing ${methodName}:`, error);
    alert(`${methodName}の実行中にエラーが発生しました。ページを再読み込みしてください。`);
  }
}

// ページ読み込み時の初期化
window.addEventListener('DOMContentLoaded', async function() {
  try {
    // ユーザーID取得（localStorage優先、なければURL）
    let userId = null;
    try {
      userId = localStorage.getItem('exp_user_id_persistent');
    } catch (e) {}
    if (!userId) {
      const urlParams = new URLSearchParams(window.location.search);
      userId = urlParams.get('id');
    }
    if (!userId) {
      alert('ユーザーIDが取得できません。最初からやり直してください。');
      window.location.href = '/top1_2';
      return;
    }
  } catch (e) {
    alert('進捗情報の取得に失敗しました。');
    window.location.href = '/top1_2';
  }
});

// グローバル関数として公開（HTMLからの呼び出し用）
window.check_description = async () => {
  if (!experimentManager) {
    console.error('experimentManager not initialized when calling check_description');
    alert('実験システムの初期化が完了していません。ページを再読み込みしてください。');
    return;
  }
  if (typeof experimentManager.checkDescription !== 'function') {
    console.error('Method checkDescription not found on experimentManager');
    alert('実験システムにエラーが発生しました。ページを再読み込みしてください。');
    return;
  }
  try {
    return await experimentManager.checkDescription();
  } catch (error) {
    console.error('check_description execution error:', error);
    alert('チェックボックスの確認中にエラーが発生しました。ページを再読み込みしてください。');
  }
};
window.to_next_new_sample_page = () => {
  console.log('to_next_new_sample_page called');
  
  // 追加のチェック: experimentManagerの初期化状態を確認
  if (!experimentManager) {
    console.error('to_next_new_sample_page: experimentManager is not initialized');
    alert('実験システムの初期化が完了していません。ページを再読み込みしてください。');
    return;
  }
  
  // データの存在確認
  if (!experimentManager.testOrder || Object.keys(experimentManager.testOrder).length === 0) {
    console.error('to_next_new_sample_page: testOrder is not ready');
    alert('実験データの読み込みが完了していません。しばらく待ってから再度お試しください。');
    return;
  }
  
  if (!experimentManager.scenarios || experimentManager.scenarios.length === 0) {
    console.error('to_next_new_sample_page: scenarios is not ready');
    alert('シナリオデータが読み込まれていません。ページを再読み込みしてください。');
    return;
  }
  
  safeCall('toNextNewSamplePage');
};
window.to_next_sample = () => safeCall('toNextSample');
window.draw_estimate = (c) => safeCall('drawEstimate', c);
window.get_value = async () => {
  if (!experimentManager) {
    console.error('experimentManager not initialized when calling get_value');
    alert('実験システムの初期化が完了していません。ページを再読み込みしてください。');
    return;
  }
  try {
    return await experimentManager.getValue();
  } catch (error) {
    console.error('get_value execution error:', error);
    alert('回答の記録中にエラーが発生しました。もう一度お試しください。');
  }
};
window.check_estimate = () => safeCall('checkEstimate');
window.to_next_scenario_description = (isFirstTime) => safeCall('toNextScenarioDescription', isFirstTime);
window.showStimulation = () => safeCall('showStimulation');
window.get_value_fin = async function() {
  if (!experimentManager) {
    alert('実験システムの初期化が完了していません。ページを再読み込みしてください。');
    return;
  }
  try {
    await window.get_value();
    // validateProgressOnSubmitによる進行順序チェックは不要になったため削除
    await experimentManager.exportResults();
  } catch (error) {
    alert('進捗情報の取得に失敗しました。ページを再読み込みしてください。');
    console.error(error);
  }
};

// ページロード時に初期化を必ず実行
window.addEventListener('DOMContentLoaded', async () => {
  try {
    experimentManager = new Experiment12Manager();
    window.experimentManager = experimentManager;
    await experimentManager.initializeAsync();
    console.log('examine1_2: ページ初期化完了');
  } catch (e) {
    alert('ページ初期化に失敗しました。再読み込みしてください。');
    console.error('examine1_2: 初期化エラー', e);
  }
});

window.addEventListener('DOMContentLoaded', function() {
  if (isAlreadyParticipated()) {
    const btn = document.getElementById('participate_btn');
    if (btn) btn.style.display = 'none';
    const msg = document.getElementById('already_participated_msg');
    if (msg) msg.style.display = 'block';
  }
});