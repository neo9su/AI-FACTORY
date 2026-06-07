# 视频内容生产管线 — 实现计划

> **目标：** 在 AI Factory 中接入可视化的视频生产工作流，包含 去水印→配音→换脸→唇形同步→去重处理 五个阶段。

## 架构设计

```
Models         →  VideoProject, VideoPipelineStage, VideoAsset
Backend API    →  /api/v1/video-projects/*  (新模块)
Frontend       →  /video-projects/*  (新页面)
Existing       →  publisher 模块复用（发布到小红书/抖音/TikTok）
```

---

### Task 1: 数据库模型 — VideoProject + VideoPipelineStage + VideoAsset

**目标：** 创建视频生产项目模型，包含管线状态追踪和资产记录。

**文件：**
- 新建: `backend/models/video.py`

### Task 2: 后端 API 路由 — Video Projects CRUD + 管线控制

**目标：** 完整的视频项目 API，支持创建、列表、查看详情、启动管线、执行阶段

**文件：**
- 新建: `backend/api/video_projects.py`

### Task 3: 注册路由到 main.py

**目标：** 将新 API 注册到 FastAPI 应用

**文件：**
- 修改: `backend/main.py`

### Task 4: 前端 API 客户端 — 视频项目类型和请求

**目标：** 在 frontend API 层添加视频项目的类型定义和请求方法

**文件：**
- 修改: `frontend/lib/api.ts`

### Task 5: 前端页面 — 视频项目列表页

**目标：** 显示所有视频项目，状态筛选，新建入口

**文件：**
- 新建: `frontend/app/video-projects/page.tsx`

### Task 6: 前端页面 — 新建视频项目

**目标：** 上传源视频，填写项目信息

**文件：**
- 新建: `frontend/app/video-projects/new/page.tsx`

### Task 7: 前端组件 — 视频管线视图 (PipelineVisualizer)

**目标：** 可视化展示 5 个阶段的执行状态，支持阶段重跑

**文件：**
- 新建: `frontend/components/video-pipeline-visualizer.tsx`

### Task 8: 前端页面 — 视频项目详情页

**目标：** 整合管线可视化、资产预览、发布入口

**文件：**
- 新建: `frontend/app/video-projects/[id]/page.tsx`

### Task 9: 前端导航 — 添加视频生产入口

**目标：** 在导航栏和首页添加视频生产入口

**文件：**
- 修改: `frontend/components/navbar.tsx` (如存在)
- 或 `frontend/app/layout.tsx`

### Task 10: Git 提交

**目标：** 提交全部新增代码

---

## 执行顺序

Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7 → Task 8 → Task 9 → Task 10
