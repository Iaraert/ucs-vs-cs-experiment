/**
 * examine1_2.js - 因果関係の強さを推定する実験
 */
import { getNow, zeroPadding, shuffleArray, preventBrowserBack, getOrCreateUserId, loadPageStyles, getNextPageUrl } from './utilities.js';
import { fetchJson, postData } from './ajax-utils.js';
import eventBus from './event-bus.js';

// shuffleArrayのエイリアス
const shuffle = shuffleArray;

/**
 * 実験1.2の管理クラス
 */
class Experiment12Manager {
  constructor() {
    // 実験データ
    this.experimentData = null;
    this.userData = [];
    this.estimations = [];
    
    // 実験の状態
    this.currentTestPage = 0;
    this.sampleSize = 0;
    this.scenarioIndex = 0;
    this.currentSampleSelection = [];
    this.cellSize = 0;
    this.userId = 0;
    this.startTime = null;
    this.estimationIndex = 0;
    
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
    
    this.setupEventListeners();
  }

  setupEventListeners() {
    // ページ読み込み時の処理
    window.addEventListener('load', () => this.initialize());
    
    // ブラウザのバック防止
    preventBrowserBack();
    
    // ページを離れる前の確認
    window.addEventListener('beforeunload', (e) => {
      e.returnValue = "ページを離れると、これまで入力した内容は全て破棄されます。ページを離れてもよろしいですか？";
    });
    
    // イベント委譲によるクリックハンドリング
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
    
    // チェックボックスの監視
    document.addEventListener('change', (e) => {
      if (e.target && e.target.classList.contains('checkbox')) {
        this.checkDescription();
      } else if (e.target && e.target.id === 'checkbox') {
        this.checkEstimate();
      }
    });
  }

  async initialize() {
    try {
      this.userId = getOrCreateUserId({ persistent: true });
      this.startTime = getNow();
      
      await loadPageStyles('examine1_2');
      await this.loadExperimentData();
      await this.preloadImages();
      
      this.setupLazyLoading();
      this.toNextScenarioDescription(true);
    } catch (error) {
      console.error('実験の初期化に失敗しました', error);
      alert('実験の準備中にエラーが発生しました。ページを再読み込みしてください。');
    }
  }

  async loadExperimentData() {
    try {
      this.experimentData = await fetchJson('../static/material1_2.json');
      return this.experimentData;
    } catch (error) {
      console.error('実験データの読み込みに失敗しました', error);
      alert('データの読み込みに失敗しました。ページを再読み込みしてください。');
      throw error;
    }
  }

  async preloadImages() {
    this.preloadedImages = new Map();
    
    // 必要な画像URLを収集
    const imageUrls = [];
    const basePath = '..';
    
    for (const scenario of this.scenarios) {
      // 矢印画像
      imageUrls.push(`${basePath}/${this.experimentData[scenario]['images']['arrow']}`);
      
      // cause/effect画像
      for (const type of this.imageType) {
        imageUrls.push(`${basePath}/${this.experimentData[scenario]['images'][type]}`);
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
    
    const descLen = this.experimentData[this.scenarios[this.scenarioIndex]]['descriptions'].length;
    for (let i = 0; i < descLen; i++) {
      document.getElementById('scenario_description' + String(i + 1)).innerHTML = 
        this.experimentData[this.scenarios[this.scenarioIndex]]['descriptions'][i];
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

  showStimulation() {
    const sample = this.currentSampleSelection[this.currentTestPage];
    const desc = this.experimentData[this.scenarios[this.scenarioIndex]]['sentences'][sample];
    
    const sentences = desc.split('、');
    document.getElementById('first_sentence').innerHTML = "<h4>" + sentences[0] + "</h4>";
    document.getElementById('last_sentence').innerHTML = "<h4>" + sentences[1] + "</h4>";
    
    document.getElementById('show_sample_area').style.display = "inline";
    document.getElementById('first_sentence').style.display = 'inline-block';
    document.getElementById('last_sentence').style.display = 'inline-block';
    document.getElementById('sample_before').style.display = 'inline';
    document.getElementById('estimate_input_area').style.display = 'none';
    document.getElementById('next_sample').style.display = 'inline';
    
    const currentScenario = this.scenarios[this.scenarioIndex];
    const combination = this.imgCombination[sample];
    
    document.getElementById('sample_before').src = 
      `../${this.experimentData[currentScenario]['images'][combination['cause']]}`;
    document.getElementById('arrow').src = 
      `../${this.experimentData[currentScenario]['images']['arrow']}`;
    document.getElementById('sample_after').src = 
      `../${this.experimentData[currentScenario]['images'][combination['effect']]}`;
    
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
    
    document.getElementById('estimate_description').innerHTML = 
      '<h3>' + currentScenario['result'] + 'と思いますか？</h3>' + 
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
    
    this.estimations.push({
      'user_id': this.userId,
      'number': this.scenarios[this.scenarioIndex],
      'stimuli': this.stimuli[this.scenarioIndex],
      'estimation': estimation
    });
  }

  async exportResults() {
    this.userData.push({
      'user_id': this.userId,
      'start_time': this.startTime,
      'end_time': getNow(),
      'user_agent': window.navigator.userAgent
    });

    try {
      await postData('/send', {
        'user_data': JSON.stringify(this.userData),
        'estimations': JSON.stringify(this.estimations),
        'file_name_suffix': 'exp1'
      }, {
        timeout: 50000
      });
      
      // 現在のページがexamine1_2であることを指定し、ユーザーIDに基づいて次のページを決定
      const nextUrl = await getNextPageUrl('examine1_2', this.userId);
      location.href = nextUrl;
    } catch (error) {
      console.error("回答送信中にエラーが発生しました", error);
      alert("回答送信中にエラーが発生しました。もう一度終了ボタンを押してください。");
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

// スライダーの値変更時のイベントハンドラー
document.getElementById('estimate_slider').addEventListener('input', function() {
  document.getElementById('estimate').innerHTML = this.value;
});