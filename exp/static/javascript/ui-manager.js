/**
 * ui-manager.js - UIの操作と表示を担当するモジュール
 */
import config from './config.js';
import dataManager from './data-manager.js';

/**
 * UI操作を管理するクラス
 */
export class UIManager {
  /**
   * コンストラクタ - UIマネージャーを初期化
   */
  constructor() {
    // ローディング状態管理
    this.loadingCount = 0;
    this.loadingElement = null;
  }

  /**
   * UIマネージャーを初期化
   */
  init() {
    this.preloadImages();
    return this;
  }
  
  /**
   * シナリオの説明文と選択肢を表示
   * @param {boolean} isFirstTime - 最初のシナリオ表示かどうか
   */
  displayScenarioDescription(isFirstTime = false) {
    this.clearPage();
    
    if (!isFirstTime) {
      // moveToNextScenario()の戻り値で進捗判定
      const idx = dataManager.moveToNextScenario();
      // --- 進捗ログを追加 ---
      console.log(`[uiManager.displayScenarioDescription] ページ移動: currentScenarioIndex=${dataManager.currentScenarioIndex}`);
    }
    // 背景色をリセット - experimentAppを通じて呼び出し
    if (window.experimentApp && typeof window.experimentApp.resetBackGround === 'function') {
      window.experimentApp.resetBackGround();
    }

    const currentIndex = dataManager.currentScenarioIndex;
    
    // 境界チェック
    if (currentIndex >= config.scenarios.length) {
      console.error(`シナリオインデックスが範囲外です: ${currentIndex}/${config.scenarios.length}`);
      // ここでデータ送信と遷移を行う
      import('./utilities.js').then(async ({ getNextPageUrl, getProgressToken, validateProgressOnSubmit }) => {
        try {
          const nextUrl = await getNextPageUrl(dataManager.experimentType, dataManager.userId);
          const progressToken = getProgressToken();
          const valid = await validateProgressOnSubmit(dataManager.userId, dataManager.experimentType, progressToken);
          if (!valid) {
            alert('不正な進行順序です。最初からやり直してください。');
            window.location.href = '/';
            return;
          }
          await dataManager.exportResults(nextUrl);
        } catch (error) {
          console.error('結果送信に失敗しました:', error);
          alert("回答送信中にエラーが発生しました。もう一度送信ボタンを押してください。");
        }
      });
      return;
    }
    
    const scenarioKey = dataManager.getCurrentScenarioKey();
    const scenarioData = dataManager.getCurrentScenarioData();
    
    // シナリオデータの存在確認
    if (!scenarioData) {
      console.error(`シナリオデータが見つかりません: ${scenarioKey}`);
      alert(`シナリオ "${scenarioKey}" のデータが見つかりません。管理者にお問い合わせください。`);
      return;
    }
    
    // 必須プロパティの確認
    if (!scenarioData.title || !scenarioData.descriptions) {
      console.error(`シナリオ "${scenarioKey}" に必要なプロパティがありません`);
      alert('シナリオデータが不完全です。管理者にお問い合わせください。');
      return;
    }
    
    console.log(`シナリオ表示: インデックス=${currentIndex}, キー=${scenarioKey}`);
    
    // progress_barの最大値と現在値を更新
    const progressBar = document.getElementById('progress_bar');
    if (progressBar) {
      progressBar.max = config.scenarios.length;
      progressBar.value = currentIndex + 1;
    }

    document.getElementById('page').innerHTML = `<h5>${currentIndex + 1}/${config.scenarios.length}種類目</h5>`;
    document.getElementById('scenario_title').innerHTML = `<h3>${scenarioData.title}</h3>`;
    document.getElementById('check_sentence').style.display = "inline-block";
    document.getElementById('description_area').style.display = "inline-block";
    document.getElementById('start_scenario_button').setAttribute("disabled", true);
    
    // 条件によって表示する説明文を選択
    let descriptions;
    if (dataManager.sampleType === 'symmetric') {
      descriptions = scenarioData['descriptions_symmetric'];
    } else {
      descriptions = scenarioData['descriptions'];
    }
    
    // 説明文のHTML要素を動的に生成
    const scenarioDescriptionsContainer = document.getElementById('scenario_descriptions');
    if (scenarioDescriptionsContainer) {
      let html = '<form action="cgi-bin/abc.cgi" method="post">';
      for (let i = 0; i < descriptions.length; i++) {
        html += `
          <p>
            <input class="checkbox" type="checkbox" id="checkbox${i + 1}" style="transform:scale(1.5)" onclick="check_description()" />
            <label for="checkbox${i + 1}" id="scenario_description${i + 1}">${descriptions[i]}</label>
          </p>`;
        if (i < descriptions.length - 1) {
          html += '<br>';
        }
      }
      html += '</form>';
      scenarioDescriptionsContainer.innerHTML = html;
    } else {
      // 既存のラベル要素を使用（フォールバック）
      for (let i = 0; i < descriptions.length; i++) {
        const element = document.getElementById(`scenario_description${i + 1}`);
        if (element) {
          element.innerHTML = descriptions[i];
        }
      }
    }
    
    // チェックボックスをリセット
    const checkboxes = document.getElementsByClassName("checkbox");
    for (let i = 0; i < checkboxes.length; i++) {
      checkboxes[i].checked = false;
    }
  }
  
