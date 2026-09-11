# 🤖 Go2 智能巡检系统

> 基于宇树 Go2 X 机器狗的智慧工厂/园区 AI 巡检系统
> 参赛项目：职业院校技能大赛——新一代信息技术赛道

---

## 📖 项目简介

本项目旨在解决工业场景下**人工巡检风险高、频次低、数据不标准**的痛点，通过机器狗自主巡检 + AI 视觉识别，实现设备异常（火焰、烟雾、漏油）的自动发现与实时上报。

### 核心价值

- 🏭 **替代人工进入危险区域**：高温、有毒、密闭环境下人员无法长时间停留
- 🔄 **7×24小时不间断巡检**：标准化的巡检路线与频次
- 🧠 **AI 视觉识别异常**：火焰、烟雾、漏油等常见隐患自动识别
- 📊 **数据化巡检报告**：实时上报、自动生成报告、可追溯

---

## 🏗️ 系统架构

```
┌─────────────────┐     WebSocket/HTTP     ┌─────────────────┐
│  笔记本 (前端)   │ ─────────────────────> │  AI机台 (后端)   │
│  SvelteKit 控制台│ <───────────────────── │  FastAPI 服务    │
└─────────────────┘     视频流/状态数据     └─────────────────┘
                                                    │
                                                    │ 网线/WiFi
                                                    ▼
                                            ┌─────────────────┐
                                            │  机器狗 Go2 X    │
                                            │  执行 + 采集     │
                                            └─────────────────┘
```

### 设备职责

| 设备 | 角色 | 运行内容 |
| :--- | :--- | :--- |
| **笔记本** | 前端展示 | SvelteKit 控制台、视频显示、指令下发 |
| **AI机台 (Ubuntu)** | 后端服务 | FastAPI + WebSocket + 视频流 + AI检测 |
| **机器狗 Go2 X** | 执行终端 | 运动控制、摄像头采集 |

---

## 🛠️ 技术栈

### 前端

| 技术 | 版本 | 说明 |
| :--- | :--- | :--- |
| **SvelteKit** | 2.x | 现代 SPA 框架 |
| **TypeScript** | 5.x | 类型安全 |
| **TailwindCSS** | 3.x | 原子化 CSS |
| **WebSocket** | - | 实时双向通信 |

### 后端

| 技术 | 版本 | 说明 |
| :--- | :--- | :--- |
| **Python** | 3.10+ | 运行时 |
| **FastAPI** | - | Web 框架 |
| **Uvicorn** | - | ASGI 服务器 |
| **OpenCV** | - | 图像处理、颜色检测 |
| **WebSocket** | - | 实时通信 |

### 机器狗 SDK

| 方式 | 说明 |
| :--- | :--- |
| **unitree_sdk2py** | 官方 SDK（网线直连） |
| **go2-webrtc-connect** | 社区方案（WiFi 无线，备选） |

---

## ✨ 功能模块

### ✅ 已实现

| 模块 | 状态 | 说明 |
| :--- | :--- | :--- |
| 前后端通信 | ✅ | WebSocket 实时双向通信 |
| 视频流服务 | ✅ | MJPEG 流，浏览器实时显示 |
| 机器狗控制接口 | ✅ | 模拟模式（真机待接入） |
| 状态监控 | ✅ | 电量、任务、在线状态实时更新 |
| 巡检日志 | ✅ | 实时日志滚动显示 |
| 巡检流程 | ✅ | 前端模拟完整巡检流程 |
| ArUco 识别 | ✅ | 起点/终点标记识别 |
| 异常检测（颜色） | ✅ | 火焰、烟雾、漏油识别 |

### 🚧 待接入

| 模块 | 说明 |
| :--- | :--- |
| 真实机器狗控制 | 等机器狗到位后，切换 `USE_MOCK_ROBOT=false` |
| 机器狗摄像头视频流 | 替代 AI 机台摄像头 |
| WiFi 无线控制 | 基于 WebRTC（依赖 AES 密钥） |

---

## 📁 项目结构

```
go2-inspection/
├── frontend/                 # 前端 (SvelteKit)
│   ├── src/
│   │   ├── routes/
│   │   │   └── +page.svelte  # 主控制台页面
│   │   ├── lib/
│   │   │   ├── components/   # UI 组件
│   │   │   │   ├── VideoStream.svelte
│   │   │   │   └── LogViewer.svelte
│   │   │   ├── services/
│   │   │   │   └── websocket.ts   # WebSocket 服务
│   │   │   └── stores/
│   │   │       ├── robot.ts       # 机器狗状态 store
│   │   │       └── log.ts         # 日志 store
│   │   └── app.html
│   └── package.json
│
└── backend/                  # 后端 (FastAPI)
    ├── app/
    │   ├── main.py           # FastAPI 入口 + WebSocket
    │   ├── routers/
    │   │   ├── robot.py      # 机器狗控制
    │   │   ├── camera.py     # 视频流 + 快照
    │   │   ├── detection.py  # ArUco + 异常检测
    │   │   └── route.py      # 路线管理
    │   ├── services/
    │   │   ├── robot_interface.py   # 抽象接口
    │   │   ├── robot_mock.py        # 模拟实现
    │   │   ├── robot_real.py        # 真机实现
    │   │   └── robot_factory.py     # 工厂函数
    │   ├── models/
    │   │   └── robot.py      # 数据模型
    │   └── utils/
    │       └── websocket_manager.py
    ├── requirements.txt
    └── run.py
```

