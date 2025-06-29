/**
 * UI要素生成のファクトリーパターン実装
 */
import eventBus from './event-bus.js';

/**
 * UI要素の基本クラス
 */
export class UIElement {
  constructor(id, options = {}) {
    this.id = id;
    this.options = options;
    this.element = null;
  }

  /**
   * 要素を生成（サブクラスで実装）
   */
  create() {
    throw new Error('サブクラスで実装する必要があります');
  }

  /**
   * 要素をコンテナに追加
   */
  appendTo(container) {
    if (!this.element) {
      this.element = this.create();
    }
    
    const containerElement = typeof container === 'string' 
      ? document.getElementById(container) 
      : container;
      
    if (containerElement) {
      containerElement.appendChild(this.element);
    }
    
    return this.element;
  }

  getValue() {
    return this.element ? this.element.value : null;
  }

  setValue(value) {
    if (this.element) {
      this.element.value = value;
    }
  }

  setVisible(visible) {
    if (this.element) {
      this.element.style.display = visible ? '' : 'none';
    }
  }

  setEnabled(enabled) {
    if (this.element) {
      this.element.disabled = !enabled;
    }
  }
}

/**
 * テキスト入力要素
 */
export class TextInput extends UIElement {
  /**
   * テキスト入力要素を作成
   * @returns {HTMLElement} 入力要素
   */
  create() {
    const input = document.createElement('input');
    input.type = 'text';
    input.id = this.id;
    input.name = this.options.name || this.id;
    
    if (this.options.placeholder) {
      input.placeholder = this.options.placeholder;
    }
    
    if (this.options.className) {
      input.className = this.options.className;
    }
    
    if (this.options.value) {
      input.value = this.options.value;
    }
    
    if (this.options.required) {
      input.required = true;
    }
    
    // イベントリスナーの設定
    if (this.options.onChange) {
      input.addEventListener('input', (e) => {
        this.options.onChange(e.target.value, e);
        // 状態変更を通知
        eventBus.emit('input:change', {
          id: this.id,
          value: e.target.value,
          element: input
        });
      });
    }
    
    this.element = input;
    return input;
  }
}

/**
 * 数値入力要素
 */
export class NumberInput extends UIElement {
  /**
   * 数値入力要素を作成
   * @returns {HTMLElement} 入力要素
   */
  create() {
    const input = document.createElement('input');
    input.type = 'number';
    input.id = this.id;
    input.name = this.options.name || this.id;
    
    if (this.options.min !== undefined) {
      input.min = this.options.min;
    }
    
    if (this.options.max !== undefined) {
      input.max = this.options.max;
    }
    
    if (this.options.step !== undefined) {
      input.step = this.options.step;
    }
    
    if (this.options.placeholder) {
      input.placeholder = this.options.placeholder;
    }
    
    if (this.options.className) {
      input.className = this.options.className;
    }
    
    if (this.options.value !== undefined) {
      input.value = this.options.value;
    }
    
    if (this.options.required) {
      input.required = true;
    }
    
    // イベントリスナーの設定
    if (this.options.onChange) {
      input.addEventListener('input', (e) => {
        this.options.onChange(parseFloat(e.target.value), e);
        // 状態変更を通知
        eventBus.emit('input:change', {
          id: this.id,
          value: parseFloat(e.target.value),
          element: input
        });
      });
    }
    
    this.element = input;
    return input;
  }
}

/**
 * スライダー（レンジ）入力要素
 */
