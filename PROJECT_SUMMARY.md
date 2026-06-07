# Autonomous AI Software Factory — 项目总结

## 一、项目目标

构建一个**全自主 AI 软件工厂平台**：用户输入需求，系统自动生成 PRD、架构设计、代码、测试，并自动部署上线，实现"需求 → 交付"的全流程自动化。

**核心理念：** Input requirements → AI builds, tests, and deploys automatically.

---

## 二、技术栈

| 层 | 技术 |
|---|---|
| **前端** | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| **后端** | FastAPI (Python 3.11), PostgreSQL, Redis + ARQ 队列 |
| **编排** | 自定义 Python Orchestrator，调用 Claude Code 子进程 |
| **测试** | pytest (后端), vitest (前端), Playwright (E2E) |
| **实时** | WebSocket (实时活动流推送) |
| **通知** | QQBot/飞书 (阶段更新通知) |
| **部署** | Docker Compose + GitHub Actions CI |

---

## 三、核心功能

### 3.1 项目管线 (Pipeline)

完整的八阶段状态机，按序执行：

| 阶段 | 状态值 | AI 行为 |
|---|---|---|
| 1. 接收 | `created` | 验证需求完整性 |
| 2. 需求分析 | `requirement_analyzing` | AI 分析需求，生成 PRD |
| 3. 规划 | `planning` | 拆分开发任务，建立依赖关系 |
| 4. 开发 | `developing` | Claude Code 并行执行任务（无依赖任务并发） |
| 5. 测试 | `testing` | 自动生成并运行测试套件 |
| 6. 修复 | `fixing` | 基于错误日志自动修复（最多 3 轮重试） |
| 7. 审查 | `reviewing` | AI 代码审查 + 质量报告 |
| 8. 部署 | `deploying` | 部署到预览环境 |
| 9. 交付 | `delivered` | 生成交付报告 |

**关键特性：**
- **并行执行**：无依赖任务同时执行，多 Wave 调度，大幅缩短总耗时
- **超时保护**：全局超时（默认 600s）+ 每阶段超时（默认 180s）
- **权限门控**：Gatekeeper 控制危险操作（外部 API、DB 迁移、生产发布等）
- **实时推送**：WebSocket 向 UI 推送任务状态变更、日志、测试结果

### 3.2 功能模块

| 模块 | 描述 | API 路由 |
|---|---|---|
| **项目管理** | 创建、查看、重跑项目管线 | `/api/projects` |
| **机会发现** | Reddit 猎人 + MBTI 猎人 + 心理测试产品猎人 + 产品 Hunt 猎人 | `/api/opportunities` |
| **趋势扫描** | 扫描热门趋势，生成机会报告（病毒潜力、ROI 评分、自动化评分） | `/api/trends` |
| **内容优化** | AI 内容优化循环，分析反馈 | `/api/optimizer` |
| **平台发布** | 小红书/抖音/TikTok 平台发布 + QR 登录 + Cookie 管理 | `/api/publish` |
| **TTS 合成** | CosyVoice2 语音合成服务 | `/api/tts` |
| **分析反馈** | 互动数据分析 + 用户反馈收集 | `/api/analytics` |
| **平台登录** | 小红书/抖音 QR 码登录 | `/api/platform_login` |
| **设置** | 项目配置、模型选择、通知设置 | `/api/settings` |
| **WebSocket** | 实时事件推送（5 种事件类型） | `/api/ws` |

### 3.3 前端页面

| 页面 | 功能 |
|---|---|
| **首页** | Hero Section + 四大特性 + 工作流说明 |
| **Dashboard** | 数据概览、项目统计、快速操作 |
| **Projects** | 项目列表、状态筛选、新建项目 |
| **Project Detail** | 管线进度、实时活动流、代码预览、测试报告、Agent 日志 |
| **Opportunities** | 机会发现 + 产品建议 + 变现策略 + 行动计划 |
| **Analytics** | 数据分析 + 互动数据面板 |
| **Settings** | 模型选择、通知配置、权限设置 |

---

## 四、代码统计

