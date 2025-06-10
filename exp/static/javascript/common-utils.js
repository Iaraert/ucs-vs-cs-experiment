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
  const checkboxes = document.getElementsByClassName(checkboxClass);
  let checkedCount = 0;
  
  for (let i = 0; i < checkboxes.length; i++) {
    if (checkboxes[i].checked) {
      checkedCount++;
    }
  }
  
  const targetButton = document.getElementById(targetButtonId);
  if (targetButton) {
    if (checkedCount === checkboxes.length) {
      targetButton.removeAttribute("disabled");
    } else {
      targetButton.setAttribute("disabled", true);
    }
  }
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