/**
 * 共通ユーティリティ関数
 */

/**
 * 配列内の要素をシャッフル
 */
export function shuffleArray([...array]) {
  for (let i = array.length - 1; i >= 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
  }
  return array;
}

/**
 * 0埋め関数
 */
export function zeroPadding(num, length) {
  return (Array(length).join('0') + num).slice(-length);
}

/**
 * 現在時刻を"YYYY/MM/DD HH:MM:SS"形式で返す
 */
export function getNow() {
  const now = new Date();
  const year = now.getFullYear();
  const mon = now.getMonth() + 1;
  const day = now.getDate();
  const hour = now.getHours();
  const min = now.getMinutes();
  const sec = now.getSeconds();
  return `${year}/${mon}/${day} ${hour}:${min}:${sec}`;
}

/**
 * ブラウザバックを禁止
 */
export function preventBrowserBack() {
  history.pushState(null, null, location.href);
  window.addEventListener('popstate', () => {
    history.go(1);
  });
}

/**
 * URLパラメータからユーザーIDを取得
 */
export function getUserIdFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('id');
}

/**
 * ユーザーIDをストレージに保存
 */
export function saveUserId(userId, persistent = false) {
  sessionStorage.setItem('exp_user_id', userId);
  
  if (persistent) {
    localStorage.setItem('exp_user_id_persistent', userId);
  }
  
  return userId;
}

/**
 * ユーザーIDを生成または復元
 */
export function getOrCreateUserId(options = {}) {
  const { 
    urlParam = true, 
    persistent = false 
  } = options;
  
  // URLからのID取得を試みる
  if (urlParam) {
    const urlId = getUserIdFromUrl();
    if (urlId) {
      return saveUserId(urlId, persistent);
    }
  }
  
  // セッションストレージから取得を試みる
  const sessionId = sessionStorage.getItem('exp_user_id');
  if (sessionId) {
    return sessionId;
  }
  
  // 永続ストレージから取得を試みる
  if (persistent) {
    const localId = localStorage.getItem('exp_user_id_persistent');
    if (localId) {
      return saveUserId(localId, true);
    }
  }
  
  // 新規IDを生成
  const newId = generateUniqueId();
  return saveUserId(newId, persistent);
}

/**
 * ランダムな一意のID文字列を生成
 */
export function generateUniqueId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
}

/**
 * ページ離脱警告を設定
 */
export function setupPageLeaveWarning(enabled = true) {
  if (enabled) {
    window.onbeforeunload = function(e) {
      e.returnValue = "ページを離れると、これまで入力した内容は全て破棄されます。ページを離れてもよろしいですか？";
      return e.returnValue;
    };
  } else {
    window.onbeforeunload = null;
  }
}

/**
 * JSONファイルを非同期で読み込み
 */
export function readJson(filename) {
  return new Promise((resolve, reject) => {
    $.ajax({
      type: 'GET',
      url: filename,
      dataType: 'json',
      success: function(data) {
        resolve(data);
      },
      error: function(xhr, status, error) {
        console.error(`JSONファイルの読み込みに失敗: ${filename}`, error);
        reject(new Error(`JSONファイルの読み込みエラー: ${error}`));
      }
    });
  });
}

/**
 * 入力フィールドの検証
 */
export function validateInput(field, errorMsg = '入力してください') {
  const $field = $(field);
  if (!$field.val()) {
    const $errorText = $field.siblings('.error-text');
    if ($errorText.length) {
      $errorText.text(errorMsg);
    } else {
      console.error(errorMsg);
    }
    return false;
  }
  return true;
}

/**
 * CSSファイルが読み込まれているか確認
 */
export function isStylesheetLoaded(href) {
  return Array.from(document.styleSheets).some(
    sheet => sheet.href && sheet.href.includes(href)
  );
}

/**
 * CSSファイルを読み込み
 */
export function loadStylesheet(href) {
  if (isStylesheetLoaded(href)) {
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    
    link.onload = () => resolve();
    link.onerror = () => reject(new Error(`CSSファイルの読み込みに失敗: ${href}`));
    
    document.head.appendChild(link);
  });
}

/**
 * 複数のCSSファイルを読み込み
 */
export function loadStylesheets(hrefs) {
  return Promise.all(hrefs.map(href => loadStylesheet(href)));
}

/**
 * ページ固有のCSSを読み込む
 */
export function loadPageStyles(pageName) {
  return loadStylesheet(`../static/css/${pageName}.css`);
}

/**
 * ユーザーIDに基づいて実験順序を決定する
 * 「examine1 → examine1_2」と「examine1_2 → examine1」の2パターンを均等に割り振る
 * @param {string} userId - ユーザーID
 * @returns {Promise<string>} - 'order1'（examine1 → examine1_2）または'order2'（examine1_2 → examine1）
 */
export async function getExperimentOrder(userId) {
  if (!userId) {
    console.warn('ユーザーIDが指定されていないため、デフォルトの順序（order1）を使用します');
    return Promise.resolve('order1');
  }
  
  try {
    // サーバーから実験経路を取得
    const response = await fetch(`/getExperimentPath?user_id=${encodeURIComponent(userId)}`);
    
    if (!response.ok) {
      throw new Error(`サーバーエラー: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('実験経路取得結果:', data);
    
    return data.pathType || 'order1';
  } catch (error) {
    console.error('実験経路の取得に失敗しました:', error);
    // エラー時はデフォルトの順序を返す
    return 'order1';
  }
}

/**
 * 実験順序に基づいて次のページURLを取得
 * @param {string} currentPage - 現在のページ名（'examine1'または'examine1_2'）
 * @param {string} userId - ユーザーID
 * @returns {Promise<string>} - 次のページへのURLを含むPromise
 */
export async function getNextPageUrl(currentPage, userId) {
  const experimentOrder = await getExperimentOrder(userId);
  
  if (currentPage === 'examine1') {
    if (experimentOrder === 'order1') {
      // examine1 → examine1_2 → examine2の順序
      return `../examine1_2?id=${encodeURIComponent(userId)}`;
    } else {
      // examine1_2 → examine1 → examine2の順序（examine1が最後）
      return `../examine2?id=${encodeURIComponent(userId)}`;
    }
  } else if (currentPage === 'examine1_2') {
    if (experimentOrder === 'order1') {
      // examine1 → examine1_2 → examine2の順序（examine1_2が最後）
      return `../examine2?id=${encodeURIComponent(userId)}`;
    } else {
      // examine1_2 → examine1 → examine2の順序
      return `../examine1?id=${encodeURIComponent(userId)}`;
    }
  }
  
  // デフォルトはexamine2
  return `../examine2?id=${encodeURIComponent(userId)}`;
}