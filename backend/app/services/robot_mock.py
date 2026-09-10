import time
from typing import Dict, Any
from app.services.robot_interface import RobotInterface

class RobotMock(RobotInterface):
    """模拟机器狗 - 用于无硬件测试"""

    def __init__(self):
        self._connected = False
        self._position = {"x": 0.0, "y": 0.0, "z": 0.0}
        self._battery = 85.0
        self._mode = "standby"
        print("🤖 [Mock] 模拟机器狗已初始化")

    def connect(self) -> bool:
        self._connected = True
        print("✅ [Mock] 模拟连接成功")
        return True

    def stand_up(self) -> Dict[str, Any]:
        if not self._connected:
            return {"success": False, "error": "未连接"}
        self._mode = "standing"
        print("🧍 [Mock] 机器狗站立")
        return {"success": True, "action": "stand_up", "mode": self._mode}

    def sit_down(self) -> Dict[str, Any]:
        if not self._connected:
            return {"success": False, "error": "未连接"}
        self._mode = "sitting"
        print("🪑 [Mock] 机器狗坐下")
        return {"success": True, "action": "sit_down", "mode": self._mode}

    def move(self, vx: float, vy: float, vyaw: float) -> Dict[str, Any]:
        if not self._connected:
            return {"success": False, "error": "未连接"}
        # 模拟位置变化
        self._position["x"] += vx * 0.1
        self._position["y"] += vy * 0.1
        print(f"🚀 [Mock] 移动 vx={vx}, vy={vy}, vyaw={vyaw}")
        return {
            "success": True,
            "action": "move",
            "velocity": [vx, vy, vyaw],
            "position": self._position
        }

    def stop_move(self) -> Dict[str, Any]:
        if not self._connected:
            return {"success": False, "error": "未连接"}
        print("🛑 [Mock] 停止移动")
        return {"success": True, "action": "stop_move"}

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self._connected,
            "battery": self._battery,
            "position": self._position,
            "mode": self._mode,
            "source": "mock"
        }

    def disconnect(self) -> Dict[str, Any]:
        self._connected = False
        print("👋 [Mock] 已断开连接")
        return {"success": True, "action": "disconnect"}