/**
 * examine1_2.js - 因果関係の強さを推定する実験
 * モジュラー構造に対応し、examine1との互換性を確保
 */

// 共有モジュールのインポート
import config from './config.js';
import dataManager from './data-manager.js';
import uiManager from './ui-manager.js';
import eventHandler from './event-handler.js';
import { preventBrowserBack, setupPageLeaveWarning, shuffleArray, zeroPadding, getNow } from './utilities.js';

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
      // ユーザーIDの生成
      this.userId = Math.round(Math.random() * 100000000);
      this.userId = zeroPadding(this.userId, 8);
      
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
  }  /**
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
  }
  /**
   * 画像のプリロード
   */
  getImages() {
    // testOrderがオブジェクトであることを確認
    if (!this.testOrder || typeof this.testOrder !== 'object') {
      console.warn('testOrderが初期化されていません。画像プリロードをスキップします。');
      return;
    }
    
    try {
      for (let scenario in this.scenarios) {
        const scenarioKey = this.scenarios[scenario];
        
        // シナリオが存在するかチェック
        if (!this.testOrder[scenarioKey] || !this.testOrder[scenarioKey]['images1_2']) {
          console.warn(`シナリオ ${scenarioKey} の画像データが見つかりません`);
          continue;
        }
        
        for (let type in this.imageType) {
          const imageType = this.imageType[type];
          const imagePath = this.testOrder[scenarioKey]['images1_2'][imageType];
          
          if (imagePath) {
            var img = document.createElement('img');
            img.src = `../${imagePath}`;
            img.onerror = () => console.warn(`画像の読み込みに失敗: ${imagePath}`);
          }
        }
      }
      
      // プリロード表示を非表示
      const preloadElement = document.getElementById('preload_image');
      if (preloadElement) {
        preloadElement.style.display = "none";
      }
      
      console.log('examine1_2: 画像プリロード完了');
    } catch (error) {
      console.error('画像プリロード中にエラーが発生しました:', error);
    }
  }

  /**
   * ページをクリアする
   */
  clearPage() {
    document.getElementById('estimate_input_area').style.display = "none";
    document.getElementById('check_sentence').style.display = "none";
    document.getElementById('description_area').style.display = "none";
    document.getElementById('show_sample_area').style.display = 'none';
  }
  /**
   * 次のシナリオの説明を表示
   */
  toNextScenarioDescription(isFirstTime = false) {
    if (!this.testOrder || typeof this.testOrder !== 'object') {
      console.error('testOrderが初期化されていません');
      return;
    }
    
    this.clearPage();
    if (!isFirstTime) {
      this.sceIdx++;
    }
    this.resetBackGround();
    
    const scenarioKey = this.scenarios[this.sceIdx];
    if (!this.testOrder[scenarioKey]) {
      console.error(`シナリオ ${scenarioKey} が見つかりません`);
      return;
    }
    
    document.getElementById('page').innerHTML = "<h4>" + (this.sceIdx + 1) + '/' + this.scenarios.length + "種類目</h4>";
    document.getElementById('scenario_title').innerHTML = "<h2>" + this.testOrder[scenarioKey]['title'] + "</h2>";
    document.getElementById('check_sentence').style.display = "inline-block";
    document.getElementById('description_area').style.display = "inline-block";
    document.getElementById('start_scenario_button').setAttribute("disabled", true);
    
    const descriptions = this.testOrder[scenarioKey]['descriptions'];
    if (descriptions && descriptions.length > 0) {
      for (let i = 0; i < descriptions.length; i++) {
        const element = document.getElementById('scenario_description' + String(i + 1));
        if (element) {
          element.innerHTML = descriptions[i];
        }
      }
    }
  }

  /**
   * チェックボックスの確認
   */
  checkDescription() {
    let checkbox = document.getElementsByClassName("checkbox");
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
  /**
   * 次のサンプル表示ページへ遷移
   */
  toNextNewSamplePage() {
    if (!this.testOrder || typeof this.testOrder !== 'object') {
      console.error('testOrderが初期化されていません');
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
    if (!this.testOrder[scenarioKey] || 
        !this.testOrder[scenarioKey]['samples'] || 
        !this.testOrder[scenarioKey]['samples'][stimulusKey]) {
      console.error(`サンプルデータが見つかりません: ${scenarioKey}/${stimulusKey}`);
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
    
    // データ構造の存在確認
    if (!this.testOrder[scenarioKey] || 
        !this.testOrder[scenarioKey]['sentences'] || 
        !this.testOrder[scenarioKey]['sentences'][sample]) {
      console.error(`センテンスデータが見つかりません: ${scenarioKey}/${sample}`);
      return;
    }
    
    const desc = this.testOrder[scenarioKey]['sentences'][sample];
    console.log("showStimulation_in");
    const descParts = desc.split('、');
    
    document.getElementById('first_sentence').innerHTML = "<h4>" + descParts[0] + "</h4>";
    document.getElementById('last_sentence').innerHTML = "<h4>" + descParts[1] + "</h4>";
    document.getElementById('show_sample_area').style.display = "inline";
    document.getElementById('first_sentence').style.display = 'inline-block';
    document.getElementById('last_sentence').style.display = 'inline-block';
    document.getElementById('sample_before').style.display = 'inline';
    document.getElementById('estimate_input_area').style.display = 'none';
    document.getElementById('next_sample').style.display = 'inline';
    
    // 画像パスの設定（images1_2を使用）
    const images = this.testOrder[scenarioKey]['images1_2'];
    if (images && this.imgCombination[sample]) {
      const causePath = images[this.imgCombination[sample]['cause']];
      const effectPath = images[this.imgCombination[sample]['effect']];
      const arrowPath = images['arrow'];
      
      if (causePath) {
        document.getElementById('sample_before').src = `../${causePath}`;
      }
      if (arrowPath) {
        document.getElementById('arrow').src = `../${arrowPath}`;
      }
      if (effectPath) {
        document.getElementById('sample_after').src = `../${effectPath}`;
      }
    }
    
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
  }
  /**
   * 推定画面を描画
   */
  drawEstimate(c) {
    const scenarioKey = this.scenarios[this.sceIdx];
    if (!this.testOrder[scenarioKey]) {
      console.error(`シナリオデータが見つかりません: ${scenarioKey}`);
      return;
    }
    
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
    
    if (c == 'fin') {
      document.getElementById('continue_scenario').style.display = 'none';
      if (this.sceIdx == this.scenarios.length - 1) {
        document.getElementById('finish_all_scenarios').style.display = 'inline';
      } else {
        document.getElementById('next_scenario').style.display = 'inline';
      }
    }

    const scenarioData = this.testOrder[scenarioKey];
    document.getElementById('estimate_description').innerHTML =
      '<h3>' + (scenarioData['result'] || '結果を評価してください') + 'と思いますか？</h3>' +
      '<ul>0：' + (scenarioData['min_result'] || '全く引き起こさない') + '</ul>' +
      '<ul>100：' + (scenarioData['max_result'] || '確実に引き起こす') + '</ul>' +
      '<ul>として、0から100の値で<b>直感的に</b>回答してください。</ul>' +
      '<p>※スライダーの挙動に不具合が生じた場合、スライダーを直接クリックして値を選択してください。</p>';
  }

  /**
   * 推定値を取得
   */
  getValue() {
    this.appendEstimation(
      document.getElementById('estimate_slider').value
    );
  }

  /**
   * 最終的な値を取得
   */
  getValueFin() {
    // 回答送信ボタンの連打防止
    document.getElementById('finish_all_scenarios').disabled = true;
    this.getValue();
    this.exportResults();
  }

  /**
   * 推定画面のチェック確認
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
   * 推定データを追加
   */
  appendEstimation(estimation) {
    let data = {};
    data['user_id'] = this.userId;
    data['number'] = this.scenarios[this.sceIdx];
    data['stimuli'] = this.stimuli[this.sceIdx];
    data['estimation'] = estimation;
    this.estimations.push(data);
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
      this.userData.push(data);

      // DataManagerのsendExamine12Resultsメソッドを使用
      await dataManager.sendExamine12Results(this.estimations, `../examine2?id=${this.userId}`);
      
    } catch (error) {
      console.error('結果送信に失敗しました:', error);
      alert("回答送信中にエラーが発生しました。もう一度終了ボタンを押してください。");
      document.getElementById('finish_all_scenarios').removeAttribute("disabled");
    }
  }

  /**
   * 背景色を変更
   */
  changeBackGround() {
    document.body.style.backgroundColor = this.bgcolors[this.sceIdx];
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
window.get_value = () => experimentManager.getValue();
window.get_value_fin = () => experimentManager.getValueFin();
window.check_estimate = () => experimentManager.checkEstimate();
window.to_next_scenario_description = (isFirstTime) => experimentManager.toNextScenarioDescription(isFirstTime);