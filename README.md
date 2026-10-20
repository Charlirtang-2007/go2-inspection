# 🤖 Go2 智能巡检系统

> 基于宇树 Go2 X 机器狗的智慧工厂/园区 AI 巡检系统  
> 参赛项目：职业院校技能大赛——新一代信息技术赛道

---

## 📖 项目简介

本项目旨在解决工业场景下**人工巡检风险高、频次低、数据不标准**的痛点，通过机器狗自主巡检 + AI 视觉识别，实现设备异常（火焰、烟雾、滴漏）的自动发现与实时上报。

### 核心价值

- 🏭 **替代人工进入危险区域**：高温、有毒、密闭环境下人员无法长时间停留
- 🔄 **7×24 小时不间断巡检**：标准化的巡检路线与频次
- 🧠 **AI 视觉识别异常**：火焰、烟雾、滴漏等常见隐患自动识别
- 📊 **数据化巡检报告**：实时上报、自动录制、完整证据链

---

## 🏗️ 系统架构

为了突破传统网线直连的物理限制，本项目采用 **「前端 - 主控 - 边缘网关 - 机器狗」** 的四级解耦架构。

```
┌─────────────────┐     WebSocket/HTTP     ┌─────────────────┐
│  笔记本 (前端)   │ ─────────────────────> │  AI机台 (后端)   │
│  Tauri 桌面应用  │ <───────────────────── │  FastAPI 服务    │
│  SvelteKit 内核  │     视频流/状态数据     │ (AI检测/录制/通知)│
└─────────────────┘                        └─────────────────┘
         │                                          │
         │ WiFi                                     │ WiFi
         │（手机热点/局域网）                       │（手机热点/局域网）
         │                                          │
         └──────────────┬───────────────────────────┘
                        │
                        │ 同一局域网 HTTP 通信
                        ▼
                ┌─────────────────┐
                │  K2B (边缘网关)  │
                │  unitree_sdk2py │
                │  FastAPI 转发   │
                └─────────────────┘
                        │
                        │ 网线直连 (DDS)
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
| **AI机台 (Ubuntu)** | 主控后端 | FastAPI + WebSocket + VLM检测 + 通知 + 录制 |
| **K2B (全志H618)** | 边缘网关 | 跑 `unitree_sdk2py`，负责 DDS 协议与 HTTP/WS 的透传转发 |
| **机器狗 Go2 X** | 执行终端 | 运动控制、摄像头采集 |

### 通信方式

| 链路 | 协议 | 说明 |
| :--- | :--- | :--- |
| 前端 ↔ AI机台 | WebSocket / HTTP | 指令、状态实时双向、视频流拉取 |
| 前端 → AI机台 | mDNS | Rust 端自动发现后端地址 |
| AI机台 ↔ K2B | HTTP (REST / MJPEG) | 跨网络控制与视频流透传 |
| K2B ↔ 机器狗 | DDS | 网线直连，同一 `192.168.123.x` 网段 |
| 后端 → 手机 | HTTPS | PushPlus / 企业微信异常推送 |

---

## 🛠️ 技术栈

### 前端
- **SvelteKit** 2.x + **TypeScript** + **TailwindCSS**
- **Tauri** 2.x + **Rust** (负责 mDNS 局域网发现)

### 后端 (AI机台)
- **Python** 3.10+ + **FastAPI** + **Uvicorn**
- **OpenCV** (视频流处理与录制) + **requests** (与K2B通信)
- **阿里云百炼 (千问 `qwen3-vl-plus`)**：云端 VLM 视觉识别
- **WebSocket** / **zeroconf**

### 边缘网关 (K2B)
- **Ubuntu 22.04 Server** (ARM64)
- **CycloneDDS 0.10.x** (源码编译)
- **unitree_sdk2py** + **FastAPI** + **uvicorn**
- **systemd** (开机自启常驻服务)

---

## ✨ 功能模块

### ✅ 已实现

| 模块 | 状态 | 说明 |
| :--- | :--- | :--- |
| **K2B 边缘网关** | ✅ | 跨网络 HTTP 控狗，MJPEG 视频流透传，systemd 开机自启 |
| **全向控制** | ✅ | 站立、趴下、前进、后退、左转、右转、停止 |
| 前后端通信 | ✅ | WebSocket 实时双向通信 |
| mDNS 自动发现 | ✅ | 前端 Rust 端自动发现后端 |
| **三路检测器架构** | ✅ | preset (兜底) / yolo (本地) / vlm (云端)，环境变量切换 |
| **VLM 云端检测** | ✅ | 千问 `qwen3-vl-plus`，实测识别烟雾置信度 0.85+ |
| **异常自动推送** | ✅ | 后端 worker 状态翻转直接触发，不依赖前端轮询 |
| 视频流服务 | ✅ | MJPEG 流，支持全屏、画中画、时间水印、REC 标识 |
| 告警系统 | ✅ | 全屏弹幕/频闪 + 非全屏弹窗 + 声音 + 手动确认 + 来源隔离 |
| 巡检录制 | ✅ | 自动录制、时间戳烧录、保留最近 5 个、前端下载 |
| Windows 打包 | ✅ | GitHub Actions 自动构建安装包 |

### 🚧 待接入 / 待办

| 模块 | 说明 |
| :--- | :--- |
| 异常截图前端展示 | 后端已保存 jpg，前端需接入图片展示 (带红框) |
| 演示流程真机化 | 前端发点位 -> 后端执行 (结合 ArUco 点位与复检逻辑) |
| 日志文件生成 | 巡检日志导出为 JSON + 图片打包 ZIP |
| ArUco 铭牌设计打印 | 制作 A5 铭牌贴在场地，并实现识别联动 |
| 赛场防掉电保护 | K2B 开启 Overlayroot (防止直接断电导致系统损坏) |

---

## 📁 项目结构

```text
go2-inspection/
├── .github/workflows/build.yml # GitHub Actions 自动构建
├── frontend/                   # 前端 (SvelteKit + Tauri)
│   ├── src/
│   │   ├── routes/+page.svelte
│   │   └── lib/
│   │       ├── components/     # VideoStream, AlertModal, DetectionDebug...
│   │       ├── services/       # websocket.ts, discovery.ts, detection.ts
│   │       └── stores/         # robot.ts, log.ts, alert.ts
│   └── src-tauri/              # Rust mDNS 命令
└── backend/                    # 主控后端 (FastAPI)
    ├── app/
    │   ├── main.py             # 入口 + WebSocket
    │   ├── routers/            # robot, camera, detection, route, recording
    │   ├── services/
    │   │   ├── camera_service.py        # 拉取K2B视频流 + 发布订阅
    │   │   ├── detection_service.py     # 三路检测调度 + worker + 事件回调
    │   │   ├── robot_real.py            # 通过 requests 发指令给 K2B
    │   │   ├── notification_service.py  # PushPlus + 企业微信
    │   │   └── detectors/               # yolo_detector, vlm_detector, preset_detector
    │   ├── models/
    │   └── utils/
    ├── models/smoke.pt         # YOLO 备用模型
    ├── .env.example
    └── run.py