export class SliderInput extends UIElement {
  /**
   * スライダー入力要素を作成
   * @returns {HTMLElement} 入力要素
   */
  create() {
    const container = document.createElement('div');
    container.id = `${this.id}-container`;
    container.className = this.options.containerClass || 'slider-container';
    
    // スライダー要素
    const slider = document.createElement('input');
    slider.type = 'range';
    slider.id = this.id;
    slider.name = this.options.name || this.id;
    slider.min = this.options.min !== undefined ? this.options.min : -100;
    slider.max = this.options.max !== undefined ? this.options.max : 100;
    slider.value = this.options.value !== undefined ? this.options.value : 0;
    slider.step = this.options.step !== undefined ? this.options.step : 1;
    
    if (this.options.className) {
      slider.className = this.options.className;
    }
    
    // ラベル要素（スライダーの上部）
    if (this.options.labels) {
      const labelsDiv = document.createElement('div');
      labelsDiv.className = 'slider-labels';
      
      // 最小値ラベル
      const minLabel = document.createElement('span');
      minLabel.textContent = `${slider.min}：${this.options.labels.min || ''}`;
      minLabel.className = 'slider-label-min';
      labelsDiv.appendChild(minLabel);
      
      // 0ラベル（中央）
      if (this.options.labels.zero !== undefined) {
        const zeroLabel = document.createElement('span');
        zeroLabel.textContent = `0：${this.options.labels.zero}`;
        zeroLabel.className = 'slider-label-zero';
        labelsDiv.appendChild(zeroLabel);
      }
      
      // 最大値ラベル
      const maxLabel = document.createElement('span');
      maxLabel.textContent = `${slider.max}：${this.options.labels.max || ''}`;
      maxLabel.className = 'slider-label-max';
      labelsDiv.appendChild(maxLabel);
      
      container.appendChild(labelsDiv);
    }
    
    // スライダー要素を追加
    container.appendChild(slider);
    
    // 現在値表示エリア（スライダーの下部）
    if (this.options.showValue !== false) {
      const valueContainer = document.createElement('div');
      valueContainer.className = 'slider-value-container';
      
      const valueDisplay = document.createElement('span');
      valueDisplay.id = `${this.id}-value`;
      valueDisplay.textContent = slider.value;
      
      valueContainer.appendChild(valueDisplay);
      container.appendChild(valueContainer);
    }
    
    // イベントリスナーの設定
    slider.addEventListener('input', (e) => {
      const value = parseFloat(e.target.value);
      
      // 値表示を更新
      if (this.options.showValue !== false) {
        document.getElementById(`${this.id}-value`).textContent = value;
      }
      
      // コールバック実行
      if (this.options.onChange) {
        this.options.onChange(value, e);
      }
      
      // 状態変更を通知
      eventBus.emit('slider:change', {
        id: this.id,
        value: value,
        element: slider
      });
    });
    
    // 一定時間後にスライダーを有効化する機能
    if (this.options.enableAfter) {
      slider.disabled = true;
      
      // 待機メッセージがある場合は表示
      if (this.options.waitMessage) {
        const waitMsg = document.createElement('div');
        waitMsg.id = `${this.id}-wait-message`;
        waitMsg.className = 'slider-wait-message';
        waitMsg.textContent = this.options.waitMessage;
        container.appendChild(waitMsg);
      }
      
      setTimeout(() => {
        slider.disabled = false;
        
        // 待機メッセージがあれば非表示に
        const waitMsg = document.getElementById(`${this.id}-wait-message`);
        if (waitMsg) {
          waitMsg.style.display = 'none';
        }
        
        // 有効化イベント発火
        eventBus.emit('slider:enabled', {
          id: this.id,
          element: slider
        });
      }, this.options.enableAfter);
    }
    
    this.element = container;
    return container;
  }
  
  /**
   * スライダー値を取得
   * @returns {number} スライダーの現在値
   */
  getValue() {
    if (this.element) {
      const slider = this.element.querySelector('input[type="range"]');
      return slider ? parseFloat(slider.value) : null;
    }
    return null;
  }
  
  /**
   * スライダー値を設定
   * @param {number} value - 設定する値
   */
  setValue(value) {
    if (this.element) {
      const slider = this.element.querySelector('input[type="range"]');
      if (slider) {
        slider.value = value;
        
        // 値表示も更新
        const valueDisplay = document.getElementById(`${this.id}-value`);
        if (valueDisplay) {
          valueDisplay.textContent = value;
        }
      }
    }
  }
}

/**
 * チェックボックス要素
 */
export class Checkbox extends UIElement {
  /**
   * チェックボックス要素を作成
   * @returns {HTMLElement} チェックボックス要素
   */
  create() {
    const container = document.createElement('div');
    container.className = this.options.containerClass || 'checkbox-container';
    
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.id = this.id;
    checkbox.name = this.options.name || this.id;
    checkbox.value = this.options.value || 'on';
    
    if (this.options.checked) {
      checkbox.checked = true;
    }
    
    if (this.options.className) {
      checkbox.className = this.options.className;
    }
    
    if (this.options.required) {
      checkbox.required = true;
    }
    
    // ラベルがあれば追加
    if (this.options.label) {
      const label = document.createElement('label');
      label.htmlFor = this.id;
      
      if (this.options.labelHtml) {
        label.innerHTML = this.options.label;
      } else {
        label.textContent = this.options.label;
      }
      
      if (this.options.labelClass) {
        label.className = this.options.labelClass;
      }
      
      container.appendChild(checkbox);
      container.appendChild(label);
    } else {
      container.appendChild(checkbox);
    }
    
    // イベントリスナーの設定
    checkbox.addEventListener('change', (e) => {
      if (this.options.onChange) {
        this.options.onChange(e.target.checked, e);
      }
      
      // 状態変更を通知
      eventBus.emit('checkbox:change', {
        id: this.id,
        checked: e.target.checked,
        element: checkbox
      });
    });
    
    this.element = container;
    return container;
  }
  
