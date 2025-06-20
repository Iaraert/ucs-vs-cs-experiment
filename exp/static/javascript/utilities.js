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
 * URLパラメータからユーザーIDを取得（検証付き）
 * end.html以外では取得後にURLパラメータを隠す
 * @returns {string|null} 検証済みのユーザーIDまたはnull
 */
export function getUserIdFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  const rawId = urlParams.get('id');
  
  // end.html以外でURLパラメータを隠す
  if (!window.location.pathname.includes('/end')) {
    try {
      const cleanUrl = window.location.protocol + '//' + 
                      window.location.host + 
                      window.location.pathname;
      window.history.replaceState({}, document.title, cleanUrl);
      console.log('utilities.js: URLパラメータを非表示にしました');
    } catch (error) {
      console.error('utilities.js: URLパラメータの非表示に失敗しました:', error);
    }
  }
  
  if (!rawId) return null;
  
  // ユーザーIDをサニタイズ
  const sanitizedId = sanitizeUserId(rawId);
  
  // サニタイズ後のIDを検証
  if (!validateUserId(sanitizedId)) {
    console.warn('Invalid user ID detected from URL:', rawId);
    return null;
  }
  
  return sanitizedId;
}

/**
 * ユーザーIDをストレージに保存（検証付き）
 * @param {string} userId - 保存するユーザーID
 * @param {boolean} persistent - 永続化するかどうか
 * @returns {string|null} 保存されたユーザーIDまたはnull
 */
export function saveUserId(userId, persistent = false) {
  // ユーザーIDの検証
  if (!validateUserId(userId)) {
    console.error('Invalid user ID cannot be saved:', userId);
    return null;
  }
  
  const sanitizedId = sanitizeUserId(userId);
  
  try {
    sessionStorage.setItem('exp_user_id', sanitizedId);
    
    if (persistent) {
      localStorage.setItem('exp_user_id_persistent', sanitizedId);
    }
    
    return sanitizedId;
  } catch (error) {
    console.error('Failed to save user ID to storage:', error);
    return null;
  }
}

/**
 * ユーザーIDを生成または復元（検証強化版）
 * @param {Object} options - オプション設定
 * @returns {string} 検証済みのユーザーID
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
      const savedId = saveUserId(urlId, persistent);
      if (savedId) return savedId;
    }
  }
  
  // セッションストレージから取得を試みる
  try {
    const sessionId = sessionStorage.getItem('exp_user_id');
    if (sessionId && validateUserId(sessionId)) {
      return sessionId;
    } else if (sessionId) {
      // 無効なIDはクリア
      sessionStorage.removeItem('exp_user_id');
      console.warn('Invalid user ID found in session storage, cleared');
    }
  } catch (error) {
    console.warn('Failed to access session storage:', error);
  }
  
  // 永続ストレージから取得を試みる
  if (persistent) {
    try {
      const localId = localStorage.getItem('exp_user_id_persistent');
      if (localId && validateUserId(localId)) {
        return saveUserId(localId, true) || localId;
      } else if (localId) {
        // 無効なIDはクリア
        localStorage.removeItem('exp_user_id_persistent');
        console.warn('Invalid user ID found in local storage, cleared');
      }
    } catch (error) {
      console.warn('Failed to access local storage:', error);
    }
  }
  
  // 新規IDを生成
  const newId = generateUniqueId();
  return saveUserId(newId, persistent) || newId;
}

/**
 * ランダムな一意のID文字列を生成
 * @returns {string} より堅牢で衝突しにくい一意のID
 */
