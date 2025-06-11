/**
 * examine1.js - 実験1のメインスクリプト
 * モジュール化された構造を使用して重複コードを削除
 */
import config from './config.js';
import dataManager from './data-manager.js';
import uiManager from './ui-manager.js';
import eventHandler from './event-handler.js';
import { preventBrowserBack, setupPageLeaveWarning, getNextPageUrl } from './utilities.js';

/**
 * 実験1の管理クラス
 */
class ExperimentApp {
  constructor() {
    // 実験タイプを設定
    dataManager.setExperimentType('examine1');
    
    // 初期化
    this.initialize();
  }

  /**
   * 実験を初期化
   */
  async initialize() {
    try {
      // DataManagerを初期化
      await dataManager.init();
      
      // UIManagerを初期化
      uiManager.init();
      
      // EventHandlerを初期化
      eventHandler.init();
      
      // ページ離脱警告を設定
      setupPageLeaveWarning(true);
      
      // 最初のシナリオ説明を表示
      uiManager.displayScenarioDescription(true);
      
      console.log('examine1: 初期化完了');
      console.log('使用シナリオ:', config.scenarios);
      
    } catch (error) {
      console.error('examine1の初期化に失敗しました', error);
      uiManager.showErrorMessage('実験の準備中にエラーが発生しました。ページを再読み込みしてください。');
    }
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
}

// 実験アプリケーションのインスタンスを作成
const experimentApp = new ExperimentApp();

// グローバル関数をウィンドウに公開
window.experimentApp = experimentApp;

// グローバルスコープに公開する関数（HTMLから呼び出し可能）

// ページ読み込み時の初期化
window.onload = function() {
  experimentApp.initialize();
};

// チェックボックスの確認
window.check_description = function() {
  eventHandler.checkDescription();
};

// シナリオスタートボタン
window.to_next_new_sample_page = function() {
  experimentApp.startScenario();
};

// 次のシナリオ説明へ
window.to_next_scenario_description = function(is_first_time = false) {
  uiManager.displayScenarioDescription(is_first_time);
};

// 回答送信
window.submitResponseAndContinue = function() {
  experimentApp.submitResponse();
};

// examine1_2と互換性のあるデータ記録関数を追加
window.get_value = async function() {
  const sliderElement = document.getElementById('estimate_slider');
  if (sliderElement) {
    await dataManager.recordResponse(sliderElement.value);
    console.log('examine1: 回答値を記録しました:', sliderElement.value);
  } else {
    console.error('examine1: estimate_slider要素が見つかりません');
  }
};

window.get_value_fin = async function() {
  // 最終回答の記録と送信
  await window.get_value();
  
  try {
    // 実験順序に基づいて次のページURLを決定
    const nextUrl = await getNextPageUrl('examine1', dataManager.userId);
    console.log('examine1: 次のページURL:', nextUrl);
    
    await dataManager.exportResults(nextUrl);
  } catch (error) {
    console.error('結果送信に失敗しました:', error);
    alert("回答送信中にエラーが発生しました。もう一度送信ボタンを押してください。");
  }
};

window.check_estimate = function() {
  // examine1_2との互換性のためのスタブ関数
  console.log('check_estimate called in examine1');
};

window.showStimulation = function() {
  // サンプル表示の継続
  uiManager.displaySamplePage();
};

// ブラウザバックの禁止
window.preventBrowserBack = function() {
  preventBrowserBack();
};