/**
 * ajax-utils.js - Ajax通信のための共通ユーティリティ
 */
import uiManager from './ui-manager.js';

// デフォルト設定
const defaultConfig = {
  timeout: 30000,
  retryCount: 3,
  retryDelay: 1000,
  showLoadingUI: true
};

/**
 * 共通のAjaxエラーハンドリング
 */
export function handleAjaxError(error, customMessage = '', onError = null) {
  const errorMessage = customMessage || 'サーバーとの通信中にエラーが発生しました。';
  console.error(errorMessage, error);
  
  // UIエラー表示
  if (uiManager && typeof uiManager.showErrorMessage === 'function') {
    uiManager.showErrorMessage(errorMessage);
  }
  
  // エラーコールバックがあれば実行
  if (onError && typeof onError === 'function') {
    onError(error);
  }
}

/**
 * AJAXリクエストを実行する（再試行機能付き）
 */
export function fetchWithRetry(options, attempt = 0) {
  const settings = { ...defaultConfig, ...options };
  const { url, retryCount, retryDelay, showLoadingUI } = settings;
  
  // ローディング表示
  if (showLoadingUI && uiManager && typeof uiManager.showLoading === 'function') {
    uiManager.showLoading(true);
  }
  
  return new Promise((resolve, reject) => {
    $.ajax({
      ...settings,
      success: (data) => {
        if (showLoadingUI && uiManager && typeof uiManager.showLoading === 'function') {
          uiManager.showLoading(false);
        }
        resolve(data);
      },
      error: (jqXHR, textStatus, errorThrown) => {
        const error = new Error(`${textStatus}: ${errorThrown || '不明なエラー'}`);
        
        // タイムアウトまたはネットワークエラーで再試行
        if ((textStatus === 'timeout' || textStatus === 'error') && attempt < retryCount) {
          // 遅延して再試行
          setTimeout(() => {
            fetchWithRetry(settings, attempt + 1)
              .then(resolve)
              .catch(reject);
          }, retryDelay);
        } else {
          if (showLoadingUI && uiManager && typeof uiManager.showLoading === 'function') {
            uiManager.showLoading(false);
          }
          reject(error);
        }
      }
    });
  });
}

/**
 * JSONファイルを非同期で読み込む
 */
export function fetchJson(filename, options = {}) {
  const { 
    useCache = true, 
    cacheTTL = 3600000, // 1時間
    ...otherOptions 
  } = options;
  
  // キャッシュが不要な場合は直接取得
  if (!useCache) {
    return fetchJsonDirectly(filename, otherOptions);
  }
  
  const cacheKey = `json_cache_${filename}`;
  
  // キャッシュを確認
  const cachedData = localStorage.getItem(cacheKey);
  if (cachedData) {
    try {
      const { timestamp, data } = JSON.parse(cachedData);
      
      // キャッシュが有効か確認
      if (Date.now() - timestamp < cacheTTL) {
        return Promise.resolve(data);
      }
    } catch (e) {
      // キャッシュ読み込みエラーは無視して続行
    }
  }
  
  // キャッシュがない、または期限切れの場合は新規取得
  return fetchJsonDirectly(filename, otherOptions).then(data => {
    // データをキャッシュに保存
    try {
      const cacheData = {
        timestamp: Date.now(),
        data: data
      };
      localStorage.setItem(cacheKey, JSON.stringify(cacheData));
    } catch (e) {
      // キャッシュ保存エラーは無視して続行
    }
    return data;
  });
}

/**
 * キャッシュを使用せずにJSONファイルを直接取得する内部関数
 */
function fetchJsonDirectly(filename, options = {}) {
  return fetchWithRetry({
    type: 'GET',
    url: filename,
    dataType: 'json',
    ...options
  });
}

/**
 * POSTデータをサーバーに送信
 */
export function postData(url, data, options = {}) {
  return fetchWithRetry({
    type: 'POST',
    url: url,
    data: data,
    ...options
  });
}