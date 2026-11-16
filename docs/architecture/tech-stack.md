# 技术栈与选型

> 最后更新：2026-11-04
> 负责人：Charlirtang
> 用途：记录用了什么版本、为什么选、哪些没选
> 对应技术源：根目录 `README.md`「技术栈」+ `ADR-0001`

## 选型原则

本项目是资源受限下的比赛项目，选型遵循三条：

1. **团队已有使用经验优先**：降低学习成本，减少踩坑时间。
2. **MVP 原则**：不引入远超项目需要的生态。
3. **能脚本化、可复现**：配置即代码，避免手动操作。

> 说明：被否方案**未做深入横向对比**，下表“未选原因”是基于项目约束的判断，不是严格的基准测试结论。

## 前端

| 技术 | 版本 | 用途 | 选型理由 |
| :--- | :--- | :--- | :--- |
| **SvelteKit** | 2.x | 前端框架 | 团队已有使用经验；编译时框架，运行时体积小 |
| **TypeScript** | - | 类型系统 | 与 SvelteKit 配套，降低类型错误 |
| **TailwindCSS** | - | 样式 | 原子化 CSS，改 UI 快，适合演示界面频繁调整 |
| **Tauri** | 2.x | 桌面应用外壳 | 团队已有使用经验；安装包小、内存占用低 |
| **Rust** | - | Tauri 后端逻辑 | 负责 mDNS 局域网发现（`zeroconf`） |

**为什么不用 React / Vue**：团队没实际用过，切换成本高于收益；SvelteKit 已能满足展示需求。

**为什么不用 Electron**：Tauri 团队已有经验，且安装包和内存占用明显更小；Electron 对一台演示机来说偏重。

## 后端（AI机台）

| 技术 | 版本 | 用途 | 选型理由 |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10+ | 后端语言 | AI/视觉生态最成熟；团队主力语言 |
| **FastAPI** | - | Web 框架 | 团队已有经验；**自带集成文档接口（Swagger UI），调试方便** |
| **Uvicorn** | - | ASGI 服务器 | FastAPI 官方推荐，异步支持好 |
| **OpenCV** | - | 视频流处理与录制 | 拉 MJPEG 流、烧时间戳、保存录制 |
| **requests** | - | HTTP 客户端 | 与 K2B 通信，简单够用 |
| **WebSocket** | - | 实时双向通信 | 前后端指令与状态推送 |
| **zeroconf** | - | mDNS | 后端侧 mDNS 支持 |
| **阿里云百炼（千问 `qwen3-vl-plus`）** | - | 云端 VLM 检测 | 识别烟雾，实测置信度 0.85+ |

**为什么不用 Flask**：FastAPI 团队已有经验，且原生异步 + WebSocket 支持更好；Flask 要额外配 ASGI 适配层。

**为什么不用 Django**：项目不需要 ORM、Admin、完整 MVC，Django 偏重，违背 MVP 原则。

**为什么选千问 VLM**：见 `ADR-0001` 之外的检测方案说明；当前实际使用千问 `qwen3-vl-plus` + 百炼地址，`.env.example` 的豆包默认值正在同步。

## 边缘网关（K2B）

| 技术 | 版本 | 用途 | 选型理由 |
| :--- | :--- | :--- | :--- |
| **Ubuntu** | 22.04 Server（ARM64） | 系统 | KICKPI 官方代烧，开箱可用 |
| **CycloneDDS** | 0.10.x（源码编译） | DDS 中间件 | 与 Go2 X 的 DDS 通信；源码编译以匹配 ARM64 |
| **unitree_sdk2py** | - | 宇树官方 Python SDK | 运动控制 + 视频采集 |
| **FastAPI + Uvicorn** | - | HTTP 转发层 | 与后端统一技术栈，降低维护成本 |
| **systemd** | - | 服务管理 | 开机自启 + 崩溃自动重启（`Restart=always`） |

**为什么 K2B 用 FastAPI**：与 AI机台统一技术栈，`gateway.py` 的 HTTP 接口风格一致，接手者不需要学两套。

**为什么 CycloneDDS 源码编译**：ARM64 下官方预编译包不匹配，必须源码编译；详见 `environment/k2b-setup.md` 步骤 3。

## 检测方案

三路检测器并存，由 `DETECTION_ENGINE` 环境变量切换：

| 检测器 | 类型 | 用途 | 说明 |
| :--- | :--- | :--- | :--- |
| `preset` | 兜底 | 预设规则 | 云端不可用时的最后防线 |
| `yolo` | 本地 | YOLO 模型 | `models/smoke.pt`，CPU 推理 |
| `vlm` | 云端 | 千问 `qwen3-vl-plus` | 识别烟雾，置信度 0.85+ |

组合方式：`preset+yolo+vlm`（多路并行，任一检测到即告警）、单路、或 `both` 双路。

> 检测方案的完整决策记录见后续 `ADR-0002`（待写）。

## 被否方案汇总

| 被否项 | 未选原因 | 置信度 |
| :--- | :--- | :--- |
| React / Vue | 团队无经验，切换成本高 | 中（未深入对比） |
| Electron | 偏重，Tauri 已满足需求 | 中（未深入对比） |
| Flask | 异步/WebSocket 支持不如 FastAPI | 中（未深入对比） |
| Django | 项目不需要完整 MVC，偏重 | 中（未深入对比） |
| ROS2 桥接 | 生态过重，违背 MVP | 高（`ADR-0001` 已记录） |

## 相关文档

- 架构总览：`architecture/overview.md`
- DDS 网关决策：`architecture/adr/0001-dds-via-k2b-gateway.md`
- 环境复现：`environment/ai-machine-setup.md`、`environment/k2b-setup.md`