  /**
   * チェック状態を取得
   * @returns {boolean} チェックされている場合はtrue
   */
  getValue() {
    if (this.element) {
      const checkbox = this.element.querySelector('input[type="checkbox"]');
      return checkbox ? checkbox.checked : false;
    }
    return false;
  }
  
  /**
   * チェック状態を設定
   * @param {boolean} checked - チェックする場合はtrue
   */
  setValue(checked) {
    if (this.element) {
      const checkbox = this.element.querySelector('input[type="checkbox"]');
      if (checkbox) {
        checkbox.checked = !!checked;
      }
    }
  }
}

/**
 * ラジオボタングループ要素
 */
export class RadioGroup extends UIElement {
  /**
   * ラジオボタングループを作成
   * @returns {HTMLElement} ラジオボタングループ要素
   */
  create() {
    const container = document.createElement('div');
    container.id = `${this.id}-container`;
    container.className = this.options.containerClass || 'radio-group';
    
    if (!this.options.options || !Array.isArray(this.options.options)) {
      console.error('RadioGroupには options 配列が必要です');
      return container;
    }
    
    // 各オプションに対してラジオボタンを作成
    this.options.options.forEach((option, index) => {
      const radioContainer = document.createElement('div');
      radioContainer.className = 'radio-item';
      
      const radio = document.createElement('input');
      radio.type = 'radio';
      radio.id = `${this.id}-${index}`;
      radio.name = this.options.name || this.id;
      radio.value = option.value;
      
      if (this.options.value === option.value) {
        radio.checked = true;
      }
      
      if (this.options.className) {
        radio.className = this.options.className;
      }
      
      if (this.options.required) {
        radio.required = true;
      }
      
      const label = document.createElement('label');
      label.htmlFor = `${this.id}-${index}`;
      
      if (option.labelHtml) {
        label.innerHTML = option.label;
      } else {
        label.textContent = option.label;
      }
      
      radioContainer.appendChild(radio);
      radioContainer.appendChild(label);
      container.appendChild(radioContainer);
      
      // ラジオボタンの変更イベントを設定
      radio.addEventListener('change', (e) => {
        if (this.options.onChange) {
          this.options.onChange(e.target.value, e);
        }
        
        // 状態変更を通知
        eventBus.emit('radio:change', {
          id: this.id,
          value: e.target.value,
          element: radio
        });
      });
    });
    
    this.element = container;
    return container;
  }
  
  /**
   * 選択値を取得
   * @returns {string|null} 選択された値
   */
  getValue() {
    if (this.element) {
      const checked = this.element.querySelector(`input[name="${this.options.name || this.id}"]:checked`);
      return checked ? checked.value : null;
    }
    return null;
  }
  
  /**
   * 選択値を設定
   * @param {string} value - 設定する値
   */
  setValue(value) {
    if (this.element) {
      const radio = this.element.querySelector(`input[value="${value}"]`);
      if (radio) {
        radio.checked = true;
      }
    }
  }
}

/**
 * ボタン要素
 */
export class Button extends UIElement {
  /**
   * ボタン要素を作成
   * @returns {HTMLElement} ボタン要素
   */
  create() {
    const button = document.createElement('button');
    button.id = this.id;
    button.type = this.options.type || 'button';
    
    if (this.options.className) {
      button.className = this.options.className;
    }
    
    if (this.options.text) {
      button.textContent = this.options.text;
    }
    
    if (this.options.disabled) {
      button.disabled = true;
    }
    
    // イベントリスナーの設定
    button.addEventListener('click', (e) => {
      if (this.options.onClick) {
        this.options.onClick(e);
      }
      
      // クリックイベントを通知
      eventBus.emit('button:click', {
        id: this.id,
        element: button,
        event: e
      });
    });
    
    this.element = button;
    return button;
  }
}

/**
 * フォーム要素
 */
export class Form extends UIElement {
  /**
   * コンストラクタ
   * @param {string} id - フォームのID
   * @param {Object} options - オプション設定
   */
  constructor(id, options = {}) {
    super(id, options);
    this.fields = new Map();
  }
  
