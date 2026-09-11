from abc import ABC, abstractmethod
from typing import Dict, Any

class RobotInterface(ABC):
    """机器狗控制抽象接口"""

    @abstractmethod
    def connect(self) -> bool:
        """连接机器狗"""
        pass

    @abstractmethod
    def stand_up(self) -> Dict[str, Any]:
        """站立"""
        pass

    @abstractmethod
    def sit_down(self) -> Dict[str, Any]:
        """坐下"""
        pass

    @abstractmethod
    def move(self, vx: float, vy: float, vyaw: float) -> Dict[str, Any]:
        """移动控制 (vx:前后, vy:左右, vyaw:旋转)"""
        pass

    @abstractmethod
    def stop_move(self) -> Dict[str, Any]:
        """停止移动"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """获取机器狗状态"""
        pass

    @abstractmethod
    def disconnect(self) -> Dict[str, Any]:
        """断开连接"""
        pass