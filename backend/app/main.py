# app/main.py
# 后端主接口
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json

from app.routers import robot, camera, detection, route, recording
from app.utils.websocket_manager import manager
from app.services.robot_factory import get_robot_service
from app.services.camera_service import camera_service
from app.services.recording_service import recording_service
from app.utils.mdns_service import MDNSService

# ========== mDNS服务实例 ==========
mdns = MDNSService(port=8000)


# ========== 生命周期管理 ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---------- 启动 ----------
    mdns.start()                      # mDNS 广播
    camera_service.start()            # 摄像头后台采集

    # ★ 自动连接机器狗
    robot_service = get_robot_service()
    if robot_service.connect():
        print("✅ 机器狗已自动连接")
    else:
        print("⚠️ 机器狗自动连接失败，请检查网卡或网络")

    yield

    # ---------- 关闭 ----------
    camera_service.stop()
    mdns.stop()


app = FastAPI(
    title="Go2 巡检系统 API",
    version="2.0.0",
    description="基于 FastAPI + WebSocket 的机器狗巡检系统",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(recording.router)
app.include_router(robot.router)
app.include_router(camera.router)
app.include_router(detection.router)
app.include_router(route.router)


# ========== 指令处理辅助函数 ==========

async def execute_robot_command(cmd: str):
    """执行机器狗指令，返回结果"""
    robot_service = get_robot_service()

    if cmd in ["standup", "stand_up", "站立"]:
        return robot_service.stand_up()
    elif cmd in ["sit", "sit_down", "坐下"]:
        return robot_service.sit_down()
    elif cmd in ["forward", "前进"]:
        return robot_service.move(0.3, 0, 0)
    elif cmd in ["backward", "后退"]:
        return robot_service.move(-0.3, 0, 0)
    # 旋转速度 1.2 rad/s ≈ 69°/秒
    elif cmd in ["left", "左转"]:
        return robot_service.move(0, 0, 1.2)
    elif cmd in ["right", "右转"]:
        return robot_service.move(0, 0, -1.2)
    elif cmd in ["stop", "停止"]:
        return robot_service.stop_move()

    # 巡检开始：启动录制
    elif cmd == "start_inspection":
        ok = recording_service.start()
        return {"success": ok, "action": "start_inspection", "recording": recording_service.is_recording()}

    # 巡检结束：停止录制
    elif cmd == "stop_inspection":
        path = recording_service.stop()
        return {"success": True, "action": "stop_inspection", "file": path}

    # 紧急停止：停狗 + 停录制
    elif cmd in ["emergency_stop", "紧急停止"]:
        result = robot_service.stop_move()
        path = recording_service.stop()
        return {"success": True, "action": "emergency_stop", "file": path, "detail": result}

    else:
        return {"success": False, "error": f"未知指令: {cmd}"}


# ========== mDNS 发现信息接口（备用） ==========
@app.get("/api/discovery")
async def discovery():
    return {
        "service": "go2-inspection",
        "ip": mdns.get_local_ip(),
        "port": mdns.port,
        "ws_url": f"ws://{mdns.get_local_ip()}:{mdns.port}/ws",
    }


# ========== WebSocket 端点 ==========

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")

                if msg_type == "subscribe":
                    topics = msg.get("topics", [])
                    manager.connection_data[websocket]["subscribed"] = topics
                    await manager.send_json(websocket, {
                        "type": "subscribed",
                        "topics": topics
                    })

                elif msg_type == "command":
                    cmd = msg.get("data", {}).get("cmd")
                    print(f"🎮 WebSocket 指令: {cmd}")

                    try:
                        result = await execute_robot_command(cmd)
                        await manager.send_json(websocket, {
                            "type": "command_ack",
                            "data": {
                                "cmd": cmd,
                                "status": "executed" if result.get("success") else "failed",
                                "detail": result
                            }
                        })
                    except Exception as e:
                        await manager.send_json(websocket, {
                            "type": "command_ack",
                            "data": {
                                "cmd": cmd,
                                "status": "error",
                                "error": str(e)
                            }
                        })

                else:
                    await manager.send_json(websocket, {
                        "type": "error",
                        "message": f"未知消息类型: {msg_type}"
                    })

            except json.JSONDecodeError:
                await manager.send_json(websocket, {
                    "type": "error",
                    "message": "无效的 JSON 格式"
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ========== 健康检查 ==========

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Go2 巡检系统后端"}


@app.get("/")
async def root():
    return {
        "service": "Go2 巡检系统 API",
        "version": "2.0.0",
        "endpoints": {
            "/api/robot/status": "获取机器狗状态",
            "/api/robot/command": "发送控制指令",
            "/api/camera/video": "MJPEG 视频流",
            "/api/detection/aruco": "ArUco 标记检测",
            "/api/detection/anomaly": "异常检测（火焰/烟雾/漏油）",
            "/api/route/list": "路线列表",
            "/ws": "WebSocket 连接"
        }
    }