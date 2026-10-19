from typing import Dict, Any
import os
import requests
from app.services.robot_interface import RobotInterface

class RobotReal(RobotInterface):
    """真实机器狗控制 - 基于 K2B 边缘网关 (HTTP)"""

    def __init__(self, network_interface: str = "enp2s0"):
        # 保留该参数以兼容工厂函数的调用，但在 K2B 模式下不再使用本地网卡
        self._network_interface = network_interface
        
        # 从环境变量读取 K2B 的 IP（默认设为你的 K2B 当前 IP）
        self._k2b_ip = os.getenv("K2B_IP", "192.168.62.240")
        self._base_url = f"http://{self._k2b_ip}:8000/api/robot"
        self._connected = False
        self._battery = 100.0

    def connect(self) -> bool:
        try:
            # 向 K2B 发个轻量级请求，测试网关是否在线
            # 这里我们故意发个空指令，只要 K2B 返回 200 或 422 都说明网络通了
            requests.post(f"{self._base_url}/command", json={"cmd": "ping"}, timeout=3)
            
            self._connected = True
            print(f"✅ [Real] 成功连接 K2B 边缘网关（IP: {self._k2b_ip}）")
            return True
        except Exception as e:
            print(f"❌ [Real] 连接 K2B 失败: {e}")
            self._connected = False
            return False

    def _send_cmd(self, cmd: str) -> Dict[str, Any]:
        """发送 HTTP 指令给 K2B 的辅助函数"""
        if not self._connected:
            return {"success": False, "error": "未连接 K2B 网关"}
        try:
            res = requests.post(
                f"{self._base_url}/command",
                json={"cmd": cmd},
                timeout=3
            )
            res.raise_for_status()
            return {"success": True, "action": cmd}
        except Exception as e:
            return {"success": False, "error": f"HTTP 请求失败: {str(e)}"}

    def stand_up(self) -> Dict[str, Any]:
        return self._send_cmd("standup")

    def sit_down(self) -> Dict[str, Any]:
        return self._send_cmd("sit")

    def move(self, vx: float, vy: float, vyaw: float) -> Dict[str, Any]:
        """将速度向量映射为 K2B 的简单动作指令"""
        if vx > 0:
            return self._send_cmd("forward")
        elif vx < 0:
            return self._send_cmd("backward")
        elif vyaw > 0:
            return self._send_cmd("left")
        elif vyaw < 0:
            return self._send_cmd("right")
        else:
            return self._send_cmd("stop")

    def stop_move(self) -> Dict[str, Any]:
        return self._send_cmd("stop")

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self._connected,
            "battery": self._battery,
            "mode": "real",
            "network_interface": self._network_interface,
            "source": "k2b_gateway"
        }

    def disconnect(self) -> Dict[str, Any]:
        self._connected = False
        print("👋 [Real] 已断开与 K2B 的连接")
        return {"success": True, "action": "disconnect"}