  /**
   * 画面をクリア
   */
  clearPage() {
    document.getElementById('estimate_input_area').style.display = "none";
    document.getElementById('check_sentence').style.display = "none";
    document.getElementById('description_area').style.display = "none";
    document.getElementById('show_sample_area').style.display = 'none';
    }
  
  /**
   * 画像をプリロード
   */
  preloadImages() {
    // examine1_2実験では、examine1_2.jsで画像プリロードを行うため、
    // ui-manager.jsでのプリロードは無効化
    const currentExperiment = window.location.pathname;
    if (currentExperiment.includes('examine1_2')) {
      console.log('examine1_2実験では、専用のプリロード処理を使用します');
      
      // プリロード表示を非表示
      const preloadElement = document.getElementById('preload_image');
      if (preloadElement) {
        preloadElement.style.display = "none";
      }
      return;
    }

    // 従来のプリロード処理（他の実験用）
    const allScenarios = [
      '1', '2', '3', '4', '5', '6', 
      '7', '8', '9', '10', '11', '12'
    ];
    
    for (let scenario of allScenarios) {
      // シナリオデータを取得
      let scenarioData = dataManager.experimentData ? dataManager.experimentData[scenario] : null;
      if (!scenarioData) {
        console.warn(`シナリオ '${scenario}' のデータが見つかりません。スキップします。`);
        continue;
      }

      // 画像タイプごとにプリロード
      for (let type of config.imageTypes) {
        if (scenarioData['images'] && scenarioData['images'][type]) {
          var img = document.createElement('img');
          img.src = `../${scenarioData['images'][type]}`;
        }
      }
      
      // examine1_2用の画像もプリロード
      if (scenarioData['images1_2']) {
        const imageTypes12 = ["p", "notp", "q", "notq", "arrow"];
        for (let type of imageTypes12) {
          if (scenarioData['images1_2'][type]) {
            var img = document.createElement('img');
            img.src = `../${scenarioData['images1_2'][type]}`;
          }
        }
      }
      
      // 対称条件の画像もプリロード
      if (scenarioData['images_symmetric1_2']) {
        const imageTypes12 = ["p", "notp", "q", "notq", "arrow"];
        for (let type of imageTypes12) {
          if (scenarioData['images_symmetric1_2'][type]) {
            var img = document.createElement('img');
            img.src = `../${scenarioData['images_symmetric1_2'][type]}`;
          }
        }
      }
    }
    
    // プリロード表示を非表示
    const preloadElement = document.getElementById('preload_image');
    if (preloadElement) {
      preloadElement.style.display = "none";
    }
  }
  
