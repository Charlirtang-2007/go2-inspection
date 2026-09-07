from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json

app = FastAPI(title="Go2 巡检系统 API", version="1.0.0")

# CORS 配置（允许前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 存储所有活跃的 WebSocket 连接
active_connections: list[WebSocket] = []

async def broadcast_status():
    """模拟状态变化，广播给所有连接的客户端"""
    import random
    statuses = ['在线', '巡检中', '待命']
    while True:
        if active_connections:
            msg = {
                "type": "status_update",
                "data": {
                    "status": random.choice(statuses),
                    "battery": random.randint(70, 100),
                    "mode": "自动"
                }
            }
            for conn in active_connections:
                try:
                    await conn.send_text(json.dumps(msg))
                except:
                    pass
        await asyncio.sleep(3)  # 每3秒推送一次

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    print(f"✅ 新客户端连接，当前连接数: {len(active_connections)}")
    try:
        while True:
            data = await websocket.receive_text()
            print(f"📩 收到指令: {data}")
            
            # 解析 JSON 消息
            try:
                msg = json.loads(data)
                if msg.get("type") == "command":
                    cmd = msg.get("data", {}).get("cmd")
                    print(f"🎮 执行指令: {cmd}")
                    # TODO: 后续替换为真实的机器狗控制
                    # 这里先模拟执行，回传确认消息
                    await websocket.send_text(json.dumps({
                        "type": "command_ack",
                        "data": {"cmd": cmd, "status": "executed"}
                    }))
            except json.JSONDecodeError:
                print(f"⚠️ 无效的 JSON: {data}")
                
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print(f"❌ 客户端断开，当前连接数: {len(active_connections)}")


@app.on_event("startup")
async def startup():
    # 启动后台广播任务
    asyncio.create_task(broadcast_status())
@app.get("/")
async def root():
    return {"message": "Go2 巡检系统后端运行中 ✅"}

@app.get("/api/status")
async def get_status():
    return {"status": "online", "battery": 85, "mode": "待命"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)