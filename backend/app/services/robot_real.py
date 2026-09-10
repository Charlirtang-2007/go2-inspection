from typing import Dict, Any
from app.services.robot_interface import RobotInterface

class RobotReal(RobotInterface):
    """真实机器狗控制 - 基于 unitree_sdk2py"""

    def __init__(self, network_interface: str = "enp2s0"):
        self._network_interface = network_interface
        self._sport_client = None
        self._connected = False
        self._battery = 100.0

    def connect(self) -> bool:
        try:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize
            from unitree_sdk2py.go2.sport.sport_client import SportClient

            # 初始化 DDS 通信
            ChannelFactoryInitialize(0, self._network_interface)

            # 创建运动控制客户端
            self._sport_client = SportClient()
            self._sport_client.SetTimeout(10.0)
            self._sport_client.Init()

            self._connected = True
            print(f"✅ [Real] 真实机器狗连接成功（网卡: {self._network_interface}）")
            return True

        except Exception as e:
            print(f"❌ [Real] 连接失败: {e}")
            self._connected = False
            return False

    def stand_up(self) -> Dict[str, Any]:
        if not self._connected:
            return {"success": False, "error": "未连接"}
        try:
            self._sport_client.StandUp()
            return {"success": True, "action": "stand_up"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sit_down(self) -> Dict[str, Any]:
        if not self._connected:
            return {"success": False, "error": "未连接"}
        try:
            self._sport_client.Sit()
            return {"success": True, "action": "sit_down"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def move(self, vx: float, vy: float, vyaw: float) -> Dict[str, Any]:
        if not self._connected:
            return {"success": False, "error": "未连接"}
        try:
            self._sport_client.Move(vx, vy, vyaw)
            return {
                "success": True,
                "action": "move",
                "velocity": [vx, vy, vyaw]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_move(self) -> Dict[str, Any]:
        if not self._connected:
            return {"success": False, "error": "未连接"}
        try:
            self._sport_client.StopMove()
            return {"success": True, "action": "stop_move"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self._connected,
            "battery": self._battery,
            "mode": "real",
            "network_interface": self._network_interface,
            "source": "real"
        }

    def disconnect(self) -> Dict[str, Any]:
        self._connected = False
        self._sport_client = None
        print("👋 [Real] 已断开连接")
        return {"success": True, "action": "disconnect"}