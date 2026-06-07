# 监控面板 — 实现计划

> **目标：** 增强 Dashboard 为全功能监控面板，包含管线耗时、成本、成功率、错误分布可视化

### Task 1: 后端 stats API — 新增管线深度统计
- `GET /stats/stages` — 每阶段统计（执行次数、平均耗时、失败率）
- `GET /stats/errors` — 错误分布（按阶段/类型分组）
- `GET /stats/history` — 最近管线运行记录

### Task 2: 前端 Dashboard — 重写为监控面板
- KPI 卡片 + 成功率环形图
- 阶段耗时柱状图
- 错误分布饼图
- 管线运行历史表
- 自动刷新
