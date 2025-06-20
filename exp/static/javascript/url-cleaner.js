/**
 * URLからパラメータを隠すためのユーティリティ
 * end.html以外でURLパラメータを非表示にする
 */

/**
 * URLからパラメータを取得してからアドレスバーから除去
 * @param {string} paramName - 取得したいパラメータ名
 * @returns {string|null} - パラメータの値
 */
export function getAndHideUrlParameter(paramName) {
    // URLSearchParamsでパラメータを取得
    const urlParams = new URLSearchParams(window.location.search);
    const paramValue = urlParams.get(paramName);
    
    // アドレスバーからパラメータを除去（end.htmlの場合は除く）
    if (!window.location.pathname.includes('/end')) {
        hideUrlParameters();
    }
    
    return paramValue;
}

/**
 * URLからすべてのパラメータを除去
 */
export function hideUrlParameters() {
    try {
        // 現在のURLからパラメータ部分を除去
        const cleanUrl = window.location.protocol + '//' + 
                        window.location.host + 
                        window.location.pathname;
        
        // history.replaceStateでアドレスバーのURLを変更（履歴は残さない）
        window.history.replaceState({}, document.title, cleanUrl);
        
        console.log('URLパラメータを非表示にしました:', cleanUrl);
    } catch (error) {
        console.error('URLパラメータの非表示に失敗しました:', error);
    }
}

/**
 * 特定のパラメータのみを除去
 * @param {string[]} paramNames - 除去したいパラメータ名の配列
 */
export function hideSpecificParameters(paramNames) {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        
        // 指定されたパラメータを削除
        paramNames.forEach(paramName => {
            urlParams.delete(paramName);
        });
        
        // 新しいURLを構築
        const baseUrl = window.location.protocol + '//' + 
                       window.location.host + 
                       window.location.pathname;
        
        const remainingParams = urlParams.toString();
        const newUrl = remainingParams ? `${baseUrl}?${remainingParams}` : baseUrl;
        
        // URLを更新
        window.history.replaceState({}, document.title, newUrl);
        
        console.log('指定されたパラメータを非表示にしました:', newUrl);
    } catch (error) {
        console.error('パラメータの非表示に失敗しました:', error);
    }
}

/**
 * end.htmlページかどうかを判定
 * @returns {boolean} - end.htmlページの場合true
 */
export function isEndPage() {
    return window.location.pathname.includes('/end');
}
