import os
from app.services.robot_interface import RobotInterface
from app.services.robot_mock import RobotMock
from app.services.robot_real import RobotReal

# 全局单例
_robot_instance = None

def get_robot_service() -> RobotInterface:
    """获取机器狗服务实例（单例）"""
    global _robot_instance

    if _robot_instance is None:
        use_mock = os.getenv("USE_MOCK_ROBOT", "true").lower() == "true"

        if use_mock:
            print("🤖 使用模拟机器狗模式")
            _robot_instance = RobotMock()
        else:
            network_interface = os.getenv("ROBOT_NETWORK_INTERFACE", "enp2s0")
            print(f"🤖 使用真实机器狗模式（网卡: {network_interface}）")
            _robot_instance = RobotReal(network_interface=network_interface)

    return _robot_instance