  /**
   * サンプル表示ページの表示
   */
  displaySamplePage() {
    this.clearPage();
    
    document.getElementById('show_sample_area').style.display = "inline";
    
    // 背景色を変更 - experimentAppを通じて呼び出し
    if (window.experimentApp && typeof window.experimentApp.changeBackGround === 'function') {
      window.experimentApp.changeBackGround();
    }

    // 前のシナリオのレスポンスチェックボックスとボタンをリセット
    // 実験タイプに応じて適切なチェックボックスIDを選択
    const currentExperiment = window.location.pathname;
    const checkboxId = currentExperiment.includes('examine1_2') ? 'checkbox' : 'response_checkbox';
    const respCheckbox = document.getElementById(checkboxId);
    if (respCheckbox) {
      respCheckbox.checked = false;
      respCheckbox.disabled = true;
    }
    const submitBtn = document.getElementById('submit_response');
    if (submitBtn) submitBtn.disabled = true;
    // 次へボタン類もリセット (for experiment1_2)
    ['next_scenario','continue_scenario','finish_all_scenarios'].forEach(id => {
      const btn = document.getElementById(id);
      if (btn) btn.disabled = true;
    });
    // スライダー操作フラグをリセット
    window.sliderMoved = false;
    
    // スライダー操作フローをHTML側スクリプトでリセット
    if (window.resetResponseFlow) {
      window.resetResponseFlow();
    }
    // サンプルデータを準備
    dataManager.prepareSampleData();
    
    // スライダーのラベルを設定
    this.initializeSlider();
    
    // 刺激を表示
    this.displayStimuli();
    
    // 回答ボタンを表示
    const submitButton = document.getElementById('submit_response');
    if (submitButton) {
      submitButton.style.display = 'inline';
    }
  }
  
  /**
   * スライダーの初期化
   */
  initializeSlider() {
    const scenarioData = dataManager.getCurrentScenarioData();
    
    // 条件に応じて評価文を選択
    let resultText;
    if (dataManager.sampleType === 'symmetric' && scenarioData['result_symmetric']) {
      resultText = scenarioData['result_symmetric'];
      console.log('対称条件の評価文を使用:', resultText);
    } else {
      resultText = scenarioData['result'];
      console.log('非対称条件の評価文を使用:', resultText);
    }
    
    // DOM要素の存在確認と更新を明示的に行う
    const sliderResultElement = document.getElementById('slider_scenario_result');
    if (sliderResultElement) {
      sliderResultElement.textContent = resultText;
      console.log('評価文をDOM要素に設定しました:', resultText);
    } else {
      console.error('slider_scenario_result要素が見つかりません');
    }
    
    // 最小値と最大値も同様に確認しながら設定
    const minResultElement = document.getElementById('slider_min_result');
    if (minResultElement) {
      minResultElement.textContent = '0：' + scenarioData['min_result'];
    }
    
    const maxResultElement = document.getElementById('slider_max_result');
    if (maxResultElement) {
      maxResultElement.textContent = '100：' + scenarioData['max_result'];
    }
    
    // スライダーの初期値設定
    const slider = document.getElementById('response_slider');
    slider.value = 50;
    document.getElementById('slider_value').textContent = '50';
    
    // スライダーを一時的に無効化
    slider.setAttribute('disabled', 'disabled');
    document.getElementById('slider_wait_message').style.display = 'block';
    document.getElementById('submit_response').setAttribute('disabled', 'disabled');
    
    // 指定時間後にスライダーを有効化
    setTimeout(() => {
      slider.removeAttribute('disabled');
      document.getElementById('slider_wait_message').style.display = 'none';
      
      // スライダー操作イベントを追加
      slider.addEventListener('input', function() {
        // 値を表示
        document.getElementById('slider_value').textContent = slider.value;
      }, { once: true }); // 一度だけ実行
    }, config.sliderWaitTime);
  }
  
