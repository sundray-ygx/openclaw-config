// 健康报告生成脚本
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

// 数据目录
const DATA_DIR = './data';
const REPORTS_DIR = './reports';

// 确保报告目录存在
if (!fs.existsSync(REPORTS_DIR)) {
  fs.mkdirSync(REPORTS_DIR, { recursive: true });
}

// 读取所有健康数据
function loadHealthData() {
  const data = {
    sleep: [],
    heartRate: [],
    steps: [],
    workouts: []
  };
  
  if (!fs.existsSync(DATA_DIR)) {
    return data;
  }
  
  // 遍历数据目录
  const types = fs.readdirSync(DATA_DIR);
  for (const type of types) {
    const typePath = path.join(DATA_DIR, type);
    if (!fs.statSync(typePath).isDirectory()) continue;
    
    // 递归读取所有 JSON 文件
    const files = findJsonFiles(typePath);
    for (const file of files) {
      try {
        const content = JSON.parse(fs.readFileSync(file, 'utf8'));
        if (data[type]) {
          data[type].push(content);
        }
      } catch (e) {
        console.error(`Error reading ${file}:`, e.message);
      }
    }
  }
  
  // 按日期排序
  for (const key of Object.keys(data)) {
    data[key].sort((a, b) => new Date(a.date) - new Date(b.date));
  }
  
  return data;
}

function findJsonFiles(dir) {
  const files = [];
  const items = fs.readdirSync(dir);
  
  for (const item of items) {
    const fullPath = path.join(dir, item);
    const stat = fs.statSync(fullPath);
    
    if (stat.isDirectory()) {
      files.push(...findJsonFiles(fullPath));
    } else if (item.endsWith('.json')) {
      files.push(fullPath);
    }
  }
  
  return files;
}

// 计算统计数据
function calculateStats(data) {
  const stats = {};
  
  // 睡眠统计
  if (data.sleep.length > 0) {
    const recent = data.sleep.slice(-7);
    const durations = recent.map(d => d.duration || 0).filter(d => d > 0);
    const qualities = recent.map(d => d.quality || 0).filter(q => q > 0);
    
    stats.sleep = {
      avgDuration: durations.length > 0 ? (durations.reduce((a, b) => a + b, 0) / durations.length / 60).toFixed(1) : 0,
      avgQuality: qualities.length > 0 ? (qualities.reduce((a, b) => a + b, 0) / qualities.length).toFixed(0) : 0,
      count: recent.length
    };
  }
  
  // 心率统计
  if (data.heartRate.length > 0) {
    const recent = data.heartRate.slice(-7);
    const rates = recent.map(d => d.avg || d.value || 0).filter(r => r > 0);
    
    stats.heartRate = {
      avg: rates.length > 0 ? (rates.reduce((a, b) => a + b, 0) / rates.length).toFixed(0) : 0,
      count: recent.length
    };
  }
  
  // 步数统计
  if (data.steps.length > 0) {
    const recent = data.steps.slice(-7);
    const steps = recent.map(d => d.steps || d.value || 0).filter(s => s > 0);
    
    stats.steps = {
      avg: steps.length > 0 ? (steps.reduce((a, b) => a + b, 0) / steps.length).toFixed(0) : 0,
      total: steps.length > 0 ? (steps.reduce((a, b) => a + b, 0) / 10000).toFixed(1) : 0,
      count: recent.length
    };
  }
  
  return stats;
}

