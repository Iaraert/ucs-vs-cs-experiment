/**
 * examine1_2.js - 因果関係の強さを推定する実験
 * examine1のシンプルで堅牢な設計パターンを採用
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
    
    // 初期化
    this.initialize();
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

  /**
   * examine1_2固有の初期化処理
   */
  async initializeExamine12Specific() {
    try {
      // サンプルタイプを取得
      await this.fetchSampleType();
      
      // 画像プリロード
      await this.preloadImages();
      
      console.log('examine1_2固有の初期化完了');
      
    } catch (error) {
      console.error('examine1_2固有の初期化に失敗:', error);
      throw error;
    }
  }

  /**
   * サンプルタイプを取得
   */
  async fetchSampleType() {
    try {
      const response = await fetch('/get_sample_type', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          'user_id': dataManager.userId
        })
      });
      
      if (!response.ok) {
        throw new Error(`サンプルタイプの取得に失敗: ${response.status}`);
      }
      
      const data = await response.json();
      this.sampleType = data.sample_type || 'asymmetric';
      console.log('examine1_2: サンプルタイプ取得完了:', this.sampleType);
      
    } catch (error) {
      console.error('サンプルタイプの取得に失敗:', error);
      this.sampleType = 'asymmetric'; // デフォルト値
    }
  }

  /**
   * 画像をプリロード
   */
  async preloadImages() {
    return new Promise((resolve) => {
      // シンプルな画像プリロード実装
      const imageUrls = this.getImageUrls();
      let loadedCount = 0;
      const totalCount = imageUrls.length;
      
      if (totalCount === 0) {
        resolve();
        return;
      }
      
      imageUrls.forEach(url => {
        const img = new Image();
        img.onload = img.onerror = () => {
          loadedCount++;
          if (loadedCount === totalCount) {
            console.log('examine1_2: 画像プリロード完了');
            resolve();
          }
        };
        img.src = url;
      });
    });
  }

  /**
   * プリロードする画像URLを取得
   */
  getImageUrls() {
    const urls = [];
    
    // 基本画像
    this.imageType.forEach(type => {
      urls.push(`/static/images/${type}.png`);
    });
    
    // シナリオ固有画像
    if (config.scenarios) {
      config.scenarios.forEach(scenario => {
        this.imageType.forEach(type => {
          urls.push(`/static/images/${scenario}/${type}.png`);
        });
      });
    }
    
    return urls;
  }

  /**
   * シナリオ説明から実験画面へ
   */
  startScenario() {
    uiManager.displaySamplePage();
  }

  /**
   * 回答を送信して次へ
   */
  submitResponse() {
    eventHandler.submitResponseAndContinue();
  }

  /**
   * 推定値をチェック
   */
  checkEstimate() {
    const slider = document.getElementById('sampleSlider');
    const checkbox = document.getElementById('checkbox');
    
    if (!slider || !checkbox) {
      uiManager.showErrorMessage('推定入力の要素が見つかりません。');
      return;
    }
    
    if (!checkbox.checked) {
      uiManager.showErrorMessage('チェックボックスにチェックを入れてください。');
      return;
    }
    
    // 推定値を記録
    const estimate = parseInt(slider.value);
    dataManager.recordEstimate(estimate);
    
    // 次の画面へ進む
    this.proceedToNext();
  }

  /**
   * 次の画面に進む
   */
  proceedToNext() {
    if (this.hasMoreEstimations()) {
      this.moveToNextEstimation();
    } else {
      this.finishExperiment();
    }
  }

  /**
   * まだ推定が残っているかチェック
   */
  hasMoreEstimations() {
    return this.estimationIndex < config.totalEstimations - 1;
  }

  /**
   * 次の推定に移動
   */
  moveToNextEstimation() {
    this.estimationIndex++;
    uiManager.displayNextEstimation();
  }

  /**
   * 実験を終了
   */
  async finishExperiment() {
    try {
      // データを保存
      await dataManager.saveData();
      
      // ページ離脱警告を無効化
      setupPageLeaveWarning(false);
      
      // 次のページに移動
      const nextUrl = `/examine2?id=${encodeURIComponent(dataManager.userId)}`;
      window.location.href = nextUrl;
      
    } catch (error) {
      console.error('実験終了処理でエラー:', error);
      uiManager.showErrorMessage('データの保存に失敗しました。再度お試しください。');
    }
  }

  /**
   * 背景色を変更
   */
  changeBackGround() {
    if (this.currentTestPage < this.bgcolors.length) {
      document.body.style.backgroundColor = this.bgcolors[this.currentTestPage];
    }
  }

  /**
   * 背景色をリセット
   */
  resetBackGround() {
    document.body.style.backgroundColor = '#ffffff';
  }

  /**
   * 新しいサンプルページに移動
   */
  toNextNewSamplePage() {
    this.currentTestPage++;
    this.changeBackGround();
    uiManager.displaySamplePage();
  }
}

// 実験アプリケーションのインスタンスを作成
const experiment12Manager = new Experiment12Manager();

// グローバル関数をウィンドウに公開
window.experiment12Manager = experiment12Manager;

// グローバルスコープに公開する関数（HTMLから呼び出し可能）

// ページ読み込み時の初期化
window.onload = function() {
  experiment12Manager.initialize();
};

// チェックボックスの確認
window.check_description = function() {
  eventHandler.checkDescription();
};

// シナリオスタートボタン
window.to_next_new_sample_page = function() {
  experiment12Manager.startScenario();
};

// 次のシナリオ説明へ
window.to_next_scenario_description = function(is_first_time = false) {
  uiManager.displayScenarioDescription(is_first_time);
};

// 回答送信
window.submitResponseAndContinue = function() {
  experiment12Manager.submitResponse();
};

// 推定値チェック
window.checkEstimate = function() {
  experiment12Manager.checkEstimate();
};

// スライダー操作時の処理
window.enableEstimateCheckbox = function() {
  const checkbox = document.getElementById('checkbox');
  if (checkbox) {
    checkbox.disabled = false;
  }
};

// 新しいサンプルページへ移動
window.toNextNewSamplePage = function() {
  experiment12Manager.toNextNewSamplePage();
};

// ブラウザバックの禁止
preventBrowserBack();

export default experiment12Manager;
