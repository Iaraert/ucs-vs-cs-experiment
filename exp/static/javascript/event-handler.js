/**
 * ユーザーイベント処理
 */
import { preventBrowserBack, setupPageLeaveWarning, getNextPageUrl } from './utilities.js';
import { validateCheckboxes } from './common-utils.js';
import dataManager from './data-manager.js';
import uiManager from './ui-manager.js';

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
  }
  
  submitResponseAndContinue() {
    const sliderElement = document.getElementById('response_slider');
    if (!sliderElement) {
      console.error('スライダー要素が見つかりません');
      return;
    }
    
    const sliderValue = sliderElement.value;
    
    dataManager.recordResponse(sliderValue);
    
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
    const selectedOptions = [];
    document.querySelectorAll('input[name="sports"]:checked').forEach(function(checkbox) {
      selectedOptions.push(checkbox.value);
    });

    const validSelection = ["野球", "水泳", "その他"];
    const result = selectedOptions.length === validSelection.length &&
                  selectedOptions.every(option => validSelection.includes(option));
    
    if (!dataManager.userId) {
      uiManager.showErrorMessage("ユーザーIDが取得できません。");
      return;
    }

    const data = [{
      user_id: dataManager.userId,
      result: result
    }];

    document.getElementById('finish_all_scenarios').setAttribute('disabled', true);
    
    const nextUrl = `/examine3?id=${encodeURIComponent(dataManager.userId)}`;
    
    setupPageLeaveWarning(false);
    
    dataManager.sendTestResults(data, 'exp2', nextUrl)
      .catch(error => {
        console.error('IMC結果の送信に失敗しました:', error);
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