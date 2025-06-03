/**
 * examine1.js - 実験1のメインスクリプト
 * モジュール化された構造を使用して重複コードを削除
 */
import config from './config.js';
import dataManager from './data-manager.js';
import uiManager from './ui-manager.js';
import eventHandler from './event-handler.js';
import { preventBrowserBack, setupPageLeaveWarning } from './utilities.js';

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

// ブラウザバックの禁止
window.preventBrowserBack = function() {
  preventBrowserBack();
};