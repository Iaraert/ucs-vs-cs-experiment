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
 * アプリケーションの初期化と実行を管理するクラス
 */
class ExperimentApp {
  /**
   * アプリケーションを初期化
   */
  async init() {
    try {
      // 各モジュールを初期化
      config.init();
      dataManager.init();
      uiManager.init();
      eventHandler.init();
      
      // ユーザーIDを取得または生成
      dataManager.loadOrGenerateUserId();
      
      // 実験条件を取得
      await dataManager.fetchSampleType();
      
      // 最初のシナリオを表示
      uiManager.displayScenarioDescription(true);
      
      console.log('実験アプリケーションを初期化しました');
    } catch (error) {
      console.error('初期化エラー:', error);
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

// アプリケーションインスタンスを作成
const app = new ExperimentApp();

// グローバルスコープに公開する関数（HTMLから呼び出し可能）

// ページ読み込み時の初期化
window.onload = function() {
  app.init();
};

// チェックボックスの確認
window.check_description = function() {
  eventHandler.checkDescription();
};

// シナリオスタートボタン
window.to_next_new_sample_page = function() {
  app.startScenario();
};

// 次のシナリオ説明へ
window.to_next_scenario_description = function(is_first_time = false) {
  uiManager.displayScenarioDescription(is_first_time);
};

// 回答送信
window.submitResponseAndContinue = function() {
  app.submitResponse();
};

// ブラウザバックの禁止
window.preventBrowserBack = function() {
  preventBrowserBack();
};