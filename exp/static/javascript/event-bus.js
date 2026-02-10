/**
 * event-bus.js - イベント管理システム（Pub-Subパターン）
 * 複数のモジュール間でイベントを通知・購読する仕組み
 */

/**
 * イベントバスクラス - イベントのemit/onを管理
 */
export class EventBus {
  constructor() {
    this.listeners = new Map();  // イベント名 → リスナー配列のマップ
    this.debug = false;          // デバッグモード
  }

  /**
   * イベントリスナーを登録
   * @param {string} event - イベント名
   * @param {Function} callback - コールバック関数
   * @param {Object} context - コールバックのthisコンテキスト
   * @returns {Object} 登録解除用のハンドル
   */
  on(event, callback, context = null) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    
    const handler = { callback, context };
    this.listeners.get(event).push(handler);
    
    // 登録解除用のハンドルを返す
    return {
      remove: () => this.off(event, callback, context)
    };
  }

  /**
   * 一度だけ実行されるリスナーを登録
   */
  once(event, callback, context = null) {
    const onceWrapper = (...args) => {
      this.off(event, onceWrapper, context);
      return callback.apply(context, args);
    };
    
    return this.on(event, onceWrapper, context);
  }

  /**
   * イベントリスナーを解除
   */
  off(event, callback, context = null) {
    if (!this.listeners.has(event)) return;
    
    if (!callback) {
      this.listeners.delete(event);
      return;
    }
    
    const handlers = this.listeners.get(event);
    const remainingHandlers = handlers.filter(handler => 
      handler.callback !== callback || handler.context !== context
    );
    
    if (remainingHandlers.length === 0) {
      this.listeners.delete(event);
    } else {
      this.listeners.set(event, remainingHandlers);
    }
  }

  /**
   * イベントを発火し、登録されたリスナーを実行
   */
  emit(event, ...args) {
    if (!this.listeners.has(event)) {
      if (this.debug) {
        console.log(`[EventBus] イベント '${event}' のリスナーは登録されていません`);
      }
      return false;
    }
    
    if (this.debug) {
      console.log(`[EventBus] イベント '${event}' を発火:`, ...args);
    }
    
    const handlers = this.listeners.get(event);
    handlers.forEach(handler => {
      try {
        handler.callback.apply(handler.context, args);
      } catch (error) {
        console.error(`[EventBus] イベント '${event}' の処理中にエラー:`, error);
      }
    });
    
    return true;
  }

  clear() {
    this.listeners.clear();
  }

  setDebug(enabled) {
    this.debug = enabled;
  }
  
  listenerCount(event) {
    return this.listeners.has(event) ? this.listeners.get(event).length : 0;
  }
  
  eventNames() {
    return Array.from(this.listeners.keys());
  }
}

const eventBus = new EventBus();

export default eventBus;