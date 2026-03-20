// Cloudflare Worker - 健康数据接收与存储
// 部署: wrangler deploy

const GITHUB_API = 'https://api.github.com';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    
    // 健康检查
    if (url.pathname === '/health') {
      return new Response('OK', { status: 200 });
    }
    
    // 接收健康数据
    if (url.pathname === '/api/health-data' && request.method === 'POST') {
      return await handleHealthData(request, env);
    }
    
    return new Response('Not Found', { status: 404 });
  }
};

async function handleHealthData(request, env) {
  try {
    const data = await request.json();
    
    // 验证必要字段
    if (!data.type || !data.date) {
      return new Response(JSON.stringify({ error: 'Missing required fields: type, date' }), { 
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // 生成文件路径
    const date = new Date();
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const filePath = `data/${data.type}/${year}/${month}/${day}.json`;
    
    // 构建完整数据
    const record = {
      ...data,
      received_at: new Date().toISOString(),
      source: request.headers.get('User-Agent') || 'unknown'
    };
    
    // 推送到 GitHub
    const result = await pushToGitHub(filePath, record, env);
    
    return new Response(JSON.stringify({ 
      success: true, 
      path: filePath,
      github: result 
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), { 
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function pushToGitHub(filePath, data, env) {
  const { GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO } = env;
  
  if (!GITHUB_TOKEN || !GITHUB_OWNER || !GITHUB_REPO) {
    throw new Error('Missing GitHub configuration');
  }
  
  const content = JSON.stringify(data, null, 2);
  const contentBase64 = btoa(content);
  
  // 检查文件是否存在
  const checkUrl = `${GITHUB_API}/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/${filePath}`;
  const checkResponse = await fetch(checkUrl, {
    headers: {
      'Authorization': `token ${GITHUB_TOKEN}`,
      'Accept': 'application/vnd.github.v3+json'
    }
  });
  
  let sha = null;
  if (checkResponse.status === 200) {
    const existing = await checkResponse.json();
    sha = existing.sha;
  }
  
  // 创建或更新文件
  const putUrl = `${GITHUB_API}/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/${filePath}`;
  const body = {
    message: `Update health data: ${filePath}`,
    content: contentBase64,
    branch: 'main'
  };
  
  if (sha) {
    body.sha = sha;
  }
  
  const response = await fetch(putUrl, {
    method: 'PUT',
    headers: {
      'Authorization': `token ${GITHUB_TOKEN}`,
      'Accept': 'application/vnd.github.v3+json',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  });
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`GitHub API error: ${error}`);
  }
  
  return await response.json();
}
