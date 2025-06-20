/**
 * セキュリティ強化版URLクリーナー
 * より堅牢なセキュリティ対策を実装
 */

/**
 * セキュアなURLパラメータ処理
 * @param {string} paramName - 取得したいパラメータ名
 * @returns {string|null} - 検証済みパラメータの値
 */
export function getAndHideUrlParameterSecure(paramName) {
    try {
        // URLパラメータを取得
        const urlParams = new URLSearchParams(window.location.search);
        const rawValue = urlParams.get(paramName);
        
        if (!rawValue) {
            console.warn('URLパラメータが見つかりません:', paramName);
            return null;
        }
        
        // 基本的なセキュリティチェック
        const sanitizedValue = sanitizeValue(rawValue);
        if (!validateValue(sanitizedValue)) {
            console.error('無効なパラメータ値が検出されました');
            // セキュリティログを記録
            logSecurityIncident('invalid_parameter', {
                param: paramName,
                value: rawValue.substring(0, 20) + '...', // 部分的にログ
                timestamp: new Date().toISOString()
            });
            return null;
        }
        
        // URLパラメータを即座に除去（end.html以外）
        if (!isEndPage()) {
            clearUrlHistory();
        }
        
        return sanitizedValue;
        
    } catch (error) {
        console.error('URLパラメータ処理中にエラーが発生:', error);
        logSecurityIncident('parameter_processing_error', {
            param: paramName,
            error: error.message,
            timestamp: new Date().toISOString()
        });
        return null;
    }
}

/**
 * 値のサニタイズ
 */
function sanitizeValue(value) {
    if (!value || typeof value !== 'string') return '';
    
    return value
        .trim()
        .substring(0, 50) // 最大長制限
        .replace(/[<>'"&=;()|]/g, '') // 危険な文字を削除
        .replace(/[\x00-\x1F\x7F]/g, '') // 制御文字を削除
        .replace(/javascript:/gi, '') // JavaScriptプロトコルを削除
        .replace(/data:/gi, ''); // dataプロトコルを削除
}

/**
 * 値の検証
 */
function validateValue(value) {
    if (!value || typeof value !== 'string') return false;
    
    // 基本的な長さチェック
    if (value.length < 3 || value.length > 50) return false;
    
    // 危険なパターンをチェック
    const dangerousPatterns = [
        /<script/i,
        /javascript:/i,
        /data:/i,
        /vbscript:/i,
        /on\w+\s*=/i, // イベントハンドラー
        /expression\s*\(/i // CSS expression
    ];
    
    return !dangerousPatterns.some(pattern => pattern.test(value));
}

/**
 * URLとブラウザ履歴を安全にクリア
 */
function clearUrlHistory() {
    try {
        // 現在のURLからパラメータを除去
        const cleanUrl = `${window.location.protocol}//${window.location.host}${window.location.pathname}`;
        
        // 履歴を安全に置き換え
        window.history.replaceState(
            { cleared: true, timestamp: Date.now() }, 
            document.title, 
            cleanUrl
        );
        
        // 追加のセキュリティ対策：リファラーをクリア
        if (document.referrer && document.referrer.includes('?')) {
            window.history.replaceState(
                { cleared: true, timestamp: Date.now() }, 
                document.title, 
                cleanUrl
            );
        }
        
        console.log('URLとブラウザ履歴を安全にクリアしました');
        
    } catch (error) {
        console.error('URL履歴のクリアに失敗:', error);
        logSecurityIncident('history_clear_failed', {
            error: error.message,
            timestamp: new Date().toISOString()
        });
    }
}

/**
 * セキュリティインシデントのログ記録
 */
function logSecurityIncident(type, details) {
    try {
        // セキュリティログをサーバーに送信
        fetch('/api/security/log', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Security-Event': 'true'
            },
            body: JSON.stringify({
                type: type,
                details: details,
                userAgent: navigator.userAgent,
                timestamp: new Date().toISOString(),
                url: window.location.pathname
            })
        }).catch(err => {
            // サーバーログが失敗してもクライアント側に保存
            console.error('セキュリティログの送信に失敗:', err);
            storeSecurityLogLocally(type, details);
        });
        
    } catch (error) {
        console.error('セキュリティログの記録に失敗:', error);
    }
}

/**
 * ローカルセキュリティログ保存
 */
function storeSecurityLogLocally(type, details) {
    try {
        const logEntry = {
            type: type,
            details: details,
            timestamp: new Date().toISOString()
        };
        
        const existingLogs = JSON.parse(sessionStorage.getItem('security_logs') || '[]');
        existingLogs.push(logEntry);
        
        // ログは最大50件まで保持
        if (existingLogs.length > 50) {
            existingLogs.splice(0, existingLogs.length - 50);
        }
        
        sessionStorage.setItem('security_logs', JSON.stringify(existingLogs));
        
    } catch (error) {
        console.error('ローカルセキュリティログの保存に失敗:', error);
    }
}

/**
 * end.htmlページかどうかを判定
 */
function isEndPage() {
    return window.location.pathname.includes('/end');
}

/**
 * セキュリティ状態の監視
 */
export function initSecurityMonitoring() {
    // ページロード時の自動チェック
    document.addEventListener('DOMContentLoaded', () => {
        checkSecurityState();
    });
    
    // URL変更の監視
    let lastUrl = window.location.href;
    new MutationObserver(() => {
        const currentUrl = window.location.href;
        if (currentUrl !== lastUrl) {
            lastUrl = currentUrl;
            checkSecurityState();
        }
    }).observe(document.body, { childList: true, subtree: true });
}

/**
 * セキュリティ状態の確認
 */
function checkSecurityState() {
    // URLにまだパラメータが残っている場合の警告
    if (window.location.search && !isEndPage()) {
        console.warn('URLパラメータが残っています。セキュリティリスクの可能性があります。');
        logSecurityIncident('url_parameters_remaining', {
            url: window.location.href,
            timestamp: new Date().toISOString()
        });
    }
    
    // 開発者ツールの検出（簡易版）
    let devtools = { open: false };
    setInterval(() => {
        const before = Date.now();
        console.log('%c', 'color: transparent');
        const after = Date.now();
        
        if (after - before > 100) {
            if (!devtools.open) {
                devtools.open = true;
                logSecurityIncident('devtools_opened', {
                    timestamp: new Date().toISOString()
                });
            }
        } else {
            devtools.open = false;
        }
    }, 1000);
}

// セキュリティ監視を自動開始
if (typeof window !== 'undefined') {
    initSecurityMonitoring();
}
