# app/routers/robot.py
# 📁 机器狗控制路由
# 职责：处理与机器狗运动控制、状态查询相关的 API 请求。

from fastapi import APIRouter, HTTPException
from app.models.robot import Command, RobotStatus
from app.services.robot_factory import get_robot_service
from typing import Dict
import random

router = APIRouter(prefix="/api/robot", tags=["robot"])

# 用于模拟状态变化
_mock_status = {
    "connected": False,
    "battery": 85,
    "current_state": "待命",
    "current_task": None,
    "mode": "手动"
}


# ========== 状态查询 ==========

@router.get("/status")
async def get_status() -> RobotStatus:
    """获取机器狗状态"""
    robot = get_robot_service()
    status = robot.get_status()

    # 同步到 mock_status（兼容原有数据结构）
    _mock_status["connected"] = status.get("connected", False)
    _mock_status["battery"] = status.get("battery", 85)

    # 模拟电量缓慢变化
    if _mock_status["battery"] > 60:
        _mock_status["battery"] -= random.randint(0, 1)

    return RobotStatus(**_mock_status)


# ========== 发送控制指令 ==========

@router.post("/command")
async def send_command(command: Command) -> Dict:
    """发送控制指令"""
    robot = get_robot_service()

    cmd = command.cmd
    print(f"📩 收到指令: {cmd}")

    _mock_status["current_task"] = cmd
    _mock_status["current_state"] = "执行中"

    # 根据指令类型调用对应方法
    try:
        if cmd in ["standup", "stand_up", "站立"]:
            result = robot.stand_up()
        elif cmd in ["sit", "sit_down", "坐下"]:
            result = robot.sit_down()
        elif cmd in ["forward", "前进"]:
            result = robot.move(0.3, 0, 0)
        elif cmd in ["backward", "后退"]:
            result = robot.move(-0.3, 0, 0)
        elif cmd in ["left", "左转"]:
            result = robot.move(0, 0, 0.3)
        elif cmd in ["right", "右转"]:
            result = robot.move(0, 0, -0.3)
        elif cmd in ["stop", "停止"]:
            result = robot.stop_move()
        else:
            result = {"success": False, "error": f"未知指令: {cmd}"}

        _mock_status["current_state"] = "待命"
        _mock_status["current_task"] = None
        return {"success": result.get("success", False), "cmd": cmd, "message": f"指令 {cmd} 已执行", "detail": result}

    except Exception as e:
        _mock_status["current_state"] = "异常"
        return {"success": False, "cmd": cmd, "message": f"执行失败: {str(e)}"}


# ========== 紧急停止 ==========

@router.post("/emergency_stop")
async def emergency_stop() -> Dict:
    """紧急停止"""
    robot = get_robot_service()
    print("🛑 紧急停止")

    try:
        robot.stop_move()
    except Exception:
        pass

    _mock_status["current_state"] = "紧急停止"
    _mock_status["current_task"] = None
    return {"success": True, "message": "已紧急停止"}


# ========== 连接 / 断开（新增） ==========

@router.post("/connect")
async def connect() -> Dict:
    """连接机器狗"""
    robot = get_robot_service()
    success = robot.connect()
    if success:
        _mock_status["connected"] = True
        return {"success": True, "message": "连接成功"}
    else:
        raise HTTPException(status_code=500, detail="连接失败")


@router.post("/disconnect")
async def disconnect() -> Dict:
    """断开连接"""
    robot = get_robot_service()
    result = robot.disconnect()
    _mock_status["connected"] = False
    return result