  /**
   * 刺激の表示
   */
  displayStimuli() {
    // 現在のシナリオデータを取得
    const currentScenario = dataManager.getCurrentScenarioData();
    
    // 条件に応じたフレーム説明を選択
    let frameDescriptions;
    if (dataManager.sampleType === 'symmetric') {
      frameDescriptions = currentScenario['frame_descriptions_symmetric'];
      console.log("対称的な否定条件のフレーム説明を使用");
    } else {
      frameDescriptions = currentScenario['frame_descriptions'];
      console.log("非対称的な否定条件のフレーム説明を使用");
    }
    
    // フレーム説明を左カラムに表示
    document.getElementById('non_treated_description').textContent = frameDescriptions.top;
    document.getElementById('treated_description').textContent = frameDescriptions.bottom;
    
    // 画像パスを取得
    let imagePaths = currentScenario['images'];
    
    // センテンスから意味を抽出（"症状あり"や"症状なし"などの部分）
    const positiveMeaning = currentScenario['sentences']['a'].split('、')[1];
    const negativeMeaning = currentScenario['sentences']['b'].split('、')[1];
    
    document.getElementById('positive_meaning').textContent = positiveMeaning;
    document.getElementById('negative_meaning').textContent = negativeMeaning;
    
    // 凡例のアイコンを画像に変更
    const positiveIcon = document.getElementById('positive_icon');
    const negativeIcon = document.getElementById('negative_icon');
    
    // 既存の内容をクリア
    positiveIcon.innerHTML = '';
    negativeIcon.innerHTML = '';
    
    // 画像要素を作成して追加
    const positiveImg = document.createElement('img');
    positiveImg.className = 'sample';
    positiveImg.src = `../${imagePaths['positive']}`;
    positiveImg.alt = positiveMeaning;
    positiveImg.style.maxHeight = '30px';
    positiveIcon.appendChild(positiveImg);
    
    const negativeImg = document.createElement('img');
    negativeImg.className = 'sample';
    negativeImg.src = `../${imagePaths['negative']}`;
    negativeImg.alt = negativeMeaning;
    negativeImg.style.maxHeight = '30px';
    negativeIcon.appendChild(negativeImg);
    
    // 2群に分けて表示
    // 投与なし群：c（症状あり）と d（症状なし）の人たち
    this.displayGroupIcons(
      'non_treated_icons', 
      dataManager.currentSampleData.c, 
      dataManager.currentSampleData.d, 
      imagePaths['positive'], 
      imagePaths['negative']
    );
    
    // 投与あり群：a（症状あり）と b（症状なし）の人たち
    this.displayGroupIcons(
      'treated_icons', 
      dataManager.currentSampleData.a, 
      dataManager.currentSampleData.b, 
      imagePaths['positive'], 
      imagePaths['negative']
    );
  }
  
  /**
   * 各群のアイコンを表示する関数（画像を使用）
   * @param {string} containerId - コンテナ要素のID
   * @param {number} positiveCount - 正のアイコン数
   * @param {number} negativeCount - 負のアイコン数
   * @param {string} positiveImagePath - 正のアイコン画像パス
   * @param {string} negativeImagePath - 負のアイコン画像パス
   */
  displayGroupIcons(containerId, positiveCount, negativeCount, positiveImagePath, negativeImagePath) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    // アイコンの総数を計算
    const totalIcons = positiveCount + negativeCount;
    
    // 基本設定：2行固定で表示
    const numRows = 2;
    
    // 必要な列数を計算（正確に必要な列数を計算）
    let columnCount = Math.ceil(totalIcons / numRows);
    
    // グリッドコンテナを作成
    const gridContainer = document.createElement('div');
    gridContainer.style.display = 'grid';
    gridContainer.style.gridTemplateRows = 'repeat(2, auto)'; // 2行固定
    gridContainer.style.gridAutoFlow = 'column';
    gridContainer.style.justifyContent = 'center';
    gridContainer.style.gap = '5px';
    
    // 配置済みのセルを追跡する2次元配列（true = 使用済み）
    const occupiedCells = Array(numRows).fill().map(() => Array(columnCount).fill(false));
    
    // ポジティブアイコンを先に配置
    let remainingPositive = positiveCount;
    let posCol = 0;
    let posRow = 0;
    
    while (remainingPositive > 0) {
      // 現在の列に2つのアイコンを配置（可能な限り）
      for (let row = 0; row < numRows && remainingPositive > 0; row++) {
        createIcon(posCol, row, positiveImagePath, 'Positive');
        occupiedCells[row][posCol] = true;
        remainingPositive--;
      }
      
      // 次の列へ移動
      posCol++;
    }
    
