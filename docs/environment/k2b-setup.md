# K2B 边缘网关环境复现

> 最后更新：2026-11-04
> 负责人：Charlirtang
> 用途：让接手者从零把 K2B 边缘网关跑起来
> 对应技术源：根目录 `README.md`「技术栈」+ Nain_an 2026-11-04 环境核对清单

## 适用范围

本文只覆盖 **K2B 边缘网关（全志 H618，ARM64）**。AI机台见 `ai-machine-setup.md`，前端见根 README。

## 硬件与系统事实

| 项 | 实际值 | 确认方式 |
| :--- | :--- | :--- |
| 硬件 | KICKPI K2B（全志 H618，ARM64） | 已核对 |
| 系统 | Ubuntu 22.04 Server（官方代烧） | 已核对 |
| 默认用户 | `kickpi` | `whoami` |
| 主机名 | `kickpi` | `hostname` |
| 官方文档 | https://doc.kickpi.cn/Products/Beginner-Guide/KICKPI-K2B/ | 已核对 |
| 网关脚本 | `/home/kickpi/gateway.py` | systemd 确认 |
| CycloneDDS 安装目录 | `/home/kickpi/cyclonedds/install` | `$CYCLONEDDS_HOME` 确认 |

## 网络拓扑

K2B 有两块网卡，**默认路由必须走 wlan0**，否则无法访问外网。

| 网卡 | 用途 | 网段 / IP | 说明 |
| :--- | :--- | :--- | :--- |
| `wlan0` | 连路由器，对 AI机台提供 HTTP | `192.168.211.194`（静态） | 默认路由走这里 |
| `eth0` | 网线直连 Go2 X，走 DDS | `192.168.123.x` | 狗默认 IP `192.168.123.161` |

> **注意（事实冲突）**：根 README 示例里 `K2B_IP=192.168.62.240` 是早期占位值，**实际是 `192.168.211.194`**。AI机台 `.env` 的 `K2B_IP` 必须按实际值填，不要照抄 README 示例。

## 步骤 1：系统与官方文档

K2B 系统为 KICKPI 官方代烧的 Ubuntu 22.04 Server，无需自行重装。官方入门文档：

https://doc.kickpi.cn/Products/Beginner-Guide/KICKPI-K2B/

首次登录用户为 `kickpi`，主机名 `kickpi`。

## 步骤 2：网络配置

### 2.1 wlan0（连路由器）

```bash
ip a show wlan0
```

预期：`192.168.211.194/24`。

> **TODO**：静态 IP 的配置方式（netplan / NetworkManager）需 Charlirtang 确认，当前只记录结果值。

### 2.2 eth0（连狗）

```bash
# 给 eth0 配 192.168.123.x 网段
sudo ip addr add 192.168.123.100/24 dev eth0
sudo ip link set eth0 up

# 验证能通狗
ping 192.168.123.161
```

预期：延迟约 `0.2ms`，丢包 0%。

> **已确认**：`eth0` 的 `192.168.123.x` 是**持久化配置**，重启后保留（Nain_an 2026-11-04 确认）。具体持久化方式（netplan / systemd-networkd）待补充。

### 2.3 默认路由

```bash
ip route
```

若默认路由指向 `eth0`，改为 `wlan0`：

```bash
sudo ip route replace default via <路由器网关> dev wlan0
```

> **踩坑记录**：现象是「能控狗但 K2B 无法访问外网」，根因是默认路由冲突。详见「已知踩坑」第 3 条。

## 步骤 3：编译 CycloneDDS 0.10.x

### 3.1 安装依赖

```bash
sudo apt update
sudo apt install -y gcc g++ git cmake libssl-dev
```

### 3.2 源码编译

```bash
cd /home/kickpi
git clone https://github.com/eclipse-cyclonedds/cyclonedds.git
cd cyclonedds
git checkout 0.10.x
mkdir -p build install
cd build
cmake .. -DCMAKE_INSTALL_PREFIX=../install -DBUILD_EXAMPLES=ON
make -j$(nproc)
make install
```

