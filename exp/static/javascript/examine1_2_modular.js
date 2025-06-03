/**
 * examine1_2_modular.js - 因果関係の強さを推定する実験（モジュラー版）
 * 
 * モノリシック構造から共有モジュールを使用するモジュラーアーキテクチャに移行
 */

// 共有モジュールのインポート
import config from './config.js';
import dataManager from './data-manager.js';
import uiManager from './ui-manager.js';
import eventHandler from './event-handler.js';
import eventBus from './event-bus.js';
import { preventBrowserBack, setupPageLeaveWarning, getNextPageUrl } from './utilities.js';

/**
 * 実験1.2を管理するクラス - モジュラー版
 */
class Experiment12ModularManager {
  constructor() {
    // モジュラー版では各マネージャーへの参照のみ保持
    this.dataManager = dataManager;
    this.uiManager = uiManager;
    this.eventHandler = eventHandler;
    
    // examine1_2固有の設定を初期化
    this.initializeExperiment12Config();
    
    // examine1_2固有の状態管理
    this.currentTestPage = 0;
    this.sampleSize = 0;
    this.currentSampleSelection = [];
    this.cellSize = 0;
    this.estimationIndex = 0;
    
    // examine1_2固有の画像組み合わせ設定
    this.imageType = ["p", "notp", "q", "notq"];
    this.imgCombination = {
      'a': {'cause': 'p', 'effect': 'q'},
      'b': {'cause': 'p', 'effect': 'notq'},
      'c': {'cause': 'notp', 'effect': 'q'},
      'd': {'cause': 'notp', 'effect': 'notq'}
    };
    
    this.initializeEventHandlers();
  }

  /**
   * examine1_2固有の設定を初期化
   */
  initializeExperiment12Config() {
    // material1_2.jsonを使用するように設定を上書き
    config.jsonFilePath = '../static/material1.json';
    
    // examine1_2用のアイコン設定を維持
    config.icons = {
      'a': {'cause': 'p', 'effect': 'q'},
      'b': {'cause': 'p', 'effect': 'notq'},
      'c': {'cause': 'notp', 'effect': 'q'},
      'd': {'cause': 'notp', 'effect': 'notq'}
    };
    
    // examine1_2用の画像タイプ
    config.imageTypes = ["p", "notp", "q", "notq"];
  }

  /**
   * examine1_2固有のイベントハンドラーを初期化
   */
  initializeEventHandlers() {
    // 基本的なイベントハンドラーを初期化
    this.eventHandler.init();
    
    // examine1_2固有のイベントハンドラーを追加
    this.setupExamineSpecificHandlers();
    
    // イベントバス経由でのイベント監視
    this.setupEventBusListeners();
  }

  /**
   * examine1_2固有のイベントハンドラーを設定
   */
  setupExamineSpecificHandlers() {
    // ページ読み込み完了時の処理
    document.addEventListener('DOMContentLoaded', () => {
      this.initialize();
    });
    
    // イベント委譲によるクリックハンドリング（examine1_2固有）
    document.addEventListener('click', (e) => {
      if (!e.target || !e.target.id) return;
      
      switch (e.target.id) {
        case 'finish_all_scenarios':
          this.handleExportResults();
          break;
        case 'next_scenario':
          this.handleNextScenario();
          break;
        case 'continue_scenario':
          this.handleContinueScenario();
          break;
        case 'next_sample':
          this.toNextSample();
          break;
        case 'start_scenario_button':
          this.toNextNewSamplePage();
          break;
      }
    });
    
    // チェックボックスの監視（examine1_2固有の処理）
    document.addEventListener('change', (e) => {
      if (e.target && e.target.classList.contains('checkbox')) {
        this.eventHandler.checkDescription();
      } else if (e.target && e.target.id === 'checkbox') {
        this.checkEstimate();
      }
    });
    
    // スライダーの監視（examine1_2固有）
    document.addEventListener('input', (e) => {
      if (e.target && e.target.id === 'estimate_slider') {
        document.getElementById('estimate').innerHTML = e.target.value;
      }
    });
  }

