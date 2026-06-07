# 多模型支持 — 实现计划

> **目标：** 支持 OpenAI / Anthropic / Google Gemini / OpenAI 兼容四种 Provider，
> 支持在 Setting 页面切换 Provider 并配置对应 Key，支持一键测试连接。

### Task 1: 后端 llm.py — 多 Provider 客户端抽象
- 新增 `LLMProvider` 抽象基类
- 实现 `OpenAICompatibleProvider`（现有网关）
- 实现 `AnthropicProvider`（直接 Anthropic API）
- 实现 `OpenAIProvider`（直接 OpenAI API）  
- 实现 `GeminiProvider`（直接 Google AI API）
- 统一 `chat()` / `chat_json()` 接口

### Task 2: 后端 settings.py — 添加 Provider 配置字段
- 新增 `llm_provider` 字段
- 新增 `llm_api_key` / `llm_anthropic_key` / `llm_gemini_key` 字段

### Task 3: 后端 settings — 扩充模型列表 + 测试连接 API
- `GET /settings/models` — 按 Provider 分组返回模型
- `POST /settings/test-model` — 测试指定模型的连接

### Task 4: 后端 executor.py — 使用新 llm.py
- 更新 `Executor._call_llm()` 使用 Provider 模式
- 删除硬编码的 AsyncOpenAI client

### Task 5: 前端 settings/page.tsx — Provider 标签页 + 连接测试
- 分 Provider Tab（OpenAI兼容/Anthropic/OpenAI/Gemini）
- 每个 Tab 显示 API Key 输入 + 模型选择
- "测试连接" 按钮
