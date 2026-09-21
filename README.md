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
- 📊 **数据化巡检报告**：实时上报、自动录制、完整证据链

---

## 🏗️ 系统架构

```
┌─────────────────┐     WebSocket/HTTP     ┌─────────────────┐
│  笔记本 (前端)   │ ─────────────────────> │  AI机台 (后端)   │
│  Tauri 桌面应用  │ <───────────────────── │  FastAPI 服务    │
│  SvelteKit 内核  │     视频流/状态数据     │                 │
└─────────────────┘                        └─────────────────┘
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
| **笔记本** | 前端展示 | Tauri 桌面应用、视频显示、指令下发、告警弹窗 |
| **AI机台 (Ubuntu)** | 后端服务 | FastAPI + WebSocket + 视频流 + AI检测 + 通知 + 录制 |
| **机器狗 Go2 X** | 执行终端 | 运动控制、摄像头采集 |

### 通信方式

| 链路 | 协议 | 说明 |
| :--- | :--- | :--- |
| 前端 ↔ 后端 | WebSocket | 指令、状态实时双向 |
| 前端 ↔ 后端 | HTTP | 视频流、快照、REST API |
| 前端 → 后端 | mDNS | Rust 端自动发现后端地址 |
| 后端 ↔ 机器狗 | DDS / WebRTC | 网线直连（推荐）/ WiFi（备选） |

---

## 🛠️ 技术栈

### 前端

| 技术 | 版本 | 说明 |
| :--- | :--- | :--- |
| **SvelteKit** | 2.x | 现代 SPA 框架 |
| **TypeScript** | 5.x | 类型安全 |
| **TailwindCSS** | 3.x | 原子化 CSS |
| **Tauri** | 2.x | 桌面应用打包 |
| **Rust** | 1.7x | mDNS 发现（Tauri 内核） |

### 后端

| 技术 | 版本 | 说明 |
| :--- | :--- | :--- |
| **Python** | 3.10+ | 运行时 |
| **FastAPI** | - | Web 框架 |
| **Uvicorn** | - | ASGI 服务器 |
| **OpenCV** | - | 图像处理、颜色检测、视频录制 |
| **WebSocket** | - | 实时通信 |
| **zeroconf** | - | mDNS 广播 |

### 机器狗 SDK

| 方式 | 说明 |
| :--- | :--- |
| **unitree_sdk2py** | 官方 SDK（网线直连） |
| **go2-webrtc-connect** | 社区方案（WiFi 无线，备选） |

### 外部服务

| 服务 | 用途 |
| :--- | :--- |
| **PushPlus** | 异常推送到微信 |
| **企业微信机器人** | 异常推送到工作群 |

---

## ✨ 功能模块

### ✅ 已实现

| 模块 | 状态 | 说明 |
| :--- | :--- | :--- |
| 前后端通信 | ✅ | WebSocket 实时双向通信 |
| mDNS 自动发现 | ✅ | Rust 端自动发现后端，无需手动配 IP |
| 视频流服务 | ✅ | MJPEG 流，浏览器实时显示 |
| 视频全屏 + 画中画 | ✅ | 支持全屏、独立小窗 |
| 时间水印 + REC 标识 | ✅ | 视频叠加实时时间戳和录制状态 |
| 机器狗控制接口 | ✅ | 模拟模式（真机待接入） |
| 状态监控 | ✅ | 电量、任务、在线状态实时更新 |
| 巡检日志 | ✅ | 实时日志滚动显示 |
| 巡检流程 | ✅ | 前端模拟完整巡检流程 |
| ArUco 识别 | ✅ | 起点/终点标记识别 |
| 异常检测（颜色） | ✅ | 火焰、烟雾、漏油识别 |
| 非全屏告警弹窗 | ✅ | 弹窗 + 声音 + 手动确认 |
| 全屏告警 | ✅ | 弹幕 + 频闪 + ESC 自动确认 |
| 告警来源隔离 | ✅ | 弹窗和弹幕互不干扰 |
| 异常通知推送 | ✅ | PushPlus + 企业微信双通道 |
| 巡检录制 | ✅ | 自动录制、时间戳烧录、保留最近 5 个 |
| 录制下载 | ✅ | 列表 + 下载接口 |
| Windows 打包 | ✅ | GitHub Actions 自动构建 |

### 🚧 待接入

| 模块 | 说明 |
| :--- | :--- |
| 真实机器狗控制 | 等机器狗到位后，切换 `USE_MOCK_ROBOT=false` |
| 机器狗摄像头视频流 | 替代 AI 机台摄像头 |
| WiFi 无线控制 | 基于 WebRTC（依赖 AES 密钥） |
| YOLO 视觉模型 | 火焰烟雾模型已就绪，待接入；滴漏模型待训练 |
| 异常截图 + 红框标注 | 日志增强 |
| 日志文件生成 | 巡检日志导出 |

---

## 📁 项目结构

```
go2-inspection/
├── .github/
│   └── workflows/
│       └── build.yml              # GitHub Actions 自动构建
│
├── frontend/                       # 前端 (SvelteKit + Tauri)
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +page.svelte       # 主控制台页面
│   │   │   ├── +layout.svelte     # 全局布局
│   │   │   └── +layout.ts         # SPA 配置
│   │   └── lib/
│   │       ├── components/
│   │       │   ├── VideoStream.svelte      # 视频 + 全屏 + 画中画 + 水印
│   │       │   ├── StatusPanel.svelte      # 状态面板
│   │       │   ├── LogViewer.svelte        # 日志展示
│   │       │   ├── AlertModal.svelte       # 非全屏告警弹窗
│   │       │   ├── FullscreenAlert.svelte  # 全屏弹幕 + 频闪
│   │       │   └── AlertTester.svelte      # 测试面板（dev 专用）
│   │       ├── services/
│   │       │   ├── websocket.ts            # WebSocket 封装
│   │       │   ├── discovery.ts            # mDNS 发现调用
│   │       │   └── detection.ts            # 异常轮询
│   │       └── stores/
│   │           ├── robot.ts                # 机器狗状态
│   │           ├── log.ts                  # 日志
│   │           └── alert.ts                # 告警 + 来源隔离
│   ├── src-tauri/                 # Tauri 桌面应用
│   │   ├── src/
│   │   │   └── lib.rs             # Rust mDNS 命令
│   │   └── tauri.conf.json
│   ├── static/
│   │   ├── logo.png
│   │   └── sounds/
│   │       └── alarm.mp3          # 报警音
│   └── package.json
│
└── backend/                        # 后端 (FastAPI)
    ├── app/
    │   ├── main.py                # FastAPI 入口 + WebSocket + 巡检指令
    │   ├── routers/
    │   │   ├── robot.py           # 机器狗控制
    │   │   ├── camera.py          # 视频流 + 快照
    │   │   ├── detection.py       # ArUco + 异常检测 + 触发通知
    │   │   ├── route.py           # 路线管理
    │   │   └── recording.py       # 录制控制 + 列表 + 下载
    │   ├── services/
    │   │   ├── camera_service.py        # 摄像头单例 + 后台采集
    │   │   ├── recording_service.py     # 录制 + 时间戳 + 文件保留
    │   │   ├── detection_service.py     # 颜色检测算法
    │   │   ├── notification_service.py  # PushPlus + 企业微信
    │   │   ├── robot_interface.py       # 抽象接口
    │   │   ├── robot_mock.py            # 模拟实现
    │   │   ├── robot_real.py            # 真机实现
    │   │   └── robot_factory.py         # 工厂函数
    │   ├── models/
    │   │   ├── robot.py           # Command / RobotStatus
    │   │   └── route.py           # RoutePlan
    │   └── utils/
    │       ├── mdns_service.py          # mDNS 广播
    │       └── websocket_manager.py     # WS 连接池
    ├── data/
    │   └── routes.json            # 路线数据
    ├── recordings/                # 录制文件输出（gitignore）
    ├── .env                       # 敏感配置（gitignore）
    ├── requirements.txt
    └── run.py
