
// fitness/server/nutrition-api.js
// [DEPRECATED 2026-09-15] Legacy duplicate of nutrition_api.py, kept for
// reference only. The live service is systemd `niu-fitness-api` running the
// Python version (which now routes through niu_core.llm_client). No process
// runs this file; do not wire it back up.
import { createServer } from 'node:http';

const PORT = Number(process.env.FITNESS_API_PORT || 5177);
const ROUTES = new Set([
  '/niu-secretary/fitness/api/agent/nutrition-recognize',
  '/api/agent/nutrition-recognize'
]);
const MAX_IMAGE_BYTES = 8 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif']);

const server = createServer(async (req, res) => {
  try {
    if (req.method === 'OPTIONS') return sendNoContent(res);
    if (req.method !== 'POST' || !ROUTES.has(new URL(req.url, 'http://localhost').pathname)) {
      return sendJson(res, 404, { error: 'not_found', message: '未知接口。' });
    }
    await handleNutritionRecognize(req, res);
  } catch (error) {
    if (error?.statusCode === 413) {
      return sendJson(res, 413, { error: 'photo_too_large', message: '图片超过 8MB，请压缩后再上传。' });
    }
    console.error('[fitness-api] request failed', error);
    sendJson(res, 500, { error: 'internal_error', message: '识别服务内部错误。' });
  }
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[fitness-api] listening on http://127.0.0.1:${PORT}`);
});

async function handleNutritionRecognize(req, res) {
  const contentType = req.headers['content-type'] || '';
  if (!contentType.includes('multipart/form-data')) {
    return sendJson(res, 400, { error: 'invalid_request', message: '请使用 multipart/form-data 上传图片。' });
  }

  const body = await readBody(req, MAX_IMAGE_BYTES + 1024 * 1024);
  const form = parseMultipart(body, contentType);
  const photo = form.files.photo;
  const description = form.fields.description || '';

  if (!photo || !photo.data.length) {
    return sendJson(res, 400, { error: 'missing_photo', message: '缺少 photo 图片字段。' });
  }
  if (photo.data.length > MAX_IMAGE_BYTES) {
    return sendJson(res, 413, { error: 'photo_too_large', message: '图片超过 8MB，请压缩后再上传。' });
  }
  if (!ALLOWED_IMAGE_TYPES.has(photo.contentType)) {
    return sendJson(res, 400, { error: 'unsupported_photo_type', message: '仅支持 JPG、PNG、WebP、HEIC 图片。' });
  }
  if (!process.env.FITNESS_VISION_API_BASE || !process.env.FITNESS_VISION_API_KEY || !process.env.FITNESS_VISION_MODEL) {
    return sendJson(res, 503, { error: 'agent_unconfigured', message: '识别服务未配置，请设置 FITNESS_VISION_API_BASE、FITNESS_VISION_API_KEY、FITNESS_VISION_MODEL。' });
  }

  try {
    const result = await callVisionModel({ photo, description });
    sendJson(res, 200, normalizeMeal(result, 'agent'));
  } catch (error) {
    const timedOut = error?.name === 'AbortError';
    const message = String(error?.message || error);
    const noVision = /Unexpected item type in content|messages input is invalid|image/i.test(message);
    console.error('[fitness-api] vision call failed', message);
    sendJson(res, 502, {
      error: noVision ? 'model_no_vision' : timedOut ? 'agent_timeout' : 'agent_failed',
      message: noVision
        ? `当前模型 ${process.env.FITNESS_VISION_MODEL || ''} 不支持图片输入，请换成支持视觉/多模态的模型。`
        : timedOut ? 'Agent 识别超时，请稍后重试或使用本地估算。' : 'Agent/模型调用失败，请稍后重试或使用本地估算。'
    });
  }
}

async function callVisionModel({ photo, description }) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), Number(process.env.FITNESS_VISION_TIMEOUT_MS || 25000));
  const url = resolveVisionUrl(process.env.FITNESS_VISION_API_BASE);
  const prompt = [
    '你是营养识别助手。请识别餐食图片，估算每个可见食物和整餐热量、蛋白质、碳水、脂肪。',
    '只返回 JSON，不要 Markdown。字段：food, items[], calories, proteinG, carbsG, fatG, confidence, warnings[]。',
    'items 每项包含 name, portion, calories, proteinG, carbsG, fatG。confidence 为 0 到 1。',
    description ? `用户补充描述：${description}` : '用户没有补充描述。'
  ].join('\n');

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: buildVisionHeaders(url),
      body: JSON.stringify(buildVisionPayload({ url, prompt, photo })),
      signal: controller.signal
    });
    if (!response.ok) {
      const errorText = await response.text().catch(() => '');
      throw new Error(`vision-http-${response.status}: ${errorText.slice(0, 500)}`);
    }
    const data = await response.json();
    return parseVisionResponse(data);
  } finally {
    clearTimeout(timeout);
  }
}