  /**
   * イベントバス経由でのイベント監視を設定
   */
  setupEventBusListeners() {
    // データマネージャーからのイベントを監視
    eventBus.on('sample:prepared', (data) => {
      console.log('サンプルデータが準備されました:', data);
    });
    
    eventBus.on('response:recorded', (data) => {
      console.log('回答が記録されました:', data);
    });
    
    eventBus.on('results:exported', (data) => {
      console.log('結果が送信されました:', data);
    });
    
    eventBus.on('results:exportError', (data) => {
      console.error('結果送信エラー:', data.error);
      document.getElementById('finish_all_scenarios').removeAttribute("disabled");
    });
  }

  /**
   * 実験の初期化（モジュラー版）
   */
  async initialize() {
    try {
      // データマネージャーを初期化
      await this.dataManager.init();
      
      // UIマネージャーを初期化
      this.uiManager.init();
      
      // examine1_2固有の初期化処理
      await this.initializeExamine12Specific();
      
      // 最初のシナリオ説明を表示
      this.toNextScenarioDescription(true);
      
    } catch (error) {
      console.error('実験の初期化に失敗しました', error);
      alert('実験の準備中にエラーが発生しました。ページを再読み込みしてください。');
    }
  }

  /**
   * examine1_2固有の初期化処理
   */
  async initializeExamine12Specific() {
    // 実験条件を取得
    await this.dataManager.fetchSampleType();
    
    // examine1_2用の追加のプリロード処理などがあれば実行
    await this.preloadExamine12Images();
    
    // ページ離脱防止
    setupPageLeaveWarning(true);
  }

  /**
   * examine1_2固有の画像プリロード
   */
  async preloadExamine12Images() {
    // 基本的なプリロードはUIManagerで実行済み
    // examine1_2固有の追加画像があれば個別処理
    console.log('examine1_2固有の画像プリロードが完了しました');
  }

  /**
   * シナリオ説明ページの表示（examine1_2固有）
   */
  toNextScenarioDescription(isFirstTime = false) {
    // UIManagerの基本機能を使用
    this.uiManager.displayScenarioDescription(isFirstTime);
    
    // examine1_2固有の処理
    this.updateExamine12SpecificUI();
  }

  /**
   * examine1_2固有のUI更新
   */
  updateExamine12SpecificUI() {
    const currentIndex = this.dataManager.currentScenarioIndex;
    const scenarioKey = this.dataManager.getCurrentScenarioKey();
    
    // examine1_2固有のページ情報表示
    document.getElementById('page').innerHTML = `<h4>${currentIndex + 1}/${config.scenarios.length}種類目</h4>`;
    
    // examine1_2固有のタイトル表示
    const scenarioData = this.dataManager.getCurrentScenarioData();
    document.getElementById('scenario_title').innerHTML = `<h2>${scenarioData.title}</h2>`;
  }

  /**
   * 新しいサンプルページの表示（examine1_2固有）
   */
  toNextNewSamplePage() {
    // 基本的なクリア処理
    this.uiManager.clearPage();
    
    // チェックボックスをリセット
    const list = document.getElementsByClassName("checkbox");
    for (let index = 0; index < list.length; ++index) {
      list[index].checked = false;
    }
    
    this.currentTestPage = 0;
    document.getElementById('show_sample_area').style.display = "inline";
    document.getElementById('order').innerHTML = "実験の進捗状況";
    this.changeBackGround();

    // examine1_2固有のサンプル作成ロジック
    this.prepareExamine12Samples();
    this.toNextSample();
  }
  /**
   * examine1_2固有のサンプル準備
   */
  prepareExamine12Samples() {
    this.currentSampleSelection = [];
    this.sampleSize = 0;
    
    const currentIndex = this.dataManager.currentScenarioIndex;
    const scenarioKey = this.dataManager.getCurrentScenarioKey();
    
    // examine1_2では専用のstimuli配列を使用
    const stimuli = this.shuffleArray(['1','2','3','4','5','6']);
    const currentStimulus = stimuli[currentIndex];
    
    const experimentData = this.dataManager.experimentData;
    const samples = experimentData[scenarioKey]['samples'][currentStimulus];
    
    Object.keys(samples).forEach(elm => {
      if (samples[elm] > 0) {
        this.sampleSize += samples[elm];
        this.cellSize = samples[elm];
        
        for (let i = 0; i < this.cellSize; i++) {
          this.currentSampleSelection.push(elm);
        }
      }
    });
    
    // 配列をシャッフル
    this.currentSampleSelection = this.shuffleArray(this.currentSampleSelection);
    
    // stimuliを保存（記録用）
    this.currentStimulus = currentStimulus;
  }