```

---

## 🚀 快速开始

### 前置要求

- **AI机台**：Ubuntu 22.04，Python 3.10+
- **笔记本**：Node.js 18+，npm（开发时）/ 直接安装打包好的 exe（比赛时）
- **网络**：两台设备处于**同一局域网**（路由器或手机热点）

### 后端启动（AI机台）

```bash
# 1. 进入后端目录
cd go2-inspection/backend

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 .env（通知服务凭证）
cat > .env << 'EOF'
PUSHPLUS_TOKEN=你的PushPlus_Token
WECOM_WEBHOOK=你的企业微信Webhook地址
EOF

# 5. 设置模拟模式（无机器狗时）
export USE_MOCK_ROBOT=true

# 6. 启动服务
python run.py
```

服务启动后：
- API 文档：`http://<AI机台IP>:8000/docs`
- 健康检查：`http://<AI机台IP>:8000/health`

### 前端启动（开发模式）

```bash
cd go2-inspection/frontend
npm install
npm run dev
npm run tauri dev(tauri环境开发)
# 浏览器访问 http://localhost:5173
```

### 前端启动（比赛模式）

从 GitHub Actions 下载 Windows 安装包，双击安装，从开始菜单启动。**应用会自动通过 mDNS 发现后端，无需配置 IP。**

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
| `GET` | `/api/route/default` | 默认路线 |
| `POST` | `/api/route/save` | 保存路线 |
| `POST` | `/api/route/confirm` | 确认路线 |
| `POST` | `/api/recording/start` | 开始录制 |
| `POST` | `/api/recording/stop` | 停止录制 |
| `GET` | `/api/recording/status` | 录制状态 |
| `GET` | `/api/recording/list` | 录制文件列表 |
| `GET` | `/api/recording/download/{filename}` | 下载录制文件 |
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

