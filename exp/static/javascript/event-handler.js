/**
 * ユーザーイベント処理
 */
import { preventBrowserBack, setupPageLeaveWarning, getNextPageUrl, getExperimentOrder } from './utilities.js';
import { validateCheckboxes } from './common-utils.js';
import dataManager from './data-manager.js';
import uiManager from './ui-manager.js';
import config from './config.js';

/**
 * イベント処理管理
 */
export class EventHandler {
  constructor() {
    this.initialized = false;
  }

  init() {
    if (this.initialized) return this;
    
    this.setupEventHandlers();
    this.initialized = true;
    return this;
  }
  
  setupEventHandlers() {
    preventBrowserBack();
    setupPageLeaveWarning(true);
    this.setupSliderEvents();
  }
  
  setupSliderEvents() {
    const slider = document.getElementById('response_slider');
    if (slider) {
      slider.addEventListener('input', this.onSliderChange.bind(this));
    }
  }
  
  onSliderChange(event) {
    const value = event.target.value;
    document.getElementById('slider_value').textContent = value;
  }
  
  checkDescription() {
    // 共通ユーティリティ関数を使用してチェックボックス確認ロジックを統一化
    validateCheckboxes("checkbox", "start_scenario_button");
    
    // 実験形式変更通知のチェック（全チェックボックス完了時に実行）
    this.checkFormatChangeNotification();
  }
  
  /**
   * 実験形式変更通知をチェックする
   * 1つ目のシナリオで全チェックボックス完了時に通知を表示
   */
  async checkFormatChangeNotification() {
    try {
      // シナリオ説明用のチェックボックスが全て完了しているかチェック
      const checkboxes = document.getElementsByClassName("checkbox");
      let allChecked = true;
      
      // チェックボックスが存在しない場合は処理しない
      if (checkboxes.length === 0) {
        console.log('checkFormatChangeNotification: チェックボックスが存在しないため処理をスキップ');
        return;
      }
      
      for (let i = 0; i < checkboxes.length; i++) {
        if (!checkboxes[i].checked) {
          allChecked = false;
          break;
        }
      }
      
      // 全チェックボックスが完了していない場合は処理しない
      if (!allChecked) {
        console.log('checkFormatChangeNotification: 全チェックボックスが完了していないため通知をスキップ');
        return;
      }
      
      // 現在のシナリオインデックスを取得
      let currentIndex = -1;
      
      // examine1の場合: dataManagerから取得
      if (window.dataManager && typeof window.dataManager.getScenarioAssignment === 'function') {
        const scenarioInfo = window.dataManager.getScenarioAssignment();
        currentIndex = scenarioInfo.currentIndex;
        console.log('checkFormatChangeNotification: dataManagerから現在のシナリオインデックスを取得:', currentIndex);
      } else if (typeof dataManager !== 'undefined' && typeof dataManager.getScenarioAssignment === 'function') {
        const scenarioInfo = dataManager.getScenarioAssignment();
        currentIndex = scenarioInfo.currentIndex;
        console.log('checkFormatChangeNotification: グローバルdataManagerから現在のシナリオインデックスを取得:', currentIndex);
      }
      // examine1_2の場合: experimentManagerから取得
      else if (window.experimentManager && typeof window.experimentManager.sceIdx !== 'undefined') {
        currentIndex = window.experimentManager.sceIdx;
        console.log('checkFormatChangeNotification: experimentManagerから現在のシナリオインデックスを取得:', currentIndex);
      } else if (typeof experimentManager !== 'undefined' && typeof experimentManager.sceIdx !== 'undefined') {
        currentIndex = experimentManager.sceIdx;
        console.log('checkFormatChangeNotification: グローバルexperimentManagerから現在のシナリオインデックスを取得:', currentIndex);
      }
      // フォールバック: HTMLから推定
      else {
        const pageElement = document.getElementById('page');
        if (pageElement && pageElement.innerHTML) {
          const match = pageElement.innerHTML.match(/(\d+)\/\d+/);
          if (match) {
            currentIndex = parseInt(match[1]) - 1; // 0ベースのインデックスに変換
            console.log('checkFormatChangeNotification: HTMLから現在のシナリオインデックスを推定:', currentIndex);
          }
        }
      }
      
      // 1つ目のシナリオでない場合は処理しない
      if (currentIndex !== 0) {
        console.log(`checkFormatChangeNotification: 1つ目のシナリオではないため通知をスキップ (現在のインデックス: ${currentIndex})`);
        return;
      }
      
      // ユーザーIDを取得
      let userId = null;
      if (window.dataManager && window.dataManager.userId) {
        userId = window.dataManager.userId;
      } else if (window.experimentManager && window.experimentManager.userId) {
        userId = window.experimentManager.userId;
      } else if (typeof dataManager !== 'undefined' && dataManager.userId) {
        userId = dataManager.userId;
      } else if (typeof experimentManager !== 'undefined' && experimentManager.userId) {
        userId = experimentManager.userId;
      } else {
        // URLからユーザーIDを取得を試みる
        const urlParams = new URLSearchParams(window.location.search);
        userId = urlParams.get('id');
      }
      
      if (!userId) {
        console.log('checkFormatChangeNotification: ユーザーIDが取得できないため通知をスキップ');
        return;
      }
      
      // 現在のページを判定
      const currentPage = window.location.pathname.includes('examine1_2') ? 'examine1_2' : 'examine1';
      
      console.log(`checkFormatChangeNotification: 通知処理開始 - ユーザーID: ${userId}, シナリオ: ${currentIndex}, ページ: ${currentPage}`);
      
      // 実験形式変更通知を呼び出し
      const { checkAndShowFormatChangeNotification } = await import('./utilities.js');
      await checkAndShowFormatChangeNotification(userId, currentIndex, currentPage);
      
    } catch (error) {
      console.error('checkFormatChangeNotification: エラーが発生しました:', error);
    }
  }
  
