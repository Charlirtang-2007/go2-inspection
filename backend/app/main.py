# app/main.py
# 后端主接口
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import asyncio

from app.routers import robot, camera, detection, route
from app.utils.websocket_manager import manager

app = FastAPI(
    title="Go2 巡检系统 API",
    version="2.0.0",
    description="基于 FastAPI + WebSocket 的机器狗巡检系统"
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
                    # TODO: 接入真实机器狗控制
                    await manager.send_json(websocket, {
                        "type": "command_ack",
                        "data": {"cmd": cmd, "status": "received"}
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