---

## 🚀 快速开始

### 前置要求

- **AI机台**：Ubuntu 22.04，Python 3.10+
- **笔记本**：Node.js 18+，npm
- **网络**：两台设备处于**同一局域网**

### 后端启动（AI机台）

```bash
# 1. 进入后端目录
cd go2-inspection/backend

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 设置模拟模式（无机器狗时）
export USE_MOCK_ROBOT=true

# 5. 启动服务
python run.py
```

服务启动后：
- API 文档：`http://<AI机台IP>:8000/docs`
- 健康检查：`http://<AI机台IP>:8000/health`

### 前端启动（笔记本）

```bash
# 1. 进入前端目录
cd go2-inspection/frontend

# 2. 安装依赖
npm install

# 3. 配置后端地址（在 .env 中）
echo "VITE_API_BASE=http://<AI机台IP>:8000" > .env
echo "VITE_WS_BASE=ws://<AI机台IP>:8000" >> .env

# 4. 启动开发服务器
npm run dev
```

浏览器访问 `http://localhost:5173` 即可看到控制台。

---

## 🔌 API 接口一览

| 方法 | 路径 | 功能 |
| :--- | :--- | :--- |
| `GET` | `/api/robot/status` | 获取机器狗状态 |
| `POST` | `/api/robot/command` | 发送控制指令 |
| `POST` | `/api/robot/connect` | 连接机器狗 |
| `POST` | `/api/robot/disconnect` | 断开连接 |
| `POST` | `/api/robot/emergency_stop` | 紧急停止 |
| `GET` | `/api/camera/video` | MJPEG 视频流 |
| `GET` | `/api/camera/snapshot` | 单帧快照 |
| `GET` | `/api/detection/aruco` | ArUco 标记检测 |
| `GET` | `/api/detection/anomaly` | 异常检测 |
| `GET` | `/api/route/list` | 路线列表 |
| `WS` | `/ws` | WebSocket 实时通信 |

---

## 📡 WebSocket 消息格式

### 客户端 → 服务端

```json
{
  "type": "command",
  "data": { "cmd": "forward" }
}
```

支持的指令：`forward` / `backward` / `left` / `right` / `stop` / `standup` / `sit` / `emergency_stop`

### 服务端 → 客户端

```json
{
  "type": "command_ack",
  "data": {
    "cmd": "forward",
    "status": "executed",
    "detail": {
      "success": true,
      "action": "move",
      "velocity": [0.3, 0, 0]
    }
  }
}
```

---

## 🐕 机器狗接入指南

### 切换模拟 → 真机

```bash
# 关闭模拟模式
export USE_MOCK_ROBOT=false

# 指定网卡（用 ifconfig 查看）
export ROBOT_NETWORK_INTERFACE=enp2s0

# 重启后端
python run.py
```

### 网线直连模式（推荐）

1. 用网线连接机器狗与 AI 机台
2. AI 机台有线网卡 IP 设为 `192.168.123.222`
3. 验证连通：`ping 192.168.123.161`

### WiFi 无线模式（备选）

1. AI 机台连接机器狗热点 `Unitree-XXXXXX`
2. 使用 `go2-webrtc-connect` 建立连接
3. ⚠️ 需 AES 密钥，官方不提供，需社区方案

---

## ⚠️ 常见问题

### 1. 前端视频流不显示

- 确认后端 `/api/camera/video` 可访问
- 检查前端 `.env` 中 `VITE_API_BASE` 是否指向**AI机台IP**（不是 `localhost`）
- 打开浏览器 F12 控制台，查看是否有 CORS 或网络错误

### 2. WebSocket 连接失败

- 确认 `.env` 中 `VITE_WS_BASE` 是 `ws://<AI机台IP>:8000`
- 检查防火墙：`sudo ufw allow 8000`
- 在浏览器控制台测试：
  ```javascript
  new WebSocket('ws://<AI机台IP>:8000/ws')
  ```

### 3. 环境混乱

- 必须在 `(venv)` 虚拟环境下运行后端
- 不要在 `(base)` conda 环境下运行

---

## 📌 开发路线图

- [x] 前后端通信（WebSocket）
- [x] 视频流服务（MJPEG）
- [x] 机器狗控制接口（模拟）
- [x] 巡检流程前端模拟
- [x] ArUco 标记识别
- [x] 异常检测（颜色检测）
- [ ] 接入真实机器狗
- [ ] 机器狗摄像头视频流
- [ ] WiFi 无线控制
- [ ] 场地道具与演示准备

---

## 👥 团队

- **项目负责**：Charlirtang：项目架构，前后端通信，整个后端；
- Forward-going-Yang：前端页面设置，ui界面美化；
- **技术栈**：SvelteKit + FastAPI + WebSocket
- **硬件平台**：宇树 Go2 X 可开发版

---

## 📄 许可

本项目仅用于职业院校技能大赛备赛，未经许可请勿用于商业用途。
```