  async submitResponseAndContinue() {
    const sliderElement = document.getElementById('response_slider');
    if (!sliderElement) {
      console.error('スライダー要素が見つかりません');
      return;
    }
    
    const sliderValue = sliderElement.value;
    
    await dataManager.recordResponse(sliderValue);
    
    if (dataManager.isExperimentComplete()) {
      setupPageLeaveWarning(false);
      
      // 現在のページがexamine1であることを指定し、ユーザーIDに基づいて次のページを決定（非同期）
      getNextPageUrl('examine1', dataManager.userId)
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
          // エラー時はデフォルト値を使用
          const defaultNextUrl = `../examine1_2?id=${encodeURIComponent(dataManager.userId)}`;
          dataManager.exportResults(defaultNextUrl)
            .catch(exportError => {
              console.error('結果の送信に失敗しました:', exportError);
              uiManager.showErrorMessage('回答送信中にエラーが発生しました。もう一度送信ボタンを押してください。');
              document.getElementById('submit_response').removeAttribute("disabled");
            });
        });
    } else {
      uiManager.displayScenarioDescription();
    }
  }
  
  handleIMCSubmit() {
    console.log('🟦 event-handler.js - handleIMCSubmit() started');
    console.log('🟦 event-handler.js - Current user ID:', dataManager.userId);
    
    const selectedOptions = [];
    document.querySelectorAll('input[name="sports"]:checked').forEach(function(checkbox) {
      selectedOptions.push(checkbox.value);
    });

    console.log('🟦 event-handler.js - Selected options:', selectedOptions);

    const validSelection = ["野球", "水泳", "その他"];
    const result = selectedOptions.length === validSelection.length &&
                  selectedOptions.every(option => validSelection.includes(option));
    
    console.log('🟦 event-handler.js - IMC result:', result);
    
    if (!dataManager.userId) {
      console.error('🔴 event-handler.js - User ID not found during IMC submit');
      uiManager.showErrorMessage("ユーザーIDが取得できません。");
      return;
    }

    const data = [{
      user_id: dataManager.userId,
      result: result
    }];

    console.log('🟦 event-handler.js - IMC data to send:', data);

    document.getElementById('finish_all_scenarios').setAttribute('disabled', true);
    
    const nextUrl = `/examine3?id=${encodeURIComponent(dataManager.userId)}`;
    console.log('🟦 event-handler.js - Next URL for examine3:', nextUrl);
    
    setupPageLeaveWarning(false);
    
    dataManager.sendTestResults(data, 'exp2', nextUrl)
      .catch(error => {
        console.error('🔴 event-handler.js - IMC結果の送信に失敗しました:', error);
        uiManager.showErrorMessage('回答送信中にエラーが発生しました。もう一度終了ボタンを押してください。');
        document.getElementById('finish_all_scenarios').removeAttribute("disabled");
      });
  }
  
  handleCRTSubmit() {
    const inputs = document.querySelectorAll('input[type="number"]');
    let isValid = true;
    
    inputs.forEach(input => {
      if (!input.value) {
        isValid = false;
        const errorElement = input.nextElementSibling;
        if (errorElement && errorElement.classList.contains('error-text')) {
          errorElement.textContent = 'この項目は必須です';
        }
      }
    });
    
    if (!isValid) {
      return;
    }
    
    const answers = {
      q1: document.querySelector('input[name="q1"]').value,
      q2: document.querySelector('input[name="q2"]').value,
      q3: document.querySelector('input[name="q3"]').value
    };

    const crtData = [{
      user_id: dataManager.userId || 'unknown',
      ...answers
    }];

    const submitBtn = document.querySelector('.submit-btn');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = '送信中...';
    }
    
    const nextUrl = dataManager.userId ? `/end?id=${encodeURIComponent(dataManager.userId)}` : '/end';

    setupPageLeaveWarning(false);
    
    dataManager.sendTestResults(crtData, 'exp3', nextUrl)
      .catch(error => {
        console.error('CRT結果の送信に失敗しました:', error);
        uiManager.showErrorMessage('送信中にエラーが発生しました。もう一度お試しください。');
        
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = '回答を送信';
        }
      });
  }
  
  showNextCRTQuestion(currentQ) {
    const currentInput = document.querySelector(`input[name="${currentQ}"]`);
    if (!currentInput || !currentInput.value) {
      uiManager.showErrorMessage('回答を入力してください');
      return;
    }

    const currentSection = document.getElementById(`${currentQ}-section`);
    const nextQ = currentQ === 'q1' ? 'q2' : 'q3';
    const nextSection = document.getElementById(`${nextQ}-section`);
    
    if (currentSection && nextSection) {
      if (typeof $ === 'function') {
        $(currentSection).fadeOut(300, function() {
          $(nextSection).fadeIn(300);
        });
      } else {
        currentSection.style.display = 'none';
        nextSection.style.display = 'block';
      }
    }
  }
  
  /**
   * examine1_2実験専用のイベント処理
   */
  setupExamine12Events(experimentManager) {
    // 基本イベントセットアップ
    this.setupEventHandlers();
    
    // examine1_2固有のスライダーイベント
    const estimateSlider = document.getElementById('estimate_slider');
    if (estimateSlider) {
      estimateSlider.addEventListener('input', function() {
        const estimateElement = document.getElementById('estimate');
        if (estimateElement) {
          estimateElement.innerHTML = this.value;
        }
      });
    }
    
    // examine1_2固有のイベント委譲
    document.addEventListener('click', (e) => {
      if (!e.target || !e.target.id) return;
      
      switch (e.target.id) {
        case 'finish_all_scenarios':
          experimentManager.handleExportResults();
          break;
        case 'next_scenario':
          experimentManager.handleNextScenario();
          break;
        case 'continue_scenario':
          experimentManager.handleContinueScenario();
          break;
        case 'next_sample':
          experimentManager.toNextSample();
          break;
        case 'start_scenario_button':
          experimentManager.toNextNewSamplePage();
          break;
      }
    });
    
    // チェックボックスの監視
    document.addEventListener('change', (e) => {
      if (e.target && e.target.classList.contains('checkbox')) {
        experimentManager.checkDescription();
      } else if (e.target && e.target.id === 'checkbox') {
        experimentManager.checkEstimate();
      }
    });
  }
}

export default new EventHandler();