    // ネガティブアイコンを配置
    let remainingNegative = negativeCount;
    
    // 空いているセルを探してネガティブアイコンを配置
    for (let col = 0; col < columnCount && remainingNegative > 0; col++) {
      for (let row = 0; row < numRows && remainingNegative > 0; row++) {
        // このセルが空いている場合のみ配置
        if (!occupiedCells[row][col]) {
          createIcon(col, row, negativeImagePath, 'Negative');
          occupiedCells[row][col] = true;
          remainingNegative--;
        }
      }
    }
    
    // もし配置しきれなかった場合、新しい列を追加
    let extraCol = columnCount;
    while (remainingNegative > 0) {
      for (let row = 0; row < numRows && remainingNegative > 0; row++) {
        createIcon(extraCol, row, negativeImagePath, 'Negative');
        remainingNegative--;
      }
      extraCol++;
    }
    
    // アイコンを作成して追加する内部関数
    function createIcon(col, row, imagePath, altText) {
      // グリッドアイテムを作成
      const gridItem = document.createElement('div');
      gridItem.style.gridRow = (row + 1).toString();
      gridItem.style.gridColumn = (col + 1).toString();
      
      // アイコンコンテナを作成
      const iconContainer = document.createElement('span');
      iconContainer.className = 'group-icon';
      
      // 画像要素を作成
      const imageElement = document.createElement('img');
      imageElement.src = `../${imagePath}`;
      imageElement.alt = altText;
      imageElement.className = 'icon-image';
      imageElement.style.maxHeight = '60px';
      imageElement.style.maxWidth = '60px';
      
      // データ属性を追加して識別を容易に
      gridItem.dataset.iconType = altText.toLowerCase();
      gridItem.dataset.row = row;
      gridItem.dataset.col = col;
      
      // 要素を組み立てる
      iconContainer.appendChild(imageElement);
      gridItem.appendChild(iconContainer);
      gridContainer.appendChild(gridItem);
    }
    
    // コンテナに追加
    container.appendChild(gridContainer);
    
