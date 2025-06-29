/**
 * examine1.js - 実験1のメインスクリプト
 * モジュール化された構造を使用して重複コードを削除
 */
import config from './config.js';
import dataManager from './data-manager.js';
import uiManager from './ui-manager.js';
import eventHandler from './event-handler.js';
import { preventBrowserBack, setupPageLeaveWarning, getNextPageUrl, getExperimentOrder, shuffleArray, isAlreadyParticipated } from './utilities.js';

/**
 * 実験1の管理クラス
 */
class ExperimentApp {
  constructor() {
    // 実験タイプを新しい名称に変更
    dataManager.setExperimentType('eXaMinE1');
    
    // 背景色を2色交互に設定（アイコンの色と被らないように）
    this.bgcolors = ['#f8f9fa', '#fff8f0']; // 淡いグレーと淡いベージュ
    
    // 初期化フラグ
    this.initialized = false;
  }

  /**
   * 実験を初期化
   */
  async initialize() {
    try {
      // utilities.jsからユーザーID取得
      const { getOrCreateUserId } = await import('./utilities.js');
      this.userId = getOrCreateUserId({ urlParam: true, persistent: false });
      if (!this.userId) {
        console.error('eXaMinE1: ユーザーIDの取得に失敗しました');
        alert('ユーザー識別情報の取得に失敗しました。最初のページからやり直してください。');
        window.location.href = '/';
        return;
      }
      console.log('eXaMinE1: ユーザーID:', this.userId);
      await dataManager.init(this.userId);
      await dataManager.fetchSampleType();
      console.log('eXaMinE1: 実験条件:', dataManager.sampleType);
      uiManager.init();
      eventHandler.init();
      setupPageLeaveWarning(true);
      uiManager.displayScenarioDescription(true);
      console.log('eXaMinE1: 初期化完了');
      console.log('使用シナリオ:', config.scenarios);
      this.initialized = true;
    } catch (error) {
      console.error('eXaMinE1の初期化に失敗しました', error);
      uiManager.showErrorMessage('実験の準備中にエラーが発生しました。ページを再読み込みしてください。');
    }
  }
  
  /**
   * スライダーの質問文とラベルを設定（examine1_2と同等のロジック）
   */
  initializeSlider() {
    // シナリオデータ取得
    const scenarioKey = dataManager.getCurrentScenarioKey();
    const scenarioData = dataManager.getCurrentScenarioData();
    if (!scenarioData) {
      console.error('initializeSlider: シナリオデータが取得できません:', scenarioKey);
      alert('スライダー説明文のデータが取得できません。データ構造やJSONを確認してください。');
      return;
    }
    const resultEvent = scenarioData['result_event'] || '';
    let minLabel = '';
    let zeroLabel = '';
    let maxLabel = '';
    if (dataManager.sampleType === 'symmetric') {
      minLabel = `-100: より確実に${resultEvent}を妨げる`;
      zeroLabel = '0: 差はない';
      maxLabel = `100: より確実に${resultEvent}を引き起こす`;
    } else {
      minLabel = `-100: 確実に${resultEvent}を妨げる`;
      zeroLabel = '0: 全く影響しない';
      maxLabel = `100: 確実に${resultEvent}を引き起こす`;
    }
    // ラベルをDOMに反映
    const minResultElement = document.getElementById('slider_min_result');
    if (minResultElement) minResultElement.textContent = minLabel;
    const zeroResultElement = document.getElementById('slider_zero_result');
    if (zeroResultElement) zeroResultElement.textContent = zeroLabel;
    const maxResultElement = document.getElementById('slider_max_result');
    if (maxResultElement) maxResultElement.textContent = maxLabel;

    // スライダーの初期値を明示的に0に設定し、表示も0に
    const slider = document.getElementById('response_slider');
    if (slider) {
      slider.value = 0;
      slider.min = -100; // レンジ下限
      slider.max = 100;  // レンジ上限
      // --- スライダーinputイベントでチェックボックス有効化（要素存在チェック付き） ---
      slider.addEventListener('input', function() {
        const cb = document.getElementById('slider_confirmation_checkbox');
        if (cb) cb.disabled = false;
      });
    }
    const valueDisplay = document.getElementById('slider_value');
    if (valueDisplay) valueDisplay.textContent = '0';
  }

  /**
   * シナリオ説明から実験画面へ
   */
  startScenario() {
    // --- 進捗ログを追加 ---
    console.log(`[examine1.startScenario] currentScenarioIndex=${dataManager.currentScenarioIndex}`);
    this.initializeSlider();
    uiManager.displaySamplePage();
  }
  