  /**
   * 配列シャッフル（ユーティリティ）
   */
  shuffleArray(array) {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  }

  /**
   * 次のサンプル表示
   */
  toNextSample() {
    const button = document.getElementById('next_sample');
    button.disabled = true;
    
    if (this.currentTestPage >= this.sampleSize) {
      alert('結果は以上になります。');
      this.drawEstimate('fin');
      return;
    }
    
    this.showStimulation();
    
    // 連打防止
    setTimeout(() => {
      button.disabled = false;
    }, 500);
  }

  /**
   * 刺激表示（examine1_2固有）
   */
  showStimulation() {
    const sample = this.currentSampleSelection[this.currentTestPage];
    const scenarioKey = this.dataManager.getCurrentScenarioKey();
    const experimentData = this.dataManager.experimentData;
    
    // 条件に応じて適切な文章を選択
    let sentences;
    if (this.dataManager.sampleType === 'symmetric' && experimentData[scenarioKey]['sentences_symmetric']) {
      sentences = experimentData[scenarioKey]['sentences_symmetric'];
      console.log('対称条件の文章を使用');
    } else {
      sentences = experimentData[scenarioKey]['sentences'];
      console.log('非対称条件の文章を使用');
    }
    
    const desc = sentences[sample];
    const sentenceParts = desc.split('、');
    document.getElementById('first_sentence').innerHTML = `<h4>${sentenceParts[0]}</h4>`;
    document.getElementById('last_sentence').innerHTML = `<h4>${sentenceParts[1]}</h4>`;
    
    // UI要素の表示制御
    document.getElementById('show_sample_area').style.display = "inline";
    document.getElementById('first_sentence').style.display = 'inline-block';
    document.getElementById('last_sentence').style.display = 'inline-block';
    document.getElementById('sample_before').style.display = 'inline';
    document.getElementById('estimate_input_area').style.display = 'none';
    document.getElementById('next_sample').style.display = 'inline';
    
    // 画像表示の処理
    this.displaySampleImages(sample, scenarioKey);
    
    this.updateProgressBar();
    this.currentTestPage++;
    document.getElementById('current_page').innerHTML = `${this.currentTestPage}/${this.sampleSize}`;
  }

  /**
   * サンプル画像の表示
   */
  displaySampleImages(sample, scenarioKey) {
    const combination = this.imgCombination[sample];
    const experimentData = this.dataManager.experimentData;
    
    // 条件に応じて適切な画像セットを選択
    let imageSet;
    if (this.dataManager.sampleType === 'symmetric' && experimentData[scenarioKey]['images_symmetric1_2']) {
      imageSet = experimentData[scenarioKey]['images_symmetric1_2'];
      console.log('対称条件の画像を使用');
    } else {
      imageSet = experimentData[scenarioKey]['images1_2'];
      console.log('非対称条件の画像を使用');
    }
    
    document.getElementById('sample_before').src = `../${imageSet[combination['cause']]}`;
    document.getElementById('arrow').src = `../${imageSet['arrow']}`;
    document.getElementById('sample_after').src = `../${imageSet[combination['effect']]}`;
  }

