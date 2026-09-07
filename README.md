# 🤖 Go2 巡检系统

基于 SvelteKit + FastAPI + WebSocket 的机器狗巡检控制系统。

---

## 🏗️ 技术栈

### 前端
- [SvelteKit 2.x](https://kit.svelte.dev/) + TypeScript
- [TailwindCSS 3.x](https://tailwindcss.com/)
- WebSocket 实时通信

### 后端
- [FastAPI](https://fastapi.tiangolo.com/) + Python 3.10+
- WebSocket 双向通信
- 宇树 Go2 SDK 集成（计划中）

### 桌面应用（计划）
- [Tauri 2.x](https://tauri.app/)

---

## 📁 项目结构
go2-inspection/
├── frontend/ # SvelteKit 前端
│ ├── src/
│ │ ├── lib/
│ │ │ ├── components/ # UI 组件
│ │ │ ├── services/ # WebSocket + API 服务
│ │ │ ├── stores/ # Svelte 状态管理
│ │ │ └── types/ # TypeScript 类型定义
│ │ ├── routes/ # 页面路由
│ │ └── app.html
│ ├── package.json
│ └── vite.config.ts
├── backend/ # FastAPI 后端
│ ├── app/
│ │ ├── main.py # 入口 + WebSocket 端点
│ │ ├── routers/ # API 路由
│ │ ├── models/ # Pydantic 模型
│ │ └── services/ # 业务逻辑
│ ├── requirements.txt
│ └── run.py
└── README.md


---

## 🚀 快速开始

### 环境要求
- Node.js 18+
- Python 3.10+
- npm / yarn / pnpm

### 1️⃣ 克隆项目
```bash
git clone ...
cd go2-inspection
2️⃣ 前端
bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
3️⃣ 后端
bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
# API 地址 http://localhost:8000
```
4️⃣ 验证通信
前端页面自动连接 WebSocket

后端每 3 秒广播模拟状态

状态面板实时更新

📡 WebSocket 通信协议
消息格式
typescript
// 前端 → 后端
{ "type": "command", "data": { "cmd": "forward" } }

// 后端 → 前端
{ "type": "status_update", "data": { "status": "在线", "battery": 85 } }
支持指令
指令	说明
forward	前进
backward	后退
stop	停止
left	左转
right	右转
standup	站立
sit	坐下
🗺️ 迁移进度
原 MVC 功能	新系统状态
机器狗控制	✅ WebSocket 框架已就绪
状态监控	✅ WebSocket 广播已实现
巡检日志	⏳ 待接入
视频流	⏳ 待接入
地图编辑器	⏳ 待接入
异常检测	⏳ 待接入

## 👥 协作规范
分支策略：main 主分支，feature/* 功能分支

提交信息：<类型>: <简述>，如 feat: 添加视频流组件

代码风格：前端 Prettier + ESLint，后端 Black