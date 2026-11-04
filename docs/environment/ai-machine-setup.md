# AI机台环境复现

> 最后更新：2026-11-03
> 负责人：Charlirtang
> 用途：让接手者从零把 AI机台（主控后端）跑起来
> 对应技术源：根目录 `README.md`「快速开始」+ `backend/requirements.txt` + `backend/.env.example` + `backend/run.py`

## 适用范围

本文只覆盖 **AI机台（Ubuntu 主控后端）**。K2B 边缘网关见 `k2b-setup.md`，前端见根 README。

## 设备角色速查

| 设备 | 实际系统 | 跑什么 | 备注 |
| :--- | :--- | :--- | :--- |
| Arch 开发机 | Arch Linux | 写代码、改配置 | 开发环境，不在运行架构里 |
| **AI机台** | **Ubuntu 22.04** | **FastAPI 主控后端** | 本文的目标设备 |
| Win11 演示机 | Windows 11 | Tauri 桌面应用（前端） | 不是 AI机台，不要混淆 |
| K2B | Ubuntu 22.04 ARM64 | 边缘网关 | 见 `k2b-setup.md` |
| Go2 X | - | 机器狗执行终端 | 网线直连 K2B |

## 前置条件

| 项 | 要求 | 来源 |
| :--- | :--- | :--- |
| 系统 | Ubuntu 22.04 | 根 README「前置要求」 |
| Python | 3.10+ | 根 README「前置要求」 |
| 网络 | 与 K2B 处于同一局域网（推荐稳定手机热点/随身 WiFi） | 根 README「前置要求」 |

## 步骤 1：获取代码

```bash
git clone https://github.com/Charlirtang-2007/go2-inspection.git
cd go2-inspection
git switch Archlinux
```

> 文档随 `Archlinux` 分支维护，稳定层后续可合回 `main`。

## 步骤 2：Python 环境

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

> 本项目**只用 venv，不使用 pyenv**。不要额外引入 `.python-version`。

## 步骤 3：安装依赖

```bash
pip install -r requirements.txt
```

若报 `ModuleNotFoundError: No module named 'requests'`，说明虚拟环境没激活或依赖未装全，先 `pip install requests`，再回头核对 `requirements.txt`。

## 步骤 4：配置 `.env`

```bash
cp .env.example .env
vim .env
```

### 4.1 机器人连接

| 字段 | 含义 | 默认值 | 何时改 |
| :--- | :--- | :--- | :--- |
| `USE_MOCK_ROBOT` | `true`=模拟模式（无硬件）；`false`=真机模式 | `true` | 真机联调时改 `false` |
| `ROBOT_NETWORK_INTERFACE` | 连接机器狗的网卡名 | `enp2s0` | 按 AI机台实际网卡改（`ip a` 查） |
| `K2B_IP` | K2B 的局域网 IP | 空 | **真机模式必填**，从 K2B 上 `ip a` 或路由器 MAC 绑定获取 |

### 4.2 检测引擎

| 字段 | 含义 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `DETECTION_ENGINE` | 引擎组合：`preset` / `yolo` / `vlm` / `preset+yolo+vlm` | `preset+yolo+vlm` | 比赛推荐多路并行，任一检测到即告警 |
| `YOLO_MODEL_PATH` | YOLO 模型路径（相对 `backend/`） | `models/smoke.pt` | 不用 yolo 可忽略 |
| `YOLO_CONF_THRESHOLD` | YOLO 置信度阈值，越低越敏感 | `0.1` | 误报多则调高 |
| `YOLO_IMGSZ` | YOLO 输入尺寸，越大越准但 CPU 越慢 | `1280` | 低算力机器可降 |

### 4.3 VLM（云端视觉大模型）

| 字段 | 含义 | 默认值 | 何时必填 |
| :--- | :--- | :--- | :--- |
| `DASHSCOPE_API_KEY` | 千问 API Key，格式 `sk-xxx` | 空 | 启用 `vlm` 或多路组合时必填 |
| `VLM_URL` | VLM 接口地址 | 千问百炼地址 | 默认千问；切豆包时改为注释中的火山地址 |
| `VLM_MODEL` | 模型名 | `qwen3-vl-plus` | 当前用千问；拼错会报 `Model not exist` |
| `VLM_TIMEOUT` | 调用超时（秒） | `30` | 网络差可调高 |

