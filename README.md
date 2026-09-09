# 🤖 Go2 巡检系统

基于 **SvelteKit + FastAPI + WebSocket** 的机器狗智能巡检控制系统。

---

## 📋 项目状态

| 模块 | 状态 | 说明 |
| :--- | :--- | :--- |
| FastAPI 后端 | ✅ 已完成 | 路由、服务、WebSocket 已就绪 |
| SvelteKit 前端 | ⚠️ 骨架完成 | 框架已搭建，页面持续开发中 |
| 机器狗 SDK | ⏳ 待接入 | 需机器狗到位后测试 |
| 视觉模型 | ⏳ 待训练 | 准备火焰/烟雾/漏油数据集 |

---

## 🏗️ 技术架构

### 整体架构（三层分离）
┌─────────────────────────────────────────────────────────────────────┐
│ 前端 (SvelteKit + TailwindCSS) │
│ - 主控制台（状态监控 / 控制指令 / 视频流 / 巡检日志） │
│ - 地图编辑器（路线规划 / 甲方乙方视角） │
│ - WebSocket 实时通信 │
└─────────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│ 后端 (FastAPI + WebSocket) │
│ - RESTful API（控制 / 检测 / 路线管理） │
│ - WebSocket 实时推送（状态 / 日志 / 报警） │
│ - 视觉检测服务（ArUco / 颜色检测 / YOLO） │
└─────────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│ 机器狗 (Go2 X) + SDK │
│ - 官方 unitree_sdk2py（网线直连） │
│ - 社区 go2-webrtc-connect（WiFi 备选） │
└─────────────────────────────────────────────────────────────────────┘


### 技术栈

| 层级 | 技术 |
| :--- | :--- |
| **前端框架** | SvelteKit 2.x + TypeScript |
| **样式** | TailwindCSS 3.x |
| **实时通信** | WebSocket |
| **后端框架** | FastAPI + Python 3.10+ |
| **视觉处理** | OpenCV + YOLO（计划中） |
| **机器狗控制** | unitree_sdk2py / go2-webrtc-connect |
| **桌面打包** | Tauri 2.x（计划中） |

---

## 📁 项目结构
go2-inspection/
├── frontend/ # SvelteKit 前端
│ ├── src/
│ │ ├── routes/ # 页面路由
│ │ │ ├── +layout.svelte # 全局布局
│ │ │ ├── +page.svelte # 主控制台
│ │ │ └── map-editor/ # 地图编辑器（待开发）
│ │ ├── lib/
│ │ │ ├── components/ # UI 组件
│ │ │ ├── services/ # WebSocket + API 服务
│ │ │ ├── stores/ # Svelte 状态管理
│ │ │ └── types/ # TypeScript 类型定义
│ │ ├── app.html
│ │ └── app.css
│ ├── package.json
│ └── vite.config.ts
│
├── backend/ # FastAPI 后端
│ ├── app/
│ │ ├── main.py # 入口 + WebSocket 端点
│ │ ├── routers/ # API 路由
│ │ │ ├── robot.py # 机器狗控制
│ │ │ ├── camera.py # 视频流
│ │ │ ├── detection.py # 视觉检测
│ │ │ └── route.py # 路线管理
│ │ ├── services/ # 业务逻辑
│ │ │ ├── camera_service.py # 摄像头管理
│ │ │ └── detection_service.py # ArUco + 颜色检测
│ │ ├── models/ # Pydantic 数据模型
│ │ │ ├── robot.py
│ │ │ └── route.py
│ │ └── utils/
│ │ └── websocket_manager.py # WebSocket 连接管理
│ ├── data/
│ │ └── routes.json # 路线存储
│ ├── requirements.txt
│ └── run.py
│
└── README.md


---

## 🚀 快速开始

### 环境要求

| 工具 | 版本要求 |
| :--- | :--- |
| Node.js | ≥ 18.x |
| Python | ≥ 3.10 |
| npm | ≥ 8.x |

### 1️⃣ 克隆项目

```bash
git clone https://github.com/Charlirtang-2007/go2-inspection.git
cd go2-inspection
2️⃣ 启动前端
bash
cd frontend
npm install
npm run dev
访问 http://localhost:5173

3️⃣ 启动后端
bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
访问 http://localhost:8000 查看 API 文档
```
📡 API 接口
方法	路径	功能
GET	/api/robot/status	获取机器狗状态
POST	/api/robot/command	发送控制指令
GET	/api/camera/video	MJPEG 视频流
GET	/api/camera/snapshot	获取一帧截图
GET	/api/detection/aruco	ArUco 标记检测
GET	/api/detection/anomaly	异常检测（火焰/烟雾/漏油）
GET	/api/route/list	获取路线列表
POST	/api/route/save	保存路线
POST	/api/route/confirm	确认路线生效
WS	/ws	WebSocket 实时通信
🔌 WebSocket 协议
消息格式
json
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
✅ 已完成功能
后端（100%）
☑ FastAPI 项目骨架搭建
☑ WebSocket 实时通信（连接管理 + 消息路由）
☑ 机器狗控制接口（模拟状态 + 指令处理）
☑ 视频流接口（MJPEG + 快照）
☑ 视觉检测接口（ArUco + 颜色检测）
☑ 路线管理接口（CRUD + 甲方/乙方流程）
☑ 路线 JSON 文件存储
☑ CORS 跨域配置
☑ 健康检查接口
前端（骨架已完成）
☑ SvelteKit + TypeScript + TailwindCSS 配置
☑ 项目目录结构
☑ 路径别名配置（#lib/）
☑ WebSocket 服务封装（连接/重连/消息收发）
☑ 状态管理 Stores（robot / log）
☑ 主控制台页面（+page.svelte）
☑ 状态面板组件（StatusPanel.svelte）
☑ 前端 ↔ 后端 API 联调通过
⏳ 待完成功能
前端（组员任务）
□ 控制按钮组件（ControlButtons.svelte）
□ 视频流组件（VideoStream.svelte）
□ 日志查看器组件（LogViewer.svelte）
□ 侧边栏组件（Sidebar.svelte）
□ 地图编辑器页面（/map-editor）
□ 历史日志页面（/logs）
□ 响应式适配
机器狗接入
□ SDK 环境配置（教师主机 Ubuntu）
□ 网线直连通信测试
□ 视频流获取测试
□ 真实状态推送（替换模拟数据）
视觉模型
□ 数据集收集（火焰/烟雾/漏油各 50+ 张）
□ YOLO 模型训练
□ 模型集成到后端（替换颜色检测）
📝 开发规范
前端
组件文件用 PascalCase（如 StatusPanel.svelte）

使用 #lib/ 别名导入（如 #lib/components/StatusPanel.svelte）

Props 使用 $props()（Svelte 5 语法）

样式优先使用 TailwindCSS

后端
路由文件放在 routers/ 目录

业务逻辑放在 services/ 目录

数据模型用 Pydantic

异步 I/O 使用 async/await

👥 团队分工
角色	职责
前端开发	SvelteKit 页面 + 组件开发
后端开发	FastAPI 接口 + SDK 接入
视觉模型	YOLO 训练 + 模型集成