export function generateUniqueId() {
  // より強力な一意性を保証するため、複数の要素を組み合わせ
  const timestamp = Date.now().toString(36);
  const randomPart1 = Math.random().toString(36).substr(2, 6);
  const randomPart2 = Math.random().toString(36).substr(2, 4);
  const performanceNow = performance.now().toString(36).substr(2, 4);
  
  return `${timestamp}${randomPart1}${randomPart2}${performanceNow}`;
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
 * @param {boolean} reallocate - 既存の割り当てを無視して再割り当てするかどうか
 * @returns {Promise<string>} - 'order1'（examine1 → examine1_2）または'order2'（examine1_2 → examine1）
 */
export async function getExperimentOrder(userId, reallocate = false) {
  if (!userId) {
    console.warn('ユーザーIDが指定されていないため、デフォルトの順序（order1）を使用します');
    return Promise.resolve('order1');
  }
  
  try {
    // サーバーから実験経路を取得
    // reallocateパラメータを明示的に設定
    const url = `/getExperimentPath?user_id=${encodeURIComponent(userId)}&reallocate=${reallocate}`;
    // console.log(`実験経路を取得中: ユーザーID=${userId}, reallocate=${reallocate}`);
    const response = await fetch(url);
    
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
  // reallocate=falseを明示的に設定して既存の経路を尊重するようにする
  const experimentOrder = await getExperimentOrder(userId, false);
  
  // console.log(`getNextPageUrl: currentPage=${currentPage}, experimentOrder=${experimentOrder}, userId=${userId}`);
  
  if (currentPage === 'examine1') {
    if (experimentOrder === 'order1') {
      // examine1 → examine1_2 → examine2の順序
      console.log('order1: examine1 → examine1_2への遷移');
      return `../examine1_2?id=${encodeURIComponent(userId)}`;
    } else {
      // order2: examine1_2 → examine1 → examine2の順序（examine1が最後）
      console.log('order2: examine1 → examine2への遷移（examine1が最後）');
      return `../examine2?id=${encodeURIComponent(userId)}`;
    }
  } else if (currentPage === 'examine1_2') {
    if (experimentOrder === 'order1') {
      // order1: examine1 → examine1_2 → examine2の順序（examine1_2が最後）
      console.log('order1: examine1_2 → examine2への遷移（examine1_2が最後）');
      return `../examine2?id=${encodeURIComponent(userId)}`;
    } else {
      // order2: examine1_2 → examine1 → examine2の順序
      console.log('order2: examine1_2 → examine1への遷移');
      return `../examine1?id=${encodeURIComponent(userId)}`;
    }
  }
  
  // デフォルトはexamine2
  console.log('デフォルト: examine2への遷移');
  return `../examine2?id=${encodeURIComponent(userId)}`;
}

/**
 * 実験形式変更通知を表示する
 * @param {string} currentExperiment - 現在の実験タイプ ('examine1' または 'examine1_2')
 * @param {string} experimentOrder - 実験順序 ('order1' または 'order2')
 * @param {number} currentScenarioIndex - 現在のシナリオインデックス（0ベース）
 * @param {number} totalScenarios - 総シナリオ数
 * @returns {Promise} - 通知処理の完了を示すPromise
 */
export function showExperimentFormatChangeNotification(currentExperiment, experimentOrder, currentScenarioIndex = 5, totalScenarios = 6) {
  return new Promise((resolve) => {
    try {
      // 6個目のシナリオ（インデックス5）の時のみ通知を表示
      const isLastScenario = currentScenarioIndex === totalScenarios - 1;
      
      // 通知が必要なタイミングかチェック
      const shouldShowNotification = isLastScenario && (
        (experimentOrder === 'order1' && currentExperiment === 'examine1') ||
        (experimentOrder === 'order2' && currentExperiment === 'examine1_2')
      );
      
      if (!shouldShowNotification) {
        resolve();
        return;
      }
      
      // 既に通知が表示されているかチェック
      if (document.getElementById('experiment-format-notification')) {
        resolve();
        return;
      }
      
      // モーダル形式の通知を表示
      const notification = document.createElement('div');
      notification.id = 'experiment-format-notification';
      notification.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.7);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
        font-family: Arial, sans-serif;
      `;
      
      const modal = document.createElement('div');
      modal.style.cssText = `
        background-color: white;
        padding: 30px;
        border-radius: 10px;
        text-align: center;
        max-width: 500px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
      `;
      
      // 次の実験の形式を決定
      const nextExperiment = experimentOrder === 'order1' ? 'examine1_2' : 'examine1';
      const formatDescription = nextExperiment === 'examine1_2' ? 
        '次の実験では、複数の事例を観察した後に評価を行う形式になります。' :
        '次の実験では、1つの事例を観察した後に評価を行う形式になります。';
      
      modal.innerHTML = `
        <h3 style="color: #2c5282; margin-bottom: 20px;">実験形式の変更について</h3>
        <p style="margin-bottom: 20px; line-height: 1.6;">
          これまでの実験お疲れ様でした。<br>
          ${formatDescription}
        </p>
        <p style="margin-bottom: 30px; font-weight: bold; color: #e53e3e;">
          実験の進め方が変わりますので、次のページの説明をよくお読みください。
        </p>
        <button id="notification-ok-btn" style="
          background-color: #2c5282;
          color: white;
          border: none;
          padding: 12px 30px;
          border-radius: 5px;
          font-size: 16px;
          cursor: pointer;
          transition: background-color 0.3s;
        " onmouseover="this.style.backgroundColor='#2a4db7'" onmouseout="this.style.backgroundColor='#2c5282'">
          了解しました
        </button>
      `;
      
      notification.appendChild(modal);
      document.body.appendChild(notification);
      
      // ボタンクリックでモーダルを閉じる
      const okButton = document.getElementById('notification-ok-btn');
      okButton.addEventListener('click', () => {
        document.body.removeChild(notification);
        resolve();
      });
      
      // 自動削除（30秒後）
      setTimeout(() => {
        if (document.body.contains(notification)) {
          document.body.removeChild(notification);
          resolve();
        }
      }, 30000);
      
      console.log(`実験形式変更通知を表示: ${currentExperiment} → ${nextExperiment} (${experimentOrder}), シナリオ: ${currentScenarioIndex + 1}/${totalScenarios}`);
      
    } catch (error) {
      console.error('実験形式変更通知の表示中にエラーが発生しました:', error);
      // エラーが発生しても実験の進行に影響しないようにする
      resolve();
    }
  });
}

/**
 * ユーザーIDの妥当性を検証
 * @param {string} userId - 検証するユーザーID
 * @returns {boolean} IDが有効かどうか
 */
export function validateUserId(userId) {
  if (!userId) return false;
  
  // 基本的な長さチェック（最小3文字、最大50文字）
  if (userId.length < 3 || userId.length > 50) return false;
  
  // 危険な文字の除外（SQLインジェクション、XSS対策）
  const dangerousChars = /[<>'"&=;()|]/;
  if (dangerousChars.test(userId)) return false;
  
  // 制御文字の除外
  if (/[\x00-\x1F\x7F]/.test(userId)) return false;
  
  return true;
}

/**
 * ユーザーIDをサニタイズ
 * @param {string} userId - サニタイズするユーザーID
 * @returns {string} サニタイズされたユーザーID
 */
export function sanitizeUserId(userId) {
  if (!userId) return '';
  
  // 基本的なサニタイズ
  return userId
    .toString()
    .trim()
    .substring(0, 50) // 最大長制限
    .replace(/[<>'"&=;()|]/g, '') // 危険な文字を削除
    .replace(/[\x00-\x1F\x7F]/g, ''); // 制御文字を削除
}