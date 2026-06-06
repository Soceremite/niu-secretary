# 牛秘书 AI 模型调用参考手册 v4
# ==================================
# 基于 OpenCode Go 订阅实测 + DeepSeek 官方端点
# 核心改进：reasoningEffort=low / thinking=disabled 压制啰嗦推理

## 模型池

| 模型 ID | 端点 | 推理控制 | 速度 | 视觉 | 用途 |
|---------|------|----------|------|------|------|
| kimi-k2.6 | OpenCode Go /chat/completions | reasoningEffort=low + textVerbosity=low | ~1.7s | ❌ | 🔥意图分类首选 |
| kimi-k2.5 | OpenCode Go /chat/completions | reasoningEffort=low + textVerbosity=low | ~3.4s | ❌ | 分类备选 |
| deepseek-v4-flash | DeepSeek 官方 | thinking.type=disabled | ~2s | ❌ | 分类备选 |
| deepseek-v4-pro | DeepSeek 官方 | thinking.type=disabled | ~5s | ❌ | 复杂动作 |
| qwen3.7-max | OpenCode Go /messages | thinking.type=disabled | ~3s | ✅ | 复杂动作+多模态 |
| qwen3.6-plus | OpenCode Go /messages | thinking.type=disabled | ~2s | ✅ | 分类备选+视觉 |

## v4 推理压制参数

### OpenAI 端点 (Kimi/DeepSeek via OpenCode Go)
```json
{
  "reasoningEffort": "low",
  "textVerbosity": "low",
  "reasoningSummary": "auto"
}
```

### DeepSeek 官方端点
```json
{
  "thinking": {"type": "disabled"}
}
```

### Anthropic 端点 (Qwen via OpenCode Go)
```json
{
  "thinking": {"type": "disabled"}
}
```

## 降级链

### 意图分类
```
kimi-k2.6(1.7s) → kimi-k2.5(3.4s) → deepseek-v4-flash → qwen3.6-plus → 本地规则引擎
```

### 动作生成
```
kimi-k2.6 → kimi-k2.5 → deepseek-v4-pro → qwen3.7-max → qwen3.6-plus → 本地规则引擎
```

每个模型失败后自动切换下一个，响应时间内任一成功即返回。

## Prompt 强化

v4 所有 prompt 以「只返回JSON不分析不解释」开头，杜绝 Kimi K2.6 的啰嗦推理前缀。

## API 调用格式

### openai-completions (Kimi via OpenCode Go)
```bash
POST /chat/completions
Authorization: Bearer <key>
{
  "model": "kimi-k2.6",
  "messages": [{"role":"user","content":"..."}],
  "max_tokens": 100,
  "reasoningEffort": "low",
  "textVerbosity": "low",
  "reasoningSummary": "auto"
}
```

### openai-completions (DeepSeek 官方)
```bash
POST /chat/completions
Authorization: Bearer <DEEPSEEK_API_KEY>
{
  "model": "deepseek-v4-flash",
  "messages": [{"role":"user","content":"..."}],
  "max_tokens": 100,
  "thinking": {"type": "disabled"}
}
```

### anthropic-messages (Qwen via OpenCode Go)
```bash
POST /messages
x-api-key: <key>
{
  "model": "qwen3.7-max",
  "max_tokens": 300,
  "messages": [{"role":"user","content":"..."}],
  "thinking": {"type": "disabled"}
}
```

## 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| NIU_ASSISTANT_API_KEY | OpenCode Go / OpenAI 兼容端点 API key | sk-... |
| NIU_ASSISTANT_API_BASE | OpenCode Go / OpenAI 兼容端点 base URL | https://opencode.ai/zen/go/v1 |
| OPENCODEGO_API_KEY | 备用 API key 变量名，未配置 NIU_ASSISTANT_API_KEY 时使用 | sk-... |
| DEEPSEEK_API_KEY | DeepSeek 官方 API key | sk-... |

其他端点通过 OpenCode Go 统一鉴权，密钥必须从环境变量读取，不能写入代码仓库。

## v4 vs v3 对比

| 维度 | v3 | v4 |
|------|-----|-----|
| Kimi 推理控制 | ❌ 无参数 | ✅ reasoningEffort=low |
| DeepSeek thinking | ❌ 未用官方端点 | ✅ thinking:disabled |
| Qwen thinking | ❌ 无参数 | ✅ thinking:disabled |
| Prompt | 普通描述 | ✅ 「只返回JSON不分析」 |
| 返回字段 | intent/module混用 | ✅ 统一 module |
| 大餐估算 | 350千卡 | ✅ 1200千卡 |
