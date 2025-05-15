/**
 * examine3.js - 実験3（CRT）のメインスクリプト
 * モジュール化された構造を使用して重複コードを削除
 */
import dataManager from './data-manager.js';
import uiManager from './ui-manager.js';
import eventHandler from './event-handler.js';
import { preventBrowserBack, setupPageLeaveWarning, getUserIdFromUrl, validateInput } from './utilities.js';

/**
 * CRT実験アプリケーションを管理するクラス
 */
class CRTExperiment {
  /**
   * コンストラクタ - CRT実験インスタンスを初期化
   */
  constructor() {
    // 設定
    this.initialized = false;
  }

  /**
   * アプリケーションを初期化
   */
  init() {
    if (this.initialized) return;
    
    try {
      // ユーザーIDを取得（一度だけ）
      dataManager.userId = getUserIdFromUrl();
      if (!dataManager.userId) {
        console.warn('Warning: user_id not found in CRT test');
      }
      
      // イベントリスナーを設定
      this.setupEventListeners();
      
      // ブラウザバックを禁止
      preventBrowserBack();
      
      this.initialized = true;
    } catch (error) {
      console.error('初期化エラー:', error);
    }
  }
  
  /**
   * イベントリスナーを設定
   */
  setupEventListeners() {
    // フォーム送信処理
    const crtForm = document.getElementById('crt_form');
    if (crtForm) {
      crtForm.addEventListener('submit', (e) => {
        e.preventDefault();
        if (this.validateAllInputs()) {
          eventHandler.handleCRTSubmit();
        }
      });
    }
    
    // 入力値の検証をリアルタイムで行う
    const numberInputs = document.querySelectorAll('input[type="number"]');
    numberInputs.forEach(input => {
      input.addEventListener('input', () => {
        if (input.value) {
          const errorElement = input.nextElementSibling;
          if (errorElement && errorElement.classList.contains('error-text')) {
            errorElement.textContent = '';
          }
        }
      });
    });
  }
  
  /**
   * 次の問題を表示
   * @param {string} currentQ - 現在の問題ID
   */
  showNext(currentQ) {
    eventHandler.showNextCRTQuestion(currentQ);
  }
  
  /**
   * 全ての入力値を検証
   * @returns {boolean} 検証結果
   */
  validateAllInputs() {
    let isValid = true;
    const inputs = document.querySelectorAll('input[type="number"]');
    
    inputs.forEach(input => {
      if (!validateInput(input, 'この項目は必須です')) {
        isValid = false;
      }
    });
    
    return isValid;
  }
}

// CRT実験アプリケーションのインスタンスを作成
const crtExperiment = new CRTExperiment();

// DOMが読み込まれた時に初期化
document.addEventListener('DOMContentLoaded', () => {
  crtExperiment.init();
});

// グローバルスコープに公開する関数（HTMLから呼び出し可能）
window.showNext = function(currentQ) {
  crtExperiment.showNext(currentQ);
};

window.validateAllInputs = function() {
  return crtExperiment.validateAllInputs();
};

window.submitAnswers = function() {
  if (crtExperiment.validateAllInputs()) {
    eventHandler.handleCRTSubmit();
  }
};

window.preventBrowserBack = function() {
  preventBrowserBack();
};