**运动指令**：`forward` / `backward` / `left` / `right` / `stop` / `standup` / `sit`

**巡检指令**：`start_inspection`（开始巡检 + 启动录制）/ `stop_inspection`（结束巡检 + 停止录制）/ `emergency_stop`（急停 + 停止录制）

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

## 🔔 告警系统

### 触发链

```
检测到异常（颜色检测 / YOLO）
    ↓
后端 /api/detection/anomaly 返回 has_anomaly=true
    ↓
后端触发通知（PushPlus + 企业微信，5分钟冷却）
    ↓
前端轮询发现异常 → 推入 alertStore
    ↓
根据当前是否全屏，分流到两个通道：
    ├─ 非全屏：AlertModal 弹窗 + 声音 + 手动确认
    └─ 全屏：FullscreenAlert 弹幕 + 频闪 + 声音 + ESC 自动确认
```

### 告警来源隔离

| 来源 | 展示通道 | 确认方式 |
| :--- | :--- | :--- |
| 非全屏产生 | Modal 弹窗 | 点"已知晓"按钮 |
| 全屏产生 | 弹幕 + 频闪 | 按 ESC 退出全屏自动确认 |

两个通道互不干扰。

---

## 🎬 录制系统

### 触发时机

| 事件 | 动作 |
| :--- | :--- |
| 开始巡检 | `recording_service.start()` |
| 巡检完成 | `recording_service.stop()` |
| 紧急停止 | `recording_service.stop()` |

### 录制特性

- 分辨率：1280×720
- 帧率：25 fps
- 时间戳：烧录在左上角
- 保留策略：最近 5 个文件

### 文件位置

```
backend/recordings/
├── 20260921_153045_inspection.mp4
├── 20260921_162030_inspection.mp4
└── ...
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

## 📦 打包与部署

### 自动构建（GitHub Actions）

推送代码到 `develop` 分支后，GitHub Actions 自动构建 Windows 安装包：

```
https://github.com/Charlirtang-2007/go2-inspection/actions
```

构建产物：
- `go2-inspection-windows-xxxxx.zip`
  - `msi/Go2智能巡检_0.1.0_x64_zh-CN.msi`
  - `nsis/Go2智能巡检_0.1.0_x64-setup.exe`

### 手动构建

```bash
cd frontend
npm install -D @tauri-apps/cli@latest
npx tauri build
```

---

## ⚠️ 常见问题

### 1. 前端视频流不显示

- 确认后端 `/api/camera/video` 可访问
- 检查浏览器 F12 控制台，查看是否有 CORS 或网络错误
- 确认摄像头被 `camera_service` 正确持有（后端启动时应有 `✅ CameraService: 摄像头已启动`）

### 2. WebSocket 连接失败

- 确认 AI机台防火墙：`sudo ufw allow 8000`
- 在浏览器控制台测试：
  ```javascript
  new WebSocket('ws://<AI机台IP>:8000/ws')
  ```

### 3. mDNS 发现失败

- 确认 AI机台 和后端在同一局域网
- 手机热点可能开启客户端隔离，换路由器
- 检查 5353/udp 端口：`sudo ufw allow 5353/udp`

### 4. 告警通知收不到

- 检查 `.env` 里的 `PUSHPLUS_TOKEN` 和 `WECOM_WEBHOOK`
- 检查后端终端日志是否有 `✅ PushPlus 已发送`
- 同一异常 5 分钟冷却，测试时改 `notification_service.py` 里 `self.cooldown = 0`

### 5. 环境混乱

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
- [x] mDNS 自动发现（Tauri + Rust）
- [x] 非全屏弹窗 + 声音 + 确认
- [x] 全屏弹幕 + 频闪 + ESC 确认
- [x] 告警来源隔离
- [x] 通知推送（PushPlus + 企业微信）
- [x] 视频全屏 + 画中画
- [x] 时间水印 + REC 标识
- [x] 录制 + 下载
- [x] Windows 打包（GitHub Actions）
- [ ] 接入真实机器狗
- [ ] 机器狗摄像头视频流
- [ ] WiFi 无线控制
- [ ] YOLO 视觉模型接入
- [ ] 滴漏数据集采集与训练
- [ ] 异常截图 + 红框标注
- [ ] 场地道具与演示准备

---

## 👥 团队

- **项目负责**：Charlirtang（项目架构，前后端通信，整个后端）
- **前端开发**：Forward-going-Yang（前端页面设置，UI 界面美化）
- **技术栈**：SvelteKit + FastAPI + WebSocket + Tauri
- **硬件平台**：宇树 Go2 X 可开发版

---

## 📄 许可

本项目仅用于职业院校技能大赛备赛，未经许可请勿用于商业用途。
