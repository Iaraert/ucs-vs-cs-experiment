/**
 * common-utils.js - 共通ユーティリティ関数
 * 重複コードの削減と保守性の向上を目的とした共通機能
 */

/**
 * チェックボックス確認機能の統一化
 * @param {string} checkboxClass - チェックボックスのクラス名
 * @param {string} targetButtonId - 有効/無効を切り替えるボタンのID
 */
export function validateCheckboxes(checkboxClass, targetButtonId) {
  // DOM更新完了を確実に待機してからチェックボックス数をカウント
  setTimeout(() => {
    const checkboxes = document.getElementsByClassName(checkboxClass);
    let checkedCount = 0;
    
    // デバッグ情報: DOM更新状況とチェックボックス総数
    console.log(`validateCheckboxes: DOM更新待機完了 - 総チェックボックス数 = ${checkboxes.length}`);
    console.log(`validateCheckboxes: DOM状況 - readyState: ${document.readyState}`);
    
    // 詳細なデバッグ情報: 各チェックボックスの状態
    for (let i = 0; i < checkboxes.length; i++) {
      const isChecked = checkboxes[i].checked;
      console.log(`validateCheckboxes: チェックボックス${i + 1} (ID: ${checkboxes[i].id}) - チェック状態: ${isChecked}, 表示状態: ${checkboxes[i].style.display !== 'none' ? '表示' : '非表示'}`);
      if (isChecked) {
        checkedCount++;
      }
    }
    
    // デバッグ情報: チェック済み数と総数の詳細
    console.log(`validateCheckboxes: チェック済み数 = ${checkedCount}, 総数 = ${checkboxes.length}, 全チェック済み: ${checkedCount === checkboxes.length && checkboxes.length > 0}`);
    
    const targetButton = document.getElementById(targetButtonId);
    if (targetButton) {
      if (checkedCount === checkboxes.length && checkboxes.length > 0) {
        targetButton.removeAttribute("disabled");
        console.log(`validateCheckboxes: ボタン "${targetButtonId}" を有効化しました`);
      } else {
        targetButton.setAttribute("disabled", true);
        console.log(`validateCheckboxes: ボタン "${targetButtonId}" を無効化しました (${checkedCount}/${checkboxes.length})`);
      }
    } else {
      // ボタンが見つからない場合は何もしない（warnは出すがエラーにしない）
      console.warn(`validateCheckboxes: ターゲットボタン "${targetButtonId}" が見つかりません`);
      // return; // ここでreturnしてもOK
    }
  }, 200); // DOM更新完了を確実に待機（200msに延長）
}

/**
 * チェックボックス確認機能の統一化（堅牢版）
 * DOM更新の遅延に対応するため、複数回の検証を実行
 * @param {string} checkboxClass - チェックボックスのクラス名
 * @param {string} targetButtonId - 有効/無効を切り替えるボタンのID
 */
export function validateCheckboxesRobust(checkboxClass, targetButtonId) {
  let attempts = 0;
  const maxAttempts = 5; // より多くの再試行
  
  function performValidation() {
    attempts++;
    const checkboxes = document.getElementsByClassName(checkboxClass);
    
    console.log(`validateCheckboxesRobust: 試行 ${attempts}/${maxAttempts} - チェックボックス数: ${checkboxes.length}, DOM状態: ${document.readyState}`);
    
    // チェックボックスが見つからない場合は再試行
    if (checkboxes.length === 0 && attempts < maxAttempts) {
      console.log('validateCheckboxesRobust: チェックボックスが見つからない - 再試行します');
      setTimeout(performValidation, 150);
      return;
    }
    
    let checkedCount = 0;
    for (let i = 0; i < checkboxes.length; i++) {
      const isChecked = checkboxes[i].checked;
      console.log(`validateCheckboxesRobust: チェックボックス${i + 1} (ID: ${checkboxes[i].id}) - チェック状態: ${isChecked}, 可視性: ${checkboxes[i].offsetParent !== null ? '表示' : '非表示'}`);
      if (isChecked) {
        checkedCount++;
      }
    }
    
    console.log(`validateCheckboxesRobust: チェック済み数 = ${checkedCount}/${checkboxes.length}, 全チェック済み: ${checkedCount === checkboxes.length && checkboxes.length > 0}`);
    
    const targetButton = document.getElementById(targetButtonId);
    if (targetButton) {
      if (checkedCount === checkboxes.length && checkboxes.length > 0) {
        targetButton.removeAttribute("disabled");
        console.log(`validateCheckboxesRobust: ボタン "${targetButtonId}" を有効化しました`);
      } else {
        targetButton.setAttribute("disabled", true);
        console.log(`validateCheckboxesRobust: ボタン "${targetButtonId}" を無効化しました`);
      }
    } else {
      console.warn(`validateCheckboxesRobust: ターゲットボタン "${targetButtonId}" が見つかりません`);
    }
  }
  
  // 初回実行
  setTimeout(performValidation, 100);
}

/**
 * データ構造の存在確認パターンの共通化
 * @param {Object} testOrder - テストオーダーオブジェクト
 * @param {string} scenarioKey - シナリオキー
 * @param {Array<string>} requiredPaths - 必要なパスの配列（例: ['samples.1', 'images1_2']）
 * @returns {boolean} データ構造が有効な場合はtrue
 */