> **TODO**：实际 checkout 的 tag/branch 需确认，文档写的是 `0.10.x`，可能与实际不完全一致。

### 3.3 环境变量

```bash
echo 'export CYCLONEDDS_HOME=/home/kickpi/cyclonedds/install' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=$CYCLONEDDS_HOME/lib:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

验证：

```bash
echo $CYCLONEDDS_HOME
find /home/kickpi/cyclonedds/install -name "libddsc*" -type f
```

> **注意**：DDS 库**不在** `/usr/local`，而在 `/home/kickpi/cyclonedds/install`。排查时不要只查 `/usr/local`。

## 步骤 4：安装 unitree_sdk2py

### 4.1 依赖

```bash
sudo apt install -y python3-dev python3-pip build-essential
```

### 4.2 安装

```bash
cd /home/kickpi
git clone <unitree_sdk2py 仓库地址>
cd unitree_sdk2py
pip3 install -e .
```

> **TODO**：`unitree_sdk2py` 的仓库地址需补充，当前只记录安装方式。
> **踩坑记录**：安装报错找不到 `Python.h`，原因是缺 `python3-dev` 或 `setuptools` 过旧。详见「已知踩坑」第 4 条。

## 步骤 5：gateway.py 与 systemd

### 5.1 脚本位置

```text
/home/kickpi/gateway.py
```

### 5.2 完整内容

```python
# ~/gateway.py
import os
os.environ["CYCLONEDDS_HOME"] = "/home/kickpi/cyclonedds/install"
import time
import asyncio
import subprocess
import threading
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient
from unitree_sdk2py.go2.video.video_client import VideoClient

while subprocess.call(["ping", "-c", "1", "-W", "1", "192.168.123.161"], stdout=subprocess.DEVNULL) != 0:
    time.sleep(2)
print("✅ 狗已连通！")

ChannelFactoryInitialize(0, "eth0")
sport_client = SportClient()
sport_client.SetTimeout(10.0)
sport_client.Init()

video_client = VideoClient()
video_client.Init()

latest_frame_data = None
frame_lock = threading.Lock()

def video_capture_worker():
    global latest_frame_data
    while True:
        ret, data = video_client.GetImageSample()
        if ret == 0 and data:
            with frame_lock:
                latest_frame_data = bytes(data) if isinstance(data, list) else data
        else:
            time.sleep(0.01)

threading.Thread(target=video_capture_worker, daemon=True).start()

app = FastAPI()

class CommandReq(BaseModel):
    cmd: str

@app.post("/api/robot/command")
def send_command(req: CommandReq):
    cmd = req.cmd
    try:
        if cmd == "standup": sport_client.StandUp()
        elif cmd == "risesit": sport_client.RiseSit()
        elif cmd == "forward": sport_client.Move(0.3, 0, -0.03)
        elif cmd == "backward": sport_client.Move(-0.3, 0, 0)
        elif cmd == "left": sport_client.Move(0, 0, 1.0)
        elif cmd == "sit": sport_client.Sit()
        elif cmd == "right": sport_client.Move(0, 0, -1.0)
        elif cmd == "stop": sport_client.StopMove()
        return {"success": True, "cmd": cmd}
    except Exception as e:
        return {"success": False, "msg": str(e)}

async def gen_frames():
    while True:
        with frame_lock:
            frame = latest_frame_data
        if frame:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            await asyncio.sleep(1/30)
        else:
            await asyncio.sleep(0.01)

@app.get("/api/camera/video")
async def video_feed():
    return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 5.3 启动流程与关键点

