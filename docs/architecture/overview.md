# 架构总览

> 最后更新：2026-11-04
> 负责人：Charlirtang
> 用途：让接手者理解四级解耦架构、数据流与失败边界
> 对应技术源：根目录 `README.md`「系统架构」+「设备职责」+「通信方式」

## 一句话架构

**前端 - 主控 - 边缘网关 - 机器狗** 四级解耦。核心目的是突破传统网线直连的物理限制：前端不必接入狗的 DDS 网段，而是通过 K2B 网关把 DDS 转成 HTTP/MJPEG。

## 架构图

```text
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

## 设备职责

| 设备 | 角色 | 运行内容 | 详见 |
| :--- | :--- | :--- | :--- |
| 笔记本 / Win11 演示机 | 前端展示 | Tauri 桌面应用、视频显示、指令下发、告警弹窗 | 根 README |
| AI机台（Ubuntu） | 主控后端 | FastAPI + WebSocket + VLM 检测 + 通知 + 录制 | `environment/ai-machine-setup.md` |
| K2B（全志 H618） | 边缘网关 | 跑 `unitree_sdk2py`，负责 DDS 协议与 HTTP/WS 的透传转发 | `environment/k2b-setup.md` |
| 机器狗 Go2 X | 执行终端 | 运动控制、摄像头采集 | 官方文档 |

## 通信方式

| 链路 | 协议 | 说明 |
| :--- | :--- | :--- |
| 前端 ↔ AI机台 | WebSocket / HTTP | 指令、状态实时双向、视频流拉取 |
| 前端 → AI机台 | mDNS | Rust 端自动发现后端地址 |
| AI机台 ↔ K2B | HTTP (REST / MJPEG) | 跨网络控制与视频流透传 |
| K2B ↔ 机器狗 | DDS | 网线直连，同一 `192.168.123.x` 网段 |
| 后端 → 手机 | HTTPS | PushPlus / 企业微信异常推送 |

## 数据流（两条主链路）

### 1. 控制链路

```text
前端点击按钮
  → WebSocket 发指令到 AI机台
  → AI机台 HTTP POST 到 K2B /api/robot/command
  → gateway.py 调用 SportClient
  → DDS 下发到 Go2 X
```

### 2. 视频与检测链路

```text
Go2 X 摄像头
  → DDS 到 K2B
  → gateway.py 独立线程拉流
  → MJPEG /api/camera/video
  → AI机台拉流
  → 三路检测器（preset / yolo / vlm）
  → 异常触发通知 + 录制
  → WebSocket 推前端告警
```

## 失败边界

四级解耦的价值在于**单点故障不扩散**。逐层说明：

| 故障点 | 影响范围 | 兜底 |
| :--- | :--- | :--- |
| 前端崩溃 | 仅展示层，后端和 K2B 继续运行 | 重启 Tauri 应用 |
| AI机台崩溃 | 检测、录制、通知停止；K2B 和狗仍可控 | systemd 或手动重启后端 |
| K2B 崩溃 | 控制链路和视频链路同时断；AI机台和前端仍可运行 | `Restart=always` 自动重启；见 `environment/k2b-setup.md` 5.5 |
| K2B 到狗网线松 / 狗未开机 | `gateway.py` 卡在 `wait_for_network()`，AI机台报 `Connection refused` | 检查网线和狗电源；见踩坑表第 1 条 |
| 云端 VLM 不可用 | 仅 vlm 检测器失效 | `preset` 兜底 / `yolo` 本地 |
| 路由器 / 热点断 | 前端、AI机台、K2B 三者互相失联 | 检查局域网；K2B IP 已静态 |

> **单点风险**：K2B 是控制与视频的唯一通道，它挂了整个巡检就停。当前用 `Restart=always` 兜底，但没有冗余 K2B。这是已知架构约束，不是 bug。

## 为什么这样分层

- **物理限制**：前端笔记本无法直接接入 `192.168.123.x` 的 DDS 网段。
- **职责隔离**：AI机台专注检测/录制/通知，K2B 专注 DDS 与转发，前端专注展示。
- **跨网络**：K2B 把 DDS 封装成 HTTP/MJPEG，前端和 AI机台只需在同一局域网。

> 选型理由与被否方案见 `adr/0001-dds-via-k2b-gateway.md`。本文只描述“是什么”，不展开“为什么”。

## 相关文档

- 环境复现：`environment/ai-machine-setup.md`、`environment/k2b-setup.md`
- 决策记录：`adr/0001-dds-via-k2b-gateway.md`
- 接手验收：`handover/checklist.md`
