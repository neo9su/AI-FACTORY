---
name: codex-vision
description: "Agnes Image 2.1 Flash 图像生成 Skill — 让 Codex 具备文生图/图生图能力。通过 HTTP curl 调用 Agnes API 生成高质量图像。"
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Codex Vision Skill — Agnes Image 2.1 Flash

## 概述

让 Codex 具备图像生成能力。通过 HTTP curl 调用 Agnes Image 2.1 Flash API，支持文生图和图生图。

## API 信息

- **Base URL**: `https://apihub.agnes-ai.com`
- **Endpoint**: `POST /v1/images/generations`
- **认证**: 在 header 中传递 `Authorization: Bearer ***`
- **模型名称**: `agnes-image-2.1-flash`
- **价格**: $0.003/张 (当前免费)
- **超时建议**: 60-360 秒
- **API Key**: 从环境变量 `AGNES_API_KEY` 读取，或硬编码在脚本中

## 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| model | string | 是 | `agnes-image-2.1-flash` |
| prompt | string | 是 | 图像描述或编辑指令 |
| size | string | 是 | 输出尺寸如 `"1024x768"` |
| image | string[] | 图生图必填 | 输入图片数组 (URL 或 Data URI) |
| return_base64 | boolean | 否 | 文生图返回 Base64 |
| extra_body.response_format | string | 否 | `"url"` 或 `"b64_json"` |

## curl 示例

**文生图 — URL 输出:**
```bash
API_KEY="cpk-YOUR_KEY_HERE"
curl -s -X POST https://apihub.agnes-ai.com/v1/images/generations \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{
    "model": "agnes-image-2.1-flash",
    "prompt": "A clean product photo of a glass cube on white background, studio lighting",
    "size": "1024x768",
    "extra_body": { "response_format": "url" }
  }' | jq -r '.data[0].url'
```

**图生图 — URL 输入，URL 输出:**
```bash
API_KEY="cpk-YOUR_KEY_HERE"
curl -s -X POST https://apihub.agnes-ai.com/v1/images/generations \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{
    "model": "agnes-image-2.1-flash",
    "prompt": "Transform into a rain-soaked cyberpunk night with neon reflections, preserving original composition",
    "size": "1024x768",
    "extra_body": {
      "image": ["https://example.com/input.png"],
      "response_format": "url"
    }
  }' | jq -r '.data[0].url'
```

## 重要注意事项

- **`response_format` 必须放在 `extra_body` 中**，不要放顶层
- **文生图不需要 `image` 参数**，传了会报错
- **图生图必须传 `image` 数组**
- **不要传 `tags: ["img2img"]`**
- 输入图片 URL 必须是公网可访问的 HTTPS
- 本地图片用 Data URI Base64: `data:image/png;base64,xxx`

## Prompt 结构

**文生图**: [主体] + [场景/环境] + [风格] + [光照] + [构图] + [质量要求]

**图生图**: [修改要求] + [新风格/场景] + [添加/移除元素] + [保留元素]

## 推荐尺寸

- 横图: `"1024x768"`
- 竖图: `"768x1024"`
- 正方: `"1024x1024"`
- 自定义: 任意 `"WxH"` 格式
