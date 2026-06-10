---
name: codex-video
description: "Agnes Video V2.0 视频生成 Skill — 让 Codex 具备文生视频/图生视频能力。通过 HTTP curl 调用 Agnes API 生成高质量视频。"
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Codex Video Skill — Agnes Video V2.0

## 概述

让 Codex 具备视频生成能力。通过 HTTP curl 调用 Agnes Video V2.0 API，支持文生视频、图生视频、多图视频和关键帧动画。采用异步任务 API — 先创建任务获取 video_id，再轮询查询结果。

## API 信息

- **Base URL**: `https://apihub.agnes-ai.com`
- **创建任务**: `POST /v1/videos`
- **查询结果**: `GET /agnesapi?video_id=VIDEO_ID` (5秒轮询间隔)
- **认证**: `Authorization: Bearer *** **模型名称**: `agnes-video-v2.0`
- **价格**: 当前免费
- **超时建议**: 600 秒
- **API Key**: 从环境变量 `AGNES_API_KEY` 读取

## 创建任务参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| model | string | 是 | agnes-video-v2.0 |
| prompt | string | 是 | 视频内容描述 |
| image | string | 否 | 图生视频输入图片 URL |
| mode | string | 否 | 生成模式: ti2vid / keyframes |
| height | integer | 否 | 视频高度，默认 768 |
| width | integer | 否 | 视频宽度，默认 1152 |
| num_frames | integer | 否 | 帧数，必须 <= 441 且满足 8n+1 |
| frame_rate | number | 否 | FPS，范围 1-60 |
| extra_body.image | array | 否 | 多图/关键帧输入 URL |

## 推荐帧数/时长

| 时长 | num_frames | frame_rate |
|------|-----------|-----------|
| ~3秒 | 81 | 24 |
| ~5秒 | 121 | 24 |
| ~10秒 | 241 | 24 |
| ~18秒 | 441 | 24 |

## curl 示例

**文生视频:**
```bash
API_KEY="cpk-...curl -s -X POST https://apihub.agnes-ai.com/v1/videos \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{
    "model": "agnes-video-v2.0",
    "prompt": "A cinematic shot of a cat walking on the beach at sunset, soft ocean waves, warm golden lighting",
    "height": 768,
    "width": 1152,
    "num_frames": 121,
    "frame_rate": 24
  }'
```

**图生视频:**
```bash
API_KEY="cpk-...curl -s -X POST https://apihub.agnes-ai.com/v1/videos \
  -H "Authorization: Bearer *** \
  -H "Content-Type: application/json" \
  -d '{
    "model": "agnes-video-v2.0",
    "prompt": "The woman slowly turns around and looks back at the camera, natural facial expression",
    "image": "https://example.com/image.png",
    "num_frames": 121,
    "frame_rate": 24
  }'
```

**轮询查询结果:**
```bash
# 创建任务后获取 video_id，然后轮询
VIDEO_ID="video_xxxxx"
API_KEY="cpk-...while true; do
  STATUS=$(curl -s -H "Authorization: Bearer *** "https://apihub.agnes-ai.com/agnesapi?video_id=${VIDEO_ID}" | jq -r '.status')
  echo "Status: ${STATUS}"
  if [ "${STATUS}" = "completed" ]; then
    curl -s -H "Authorization: Bearer *** "https://apihub.agnes-ai.com/agnesapi?video_id=${VIDEO_ID}" | jq -r '.remixed_from_video_id'
    break
  elif [ "${STATUS}" = "failed" ]; then
    echo "Failed!"
    break
  fi
  sleep 5
done
```

## 重要注意事项

- **`num_frames` 必须满足 `8n + 1`** (81, 121, 161, 241, 441)
- **推荐轮询间隔 5 秒**
- **超时建议设为 600 秒**
- **视频 URL 在 `remixed_from_video_id` 字段，仅 completed 时有值**
- 多图/关键帧必须在 `extra_body` 中传 image
- 不需要传 `tags: ["img2img"]`

## Prompt 结构

**文生视频**: [主体] + [动作] + [场景] + [镜头运动] + [光照] + [风格]
**图生视频**: 描述运动 + 保持稳定元素
**多图视频**: 描述图片间关系 + 过渡方式
**关键帧**: 描述帧间过渡 + 一致性要求