> **注意**：当前实际使用千问方案（`DASHSCOPE_API_KEY` + `qwen3-vl-plus` + 百炼地址）。`.env.example` 的默认值正在同步为千问；若发现仍是豆包默认，以本文为准并同步 `.env.example`。

### 4.4 检测 worker

| 字段 | 含义 | 默认值 | 建议 |
| :--- | :--- | :--- | :--- |
| `DETECTION_INTERVAL` | 推理间隔（秒） | `3.0` | YOLO 快可 `1.0`；VLM 慢建议 `3.0` |

### 4.5 告警通知

| 字段 | 含义 | 默认值 | 获取方式 |
| :--- | :--- | :--- | :--- |
| `PUSHPLUS_TOKEN` | PushPlus 微信推送 token | 空 | https://www.pushplus.plus/ |
| `WECOM_WEBHOOK` | 企业微信群机器人 Webhook | 空 | 企微群「添加机器人」 |
| `NOTIFY_COOLDOWN` | 同类异常通知冷却（秒） | `300` | 防刷屏 |

### 4.6 视频流与录制

| 字段 | 含义 | 默认值 |
| :--- | :--- | :--- |
| `MJPEG_WIDTH` / `MJPEG_HEIGHT` | MJPEG 输出分辨率 | `1280` / `720` |
| `MJPEG_QUALITY` | JPEG 编码质量（1–100） | `80` |
| `RECORDING_KEEP_LAST` | 录制文件保留数量 | `5` |
| `RECORDING_DIR` | 录制输出目录（相对 `backend/`） | `recordings` |

### 4.7 服务器与日志

| 字段 | 含义 | 默认值 | 注意 |
| :--- | :--- | :--- | :--- |
| `HOST` | 后端监听地址 | `0.0.0.0` | 仅作参考，`run.py` 硬编码，改此字段不生效 |
| `PORT` | 后端监听端口 | `8000` | 仅作参考，`run.py` 硬编码，改此字段不生效 |
| `MDNS_SERVICE_TYPE` | mDNS 服务类型，前端 Rust 发现后端用 | `_go2-backend._tcp.local.` | 前端发现依赖此值 |
| `LOG_LEVEL` | 日志级别 | `INFO` | 排查时可改 `DEBUG` |

## 步骤 5：启动

```bash
python run.py
```

`run.py` 实际内容：

```python
uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

> **设计说明**：端口固定 `8000`，`host` 固定 `0.0.0.0`，均为硬编码。`.env` 中的 `HOST`/`PORT` 是模板参考值，**不参与启动**，修改它们不会改变监听端口。需要改端口时改 `run.py`，这是有意设计，不是 bug。

### 预期日志

```text
✅ 成功连接 K2B 视频流
✅ [Real] 成功连接 K2B 边缘网关
```

两条都出现，说明 AI机台到 K2B 的链路通了。

## 验证清单

- [ ] `pip install -r requirements.txt` 无报错
- [ ] `.env` 中 `K2B_IP` 是当前 K2B 的真实 IP
- [ ] 真机模式下 `USE_MOCK_ROBOT=false`、`ROBOT_NETWORK_INTERFACE` 与实际网卡一致
- [ ] 启动后两条预期日志都出现
- [ ] 前端 Tauri 应用能通过 mDNS 发现本机后端并显示视频

## 常见问题

| 现象 | 先查什么 | 详见 |
| :--- | :--- | :--- |
| `No module named 'requests'` | venv 是否激活、`requirements.txt` 是否装全 | 根 README FAQ 1 |
| 连不上 K2B 视频流 | `ping K2B_IP` → SSH 上 K2B 查 `systemctl status go2-gateway.service` → 确认网线连着狗且狗开机 | 根 README FAQ 2 |
| `Model not exist` | `.env` 中 `VLM_MODEL` 拼写，豆包/千问模型名不能混用 | 根 README FAQ 5 |
| K2B 重启后 IP 变了 | 路由器/热点按 MAC 绑定固定 IP；中期用 zeroconf 发现 `_go2-edge._tcp` | 根 README FAQ 6 |

## 待跟进（TODO）

- [ ] `.env.example` 的 `VLM_API_KEY` / 豆包默认值同步为 `DASHSCOPE_API_KEY` / 千问
- [ ] 确认实际联调用的 `DETECTION_ENGINE` 组合（当前文档写的是模板默认值 `preset+yolo+vlm`）