export function validateScenarioData(testOrder, scenarioKey, requiredPaths = []) {
  // testOrderの基本チェック
  if (!testOrder || typeof testOrder !== 'object') {
    console.warn('testOrderが初期化されていません');
    return false;
  }
  
  // scenarioKeyが指定されている場合のシナリオチェック
  if (scenarioKey) {
    if (!testOrder[scenarioKey]) {
      console.error(`シナリオデータが見つかりません: ${scenarioKey}`);
      return false;
    }
    
    // 必要なパスの存在確認
    for (const path of requiredPaths) {
      if (!validateDataPath(testOrder[scenarioKey], path)) {
        console.error(`必要なデータパスが見つかりません: ${scenarioKey}.${path}`);
        return false;
      }
    }
  }
  
  return true;
}

/**
 * データパスの存在確認ヘルパー関数
 * @param {Object} obj - チェック対象のオブジェクト
 * @param {string} path - ドット記法のパス（例: 'samples.1' or 'images1_2'）
 * @returns {boolean} パスが存在する場合はtrue
 */
function validateDataPath(obj, path) {
  const keys = path.split('.');
  let current = obj;
  
  for (const key of keys) {
    if (current && typeof current === 'object' && key in current) {
      current = current[key];
    } else {
      return false;
    }
  }
  
  return true;
}

/**
 * 汎用データ構造検証関数
 * @param {Object} data - 検証対象のデータ
 * @param {string} dataName - データ名（ログ用）
 * @param {Array<string>} requiredFields - 必須フィールドの配列
 * @returns {boolean} 検証が成功した場合はtrue
 */
export function validateDataStructure(data, dataName, requiredFields = []) {
  if (!data || typeof data !== 'object') {
    console.error(`${dataName}が無効です:`, data);
    return false;
  }
  
  for (const field of requiredFields) {
    if (!(field in data)) {
      console.error(`${dataName}に必要なフィールド '${field}' がありません`);
      return false;
    }
  }
  
  return true;
}

/**
 * 画像パス設定の最適化
 * @param {Object} imageMapping - 画像マッピングオブジェクト
 */
export function setImagePaths(imageMapping) {
  for (const [elementId, imagePath] of Object.entries(imageMapping)) {
    const element = document.getElementById(elementId);
    if (element) {
      element.src = `../${imagePath}`;
    } else {
      console.warn(`画像要素が見つかりません: ${elementId}`);
    }
  }
}

/**
 * 画像マッピングオブジェクト作成
 * @param {Object} images - 画像データオブジェクト
 * @param {Object} imgCombination - 画像の組み合わせ設定
 * @param {string} sample - サンプルタイプ
 * @returns {Object} 画像マッピングオブジェクト
 */
export function createImageMapping(images, imgCombination, sample) {
  if (!images || !imgCombination || !imgCombination[sample]) {
    console.warn('画像マッピングの作成に必要なデータが不足しています');
    return {};
  }
  
  const combination = imgCombination[sample];
  return {
    'sample_before': images[combination.cause],
    'sample_after': images[combination.effect],
    'arrow': images['arrow']
  };
}

/**
 * 複数要素の表示状態を一括設定
 * @param {Object} displaySettings - 要素IDと表示状態のマッピング
 */
export function setElementsDisplay(displaySettings) {
  for (const [elementId, displayValue] of Object.entries(displaySettings)) {
    const element = document.getElementById(elementId);
    if (element) {
      element.style.display = displayValue;
    } else {
      console.warn(`要素が見つかりません: ${elementId}`);
    }
  }
}

/**
 * 複数ボタンの状態を一括設定
 * @param {Object} buttonStates - ボタンIDと無効状態のマッピング（true = disabled, false = enabled）
 */
export function setButtonStates(buttonStates) {
  for (const [buttonId, isDisabled] of Object.entries(buttonStates)) {
    const button = document.getElementById(buttonId);
    if (button) {
      if (isDisabled) {
        button.setAttribute("disabled", true);
      } else {
        button.removeAttribute("disabled");
      }
    } else {
      console.warn(`ボタンが見つかりません: ${buttonId}`);
    }
  }
}

/**
 * 要素の属性を一括設定
 * @param {string} elementId - 要素ID
 * @param {Object} attributes - 属性名と値のマッピング
 */
export function setElementAttributes(elementId, attributes) {
  const element = document.getElementById(elementId);
  if (element) {
    for (const [attrName, attrValue] of Object.entries(attributes)) {
      if (attrValue === null || attrValue === undefined) {
        element.removeAttribute(attrName);
      } else {
        element.setAttribute(attrName, attrValue);
      }
    }
  } else {
    console.warn(`要素が見つかりません: ${elementId}`);
  }
}

/**
 * 複数要素のテキストコンテンツを一括設定
 * @param {Object} textSettings - 要素IDとテキストのマッピング
 */
export function setElementTexts(textSettings) {
  for (const [elementId, text] of Object.entries(textSettings)) {
    const element = document.getElementById(elementId);
    if (element) {
      element.textContent = text;
    } else {
      console.warn(`要素が見つかりません: ${elementId}`);
    }
  }
}

/**
 * 複数要素のHTMLコンテンツを一括設定
 * @param {Object} htmlSettings - 要素IDとHTMLのマッピング
 */
export function setElementHTMLs(htmlSettings) {
  for (const [elementId, html] of Object.entries(htmlSettings)) {
    const element = document.getElementById(elementId);
    if (element) {
      element.innerHTML = html;
    } else {
      console.warn(`要素が見つかりません: ${elementId}`);
    }
  }
}

