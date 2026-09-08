# app/models/route.py
# 定义巡检路线相关的数据结构，包括：

# 单个巡检点（RoutePoint）

# 整条巡检路线（RoutePlan）

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class RoutePoint(BaseModel):
    id: int
    name: str
    x: int
    y: int
    action: str = "识别仪表"
    stay_seconds: int = 5
    is_start_point: bool = False

class RoutePlan(BaseModel):
    id: Optional[int] = None
    name: str = "默认路线"
    points: List[RoutePoint] = []
    status: str = "draft"  # draft | pending | deployed
    created_by: str = "甲方"
    created_at: datetime = datetime.now()
    deployed_at: Optional[datetime] = None
    round_trip: bool = True