  /**
   * フォーム要素を作成
   * @returns {HTMLElement} フォーム要素
   */
  create() {
    const form = document.createElement('form');
    form.id = this.id;
    
    if (this.options.className) {
      form.className = this.options.className;
    }
    
    if (this.options.action) {
      form.action = this.options.action;
    }
    
    if (this.options.method) {
      form.method = this.options.method;
    }
    
    // 送信イベントの設定
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      
      if (this.options.onSubmit) {
        this.options.onSubmit(this.getValues(), e);
      }
      
      // 送信イベントを通知
      eventBus.emit('form:submit', {
        id: this.id,
        values: this.getValues(),
        element: form,
        event: e
      });
    });
    
    this.element = form;
    return form;
  }
  
  /**
   * フィールドを追加
   * @param {UIElement} field - 追加するフィールド
   * @returns {Form} このフォームインスタンス（チェーン可能）
   */
  addField(field) {
    if (!(field instanceof UIElement)) {
      console.error('フォームには UIElement のインスタンスのみ追加できます');
      return this;
    }
    
    this.fields.set(field.id, field);
    
    // フォームがすでに作成されていれば、フィールドを追加
    if (this.element) {
      field.appendTo(this.element);
    }
    
    return this;
  }
  
  /**
   * フォームを生成してフィールドを追加
   * @returns {HTMLElement} フォーム要素
   */
  create() {
    const form = super.create();
    
    // 各フィールドをフォームに追加
    this.fields.forEach(field => {
      field.appendTo(form);
    });
    
    return form;
  }
  
  /**
   * 全フィールドの値を取得
   * @returns {Object} フィールドIDをキーとする値のオブジェクト
   */
  getValues() {
    const values = {};
    
    this.fields.forEach((field, id) => {
      values[id] = field.getValue();
    });
    
    return values;
  }
  
  /**
   * フィールド値を設定
   * @param {Object} values - フィールドIDをキーとする値のオブジェクト
   */
  setValues(values) {
    Object.keys(values).forEach(id => {
      if (this.fields.has(id)) {
        this.fields.get(id).setValue(values[id]);
      }
    });
  }
  
  /**
   * フォームバリデーション
   * @returns {boolean} フォームが有効な場合はtrue
   */
  validate() {
    return this.element ? this.element.checkValidity() : false;
  }
}

/**
 * 質問コンポーネント
 */
export class Question extends UIElement {
  /**
   * 質問コンポーネントを作成
   * @returns {HTMLElement} 質問コンポーネント
   */
  create() {
    const container = document.createElement('div');
    container.id = this.id;
    container.className = this.options.containerClass || 'question-container';
    
    // 質問テキスト
    if (this.options.questionText) {
      const questionText = document.createElement('div');
      questionText.className = 'question-text';
      
      if (this.options.questionHtml) {
        questionText.innerHTML = this.options.questionText;
      } else {
        questionText.textContent = this.options.questionText;
      }
      
      container.appendChild(questionText);
    }
    
    // 入力フィールド
    if (this.options.inputField) {
      this.options.inputField.appendTo(container);
    }
    
    // エラーメッセージ表示エリア
    const errorContainer = document.createElement('div');
    errorContainer.className = 'error-message';
    errorContainer.style.color = 'red';
    errorContainer.style.display = 'none';
    container.appendChild(errorContainer);
    
    this.element = container;
    return container;
  }
  
  /**
   * エラーメッセージを表示
   * @param {string} message - 表示するメッセージ
   */
  showError(message) {
    if (this.element) {
      const errorContainer = this.element.querySelector('.error-message');
      if (errorContainer) {
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
      }
    }
  }
  
  /**
   * エラーメッセージを非表示
   */
  clearError() {
    if (this.element) {
      const errorContainer = this.element.querySelector('.error-message');
      if (errorContainer) {
        errorContainer.textContent = '';
        errorContainer.style.display = 'none';
      }
    }
  }
  
  /**
   * 質問の値を取得
   * @returns {*} 入力フィールドの値
   */
  getValue() {
    return this.options.inputField ? this.options.inputField.getValue() : null;
  }
  
  /**
   * 質問の値を設定
   * @param {*} value - 設定する値
   */
  setValue(value) {
    if (this.options.inputField) {
      this.options.inputField.setValue(value);
    }
  }
}

/**
 * UIファクトリークラス - ファクトリーメソッドパターンの実装
 */
export class UIFactory {
  /**
   * テキスト入力を作成
   * @param {string} id - 入力のID
   * @param {Object} options - オプション設定
   * @returns {TextInput} テキスト入力インスタンス
   */
  createTextInput(id, options = {}) {
    return new TextInput(id, options);
  }
  
  /**
   * 数値入力を作成
   * @param {string} id - 入力のID
   * @param {Object} options - オプション設定
   * @returns {NumberInput} 数値入力インスタンス
   */
  createNumberInput(id, options = {}) {
    return new NumberInput(id, options);
  }
  