# 边缘网关脚本 (存放在 K2B 的 /home/kickpi/gateway.py)
```

---

## 🚀 快速开始

### 前置要求
- **K2B**：已烧录 Ubuntu 22.04 Server，已编译 DDS，已配好 `gateway.py` 并设为 systemd 服务。
- **AI机台**：Ubuntu 22.04，Python 3.10+，安装了 `requests` 和 `opencv-python`。
- **笔记本**：Node.js 18+，前端打包后可直接双击 exe 运行。
- **网络**：三台设备处于同一局域网（推荐使用稳定的手机热点或随身 WiFi）。

### 1. K2B 网关启动 (开机自启)
K2B 联网后，连上狗，直接插电开机。网关已配置为 systemd 服务，会自动运行。
检查状态：
```bash
systemctl status go2-gateway.service
```

### 2. AI机台部署与启动
```bash
cd go2-inspection/backend
source venv/bin/activate
pip install -r requirements.txt

# 关键配置 .env
vim .env
```
`.env` 必备项：
```bash
K2B_IP=192.168.62.240     # K2B 的局域网 IP
DETECTION_ENGINE=vlm      # 默认使用云端千问进行检测
DASHSCOPE_API_KEY=sk-xxx  # 千问 API Key
PUSHPLUS_TOKEN=xxx        # 微信推送
WECOM_WEBHOOK=xxx         # 企微推送
```
启动后端：
```bash
python run.py
```
*预期日志：`✅ 成功连接 K2B 视频流` 和 `✅ [Real] 成功连接 K2B 边缘网关`。*

### 3. 前端启动
打开 Tauri 桌面应用，自动通过 mDNS 发现 AI 机台，显示视频流。

---

## ⚠️ 常见问题 (FAQ)

### 1. AI机台报错 `ModuleNotFoundError: No module named 'requests'`
- 在 AI机台的虚拟环境中执行：`pip install requests`。

### 2. AI机台无法连接 K2B 视频流
- 检查 AI机台是否可以 `ping K2B_IP`。
- SSH 登录 K2B，查看网关状态：`systemctl status go2-gateway.service`。
- 确保 K2B 的网线连着狗，且狗已开机。

### 3. K2B 编译 SDK 时找不到 `Python.h`
- 在 K2B 上执行：`sudo apt install python3-dev`，然后重新 `pip3 install -e .`。

### 4. 控狗按钮部分失效
- 检查 K2B 上的 `gateway.py`，确认指令映射（如 `left`, `right`, `backward`）是否在 `SportClient` 中正确调用了对应的接口（`Move`）。

### 5. VLM 调用报错 `Model not exist`
- 检查 `.env` 中 `VLM_MODEL=qwen3-vl-plus` 是否拼写正确。

### 6. K2B 重启后 IP 变了怎么办
- 建议在路由器/热点管理后台，通过 K2B 的 MAC 地址绑定固定 IP。
- 或者后续升级 AI机台代码，通过 `zeroconf` (mDNS) 自动发现 `_go2-edge._tcp`。

---

## 📌 开发路线图

- [x] 前后端通信（WebSocket）
- [x] 视频流服务（MJPEG）
- [x] 机器狗控制接口（模拟 / 真机直连）
- [x] ArUco 标记识别
- [x] mDNS 自动发现（Tauri + Rust）
- [x] 告警链路（弹窗/弹幕/声音/来源隔离）
- [x] 通知推送（PushPlus + 企业微信）
- [x] 视频全屏 + 画中画 + 时间水印 + REC 标识
- [x] 录制 + 下载
- [x] Windows 打包（GitHub Actions）
- [x] VLM 云端检测接入（千问 qwen3-vl-plus）
- [x] 三路检测器架构（preset / yolo / vlm）
- [x] 异常自动推送（不依赖前端轮询）
- [x] **K2B 边缘网关架构落地（跨网络控狗 + 视频流 + systemd）**
- [ ] 异常截图前端展示（带红框）
- [ ] 巡检流程真机化（路线点位 + 复检逻辑）
- [ ] 日志打包（JSON + ZIP）
- [ ] ArUco 铭牌打印及现场布置
- [ ] K2B 防掉电优化（Overlayroot）
- [ ] 场地道具采购与演练

---

## 👥 团队

- **项目负责**：Charlirtang（项目架构，前后端通信，整个后端）
- **前端开发**：Forward-going-Yang（前端页面设置，UI 界面美化）
- **硬件平台**：宇树 Go2 X 可开发版 + KICKPI K2B (全志 H618)

---

## 📄 许可

本项目仅用于职业院校技能大赛备赛，未经许可请勿用于商业用途。
