// シナリオ分割システムのテスト
const allScenarios = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];

// シード値生成の模擬（config.jsと同じロジック）
function generateSeed(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash);
}

// 決定論的シャッフルの模擬（config.jsと同じロジック）
function shuffleWithSeed(array, seed) {
  const shuffled = [...array];
  let currentSeed = seed;
  
  const random = () => {
    currentSeed = (currentSeed * 1103515245 + 12345) & 0x7fffffff;
    return currentSeed / 0x7fffffff;
  };
  
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  
  return shuffled;
}

// 複数のユーザーでテスト
const testUsers = ['12345678', '87654321', 'user001', 'test123'];

console.log('=== examine1とexamine1_2のシナリオ分割テスト ===\n');

testUsers.forEach(userId => {
  const userSeed = generateSeed(userId);
  const shuffledScenarios = shuffleWithSeed([...allScenarios], userSeed);
  
  const examine1Scenarios = shuffledScenarios.slice(0, 6);
  const examine1_2Scenarios = shuffledScenarios.slice(6, 12);
  
  console.log(`ユーザーID: ${userId}`);
  console.log(`シード値: ${userSeed}`);
  console.log(`examine1のシナリオ: ${examine1Scenarios.join(', ')}`);
  console.log(`examine1_2のシナリオ: ${examine1_2Scenarios.join(', ')}`);
  
  // 重複チェック
  const allUsed = [...examine1Scenarios, ...examine1_2Scenarios];
  const uniqueCount = new Set(allUsed).size;
  const hasNoDuplicates = uniqueCount === 12;
  
  console.log(`重複チェック: ${hasNoDuplicates ? '✅ 重複なし' : '❌ 重複あり'}`);
  console.log(`使用シナリオ数: ${allUsed.length}, ユニーク数: ${uniqueCount}`);
  console.log('---\n');
});

// 一貫性テスト（同じユーザーは常に同じシナリオセットを受け取る）
console.log('=== 一貫性テスト ===');
const consistencyUserId = '12345678';
const results = [];

for (let i = 0; i < 3; i++) {
  const userSeed = generateSeed(consistencyUserId);
  const shuffledScenarios = shuffleWithSeed([...allScenarios], userSeed);
  results.push({
    examine1: shuffledScenarios.slice(0, 6),
    examine1_2: shuffledScenarios.slice(6, 12)
  });
}

const isConsistent = results.every(result => 
  JSON.stringify(result.examine1) === JSON.stringify(results[0].examine1) &&
  JSON.stringify(result.examine1_2) === JSON.stringify(results[0].examine1_2)
);

console.log(`同じユーザーの一貫性: ${isConsistent ? '✅ 一貫している' : '❌ 一貫していない'}`);
console.log(`ユーザー ${consistencyUserId} は常に以下のシナリオセットを受け取る:`);
console.log(`examine1: ${results[0].examine1.join(', ')}`);
console.log(`examine1_2: ${results[0].examine1_2.join(', ')}`);