    // デバッグログ
    console.log(`${containerId} 表示内訳:`);
    console.log(`ポジティブアイコン: ${positiveCount}個, ネガティブアイコン: ${negativeCount}個, 合計: ${totalIcons}個`);
  }
  
  /**
   * アイコンを行に均等に分配する関数
   * @param {number} iconCount - 分配するアイコンの総数
   * @param {number} numRows - 行数
   * @returns {Array} 各行のアイコン数の配列
   */
  distributeIcons(iconCount, numRows) {
    // 各行のアイコン数を格納する配列
    const iconsPerRow = new Array(numRows).fill(0);
    
    // 一度に割り当てるアイコン数
    const batchSize = Math.ceil(iconCount / numRows);
    
    // 残りのアイコン数
    let remainingIcons = iconCount;
    
    // 最初の行から順に割り当て
    for (let row = 0; row < numRows && remainingIcons > 0; row++) {
      // この行に割り当てるアイコン数
      const iconsForThisRow = Math.min(batchSize, remainingIcons);
      iconsPerRow[row] = iconsForThisRow;
      remainingIcons -= iconsForThisRow;
    }
    
    // 残りがあれば、後ろの行から埋めていく（バランスを取るため）
    let row = numRows - 1;
    while (remainingIcons > 0 && row >= 0) {
      if (iconsPerRow[row] < batchSize) {
        iconsPerRow[row]++;
        remainingIcons--;
      }
      row--;
      if (row < 0) row = numRows - 1;  // 循環する
    }
    
    return iconsPerRow;
  }
  
  /**
   * エラーメッセージを表示
   * @param {string} message - 表示するメッセージ
   * @param {number} duration - 表示時間（ミリ秒）
   */
  showErrorMessage(message, duration = 3000) {
    const errorElement = document.getElementById('error-message');
    if (errorElement) {
      errorElement.textContent = message;
      errorElement.style.display = 'block';
      
      setTimeout(() => {
        errorElement.style.display = 'none';
      }, duration);
    } else {
      console.error(message);
      alert(message);
    }
  }
  
  /**
   * ローディングインジケーターを表示または非表示にする
   * @param {boolean} isLoading - trueで表示、falseで非表示
   */
  showLoading(isLoading) {
    if (isLoading) {
      this.loadingCount++;
    } else if (this.loadingCount > 0) {
      this.loadingCount--;
    }
    
    // ローディング要素がなければ作成
    if (!this.loadingElement) {
      this.createLoadingElement();
    }
    
    // ローディングカウンタが0より大きい場合は表示、それ以外は非表示
    if (this.loadingElement) {
      this.loadingElement.style.display = this.loadingCount > 0 ? 'flex' : 'none';
    }
  }
  
  /**
   * ローディング要素を作成
   */
  createLoadingElement() {
    // 既存の要素があれば使用
    const existingElement = document.getElementById('loading-indicator');
    if (existingElement) {
      this.loadingElement = existingElement;
      return;
    }
    
    // 要素の作成
    const loadingElement = document.createElement('div');
    loadingElement.id = 'loading-indicator';
    loadingElement.style.position = 'fixed';
    loadingElement.style.top = '0';
    loadingElement.style.left = '0';
    loadingElement.style.width = '100%';
    loadingElement.style.height = '100%';
    loadingElement.style.backgroundColor = 'rgba(255, 255, 255, 0.7)';
    loadingElement.style.display = 'none';
    loadingElement.style.justifyContent = 'center';
    loadingElement.style.alignItems = 'center';
    loadingElement.style.zIndex = '9999';
    
    // ローディングスピナーとメッセージコンテナ
    const spinnerContainer = document.createElement('div');
    spinnerContainer.style.textAlign = 'center';
    spinnerContainer.style.backgroundColor = '#fff';
    spinnerContainer.style.padding = '20px';
    spinnerContainer.style.borderRadius = '5px';
    spinnerContainer.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.2)';
    
    // スピナー要素
    const spinner = document.createElement('div');
    spinner.style.border = '4px solid #f3f3f3';
    spinner.style.borderTop = '4px solid #3498db';
    spinner.style.borderRadius = '50%';
    spinner.style.width = '30px';
    spinner.style.height = '30px';
    spinner.style.margin = '0 auto 10px auto';
    spinner.style.animation = 'spin 1s linear infinite';
    
    // スタイルシートにアニメーションを追加
    const style = document.createElement('style');
    style.innerHTML = `
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    `;
    document.head.appendChild(style);
    
    // ロードメッセージ
    const loadingText = document.createElement('div');
    loadingText.textContent = 'データを読み込み中...';
    
    // 要素を組み立てる
    spinnerContainer.appendChild(spinner);
    spinnerContainer.appendChild(loadingText);
    loadingElement.appendChild(spinnerContainer);
    document.body.appendChild(loadingElement);
    
    this.loadingElement = loadingElement;
  }

  /**
   * 要素を非表示にする
   * @param {string} elementId - 要素のID
   */
  hideElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
      element.style.display = 'none';
    } else {
      console.warn(`要素が見つかりません: ${elementId}`);
    }
  }

  /**
   * 要素を表示する
   * @param {string} elementId - 要素のID
   * @param {string} displayType - 表示タイプ（デフォルト: 'block'）
   */
  showElement(elementId, displayType = 'block') {
    const element = document.getElementById(elementId);
    if (element) {
      element.style.display = displayType;
    } else {
      console.warn(`要素が見つかりません: ${elementId}`);
    }
  }

  /**
   * 要素の表示/非表示を切り替える
   * @param {string} elementId - 要素のID
   * @param {boolean} visible - true: 表示, false: 非表示
   * @param {string} displayType - 表示タイプ（デフォルト: 'block'）
   */
  toggleElement(elementId, visible, displayType = 'block') {
    if (visible) {
      this.showElement(elementId, displayType);
    } else {
      this.hideElement(elementId);
    }
  }
}

// デフォルトインスタンスをエクスポート
export default new UIManager();