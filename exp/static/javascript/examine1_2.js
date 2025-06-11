/**
 * examine1_2.js - 因果関係の強さを推定する実験
 * モジュラー構造に対応し、examine1との互換性を確保
 */

// 共有モジュールのインポート
import config from './config.js';
import dataManager from './data-manager.js';
import uiManager from './ui-manager.js';
import eventHandler from './event-handler.js';
import { preventBrowserBack, setupPageLeaveWarning, shuffleArray, zeroPadding, getNow, getNextPageUrl } from './utilities.js';
import { 
  validateCheckboxes, 
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

/**
 * 実験1.2を管理するクラス
 */
class Experiment12Manager {  constructor() {    // 実験タイプを設定
    dataManager.setExperimentType('examine1_2');
    
    // examine1_2固有の設定
    this.file = '../static/material1.json';
    this.userData = [];
    this.testOrder = {};  // オブジェクトとして初期化
    this.currentSampleSelection = [];
    this.estimations = [];
    
    // シナリオはconfig.jsから取得（ハードコードしない）
    this.scenarios = null;  // 初期化時に設定される
    this.stimuli = shuffleArray(['1','2','3','4','5','6']);
    this.bgcolors = shuffleArray(['#f0ffff','#f0fff0','#f5f5dc','#e0ffff','#fffaf0','#f8f8ff','#fffafa','#f5f5f5','#f0f8ff','#ffe4e1','#d8bfd8']);
    
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
    this.sceIdx = 0;
    this.estI = 0;
    this.cellSize = 0;
    
    this.initialize();
  }  /**
   * 実験を初期化
   */  async initialize() {
    try {
      // URLパラメータからユーザーIDを取得（examine1と同様）
      const urlParams = new URLSearchParams(window.location.search);
      this.userId = urlParams.get('id');
      
      // ユーザーIDが取得できない場合は新規生成
      if (!this.userId) {
        this.userId = Math.round(Math.random() * 100000000);
        this.userId = zeroPadding(this.userId, 8);
        console.warn('examine1_2: URLからユーザーIDを取得できませんでした。新規生成:', this.userId);
      } else {
        console.log('examine1_2: URLからユーザーIDを取得:', this.userId);
      }
      
      // DataManagerにユーザーIDを設定
      dataManager.userId = this.userId;
      
      // サーバーから実験条件（対称/非対称）を取得
      await dataManager.fetchSampleType();
      console.log('examine1_2: 実験条件:', dataManager.sampleType);
      
      // config.jsからexamine1_2用のシナリオを取得
      this.scenarios = config.setExperimentScenarios('examine1_2', this.userId);
      console.log('examine1_2: 配布されたシナリオ:', this.scenarios.join(', '));
      
      // データの読み込み
      this.testOrder = await this.readJson(this.file);
      this.estimations = new Array();
      
      // 共通サンプルデータの解決
      await this.resolveCommonSamples();
      
      // 画像のプリロード
      this.getImages();
      
      // 最初のシナリオ表示
      this.toNextScenarioDescription(true);
      
      // ページ離脱警告の設定
      setupPageLeaveWarning();
      
      // ブラウザバック防止
      preventBrowserBack();
      
      console.log('examine1_2: 初期化完了');
    } catch (error) {
      console.error('examine1_2の初期化に失敗しました:', error);
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
  toNextScenarioDescription(isFirstTime = false) {
    if (!validateScenarioData(this.testOrder, null)) {
      return;
    }
    
    this.clearPage();
    if (!isFirstTime) {
      this.sceIdx++;
    }
    this.resetBackGround();
    
    const scenarioKey = this.scenarios[this.sceIdx];
    if (!validateScenarioData(this.testOrder, scenarioKey)) {
      return;
    }
    
    document.getElementById('page').innerHTML = "<h4>" + (this.sceIdx + 1) + '/' + this.scenarios.length + "種類目</h4>";
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
    }

    // 条件に応じて説明文を選択
    let descriptions;
    if (dataManager.sampleType === 'symmetric' && this.testOrder[scenarioKey]['descriptions_symmetric']) {
      descriptions = this.testOrder[scenarioKey]['descriptions_symmetric'];
      console.log('対称条件の説明文を使用');
    } else {
      descriptions = this.testOrder[scenarioKey]['descriptions'];
      console.log('非対称条件の説明文を使用');
    }
    
    // 説明文のHTML要素を動的に生成（examine1と同様）
    const scenarioDescriptionsContainer = document.getElementById('scenario_descriptions');
    if (scenarioDescriptionsContainer && descriptions && descriptions.length > 0) {
      let html = '<form action="cgi-bin/abc.cgi" method="post">';
      for (let i = 0; i < descriptions.length; i++) {
        html += `
          <p>
            <input class="checkbox" type="checkbox" id="checkbox${i + 1}" style="transform:scale(1.5)" onclick="check_description()" />
            <label for="checkbox${i + 1}" id="scenario_description${i + 1}">${descriptions[i]}</label>
          </p>`;
        if (i < descriptions.length - 1) {
          html += '<br>';
        }
      }
      html += '</form>';
      scenarioDescriptionsContainer.innerHTML = html;
    } else {
      // 既存のラベル要素を使用（フォールバック）
      if (descriptions && descriptions.length > 0) {
        for (let i = 0; i < descriptions.length; i++) {
          const element = document.getElementById('scenario_description' + String(i + 1));
          if (element) {
            element.innerHTML = descriptions[i];
          }
        }
      }
    }
    
    // チェックボックスをリセット
    const checkboxes = document.getElementsByClassName("checkbox");
    for (let i = 0; i < checkboxes.length; i++) {
      checkboxes[i].checked = false;
    }
  }
  /**
   * チェックボックスの確認
   */
  checkDescription() {
    validateCheckboxes("checkbox", "start_scenario_button");
  }  /**
   * 次のサンプル表示ページへ遷移
   */
  toNextNewSamplePage() {
    if (!validateScenarioData(this.testOrder, null)) {
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
    this.changeBackGround();

    // 提示するサンプルのリストを作り、サンプルサイズを求める
    this.currentSampleSelection = [];
    this.sampleSize = 0;
    
    const scenarioKey = this.scenarios[this.sceIdx];
    const stimulusKey = this.stimuli[this.sceIdx];
    
    // データ構造の存在確認
    if (!validateScenarioData(this.testOrder, scenarioKey, [`samples.${stimulusKey}`])) {
      return;
    }
    
    const samples = this.testOrder[scenarioKey]['samples'][stimulusKey];
    Object.keys(samples).forEach((elm) => {
      if (samples[elm] > 0) {
        this.sampleSize += samples[elm];
        this.cellSize = samples[elm];
        for (let i = 0; i < this.cellSize; i++) {
          this.currentSampleSelection.push(elm);
        }
      }
    });
    this.currentSampleSelection = shuffleArray(this.currentSampleSelection);

    this.toNextSample();
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
    }, 500);
  }  /**
   * スライダーの質問文を設定
   */
  initializeSlider() {
    const scenarioKey = this.scenarios[this.sceIdx];
    const scenarioData = this.testOrder[scenarioKey];
    
    if (!scenarioData) {
      console.error('シナリオデータが見つかりません:', scenarioKey);
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
      sliderResultElement.textContent = resultText;
      console.log('評価文をDOM要素に設定しました:', resultText);
    } else {
      console.error('slider_scenario_result要素が見つからないか、評価文が空です');
    }
    
    // 最小値と最大値の設定
    const minResultElement = document.getElementById('slider_min_result');
    if (minResultElement) {
      minResultElement.textContent = '0：' + (scenarioData['min_result'] || '全く引き起こさない');
    }
    
    const maxResultElement = document.getElementById('slider_max_result');
    if (maxResultElement) {
      maxResultElement.textContent = '100：' + (scenarioData['max_result'] || '確実に引き起こす');
    }
  }
  /**
   * 刺激を表示
   */
  showStimulation() {
    if (!this.currentSampleSelection || this.currentTestPage >= this.currentSampleSelection.length) {
      console.error('サンプル選択データが不正です');
      return;
    }
    
    const sample = this.currentSampleSelection[this.currentTestPage];
    const scenarioKey = this.scenarios[this.sceIdx];
    
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
    const scenarioKey = this.scenarios[this.sceIdx];
    
    // 共通化されたデータ構造存在確認
    if (!validateScenarioData(this.testOrder, scenarioKey, ['result', 'min_result', 'max_result'])) {
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
  }  /**
   * 推定値を取得
   */
  async getValue() {
    console.log(`getValue(): シナリオ ${this.sceIdx + 1}/${this.scenarios.length} の回答を記録開始`);
    await this.appendEstimation(
      document.getElementById('estimate_slider').value
    );
    console.log(`getValue(): 回答記録完了 - 総記録数: ${this.estimations.length} 件`);
  }/**
   * 最終的な値を取得
   */
  async getValueFin() {
    // 安全チェック：6つのシナリオがすべて完了しているかを確認
    if (this.sceIdx !== this.scenarios.length - 1) {
      alert(`警告: まだすべてのシナリオが完了していません。現在 ${this.sceIdx + 1}/${this.scenarios.length} です。`);
      console.warn(`getValueFin(): 不正な送信試行 - 現在のシナリオ: ${this.sceIdx + 1}, 総シナリオ数: ${this.scenarios.length}`);
      return;
    }
    
    console.log(`getValueFin(): 最終シナリオの回答記録開始 - シナリオ: ${this.sceIdx + 1}/${this.scenarios.length}, 現在の推定データ: ${this.estimations.length} 件`);
    
    // 回答送信ボタンの連打防止
    setButtonStates({ 'finish_all_scenarios': true });
    
    // 最後の回答値を記録（非同期処理完了を待つ）
    await this.getValue();
    
    // 最後の回答記録後の安全チェック
    if (this.estimations.length < this.scenarios.length) {
      alert(`警告: 推定データが不十分です。${this.estimations.length}/${this.scenarios.length} 件しか記録されていません。`);
      console.warn(`getValueFin(): 推定データ不足 - 記録数: ${this.estimations.length}, 期待数: ${this.scenarios.length}`);
      setButtonStates({ 'finish_all_scenarios': false }); // ボタンを再度有効化
      return;
    }
      console.log(`getValueFin(): 安全チェック通過 - 推定データ: ${this.estimations.length} 件`);
    
    try {
      // examine1と同様のエラーハンドリングを追加
      await this.exportResults();
    } catch (error) {
      console.error('結果送信に失敗しました:', error);
      alert("回答送信中にエラーが発生しました。もう一度送信ボタンを押してください。");
      setButtonStates({ 'finish_all_scenarios': false }); // ボタンを再度有効化
    }
  }/**
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
    
    // サンプルデータから各値を取得
    const scenarioSamples = this.testOrder[scenarioKey]['samples'][stimulusKey];
    
    // 実験順序を取得
    let experimentOrder = 'order1'; // デフォルト値
    try {
      const { getExperimentOrder } = await import('./utilities.js');
      experimentOrder = await getExperimentOrder(this.userId, false);
    } catch (error) {
      console.warn('実験順序の取得に失敗しました。デフォルト値を使用します:', error);
    }
    
    // 最適化されたデータ構造：a, b, c, d を個別の列として記録
    let data = {
      'user_id': this.userId,      'number': scenarioKey,
      'a_value': scenarioSamples.a || 0,
      'b_value': scenarioSamples.b || 0,
      'c_value': scenarioSamples.c || 0,
      'd_value': scenarioSamples.d || 0,
      'estimation': estimation,
      'order': experimentOrder,
      'symmetric_condition': dataManager.sampleType,
      'sample_number': this.currentTestPage,
      'timestamp': getNow()
    };
      this.estimations.push(data);
    console.log(`推定データを記録しました（最適化済み）- 記録数: ${this.estimations.length}/${this.scenarios.length}:`, data);
  }
/**
   * 結果をエクスポート
   */
  async exportResults() {
    try {
      let data = {};
      data['user_id'] = this.userId;
      data['start_time'] = this.startTime;
      data['end_time'] = getNow();
      data['user_agent'] = window.navigator.userAgent;
      this.userData.push(data);      // 実験順序に基づいて次のページURLを決定
      console.log('examine1_2: exportResults - ユーザーID:', this.userId);
      const nextUrl = await getNextPageUrl('examine1_2', this.userId);
      console.log('examine1_2: 次のページURL:', nextUrl);

      // DataManagerのsendExamine12Resultsメソッドを使用
      await dataManager.sendExamine12Results(this.estimations, nextUrl);
      
    } catch (error) {
      console.error('結果送信に失敗しました:', error);
      alert("回答送信中にエラーが発生しました。もう一度終了ボタンを押してください。");
      
      // エラー時はボタンを再度有効化
      setButtonStates({ 'finish_all_scenarios': false });
    }
  }
  /**
   * 背景色を変更（インデックスベース）
   */
  changeBackGround() {
    const bgColor = this.bgcolors[this.sceIdx] || 'Transparent';
    document.body.style.backgroundColor = bgColor;
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

// ページ読み込み時の初期化
window.addEventListener('DOMContentLoaded', () => {
  experimentManager = new Experiment12Manager();
});

// グローバル関数として公開（HTMLからの呼び出し用）
window.check_description = () => experimentManager.checkDescription();
window.to_next_new_sample_page = () => experimentManager.toNextNewSamplePage();
window.to_next_sample = () => experimentManager.toNextSample();
window.draw_estimate = (c) => experimentManager.drawEstimate(c);
window.get_value = async () => await experimentManager.getValue();
window.get_value_fin = async () => await experimentManager.getValueFin();
window.check_estimate = () => experimentManager.checkEstimate();
window.to_next_scenario_description = (isFirstTime) => experimentManager.toNextScenarioDescription(isFirstTime);
window.showStimulation = () => experimentManager.showStimulation();