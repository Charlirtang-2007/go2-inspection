# app/routers/detection.py
"""
视觉检测 HTTP 接口

职责：
- /api/detection/aruco             ArUco 检测（同步）
- /api/detection/anomaly           读 worker 的最新结果（只读，不触发推理、不触发通知）
- /api/detection/trigger_preset    手动触发预设异常（演示兜底）
- /api/detection/clear_preset      清除预设异常

设计说明：
- 通知由 detection_service 的 worker 在状态翻转时通过 on_anomaly 回调直接触发
- 本模块只负责给前端返回结果，不做任何副作用
"""
from fastapi import APIRouter

from app.services.detection_service import (
    detect_aruco_markers,
    get_latest_result,
)
from app.services.camera_service import camera_service
from app.services.detectors import preset_detector

router = APIRouter(prefix="/api/detection", tags=["detection"])


def get_camera_frame():
    return camera_service.get_frame_for_detection()


@router.get("/aruco")
async def detect_aruco():
    """检测画面中的 ArUco 标记"""
    frame = get_camera_frame()
    if frame is None:
        return {"error": "无法获取画面"}, 500

    markers = detect_aruco_markers(frame)
    return {
        "success": True,
        "count": len(markers),
        "markers": markers,
    }


@router.get("/anomaly")
async def detect_anomaly():
    """
    读取后台 worker 的最新检测结果。
    纯读操作：不触发推理，不触发通知。
    """
    result = get_latest_result()
    return {
        "success": True,
        "has_anomaly": result.get("has_anomaly", False),
        "anomalies": result.get("anomalies", []),
        "last_update": result.get("last_update", 0.0),
        "engine": result.get("engine", ""),
    }


@router.post("/trigger_preset")
async def trigger_preset(area: str = "B", reason: str = "手动触发"):
    """手动触发预设异常（演示兜底用）"""
    preset_detector.trigger(area=area, reason=reason)
    return {"success": True, "area": area, "reason": reason}


@router.post("/clear_preset")
async def clear_preset():
    """清除预设异常状态"""
    preset_detector.clear()
    return {"success": True}