function buildVisionHeaders(url) {
  if (url.endsWith('/messages')) {
    return {
      'x-api-key': process.env.FITNESS_VISION_API_KEY,
      'anthropic-version': '2023-06-01',
      'Content-Type': 'application/json'
    };
  }
  return {
    Authorization: `Bearer ${process.env.FITNESS_VISION_API_KEY}`,
    'Content-Type': 'application/json'
  };
}

function buildVisionPayload({ url, prompt, photo }) {
  const imageBase64 = photo.data.toString('base64');
  if (url.endsWith('/messages')) {
    return {
      model: process.env.FITNESS_VISION_MODEL,
      max_tokens: 1200,
      messages: [{
        role: 'user',
        content: [
          { type: 'text', text: prompt },
          { type: 'image', source: { type: 'base64', media_type: photo.contentType, data: imageBase64 } }
        ]
      }]
    };
  }
  return {
    model: process.env.FITNESS_VISION_MODEL,
    response_format: { type: 'json_object' },
    messages: [{
      role: 'user',
      content: [
        { type: 'text', text: prompt },
        { type: 'image_url', image_url: { url: `data:${photo.contentType};base64,${imageBase64}` } }
      ]
    }]
  };
}

function parseVisionResponse(data) {
  const content = data.choices?.[0]?.message?.content
    ?? data.output_text
    ?? data.content?.find?.((item) => item.type === 'text')?.text
    ?? data.content?.[0]?.text
    ?? data;
  return typeof content === 'string' ? JSON.parse(stripJsonFence(content)) : content;
}

function resolveVisionUrl(base) {
  const trimmed = String(base || '').replace(/\/+$/, '');
  if (trimmed.endsWith('/messages') || trimmed.endsWith('/chat/completions')) return trimmed;
  return `${trimmed}/chat/completions`;
}

function normalizeMeal(data, source) {
  const items = Array.isArray(data.items) ? data.items.map((item) => ({
    name: String(item.name || item.food || '未命名食物').slice(0, 80),
    portion: String(item.portion || item.amount || '').slice(0, 80),
    calories: clamp(item.calories, 0, 3000),
    proteinG: clamp(item.proteinG ?? item.protein, 0, 200),
    carbsG: clamp(item.carbsG ?? item.carbs, 0, 400),
    fatG: clamp(item.fatG ?? item.fat, 0, 200)
  })) : [];
  const warnings = Array.isArray(data.warnings) ? data.warnings.map((item) => String(item).slice(0, 120)) : [];
  return {
    food: String(data.food || data.name || items.map((item) => item.name).join('、') || '图片餐食').slice(0, 160),
    items,
    calories: clamp(data.calories, 0, 5000),
    proteinG: clamp(data.proteinG ?? data.protein, 0, 300),
    carbsG: clamp(data.carbsG ?? data.carbs, 0, 600),
    fatG: clamp(data.fatG ?? data.fat, 0, 300),
    confidence: Math.max(0, Math.min(1, Number(data.confidence || 0))),
    warnings,
    source
  };
}

function readBody(req, limit) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > limit) {
        reject(Object.assign(new Error('payload-too-large'), { statusCode: 413 }));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

function parseMultipart(body, contentType) {
  const match = contentType.match(/boundary=(?:"([^"]+)"|([^;]+))/i);
  if (!match) return { fields: {}, files: {} };
  const boundary = `--${match[1] || match[2]}`;
  const bodyText = body.toString('latin1');
  const fields = {};
  const files = {};

  for (const rawPart of bodyText.split(boundary)) {
    if (!rawPart || rawPart === '--\r\n' || rawPart === '--') continue;
    const part = rawPart.replace(/^\r\n/, '').replace(/\r\n--$/, '');
    const separator = part.indexOf('\r\n\r\n');
    if (separator < 0) continue;
    const headerText = part.slice(0, separator);
    let valueText = part.slice(separator + 4);
    if (valueText.endsWith('\r\n')) valueText = valueText.slice(0, -2);
    const disposition = headerText.match(/content-disposition:\s*form-data;([^\r\n]+)/i)?.[1] || '';
    const name = disposition.match(/name="([^"]+)"/)?.[1];
    const filename = disposition.match(/filename="([^"]*)"/)?.[1];
    const contentTypeMatch = headerText.match(/content-type:\s*([^\r\n]+)/i);
    if (!name) continue;
    if (filename != null) {
      files[name] = {
        filename,
        contentType: (contentTypeMatch?.[1] || 'application/octet-stream').toLowerCase(),
        data: Buffer.from(valueText, 'latin1')
      };
    } else {
      fields[name] = Buffer.from(valueText, 'latin1').toString('utf8');
    }
  }
  return { fields, files };
}

function stripJsonFence(value) {
  return String(value).trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '');
}

function clamp(value, min, max) {
  const n = Number(value || 0);
  return Math.max(min, Math.min(max, Math.round(n)));
}

function sendNoContent(res) {
  res.writeHead(204, corsHeaders());
  res.end();
}

function sendJson(res, status, body) {
  res.writeHead(status, { ...corsHeaders(), 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(body));
}

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  };
}