| 环节 | 实际行为 | 排查要点 |
| :--- | :--- | :--- |
| 等待狗连通 | 循环 `ping 192.168.123.161`，通了才继续 | 卡在这里 = 网线没插或狗没开机 |
| 设置 DDS 环境 | 脚本内**硬编码** `CYCLONEDDS_HOME`，不依赖 `.bashrc` | 即使 `.bashrc` 没配也能跑 |
| DDS 初始化 | `ChannelFactoryInitialize(0, "eth0")` | **一个进程只能调用一次**，重复调用静默失败 |
| 运动客户端 | `SportClient`，超时 10s | - |
| 视频客户端 | `VideoClient`，独立 daemon 线程拉流 | 主进程退出线程即停 |
| 视频数据类型 | 兼容 `list` 和 `bytes`，`list` 会转 `bytes` | 排查视频空白时先看 `GetImageSample` 返回类型 |
| 命令映射 | 8 个指令，见 5.4 表 | 部分指令走 `Move` 参数 |
| 视频输出 | MJPEG，30fps 上限 | `GET /api/camera/video` |
| 监听 | `uvicorn.run(app, host="0.0.0.0", port=8000)` | 与 AI机台端口同为 8000，但在不同机器上，不冲突 |

> **与 AI机台 `run.py` 的区别**：`gateway.py` 的 `uvicorn.run` **没有 `reload=True`**，改代码后必须手动重启服务；AI机台 `run.py` 带 `reload=True`，改代码会自动重载。

### 5.4 命令映射表

| 前端指令 | 实际调用 | 备注 |
| :--- | :--- | :--- |
| `standup` | `SportClient.StandUp()` | 站立 |
| `risesit` | `SportClient.RiseSit()` | 起坐 |
| `forward` | `SportClient.Move(0.3, 0, -0.03)` | 前进，带微小横移 |
| `backward` | `SportClient.Move(-0.3, 0, 0)` | 后退 |
| `left` | `SportClient.Move(0, 0, 1.0)` | 左转 |
| `right` | `SportClient.Move(0, 0, -1.0)` | 右转 |
| `sit` | `SportClient.Sit()` | 坐下/趴下 |
| `stop` | `SportClient.StopMove()` | 停止 |

> **注意**：`left` / `right` 走的是 `Move(0, 0, ±1.0)` 而不是独立转向接口。根 README FAQ 4 提到的「控狗按钮部分失效」，排查时对照这张表。

### 5.5 systemd 服务

#### 5.5.1 完整 unit 文件

