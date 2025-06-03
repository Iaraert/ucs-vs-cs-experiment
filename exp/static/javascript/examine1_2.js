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

// shuffleArrayのエイリアス
const shuffle = shuffleArray;

/**
 * 実験1.2の管理クラス
 */
class Experiment12Manager {
  constructor() {
    // 実験データ
    this.experimentData = null;
    
    // 実験の状態
    this.currentTestPage = 0;
    this.sampleSize = 0;
    this.scenarioIndex = 0;
    this.currentSampleSelection = [];
    this.cellSize = 0;
    this.estimationIndex = 0;
    this.sampleType = 'asymmetric'; // デフォルトは非対称条件
    
    // 刺激設定
    this.scenarios = shuffle(['one','two','three','four','five','six']);
    this.stimuli = shuffle(['1','2','3','4','5','6']);
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
    // DataManagerのカスタム設定
    dataManager.experimentType = 'examine1_2';
    
    // 実験固有のデータ構造を初期化
    dataManager.customData.estimations = [];
    dataManager.customData.sampleType = 'asymmetric';
  }

  setupEventListeners() {
    // ページ読み込み時の処理
    window.addEventListener('load', () => this.initialize());
    
    // 共有EventHandlerを使用してexamine1_2固有のイベントを設定
    eventHandler.setupExamine12Events(this);
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
      this.toNextScenarioDescription(true);
    } catch (error) {
      console.error('実験の初期化に失敗しました', error);
      uiManager.showErrorMessage('実験の準備中にエラーが発生しました。ページを再読み込みしてください。');
    }
  }

  async loadExperimentData() {
    try {
      this.experimentData = await fetchJson('../static/material1_2.json');
      return this.experimentData;
    } catch (error) {
      console.error('実験データの読み込みに失敗しました', error);
      uiManager.showErrorMessage('データの読み込みに失敗しました。ページを再読み込みしてください。');
      throw error;
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
      imageUrls.push(`${basePath}/${scenarioData['images']['arrow']}`);
      for (const type of this.imageType) {
        imageUrls.push(`${basePath}/${scenarioData['images'][type]}`);
      }
      
      // 対称条件の画像（存在する場合）
      if (scenarioData['images_symmetric']) {
        imageUrls.push(`${basePath}/${scenarioData['images_symmetric']['arrow']}`);
        for (const type of this.imageType) {
          imageUrls.push(`${basePath}/${scenarioData['images_symmetric'][type]}`);
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
    document.getElementById('page').innerHTML = "<h4>" + (this.scenarioIndex + 1) + '/' + this.scenarios.length + "種類目</h4>";
    document.getElementById('scenario_title').innerHTML = "<h2>" + this.experimentData[this.scenarios[this.scenarioIndex]]['title'] + "</h2>";
    document.getElementById('check_sentence').style.display = "inline-block";
    document.getElementById('description_area').style.display = "inline-block";
    document.getElementById('start_scenario_button').setAttribute("disabled", true);
    
    // 条件に応じた説明文を選択
    let descriptions;
    if (this.sampleType === 'symmetric' && this.experimentData[this.scenarios[this.scenarioIndex]]['descriptions_symmetric']) {
      descriptions = this.experimentData[this.scenarios[this.scenarioIndex]]['descriptions_symmetric'];
      console.log('対称条件の説明文を使用');
    } else {
      descriptions = this.experimentData[this.scenarios[this.scenarioIndex]]['descriptions'];
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
    
    const currentScenario = this.scenarios[this.scenarioIndex];
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
    const currentScenario = this.scenarios[this.scenarioIndex];
    
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
    if (this.sampleType === 'symmetric' && this.experimentData[currentScenario]['images_symmetric']) {
      imageSet = this.experimentData[currentScenario]['images_symmetric'];
      console.log('対称条件の画像を使用');
    } else {
      imageSet = this.experimentData[currentScenario]['images'];
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
      
      if (this.scenarioIndex === this.scenarios.length - 1) {
        document.getElementById('finish_all_scenarios').style.display = 'inline';
      } else {
        document.getElementById('next_scenario').style.display = 'inline';
      }
    }

    const currentScenario = this.experimentData[this.scenarios[this.scenarioIndex]];
    
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

  handleNextScenario() {
    this.recordEstimation();
    this.toNextScenarioDescription();
  }

  handleContinueScenario() {
    this.recordEstimation();
    this.toNextNewSamplePage();
  }

  async handleExportResults() {
    document.getElementById('finish_all_scenarios').disabled = true;
    this.recordEstimation();
    
    try {
      await this.exportResults();
    } catch (error) {
      // エラーはexportResults内で処理済み
    }
  }

  recordEstimation() {
    const estimation = document.getElementById('estimate_slider').value;
    
    dataManager.customData.estimations.push({
      'user_id': dataManager.userId,
      'number': this.scenarios[this.scenarioIndex],
      'stimuli': this.stimuli[this.scenarioIndex],
      'estimation': estimation
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

// スライダーイベントハンドラーは共有EventHandlerで処理