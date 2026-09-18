# app/main.py
# 后端主接口
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import json
import asyncio

from app.routers import robot, camera, detection, route, inspection
from app.utils.websocket_manager import manager
from app.services.robot_factory import get_robot_service
from app.services.inspection_service import inspection_service
from app.utils.mdns_service import MDNSService 

# ========== mDNS服务实例 ==========
mdns = MDNSService(port=8000)

# ========== 生命周期管理 ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：注册mDNS广播，并把事件循环注入巡检服务（供后台线程安全广播）
    mdns.start()
    inspection_service.set_loop(asyncio.get_running_loop())
    yield
    # 关闭时：停止广播、结束录制
    inspection_service.stop()
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
app.include_router(robot.router)
app.include_router(camera.router)
app.include_router(detection.router)
app.include_router(route.router)
app.include_router(inspection.router)


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
    elif cmd in ["left", "左转"]:
        return robot_service.move(0, 0, 0.3)
    elif cmd in ["right", "右转"]:
        return robot_service.move(0, 0, -0.3)
    elif cmd in ["stop", "停止"]:
        return robot_service.stop_move()
    else:
        return {"success": False, "error": f"未知指令: {cmd}"}

# 新增：提供mDNS发现信息的接口（备用）
@app.get("/api/discovery")
async def discovery():
    """返回本服务的连接信息，前端也可通过此接口获取"""
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

                    # 巡检录制指令：不经过机器狗指令执行器
                    if cmd == "start_inspection":
                        info = inspection_service.start()
                        await manager.broadcast({
                            "type": "inspection_started",
                            "data": {"inspection_id": info.get("inspection_id", "")}
                        })
                        await manager.broadcast({"type": "inspection_status", "data": info})
                        await manager.send_json(websocket, {
                            "type": "command_ack",
                            "data": {"cmd": cmd, "status": "executed", "detail": info}
                        })
                        continue

                    if cmd == "stop_inspection":
                        info = inspection_service.stop()
                        await manager.broadcast({"type": "inspection_finished", "data": info})
                        await manager.broadcast({"type": "inspection_status", "data": info})
                        await manager.send_json(websocket, {
                            "type": "command_ack",
                            "data": {"cmd": cmd, "status": "executed", "detail": info}
                        })
                        continue

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