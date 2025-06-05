/**
 * examine1_2.js - 因果関係の強さを推定する実験
 * モジュラーアーキテクチャに対応
 */
import { getNow, zeroPadding, shuffleArray, preventBrowserBack, getOrCreateUserId, loadPageStyles, getNextPageUrl, setupPageLeaveWarning } from './utilities.js';
import { fetchJson, postData } from './ajax-utils.js';
import eventBus from './event-bus.js';
import dataManager from './data-manager.js';
import eventHandler from './event-handler.js';
import uiManager from './ui-manager.js';
import config from './config.js';

// shuffleArrayのエイリアス
const shuffle = shuffleArray;

/**
 * 実験1.2の管理クラス
 */
class Experiment12Manager {
  constructor() {
    // 実験タイプを設定
    dataManager.setExperimentType('examine1_2');
    
    // 実験データ
    this.experimentData = null;
    
    // examine1_2固有の状態
    this.currentTestPage = 0;
    this.sampleSize = 0;
    this.scenarioIndex = 0;
    this.currentSampleSelection = [];
    this.cellSize = 0;
    this.estimationIndex = 0;
    this.sampleType = 'asymmetric'; // デフォルトは非対称条件
    
    // examine1_2固有の設定
    this.bgcolors = shuffle([
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
    
    // DataManagerとの連携設定
    this.initializeDataManager();
    this.setupEventListeners();
  }

  /**
   * DataManagerとの連携を初期化
   */
  initializeDataManager() {
    // 実験固有のデータ構造を初期化
    dataManager.customData.estimations = [];
    dataManager.customData.sampleType = 'asymmetric';
  }

  setupEventListeners() {
    // 共有EventHandlerを使用してexamine1_2固有のイベントを設定
    eventHandler.setupExamine12Events(this);
    
    // シナリオ配布完了イベントを監視
    eventBus.on('scenarios:assigned', (data) => {
      console.log('examine1_2: シナリオ配布完了', data);
      this.scenarios = data.scenarios;
      this.stimuli = shuffle(['1','2','3','4','5','6']);
    });
    
    // ページ読み込み完了の確認と初期化
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.initialize());
    } else if (document.readyState === 'interactive' || document.readyState === 'complete') {
      // すでに読み込み完了している場合は即座に初期化
      this.initialize();
    }
  }

  async initialize() {
    try {
      // DataManagerを使用してユーザーIDと開始時刻を設定
      dataManager.userId = getOrCreateUserId({ persistent: true });
      dataManager.startTime = getNow();
      
      await loadPageStyles('examine1_2');
      await this.loadExperimentData();
      await this.fetchSampleType(); // 実験条件を取得
      await this.preloadImages();
      
      this.setupLazyLoading();
      
      // シナリオが設定されるまで待機
      if (!this.scenarios) {
        console.log('examine1_2: シナリオ配布を待機中...');
        await new Promise(resolve => {
          const checkScenarios = () => {
            if (config.scenarios && config.scenarios.length === 6) {
              this.scenarios = config.scenarios;
              this.stimuli = shuffle(['1','2','3','4','5','6']);
              resolve();
            } else {
              setTimeout(checkScenarios, 100);
            }
          };
          checkScenarios();
        });
      }
      
      console.log('examine1_2: 使用シナリオ', this.scenarios);
      this.toNextScenarioDescription(true);
      
    } catch (error) {
      console.error('実験の初期化に失敗しました', error);
      uiManager.showErrorMessage('実験の準備中にエラーが発生しました。ページを再読み込みしてください。');
    }
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
}

// 実験マネージャーのインスタンスを作成
const experimentManager = new Experiment12Manager();

// グローバルスコープに公開する必要がある関数（HTMLから呼び出し可能）
window.experiment12Manager = null;

// ページ読み込み時に実験マネージャーを初期化
window.addEventListener('DOMContentLoaded', () => {
  window.experiment12Manager = new Experiment12Manager();
});

// HTMLのonclick属性から呼び出し可能なグローバル関数
window.checkDescription = function() {
  if (window.experiment12Manager) {
    window.experiment12Manager.checkDescription();
  }
};

window.to_next_new_sample_page = function() {
  if (window.experiment12Manager) {
    window.experiment12Manager.toNextNewSamplePage();
  }
};

window.checkEstimate = function() {
  if (window.experiment12Manager) {
    window.experiment12Manager.checkEstimate();
  }
};