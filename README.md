# NeuroTrend AI Factory

> **AI 驱动的商机发现 → 情绪分析 → 产品生成 → 自动发布 → 数据优化闭环系统**

## 项目定位

NeuroTrend 是一个从互联网热点中自动发现商业机会的 AI 系统。它不只分析"什么火"，而是分析**人为什么会对热点上瘾**——提取用户情绪、欲望、痛点，并自动生成可商业化的 AI 产品建议。

## 当前开发阶段

| 阶段 | 完成度 | 功能 |
|------|--------|------|
| **Phase 0** 基础架构 | 100% | Next.js 14 + FastAPI + PostgreSQL + Redis |
| **Phase 1** 数据采集 (Hunter) | 100% | Reddit / 小红书 / 抖音 / X 热点抓取 |
| **Phase 2** 情绪分析 (Brain) | 100% | 情绪分类、痛点提取、爆点因子分析 |
| **Phase 3** 商机生成 (Strategist) | 100% | AI 商业机会报告、产品建议、行动计划 |
| **Phase 4** 产品生成 (Factory) | 100% | AI 产品描述、TTS 语音、SD 图片生成 |
| **Phase 5-A** 发布 (Publisher) | 100% | 发布面板、多平台推送、QR 登录 |
| **Phase 5-B** 数据回流 (Analytics) | 100% | 事件追踪、评分系统、排行榜 |
| **Phase 5-C** 优化循环 (Optimizer) | 100% | 性能分析 S/A/B/C/D 评级、A/B 测试、优化建议 |
| **Phase 6** AI 自动开发 | 待开始 | 自动生成 AI 产品代码 |

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### 1. 启动后端

```bash
cd backend

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python -c "from db.init_db import init_db; import asyncio; asyncio.run(init_db())"

# 启动 API
uvicorn main:app --reload --port 8000
```

### 2. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器（确保 PORT 环境变量未设置，或用 -p 指定端口）
npm run dev
# 或指定端口：PORT=3000 npx next dev -p 3000
```

访问 http://localhost:3000

### 3. 启动任务队列（可选，用于定时扫描）

```bash
cd backend
source .venv/bin/activate
python -m workers.pipeline
```

## 访问指南

| 页面 | 路径 | 说明 |
|------|------|------|
| 首页 | `/` | 项目概览 |
| 商机发现 | `/opportunities` | 热点扫描 + 商机列表 |
| 商机详情 | `/opportunities/[id]` | 情绪分析、痛点、产品建议 |
| 优化看板 | `/opportunities/[id]/optimize` | 效果评级、优化建议 |
| 效果分析 | `/analytics` | 商机排行榜 |
| 项目列表 | `/projects` | AI 软件工厂项目 |

## 架构概览

```
数据采集 (Hunter)
   ↓ 热点数据 + 评论
情绪分析 (Brain)
   ↓ 情绪/欲望/痛点
商机生成 (Strategist)
   ↓ 商业机会报告
产品生成 (Factory)
   ↓ AI 产品
自动发布 (Publisher)
   ↓ 多平台分发
数据回流 (Analytics + Optimizer)
   ↓ 表现数据
→ 循环优化
```

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| 后端 | FastAPI (Python 3.11) |
| 数据库 | PostgreSQL + Redis |
| 任务队列 | ARQ (async job queue) |
| 爬虫 | Playwright, aiohttp |
| AI | Claude / DeepSeek / LLM API |
| 语音 | CosyVoice2 TTS |
| 图片 | Stable Diffusion (ComfyUI) |

## 部署

### 本地开发

```bash
# 确保 PostgreSQL 和 Redis 运行中
# 后端
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend && PORT=3000 npm run dev
```

### Docker（开发中）

```bash
docker compose up -d
```

## 项目结构

```
autonomous-ai-factory/
├── frontend/                # Next.js 前端
│   ├── app/                 # 页面路由
│   │   ├── opportunities/   # 商机发现页面
│   │   ├── analytics/       # 数据分析页面
│   │   ├── projects/        # AI 项目页面
│   │   └── ...
│   ├── components/          # UI 组件
│   └── lib/                 # API 客户端
├── backend/                 # FastAPI 后端
│   ├── api/                 # REST API 路由
│   │   ├── trends.py        # 趋势扫描 API
│   │   ├── brain.py         # 情绪分析 API
│   │   ├── optimizer.py     # 优化分析 API
│   │   └── ...
│   ├── core/                # 业务逻辑
│   │   ├── hunter/          # 数据采集器
│   │   ├── brain/           # 情绪分析引擎
│   │   ├── strategist/      # 商机生成器
│   │   └── optimizer/       # 性能优化器
│   ├── models/              # 数据库模型
│   ├── workers/             # 后台任务
│   └── main.py              # 入口
├── docs/                    # 文档
│   └── plans/               # 设计文档
└── docker-compose.yml
```