  /**
   * スライダー入力を作成
   * @param {string} id - 入力のID
   * @param {Object} options - オプション設定
   * @returns {SliderInput} スライダー入力インスタンス
   */
  createSliderInput(id, options = {}) {
    return new SliderInput(id, options);
  }
  
  /**
   * チェックボックスを作成
   * @param {string} id - チェックボックスのID
   * @param {Object} options - オプション設定
   * @returns {Checkbox} チェックボックスインスタンス
   */
  createCheckbox(id, options = {}) {
    return new Checkbox(id, options);
  }
  
  /**
   * ラジオグループを作成
   * @param {string} id - ラジオグループのID
   * @param {Object} options - オプション設定
   * @returns {RadioGroup} ラジオグループインスタンス
   */
  createRadioGroup(id, options = {}) {
    return new RadioGroup(id, options);
  }
  
  /**
   * ボタンを作成
   * @param {string} id - ボタンのID
   * @param {Object} options - オプション設定
   * @returns {Button} ボタンインスタンス
   */
  createButton(id, options = {}) {
    return new Button(id, options);
  }
  
  /**
   * フォームを作成
   * @param {string} id - フォームのID
   * @param {Object} options - オプション設定
   * @returns {Form} フォームインスタンス
   */
  createForm(id, options = {}) {
    return new Form(id, options);
  }
  
  /**
   * 質問コンポーネントを作成
   * @param {string} id - 質問のID
   * @param {Object} options - オプション設定
   * @returns {Question} 質問インスタンス
   */
  createQuestion(id, options = {}) {
    return new Question(id, options);
  }
  
  /**
   * CRT質問を作成（認知反射テスト用の特殊な質問）
   * @param {string} id - 質問のID
   * @param {string} questionText - 質問文
   * @param {Object} options - 追加オプション
   * @returns {Question} CRT質問インスタンス
   */
  createCRTQuestion(id, questionText, options = {}) {
    // 数値入力フィールドを作成
    const inputField = this.createNumberInput(`${id}-input`, {
      placeholder: options.placeholder || '回答を入力',
      className: options.inputClass || 'crt-input',
      required: true,
      onChange: (value) => {
        // 入力値が変更されたら検証
        if (value) {
          question.clearError();
        }
      }
    });
    
    // 質問コンポーネントを作成
    const question = this.createQuestion(id, {
      questionText,
      questionHtml: true,
      inputField,
      containerClass: options.containerClass || 'crt-question'
    });
    
    return question;
  }
  
  /**
   * IMCチェックボックスグループを作成（指示理解テスト用）
   * @param {string} id - チェックボックスグループのID
   * @param {string} instructionText - 指示文
   * @param {Array} options - チェックボックスのオプション配列
   * @param {Object} additionalOptions - 追加オプション
   * @returns {HTMLElement} IMCチェックボックスグループ要素
   */
  createIMCCheckboxGroup(id, instructionText, options, additionalOptions = {}) {
    const container = document.createElement('div');
    container.id = id;
    container.className = additionalOptions.containerClass || 'imc-container';
    
    // 指示文を追加
    if (instructionText) {
      const instruction = document.createElement('div');
      instruction.className = 'imc-instruction';
      instruction.innerHTML = instructionText;
      container.appendChild(instruction);
    }
    
    // チェックボックスを作成
    const checkboxes = [];
    options.forEach((option, index) => {
      const checkbox = this.createCheckbox(`${id}-option-${index}`, {
        label: option.label,
        value: option.value,
        containerClass: 'imc-checkbox-item',
        className: additionalOptions.checkboxClass || 'imc-checkbox',
        onChange: (checked) => {
          if (additionalOptions.onChange) {
            additionalOptions.onChange(option.value, checked);
          }
          
          // チェックボックスの状態変更を通知
          eventBus.emit('imc:checkbox:change', {
            id: `${id}-option-${index}`,
            value: option.value,
            checked: checked,
            groupId: id
          });
        }
      });
      
      checkboxes.push(checkbox);
      checkbox.appendTo(container);
    });
    
    return container;
  }
}

/*
CSS例（examine1.css等に追加することを推奨）
.slider-labels {
  display: flex;
  justify-content: space-between;
  position: relative;
}
.slider-label-min {
  flex: 0 0 auto;
  text-align: left;
}
.slider-label-zero {
  flex: 0 0 auto;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  text-align: center;
}
.slider-label-max {
  flex: 0 0 auto;
  text-align: right;
}
*/

// シングルトンインスタンスを作成
const uiFactory = new UIFactory();

// グローバルスコープにエクスポート
export default uiFactory;