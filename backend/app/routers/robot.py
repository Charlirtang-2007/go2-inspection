# app/routers/robot.py
# 📁 1. app/routers/robot.py —— 机器狗控制路由
# 职责：处理与机器狗运动控制、状态查询相关的 API 请求。

# 接口列表
# 方法	路径	功能
# GET	/api/robot/status	获取机器狗当前状态（电量、模式、任务）
# POST	/api/robot/command	发送控制指令（前进/后退/停止等）
# POST	/api/robot/emergency_stop	紧急停止



from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from app.models.robot import Command, RobotStatus
from typing import Dict
import random

router = APIRouter(prefix="/api/robot", tags=["robot"])

# 模拟状态（后续替换为真实 SDK）
_mock_status = {
    "connected": True,
    "battery": 85,
    "current_state": "待命",
    "current_task": None,
    "mode": "手动"
}

@router.get("/status")
async def get_status() -> RobotStatus:
    """获取机器狗状态"""
    # 模拟电量缓慢变化
    _mock_status["battery"] = max(60, _mock_status["battery"] - random.randint(0, 2))
    return RobotStatus(**_mock_status)

@router.post("/command")
async def send_command(command: Command) -> Dict:
    """发送控制指令（模拟）"""
    # TODO: 后续替换为真实 SDK 调用
    print(f"📩 收到指令: {command.cmd}")
    _mock_status["current_task"] = command.cmd
    _mock_status["current_state"] = "执行中"
    return {"success": True, "cmd": command.cmd, "message": f"指令 {command.cmd} 已执行"}

@router.post("/emergency_stop")
async def emergency_stop() -> Dict:
    """紧急停止"""
    print("🛑 紧急停止")
    _mock_status["current_state"] = "紧急停止"
    _mock_status["current_task"] = None
    return {"success": True, "message": "已紧急停止"}