// 生成 HTML 报告
function generateHTMLReport(data, stats) {
  const dom = new JSDOM('<!DOCTYPE html><html><head></head><body></body></html>');
  const document = dom.window.document;
  
  document.title = '健康数据报告';
  
  // 样式
  const style = document.createElement('style');
  style.textContent = `
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f5f5f7;
      padding: 20px;
      color: #1d1d1f;
    }
    .container { max-width: 800px; margin: 0 auto; }
    h1 { text-align: center; margin-bottom: 30px; font-size: 28px; }
    .date { text-align: center; color: #86868b; margin-bottom: 30px; }
    .card {
      background: white;
      border-radius: 16px;
      padding: 24px;
      margin-bottom: 20px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .card h2 { margin-bottom: 16px; font-size: 18px; color: #1d1d1f; }
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }
    .stat-item {
      background: #f5f5f7;
      padding: 16px;
      border-radius: 12px;
      text-align: center;
    }
    .stat-value {
      font-size: 32px;
      font-weight: 600;
      color: #007aff;
      margin-bottom: 4px;
    }
    .stat-label {
      font-size: 14px;
      color: #86868b;
    }
    .footer {
      text-align: center;
      color: #86868b;
      font-size: 12px;
      margin-top: 30px;
    }
  `;
  document.head.appendChild(style);
  
  const container = document.createElement('div');
  container.className = 'container';
  
  // 标题
  const title = document.createElement('h1');
  title.textContent = '📊 健康数据报告';
  container.appendChild(title);
  
  // 日期
  const date = document.createElement('div');
  date.className = 'date';
  date.textContent = new Date().toLocaleDateString('zh-CN', { 
    year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' 
  });
  container.appendChild(date);
  
  // 睡眠卡片
  if (stats.sleep) {
    const card = createCard(document, '💤 睡眠数据（最近7天）', [
      { value: stats.sleep.avgDuration, label: '平均时长（小时）' },
      { value: stats.sleep.avgQuality + '%', label: '平均质量' },
      { value: stats.sleep.count, label: '记录天数' }
    ]);
    container.appendChild(card);
  }
  
  // 心率卡片
  if (stats.heartRate) {
    const card = createCard(document, '❤️ 心率数据（最近7天）', [
      { value: stats.heartRate.avg, label: '平均心率（bpm）' },
      { value: stats.heartRate.count, label: '记录天数' }
    ]);
    container.appendChild(card);
  }
  
  // 步数卡片
  if (stats.steps) {
    const card = createCard(document, '🚶 步数数据（最近7天）', [
      { value: stats.steps.avg, label: '平均步数' },
      { value: stats.steps.total + '万', label: '总计步数' },
      { value: stats.steps.count, label: '记录天数' }
    ]);
    container.appendChild(card);
  }
  
  // 页脚
  const footer = document.createElement('div');
  footer.className = 'footer';
  footer.textContent = '由 OpenClaw 自动生成';
  container.appendChild(footer);
  
  document.body.appendChild(container);
  
  return dom.serialize();
}

function createCard(document, title, stats) {
  const card = document.createElement('div');
  card.className = 'card';
  
  const h2 = document.createElement('h2');
  h2.textContent = title;
  card.appendChild(h2);
  
  const grid = document.createElement('div');
  grid.className = 'stats-grid';
  
  for (const stat of stats) {
    const item = document.createElement('div');
    item.className = 'stat-item';
    
    const value = document.createElement('div');
    value.className = 'stat-value';
    value.textContent = stat.value;
    
    const label = document.createElement('div');
    label.className = 'stat-label';
    label.textContent = stat.label;
    
    item.appendChild(value);
    item.appendChild(label);
    grid.appendChild(item);
  }
  
  card.appendChild(grid);
  return card;
}

// 主流程
console.log('Loading health data...');
const data = loadHealthData();
console.log(`Loaded: ${data.sleep.length} sleep, ${data.heartRate.length} heartRate, ${data.steps.length} steps`);

console.log('Calculating statistics...');
const stats = calculateStats(data);

console.log('Generating HTML report...');
const html = generateHTMLReport(data, stats);

const reportPath = path.join(REPORTS_DIR, `report-${new Date().toISOString().split('T')[0]}.html`);
fs.writeFileSync(reportPath, html);
console.log(`Report saved to: ${reportPath}`);
