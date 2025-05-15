/**
 * エラー処理とログ記録のためのユーティリティ
 */
class ErrorHandler {
  /**
   * エラーハンドラを初期化する
   */
  constructor(options = {}) {
    this.reportEndpoint = options.reportEndpoint || '/api/report-error';
    this.enableGlobalHandlers = options.enableGlobalHandlers !== false;
    this.logToConsole = options.logToConsole !== false;
    this.maxRetries = options.maxRetries || 3;
    
    if (this.enableGlobalHandlers) {
      this.setupGlobalHandlers();
    }
  }
  
  /**
   * グローバル例外ハンドラを設定する
   */
  setupGlobalHandlers() {
    // 未処理のエラーをキャッチ
    window.addEventListener('error', (event) => {
      this.handleError(event.error || new Error(event.message), {
        type: 'uncaught',
        lineNo: event.lineno,
        fileName: event.filename,
        colNo: event.colno
      });
      return false;
    });
    
    // Promise内の未処理の例外をキャッチ
    window.addEventListener('unhandledrejection', (event) => {
      const error = event.reason instanceof Error ? event.reason : new Error(String(event.reason));
      this.handleError(error, {
        type: 'unhandledrejection'
      });
      return false;
    });
    
    if (this.logToConsole) {
      console.info('グローバルエラーハンドラが設定されました');
    }
  }
  
  /**
   * エラーを処理し、必要に応じて報告する
   */
  async handleError(error, context = {}) {
    const errorInfo = this.extractErrorInfo(error, context);
    
    if (this.logToConsole) {
      console.error('アプリケーションエラー:', errorInfo);
    }
    
    try {
      return await this.reportError(errorInfo);
    } catch (reportError) {
      if (this.logToConsole) {
        console.error('エラーの報告に失敗しました:', reportError);
      }
      return false;
    }
  }
  
  /**
   * エラーオブジェクトから必要な情報を抽出する
   */
  extractErrorInfo(error, additionalContext = {}) {
    let stack = '';
    let message = '';
    let type = 'Unknown';
    
    if (error instanceof Error) {
      message = error.message;
      stack = error.stack || '';
      type = error.name || error.constructor.name;
    } else if (typeof error === 'string') {
      message = error;
      type = 'String';
    } else {
      try {
        message = JSON.stringify(error);
      } catch (e) {
        message = 'Non-serializable error object';
      }
    }
    
    return {
      type,
      message,
      stack,
      timestamp: new Date().toISOString(),
      url: window.location.href,
      context: additionalContext
    };
  }
  
  /**
   * エラーをサーバーに報告する
   */
  async reportError(errorInfo) {
    let retries = 0;
    while (retries < this.maxRetries) {
      try {
        const response = await fetch(this.reportEndpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(errorInfo),
          keepalive: true
        });
        
        if (!response.ok) {
          throw new Error(`エラー報告に失敗しました: ${response.status}`);
        }
        
        return await response.json();
      } catch (error) {
        retries++;
        if (retries >= this.maxRetries) {
          throw error;
        }
        await new Promise(resolve => setTimeout(resolve, 1000 * retries));
      }
    }
  }
  
  /**
   * エラーを手動で記録して報告する
   */
  captureError(error, context = {}, level = 'error') {
    context.level = level;
    context.captured = true;
    return this.handleError(error, context);
  }
}

// グローバルインスタンスを作成
window.errorHandler = new ErrorHandler({
  enableGlobalHandlers: true,
  logToConsole: true
});

// 簡素化されたグローバル関数
window.reportError = function(message, error, context) {
  return window.errorHandler.captureError(error || message, context || {});
};