| 指标 | 数量 |
|---|---|
| Git 提交数 | 66 (当前分支) |
| 后端 Python 文件 | 88 个 (不含测试) |
| 前端 TypeScript 文件 | 47 个 |
| API 路由 | 16 个模块 |
| 核心模块 | 13 个 |
| 异步 Worker | 7 个 |
| 后端测试 | 8 个测试文件 |
| 前端 UI 组件 | 19 个 |

---

## 五、架构设计

```
用户输入需求
    │
    ▼
┌─────────────────────────────────────────┐
│           Frontend (Next.js 14)         │
│  Projects | Dashboard | Analytics       │
│  WebSocket 实时推送                      │
└───────────────┬─────────────────────────┘
                │ HTTP + WS
                ▼
┌─────────────────────────────────────────┐
│            Backend (FastAPI)             │
│                                          │
│  API Routes ──→ Orchestrator            │
│     │                    │               │
│     ├── Pipeline Worker──→ Planner (PRD) │
│     ├── Pipeline Worker──→ Executor      │
│     │                │     (Claude Code) │
│     │                ▼                   │
│     │           Tester (pytest)          │
│     │                │                   │
│     │                ▼                   │
│     │           Reviewer (Code Review)   │
│     │                │                   │
│     │                ▼                   │
│     │           Deploy (Docker/CI)       │
│     │                │                   │
│     │                ▼                   │
│     │           Delivery Report          │
│     │                                   │
│     ├── Opportunity Hunters (Reddit,    │
│     │    MBTI, ProductHunt)             │
│     ├── Publisher (小红书/抖音/TikTok)   │
│     ├── Trend Scanner                   │
│     └── QQBot/Feishu Notifier           │
│                                          │
│  DB: PostgreSQL │ Queue: Redis + ARQ    │
└─────────────────────────────────────────┘
```

---

## 六、与对标产品对比

| 功能 | AI Factory (本项目) | Cursor | Bolt.new | Replit Agent |
|---|---|---|---|---|
| 需求→PRD 自动生成 | ✅ | ❌ | ❌ | ❌ |
| 自动拆任务+并行执行 | ✅ | ❌ | ❌ | ❌ |
| 自动测试+修复 | ✅ | ❌ | ❌ | ❌ |
| AI 代码审查 | ✅ | ❌ | ❌ | ❌ |
| 自动部署 | ✅ | ❌ | ✅ | ✅ |
| 多平台发布 (小红书/抖音) | ✅ | ❌ | ❌ | ❌ |
| 机会发现 (Reddit趋势) | ✅ | ❌ | ❌ | ❌ |
| 实时活动流推送 | ✅ | ❌ | ❌ | ❌ |
| 权限门控 | ✅ | ❌ | ❌ | ❌ |
| TTS 语音合成 | ✅ | ❌ | ❌ | ❌ |

**差异化定位：** 本项目不仅做代码生成，更是一个**从商业机会发现 → 产品规划 → 开发 → 测试 → 发布**的全链路 AI 工厂平台。

---

## 七、已完成里程碑

- [x] **Phase 1** — 基础管线：需求分析→任务规划→代码开发→测试→部署→交付
- [x] **Phase 2** — 并行执行：多任务并发、Wave 调度、超时保护
- [x] **Phase 3** — 体验优化：代码预览、审查报告、实时活动流、原生 WebSocket
- [x] **Phase 4** — Git 集成、项目模板、删除、增强列表
- [x] **Phase 5** — Webhook、健康检查、重跑、导航优化、模板 UI、日志导出、设置面板
- [x] **Phase 5-C** — 内容优化循环 + .gitignore 清理
- [x] **66 commits**，全功能可用

---

## 八、待开发方向

1. **视频内容生产管线** — Phase 0-5D（去水印→配音→换脸→唇形同步→去重处理→发布）
2. **多模型支持** — 除 Claude Code 外支持 Codex/Claude/自定义模型
3. **协作功能** — 多用户、权限管理、团队项目
4. **监控面板** — 管线执行统计、成本追踪、成功率指标
5. **更多发布平台** — YouTube、Bilibili、快手等

---

*最后更新: 2026-05-20*
*总提交数: 66 | 代码文件: 135 | 测试: 8 个*
