# app/routers/route.py
# 📁 4. app/routers/route.py —— 路线管理路由
# 职责：管理巡检路线的 CRUD 操作（保存/加载/确认生效）。

# 接口列表
# 方法	路径	功能
# GET	/api/route/list	获取所有路线
# GET	/api/route/default	获取当前生效的默认路线
# POST	/api/route/save	保存路线（草稿）
# POST	/api/route/confirm	确认路线生效


from fastapi import APIRouter, HTTPException
from app.models.route import RoutePlan
import json
import os
from typing import List, Optional

router = APIRouter(prefix="/api/route", tags=["route"])

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)
ROUTES_FILE = os.path.join(DATA_DIR, "routes.json")

def _load_routes() -> List[dict]:
    """加载路线数据"""
    if not os.path.exists(ROUTES_FILE):
        return []
    with open(ROUTES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def _save_routes(routes: List[dict]):
    """保存路线数据"""
    with open(ROUTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(routes, f, ensure_ascii=False, indent=2)

@router.get("/list")
async def list_routes() -> List[dict]:
    """获取所有路线"""
    return _load_routes()

@router.get("/default")
async def get_default_route() -> Optional[dict]:
    """获取默认路线（已部署的最新路线）"""
    routes = _load_routes()
    deployed = [r for r in routes if r.get("status") == "deployed"]
    if not deployed:
        return None
    return max(deployed, key=lambda x: x.get("deployed_at", ""))

@router.post("/save")
async def save_route(route: RoutePlan) -> dict:
    """保存路线"""
    routes = _load_routes()
    route_dict = route.model_dump(mode='json')
    route_dict["created_at"] = route_dict["created_at"]
    
    # 如果是更新已有路线
    if route.id is not None:
        for i, r in enumerate(routes):
            if r.get("id") == route.id:
                routes[i] = route_dict
                _save_routes(routes)
                return {"success": True, "message": "路线已更新"}
    
    # 新建路线
    route_dict["id"] = max([r.get("id", 0) for r in routes] + [0]) + 1
    routes.append(route_dict)
    _save_routes(routes)
    return {"success": True, "message": "路线已保存", "id": route_dict["id"]}

@router.post("/confirm")
async def confirm_route(route: RoutePlan) -> dict:
    """确认路线生效"""
    from datetime import datetime
    routes = _load_routes()
    route_dict = route.model_dump(mode='json')
    route_dict["status"] = "deployed"
    route_dict["deployed_at"] = datetime.now().isoformat()
    
    if route.id is not None:
        for i, r in enumerate(routes):
            if r.get("id") == route.id:
                routes[i] = route_dict
                _save_routes(routes)
                return {"success": True, "message": "路线已生效"}
    
    # 如果没有ID，作为新路线保存并生效
    route_dict["id"] = max([r.get("id", 0) for r in routes] + [0]) + 1
    routes.append(route_dict)
    _save_routes(routes)
    return {"success": True, "message": "路线已确认并生效"}