```ini
# /etc/systemd/system/go2-gateway.service
[Unit]
Description=Go2 K2B Edge Gateway Service
After=network-online.target NetworkManager-wait-online.service
Wants=network-online.target NetworkManager-wait-online.service

[Service]
Type=simple
User=kickpi
# ★ 关键：systemd 不读 .bashrc，必须在这里声明 DDS 环境变量
Environment="CYCLONEDDS_HOME=/home/kickpi/cyclonedds/install"
WorkingDirectory=/home/kickpi
# 执行你的网关脚本
ExecStart=/usr/bin/python3 /home/kickpi/gateway.py
# 如果程序崩溃，自动重启
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

#### 5.5.2 字段解读

| 字段 | 值 | 作用 | 注意事项 |
| :--- | :--- | :--- | :--- |
| `After` | `network-online.target NetworkManager-wait-online.service` | 等网络就绪后再启动 | 确保 `wlan0` / `eth0` 已配好 |
| `Wants` | 同上 | 弱依赖，缺失不阻塞启动 | - |
| `Type` | `simple` | 主进程即 `ExecStart` | - |
| `User` | `kickpi` | 以普通用户运行 | 硬件访问权限需提前配好 |
| `Environment` | `CYCLONEDDS_HOME=...` | **systemd 不读 `.bashrc`**，必须在此声明 | 与 `gateway.py` 内的 `os.environ` 构成双重保险 |
| `WorkingDirectory` | `/home/kickpi` | 进程工作目录 | 影响相对路径解析 |
| `ExecStart` | `/usr/bin/python3 /home/kickpi/gateway.py` | 启动命令 | 用绝对路径，避免 PATH 问题 |
| `Restart` | `always` | 崩溃自动重启 | 正常退出也会重启 |
| `RestartSec` | `3` | 重启间隔 3 秒 | 防频繁重启刷日志 |
| `WantedBy` | `multi-user.target` | 多用户模式启用 | 配合 `systemctl enable` 生效 |

#### 5.5.3 双重保险说明

`gateway.py` 第一行就 `os.environ["CYCLONEDDS_HOME"] = ...`，而 unit 文件又用 `Environment=` 声明了一次。**两处都保留，不要删任何一处**：

- **脚本内硬编码**：保证手动 `python3 gateway.py` 也能跑，不依赖 systemd。
- **unit 内声明**：符合 systemd 惯例，`Environment=` 在进程启动前注入，对 `import unitree_sdk2py` 之前任何读取环境变量的代码都可见。
- 两者不冲突，删除任何一处都会降低容错性。

> **重启注意**：`gateway.py` 的 `uvicorn.run` 没有 `reload=True`，改代码后必须 `sudo systemctl restart go2-gateway.service`，不会自动重载。

### 5.6 开机自启

```bash
sudo systemctl enable go2-gateway.service
sudo systemctl start go2-gateway.service
sudo systemctl status go2-gateway.service
```

## 步骤 6：验证

### 6.1 K2B 侧

```bash
systemctl status go2-gateway.service
ping 192.168.123.161
echo $CYCLONEDDS_HOME
```

### 6.2 AI机台侧

```bash
ping 192.168.211.194
curl http://192.168.211.194:8000/
```

启动后端后应看到：

```text
✅ 成功连接 K2B 视频流
✅ [Real] 成功连接 K2B 边缘网关
```

## 已知踩坑

| # | 现象 | 根因 | 处理 |
| :--- | :--- | :--- | :--- |
| 1 | `gateway.py` 卡在 `wait_for_network()`，AI机台报 `Connection refused` | 网线没插或狗没开机，`eth0` 处于 `NO-CARRIER` | `ip a` 看 `eth0` 是否 `NO-CARRIER`；检查网线和狗电源 |
| 2 | DDS 初始化成功但收不到狗数据 | `eth0` 没配 `192.168.123.x`，或绑定了错误网卡名 | `ip a` 确认网段；`ChannelFactoryInitialize` 第二参数必须是 `eth0` |
| 3 | 能控狗但 K2B 无法访问外网 | 多网卡默认路由冲突，默认路由跑到 `eth0` | `ip route` 查默认路由，改为 `wlan0` |
| 4 | `unitree_sdk2py` 安装报 `Python.h` 找不到 | 缺 `python3-dev` 或 `setuptools` 过旧 | `sudo apt install python3-dev`；`pip3 install --upgrade setuptools` |
| 5 | 终端报 `tput: unknown terminal "xterm-kitty"` | 本地 Arch 的 kitty terminfo 不在 K2B 库中 | 不影响运行；可 `export TERM=xterm-256color` 或忽略 |

## 待跟进（TODO）

- [ ] `eth0` 的 `192.168.123.x` 已持久化，具体方式（netplan / systemd-networkd）待补充
- [ ] `wlan0` 静态 IP 的配置方式需补充
- [ ] CycloneDDS 实际 checkout 的 tag/branch 需确认
- [ ] `unitree_sdk2py` 仓库地址需补充
- [x] `go2-gateway.service` 完整 unit 文件已补入（2026-11-04）
- [x] 根 README 的 `K2B_IP` 示例值已同步为 `192.168.211.194`（2026-11-04）
- [x] 根 README 的网络描述已更新为路由器（2026-11-04）

## 维护规则

- 本文件随 `Archlinux` 分支维护。
- 网络 IP 变化时，同步更新本文与 AI机台 `.env` 的 `K2B_IP`。
- 新增踩坑记录时追加到「已知踩坑」表，并同步 `docs/issues/`。
