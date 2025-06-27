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
  const mon = (now.getMonth() + 1).toString().padStart(2, '0');
  const day = now.getDate().toString().padStart(2, '0');
  const hour = now.getHours().toString().padStart(2, '0');
  const min = now.getMinutes().toString().padStart(2, '0');
  const sec = now.getSeconds().toString().padStart(2, '0');
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
 * @param {boolean} hideParams - URLパラメータを隠すかどうか（デフォルト: true）
 * @returns {string|null} 検証済みのユーザーIDまたはnull
 */
export function getUserIdFromUrl(hideParams = true) {
  const urlParams = new URLSearchParams(window.location.search);
  const rawId = urlParams.get('id');
  
  if (!rawId) return null;
  
  // ユーザーIDをサニタイズ
  const sanitizedId = sanitizeUserId(rawId);
  
  // サニタイズ後のIDを検証
  if (!validateUserId(sanitizedId)) {
    console.warn('Invalid user ID detected from URL:', rawId);
    return null;
  }
  
  // end.html以外でURLパラメータを隠す（但し、IDを取得した後）
  if (hideParams && !window.location.pathname.includes('/end')) {
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
  
  // URLからのID取得を試みる（URLパラメータはまだ隠さない）
  if (urlParam) {
    const urlId = getUserIdFromUrl(false); // URLパラメータは隠さずにIDを取得
    if (urlId) {
      const savedId = saveUserId(urlId, persistent);
      if (savedId) {
        // IDの保存に成功したら、URLパラメータを隠す
        try {
          if (!window.location.pathname.includes('/end')) {
            const cleanUrl = window.location.protocol + '//' + 
                            window.location.host + 
                            window.location.pathname;
            window.history.replaceState({}, document.title, cleanUrl);
            console.log('getOrCreateUserId: URLパラメータを非表示にしました');
          }
        } catch (error) {
          console.error('getOrCreateUserId: URLパラメータの非表示に失敗しました:', error);
        }
        return savedId;
      }
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
 * @returns {Promise<string>} - 'order1'（eXaMinE1 → eXaM1nE_2）または'order2'（eXaM1nE_2 → eXaMinE1）
 */
export async function getExperimentOrder(userId, reallocate = false) {
  if (!userId) {
    console.warn('getExperimentOrder: ユーザーIDが指定されていないため、デフォルトの順序（order1）を使用します');
    return Promise.resolve('order1');
  }
  
  try {
    // サーバーから実験経路を取得
    // reallocateパラメータを明示的に設定
    const url = `/getExperimentPath?user_id=${encodeURIComponent(userId)}&reallocate=${reallocate}`;
    console.log(`getExperimentOrder: 実験経路を取得中: ユーザーID=${userId}, reallocate=${reallocate}`);
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`サーバーエラー: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('getExperimentOrder: 実験経路取得結果:', data);

    const pathType = data.pathType || 'order1';
    // --- ここでlocalStorageにorderを保存 ---
    try {
      if (userId && pathType) {
        localStorage.setItem(`experiment_order_${userId}`, pathType);
      }
    } catch (e) {
      // 保存失敗時は何もしない
    }
    console.log(`getExperimentOrder: 返却する実験順序: ${pathType} (ユーザーID: ${userId})`);

    return pathType;
  } catch (error) {
    console.error('getExperimentOrder: 実験経路の取得に失敗しました:', error);
    // エラー時はデフォルトの順序を返す
    console.log('getExperimentOrder: エラーのためデフォルト順序（order1）を使用');
    return 'order1';
  }
}

/**
 * 実験順序に基づいて次のページURLを取得
 * @param {string} currentPage - 現在のページ名（'eXaMinE1'または'eXaM1nE_2'）
 * @param {string} userId - ユーザーID
 * @returns {Promise<string>} - 次のページへのURLを含むPromise
 */
export async function getNextPageUrl(currentPage, userId) {
  if (!userId) {
    console.error('getNextPageUrl: ユーザーIDが指定されていません');
    return `../Ex2?id=${encodeURIComponent('unknown')}`;
  }
  
  // reallocate=falseを明示的に設定して既存の経路を尊重するようにする
  const experimentOrder = await getExperimentOrder(userId, false);
  
  console.log(`getNextPageUrl: currentPage=${currentPage}, experimentOrder=${experimentOrder}, userId=${userId}`);
  
  if (currentPage === 'eXaMinE1') {
    if (experimentOrder === 'order1') {
      // order1: eXaMinE1 → eXaM1nE_2 → Ex2
      console.log('order1: eXaMinE1 → eXaM1nE_2への遷移');
      return `../eXaM1nE_2?id=${encodeURIComponent(userId)}`;
    } else if (experimentOrder === 'order2') {
      // order2: eXaM1nE_2 → eXaMinE1 → Ex2
      console.log('order2: eXaMinE1 → Ex2への遷移（eXaMinE1が最後）');
      return `../Ex2?id=${encodeURIComponent(userId)}`;
    } else {
      console.warn(`getNextPageUrl: 不明な実験順序: ${experimentOrder}, デフォルトでeXaM1nE_2へ遷移`);
      return `../eXaM1nE_2?id=${encodeURIComponent(userId)}`;
    }
  } else if (currentPage === 'eXaM1nE_2') {
    if (experimentOrder === 'order1') {
      // order1: eXaMinE1 → eXaM1nE_2 → Ex2（eXaM1nE_2が最後）
      console.log('order1: eXaM1nE_2 → Ex2への遷移（eXaM1nE_2が最後）');
      return `../Ex2?id=${encodeURIComponent(userId)}`;
    } else if (experimentOrder === 'order2') {
      // order2: eXaM1nE_2 → eXaMinE1 → Ex2
      console.log('order2: eXaM1nE_2 → eXaMinE1への遷移');
      return `../eXaMinE1?id=${encodeURIComponent(userId)}`;
    } else {
      console.warn(`getNextPageUrl: 不明な実験順序: ${experimentOrder}, デフォルトでEx2へ遷移`);
      return `../Ex2?id=${encodeURIComponent(userId)}`;
    }
  } else {
    console.warn(`getNextPageUrl: 不明な現在ページ: ${currentPage}, デフォルトでEx2へ遷移`);
  }
  // デフォルトはEx2
  console.log('デフォルト: Ex2への遷移');
  return `../Ex2?id=${encodeURIComponent(userId)}`;
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

/**
 * 実験形式変更通知機能
 * 1つ目のシナリオで全チェックボックス完了時に次の実験形式について通知
 * @param {string} userId - ユーザーID
 * @param {number} currentIndex - 現在のシナリオインデックス
 * @param {string} currentPage - 現在のページ名（'eXaMinE1'または'eXaM1nE_2'）
 * @returns {Promise<void>}
 */
export async function checkAndShowFormatChangeNotification(userId, currentIndex, currentPage) {
  try {
    // 1つ目のシナリオでない場合は処理しない
    if (currentIndex !== 0) {
      console.log('checkAndShowFormatChangeNotification: 1つ目のシナリオではないため通知をスキップ');
      return;
    }
    
    // 通知フラグを確認（一度だけ表示）
    const notificationKey = `format_change_notification_${userId}_${currentPage}_scenario_${currentIndex}`;
    const hasShownNotification = sessionStorage.getItem(notificationKey);
    if (hasShownNotification) {
      console.log(`checkAndShowFormatChangeNotification: 既に通知済みのため表示をスキップ (キー: ${notificationKey})`);
      return;
    }
    
    // 実験順序を取得
    const experimentOrder = await getExperimentOrder(userId, false);
    console.log(`checkAndShowFormatChangeNotification: 実験順序=${experimentOrder}, 現在のページ=${currentPage}`);
    
    let shouldShowNotification = false;
    let nextExperimentType = '';
    
    // --- 通知条件ロジック修正 ---
    if (experimentOrder === 'order1' && currentPage === 'eXaM1nE_2') {
      // order1: eXaMinE1 → eXaM1nE_2 → Ex2
      // eXaM1nE_2の1つ目のシナリオで通知（次はEx2）
      shouldShowNotification = true;
      nextExperimentType = 'Ex2';
    } else if (experimentOrder === 'order2' && currentPage === 'eXaMinE1') {
      // order2: eXaM1nE_2 → eXaMinE1 → Ex2
      // eXaMinE1の1つ目のシナリオで通知（次はEx2）
      shouldShowNotification = true;
      nextExperimentType = 'Ex2';
    }
    // order2 で eXaM1nE_2 の1つ目では通知しない

    if (shouldShowNotification) {
      // 通知を表示
      const notificationMessage = `
        📢 次の実験では形式が変更されます

        次のページから、実験の形式や表示方法が変わりますが、引き続きご協力をお願いいたします。
        このメッセージは一度だけ表示されます。
      `.trim();
      
      console.log('checkAndShowFormatChangeNotification: 実験形式変更通知を表示');
      console.log(`checkAndShowFormatChangeNotification: 通知内容 - 次の実験: ${nextExperimentType}`);
      
      // モーダルスタイルの通知を表示
      showModalNotification('実験形式変更のお知らせ', notificationMessage);
      sessionStorage.setItem(notificationKey, 'true');
      console.log(`checkAndShowFormatChangeNotification: 通知済みフラグを設定: ${notificationKey}`);
    } else {
      console.log(`checkAndShowFormatChangeNotification: 通知条件に該当しないため表示をスキップ (実験順序: ${experimentOrder}, ページ: ${currentPage})`);
    }
    
  } catch (error) {
    console.error('checkAndShowFormatChangeNotification: エラーが発生しました:', error);
  }
}

/**
 * モーダル通知を表示する関数
 * @param {string} title - 通知のタイトル
 * @param {string} message - 通知メッセージ
 */
export function showModalNotification(title, message) {
  try {
    // 既存のモーダルがあれば削除
    const existingModal = document.getElementById('format-change-modal');
    if (existingModal) {
      existingModal.remove();
    }
    
    // モーダル要素を作成
    const modal = document.createElement('div');
    modal.id = 'format-change-modal';
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0, 0, 0, 0.5);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 10000;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    `;
    
    // モーダルコンテンツを作成
    const modalContent = document.createElement('div');
    modalContent.style.cssText = `
      background: white;
      padding: 30px;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
      max-width: 500px;
      width: 90%;
      text-align: center;
      position: relative;
    `;
    
    // タイトル
    const titleElement = document.createElement('h3');
    titleElement.textContent = title;
    titleElement.style.cssText = `
      margin: 0 0 20px 0;
      color: #333;
      font-size: 20px;
      font-weight: bold;
    `;
    
    // メッセージ
    const messageElement = document.createElement('p');
    messageElement.textContent = message.trim();
    messageElement.style.cssText = `
      margin: 0 0 25px 0;
      color: #555;
      line-height: 1.6;
      font-size: 14px;
      white-space: pre-line;
    `;
    
    // 閉じるボタン
    const closeButton = document.createElement('button');
    closeButton.textContent = '理解しました';
    closeButton.style.cssText = `
      background: #007bff;
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 5px;
      cursor: pointer;
      font-size: 14px;
      font-weight: bold;
    `;
    
    // ボタンホバーエフェクト
    closeButton.addEventListener('mouseenter', () => {
      closeButton.style.background = '#0056b3';
    });
    closeButton.addEventListener('mouseleave', () => {
      closeButton.style.background = '#007bff';
    });
    
    // 閉じるボタンのクリックイベント
    closeButton.addEventListener('click', () => {
      modal.remove();
    });
    
    // モーダルの外側クリックで閉じる
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    });
    
    // ESCキーで閉じる
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        modal.remove();
        document.removeEventListener('keydown', handleEscape);
      }
    };
    document.addEventListener('keydown', handleEscape);
    
    // 要素を組み立て
    modalContent.appendChild(titleElement);
    modalContent.appendChild(messageElement);
    modalContent.appendChild(closeButton);
    modal.appendChild(modalContent);
    
    // DOMに追加
    document.body.appendChild(modal);
    
    // アニメーション効果
    modal.style.opacity = '0';
    setTimeout(() => {
      modal.style.transition = 'opacity 0.3s ease-in-out';
      modal.style.opacity = '1';
    }, 10);
    
    console.log('showModalNotification: モーダル通知を表示しました');
    
  } catch (error) {
    console.error('showModalNotification: モーダル表示でエラーが発生しました:', error);
    // フォールバック: 通常のアラート
    alert(`${title}\n\n${message}`);
  }
}

/**
 * 進捗トークンをlocalStorageで管理
 */
export function saveProgressToken(token) {
  if (token) localStorage.setItem('exp_progress_token', token);
}
export function getProgressToken() {
  return localStorage.getItem('exp_progress_token');
}
export function clearProgressToken() {
  localStorage.removeItem('exp_progress_token');
}