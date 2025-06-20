/**
 * ID改善点のテストスクリプト
 */

// utilities.jsの関数をテスト用に再実装
function generateUniqueId() {
  const timestamp = Date.now().toString(36);
  const randomPart1 = Math.random().toString(36).substr(2, 6);
  const randomPart2 = Math.random().toString(36).substr(2, 4);
  const performanceNow = performance.now().toString(36).substr(2, 4);
  
  return `${timestamp}${randomPart1}${randomPart2}${performanceNow}`;
}

function validateUserId(userId) {
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

function sanitizeUserId(userId) {
  if (!userId) return '';
  
  // 基本的なサニタイズ
  return userId
    .toString()
    .trim()
    .substring(0, 50) // 最大長制限
    .replace(/[<>'"&=;()|]/g, '') // 危険な文字を削除
    .replace(/[\x00-\x1F\x7F]/g, ''); // 制御文字を削除
}

console.log('=== ID改善点のテスト ===\n');

// テスト1: 改善されたID生成のテスト
console.log('--- テスト1: 改善されたID生成 ---');
const generatedIds = [];
for (let i = 0; i < 10; i++) {
  const id = generateUniqueId();
  generatedIds.push(id);
  console.log(`生成されたID ${i + 1}: ${id} (長さ: ${id.length})`);
}

// 重複チェック
const uniqueIds = new Set(generatedIds);
console.log(`重複チェック: ${uniqueIds.size === generatedIds.length ? '✅ 重複なし' : '❌ 重複あり'}`);
console.log(`生成数: ${generatedIds.length}, ユニーク数: ${uniqueIds.size}\n`);

// テスト2: ID検証機能のテスト
console.log('--- テスト2: ID検証機能 ---');
const testIds = [
  'valid_id_123',           // 有効
  'ab',                     // 短すぎる
  'a'.repeat(51),           // 長すぎる
  'invalid<script>',        // 危険な文字
  'valid_id_with_numbers_456', // 有効
  "id'with'quotes",         // 危険な文字
  'normal_user_id',         // 有効
  '',                       // 空文字
  'id&with&special',        // 危険な文字
  'test_user_001'           // 有効
];

testIds.forEach(id => {
  const isValid = validateUserId(id);
  const sanitized = sanitizeUserId(id);
  console.log(`ID: "${id}" => 有効: ${isValid ? '✅' : '❌'}, サニタイズ後: "${sanitized}"`);
});

console.log('\n--- テスト3: ID一意性の統計 ---');
// 1000個のIDを生成して統計を取る
const largeTestIds = [];
for (let i = 0; i < 1000; i++) {
  largeTestIds.push(generateUniqueId());
}

const uniqueLargeIds = new Set(largeTestIds);
const collisionRate = ((1000 - uniqueLargeIds.size) / 1000 * 100).toFixed(4);

console.log(`1000個のID生成結果:`);
console.log(`- 生成数: 1000`);
console.log(`- ユニーク数: ${uniqueLargeIds.size}`);
console.log(`- 衝突率: ${collisionRate}%`);
console.log(`- 平均長: ${(largeTestIds.reduce((sum, id) => sum + id.length, 0) / largeTestIds.length).toFixed(1)} 文字`);

// テスト4: 旧ID生成方式との比較
console.log('\n--- テスト4: 旧方式との比較 ---');
function oldGenerateUniqueId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
}

function oldNumericId() {
  return Math.round(Math.random() * 100000000).toString().padStart(8, '0');
}

const newIds = Array.from({ length: 100 }, () => generateUniqueId());
const oldIds = Array.from({ length: 100 }, () => oldGenerateUniqueId());
const numericIds = Array.from({ length: 100 }, () => oldNumericId());

console.log(`新方式の平均長: ${(newIds.reduce((sum, id) => sum + id.length, 0) / newIds.length).toFixed(1)} 文字`);
console.log(`旧方式の平均長: ${(oldIds.reduce((sum, id) => sum + id.length, 0) / oldIds.length).toFixed(1)} 文字`);
console.log(`数値方式の平均長: ${(numericIds.reduce((sum, id) => sum + id.length, 0) / numericIds.length).toFixed(1)} 文字`);

console.log(`新方式の衝突率: ${((100 - new Set(newIds).size) / 100 * 100).toFixed(4)}%`);
console.log(`旧方式の衝突率: ${((100 - new Set(oldIds).size) / 100 * 100).toFixed(4)}%`);
console.log(`数値方式の衝突率: ${((100 - new Set(numericIds).size) / 100 * 100).toFixed(4)}%`);

console.log('\n=== テスト完了 ===');
