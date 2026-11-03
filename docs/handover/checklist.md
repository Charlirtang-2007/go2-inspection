# 接手验收清单

> 最后更新：2026-11-03
> 负责人：Charlirtang
> 用途：判断一个没参与过的人能否独立接住项目
> 对应技术源：根目录 `README.md`「快速开始」+ `docs/environment/`

## 使用方式

按顺序逐项打勾。**任一项打不了勾，就说明文档或环境还有缺口**，把缺口记到 `docs/issues/` 或 `docs/status/open-questions.md`，不要口头带过。

## A. 环境与启动

- [ ] 能说清三台设备的角色：笔记本（前端）、AI机台（后端主控）、K2B（边缘网关）、Go2 X（执行终端）
- [ ] 能在 AI机台进入 `backend/`，激活虚拟环境，`pip install -r requirements.txt` 无报错
- [ ] 能对照 `docs/environment/ai-machine-setup.md` 说清 `.env` 中每个字段的含义：
      `K2B_IP` / `DETECTION_ENGINE` / `DASHSCOPE_API_KEY` / `PUSHPLUS_TOKEN` / `WECOM_WEBHOOK`
- [ ] 能启动后端，并在日志里看到 `✅ 成功连接 K2B 视频流` 与 `✅ [Real] 成功连接 K2B 边缘网关`
- [ ] 能打开 Tauri 桌面应用，通过 mDNS 自动发现后端并显示视频流

## B. 故障定位（不求修好，求知道先查哪）

- [ ] AI机台连不上 K2B 视频流时，知道第一步查 `ping K2B_IP`，第二步 SSH 上 K2B 查 `systemctl status go2-gateway.service`
- [ ] 知道 K2B 重启后 IP 可能变化，以及当前缓解方式（路由器/热点按 MAC 绑定固定 IP）
- [ ] 控狗按钮部分失效时，知道去 K2B 的 `gateway.py` 核对指令映射（`left` / `right` / `backward` 是否调到 `SportClient.Move`）
- [ ] VLM 报 `Model not exist` 时，知道先核对 `.env` 中 `VLM_MODEL=qwen3-vl-plus` 拼写

## C. 项目状态与方向

- [ ] 打开 `docs/status/progress.md`，能说出当前优先级最高的 1–2 项；若仍为 TODO，说明该文件待填，需当场补上
- [ ] 能说出「已实现」与「待接入」的边界（对照根 `README.md` 功能模块表）
- [ ] 知道三路检测器架构（`preset` 兜底 / `yolo` 本地 / `vlm` 云端）由 `DETECTION_ENGINE` 切换

## D. 文档本身

- [ ] 知道非技术层入口在哪（`docs/for-non-technical/README.md`），并知道它不写协议名和命令
- [ ] 知道新问题该记到哪（`docs/issues/`，按模板），新决策该记到哪（`docs/architecture/adr/`）
- [ ] 知道文档随 `Archlinux` 分支维护，稳定层后续可合回 `main`

## 打不了勾时怎么办

1. 如果是**环境跑不起来**：补 `docs/environment/` 对应文件，不要只改根 README。
2. 如果是**状态说不清**：补 `docs/status/progress.md`。
3. 如果是**故障不知道怎么查**：在 `docs/issues/` 新建一条，现象 + 复现 + 待验证根因。