  /**
   * 回答を送信して次へ
   */
  submitResponse() {
    // --- 進捗ログを追加 ---
    console.log(`[examine1.submitResponse] currentScenarioIndex=${dataManager.currentScenarioIndex}`);
    // 6つ目のシナリオで送信時のみ、orderに従った次ページへの進入許可を判定
    if (dataManager.estimations.length === 6) {
      window.onbeforeunload = null;
      setupPageLeaveWarning(false);
      getNextPageUrl('eXaMinE1', dataManager.userId)
        .then(nextUrl => {
          dataManager.exportResults(nextUrl)
            .catch(error => {
              console.error('結果の送信に失敗しました:', error);
              uiManager.showErrorMessage('回答送信中にエラーが発生しました。もう一度送信ボタンを押してください。');
              document.getElementById('submit_response').removeAttribute("disabled");
            });
        })
        .catch(error => {
          console.error('次のページURLの取得に失敗しました:', error);
          const defaultNextUrl = `../eXaM1nE_2?id=${encodeURIComponent(dataManager.userId)}`;
          dataManager.exportResults(defaultNextUrl)
            .catch(exportError => {
              console.error('結果の送信に失敗しました:', exportError);
              uiManager.showErrorMessage('回答送信中にエラーが発生しました。もう一度送信ボタンを押してください。');
              document.getElementById('submit_response').removeAttribute("disabled");
            });
        });
    } else {
      eventHandler.submitResponseAndContinue();
    }
  }
  
  /**
   * 背景色を2色交互に変更（アイコンの色と被らないように）
   */
  changeBackGround() {
    // シナリオインデックスに基づいて2色を交互に選択
    const colorIndex = dataManager.currentScenarioIndex % 2;
    const bgColor = this.bgcolors[colorIndex] || 'Transparent';
    document.body.style.backgroundColor = bgColor;
    console.log(`背景色変更: シナリオ${dataManager.currentScenarioIndex + 1} -> ${bgColor}`);
  }

  /**
   * 背景色をリセット
   */
  resetBackGround() {
    document.body.style.backgroundColor = 'Transparent';
  }
}

// 実験アプリケーションのインスタンスを作成
const experimentApp = new ExperimentApp();

// グローバル関数をウィンドウに公開
window.experimentApp = experimentApp;

// 安全なアクセスのためのヘルパー関数
function safeCall(fn, fnName) {
  try {
    if (!experimentApp.initialized) {
      console.warn(`examine1: ${fnName} called before initialization complete`);
      // 初期化が完了していない場合は警告のみで実行を継続
    }
    return fn();
  } catch (error) {
    console.error(`examine1: Error in ${fnName}:`, error);
    console.error('examine1: エラーの詳細:', error.stack);
    alert(`操作中にエラーが発生しました: ${fnName}。ページを再読み込みしてください。`);
  }
}

// グローバルスコープに公開する関数（HTMLから呼び出し可能）

// ページ読み込み時の初期化
window.onload = function() {
  experimentApp.initialize();
};

// チェックボックスの確認
window.check_description = function() {
  safeCall(() => eventHandler.checkDescription(), 'check_description');
};

// シナリオスタートボタン
window.to_next_new_sample_page = function() {
  safeCall(() => experimentApp.startScenario(), 'to_next_new_sample_page');
};

// 次のシナリオ説明へ
window.to_next_scenario_description = function(is_first_time = false) {
  safeCall(() => uiManager.displayScenarioDescription(is_first_time), 'to_next_scenario_description');
};

// 回答送信
window.submitResponseAndContinue = function() {
  safeCall(() => experimentApp.submitResponse(), 'submitResponseAndContinue');
};

// examine1_2と互換性のあるデータ記録関数を追加
window.get_value = async function() {
  try {
    const sliderElement = document.getElementById('estimate_slider');
    if (sliderElement) {
      await dataManager.recordResponse(sliderElement.value);
      console.log('examine1: 回答値を記録しました:', sliderElement.value);
    } else {
      console.error('examine1: estimate_slider要素が見つかりません');
    }
  } catch (error) {
    console.error('examine1: get_value error:', error);
  }
};

window.get_value_fin = async function() {
  try {
    await window.get_value();
    const nextUrl = await getNextPageUrl('eXaMinE1', dataManager.userId);
    await dataManager.exportResults(nextUrl);
  } catch (error) {
    console.error(error);
  }
};

// checkResponseCheckbox関数はHTMLファイル内で定義されています

window.check_estimate = function() {
  // examine1_2との互換性のためのスタブ関数
  console.log('check_estimate called in examine1');
};

window.showStimulation = function() {
  try {
    // サンプル表示の継続
    uiManager.displaySamplePage();
  } catch (error) {
    console.error('examine1: showStimulation error:', error);
  }
};

// ブラウザバックの禁止
window.preventBrowserBack = function() {
  preventBrowserBack();
};

// ページロード時に進捗/orderチェックを追加。不正な場合は警告＋リダイレクト。
window.addEventListener('DOMContentLoaded', async function() {
  try {
    let userId = null;
    try {
      userId = localStorage.getItem('exp_user_id_persistent');
    } catch (e) {}
    if (!userId) {
      const urlParams = new URLSearchParams(window.location.search);
      userId = urlParams.get('id');
    }
    if (!userId) {
      alert('ユーザーIDが取得できません。最初からやり直してください。');
      window.location.href = '/t0P1_2';
      return;
    }
    if (isAlreadyParticipated()) {
      const btn = document.getElementById('participate_btn');
      if (btn) btn.style.display = 'none';
      const msg = document.getElementById('already_participated_msg');
      if (msg) msg.style.display = 'block';
    }
  } catch (e) {
    window.location.href = '/t0P1_2';
  }
});

// コピー防止（全ページ共通）
document.addEventListener('copy', function(e) {
  e.preventDefault();
  return false;
});