  /**
   * プログレスバーの更新
   */
  updateProgressBar() {
    document.getElementById('progress_bar').value = this.currentTestPage;
    document.getElementById('progress_bar').max = this.sampleSize - 1;
  }

  /**
   * 推定画面の描画
   */
  drawEstimate(condition) {
    this.uiManager.clearPage();
    
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
      
      if (this.dataManager.isExperimentComplete()) {
        document.getElementById('finish_all_scenarios').style.display = 'inline';
      } else {
        document.getElementById('next_scenario').style.display = 'inline';
      }
    }

    // 推定内容の表示
    this.displayEstimateDescription();
  }

  /**
   * 推定説明の表示
   */
  displayEstimateDescription() {
    const currentScenario = this.dataManager.getCurrentScenarioData();
    
    // 実験条件に応じて結果テキストを選択
    let resultText;
    if (this.dataManager.sampleType === 'symmetric' && currentScenario['result_symmetric']) {
      resultText = currentScenario['result_symmetric'];
      console.log('対称条件の評価文を使用:', resultText);
    } else {
      resultText = currentScenario['result'];
      console.log('非対称条件の評価文を使用:', resultText);
    }
    
    document.getElementById('estimate_description').innerHTML = 
      `<h3>${resultText}と思いますか？</h3>` + 
      `<ul>0：${currentScenario['min_result']}</ul>` + 
      `<ul>100：${currentScenario['max_result']}</ul>` +
      '<ul>として、0から100の値で<b>直感的に</b>回答してください。</ul>' +
      '<p>※スライダーの挙動に不具合が生じた場合、スライダーを直接クリックして値を選択してください。</p>';
  }

  /**
   * 次のシナリオ処理
   */
  handleNextScenario() {
    this.recordEstimation();
    this.toNextScenarioDescription();
  }

  /**
   * シナリオ継続処理
   */
  handleContinueScenario() {
    this.recordEstimation();
    this.toNextNewSamplePage();
  }

  /**
   * 結果エクスポート処理
   */
  async handleExportResults() {
    document.getElementById('finish_all_scenarios').disabled = true;
    this.recordEstimation();
    
    try {
      setupPageLeaveWarning(false);
      
      // 現在のページがexamine1_2であることを指定して次のページを決定
      const nextUrl = await getNextPageUrl('examine1_2', this.dataManager.userId);
      await this.dataManager.exportResults(nextUrl);
    } catch (error) {
      console.error('結果の送信に失敗しました:', error);
      // エラーはeventBusで処理される
    }
  }

  /**
   * 推定結果の記録
   */
  recordEstimation() {
    const estimation = document.getElementById('estimate_slider').value;
    const scenarioKey = this.dataManager.getCurrentScenarioKey();
    const currentIndex = this.dataManager.currentScenarioIndex;
    
    this.dataManager.estimations.push({
      'user_id': this.dataManager.userId,
      'number': scenarioKey,
      'stimuli': config.scenarios[currentIndex],
      'estimation': estimation
    });
    
    console.log('推定結果を記録しました:', {
      scenario: scenarioKey,
      estimation: estimation
    });
  }

  /**
   * 推定チェック
   */
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

  /**
   * 背景色の変更
   */
  changeBackGround() {
    const currentIndex = this.dataManager.currentScenarioIndex;
    document.body.style.backgroundColor = config.getBgColorForIndex(currentIndex);
  }

  /**
   * 背景色のリセット
   */
  resetBackGround() {
    document.body.style.backgroundColor = 'Transparent';
  }
}

// 実験マネージャーのインスタンスを作成（モジュラー版）
const experimentManager = new Experiment12ModularManager();

// ページロード時に初期化
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => experimentManager.initialize());
} else {
  experimentManager.initialize();
}

// HTMLから呼び出し可能なグローバル関数を定義
window.to_next_new_sample_page = function() {
  experimentManager.toNextNewSamplePage();
};

window.check_description = function() {
  experimentManager.eventHandler.checkDescription();
};
