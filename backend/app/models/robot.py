# 模型文件
# app/models/robot.py
# 定义机器狗相关的数据结构，包括：

# 机器狗的状态（RobotStatus）

# 控制指令（Command）

from pydantic import BaseModel
from typing import Optional

class RobotStatus(BaseModel):
    connected: bool
    battery: int
    current_state: str
    current_task: Optional[str] = None
    mode: str = "手动"

class Command(BaseModel):
    cmd: str
    speed: Optional[float] = 0.3
    duration: Optional[float] = 2.0