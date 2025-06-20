/**
 * examine2.js - 実験2（IMC）のメインスクリプト
 * モジュール化された構造を使用して重複コードを削除
 */
import dataManager from './data-manager.js';
import eventHandler from './event-handler.js';
import { preventBrowserBack, setupPageLeaveWarning, getUserIdFromUrl } from './utilities.js';

/**
 * IMC実験アプリケーションを管理するクラス
 */
class IMCExperiment {
  /**
   * コンストラクタ - IMC実験インスタンスを初期化
   */
  constructor() {
    this.result = false;
    this.allowPageLeave = false;
  }

  /**
   * アプリケーションを初期化
   */
  init() {
    try {
      // ユーザーID取得
      dataManager.userId = getUserIdFromUrl();
      if (!dataManager.userId) {
        console.warn('Warning: user_id not found');
        alert("ユーザーIDが取得できません。対応しますのでクラウドワークスから不具合を報告してください。");
        return;
      }
      // console.log('User ID:', dataManager.userId); // デバッグ用
      
      // ページ離脱警告を設定
      setupPageLeaveWarning(true);
      
      // ブラウザバックを禁止
      preventBrowserBack();
    } catch (error) {
      console.error('初期化エラー:', error);
    }
  }
  
  /**
   * 選択肢の確認と結果送信を行う
   */
  submitAndContinue() {
    this.validateSelections();
    this.exportResults();
  }
  
  /**
   * 選択肢を検証する
   */
  validateSelections() {
    const selectedOptions = [];
    document.querySelectorAll('input[name="sports"]:checked').forEach(function(checkbox) {
      selectedOptions.push(checkbox.value);
    });

    // 選択結果が「野球」「水泳」「その他」のみか判定
    const validSelection = ["野球", "水泳", "その他"];
    this.result = selectedOptions.length === validSelection.length &&
                 selectedOptions.every(option => validSelection.includes(option));
  }
  
  /**
   * 結果を送信する
   */
  exportResults() {
    eventHandler.handleIMCSubmit();
  }
}

// IMC実験アプリケーションのインスタンスを作成
const imcExperiment = new IMCExperiment();

// ページ読み込み時の初期化
window.onload = function() {
  imcExperiment.init();
};

// グローバルスコープに公開する関数（HTMLから呼び出し可能）
window.get_value_fin = function() {
  imcExperiment.submitAndContinue();
};

window.get_value = function() {
  imcExperiment.validateSelections();
};

window.export_results = function() {
  imcExperiment.exportResults();
};

window.preventBrowserBack = function() {
  preventBrowserBack();
};