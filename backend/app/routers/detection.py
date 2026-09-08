# app/routers/detection.py
# 📁 3. app/routers/detection.py —— 视觉检测路由
# 职责：提供 ArUco 标记识别和异常检测（火焰/烟雾/漏油）能力。

# 接口列表
# 方法	路径	功能
# GET	/api/detection/aruco	检测画面中的 ArUco 标记
# GET	/api/detection/anomaly	检测异常（火焰/烟雾/漏油）


from fastapi import APIRouter, Query
from app.services.detection_service import (
    detect_aruco_markers,
    detect_fire_by_color,
    detect_smoke_by_color,
    detect_oil_by_color
)
from app.services.camera_service import CameraService

router = APIRouter(prefix="/api/detection", tags=["detection"])

def get_camera_frame():
    """获取当前摄像头画面"""
    camera = CameraService()
    camera.start()
    frame = camera.get_frame_for_detection()
    camera.stop()
    return frame

@router.get("/aruco")
async def detect_aruco():
    """检测 ArUco 标记"""
    frame = get_camera_frame()
    if frame is None:
        return {"error": "无法获取画面"}, 500
    
    markers = detect_aruco_markers(frame)
    return {
        "success": True,
        "count": len(markers),
        "markers": markers
    }

@router.get("/anomaly")
async def detect_anomaly(
    fire_threshold: float = Query(0.01, description="火焰检测阈值"),
    smoke_threshold: float = Query(0.02, description="烟雾检测阈值"),
    oil_threshold: float = Query(0.01, description="漏油检测阈值")
):
    """检测异常（火焰/烟雾/漏油）"""
    frame = get_camera_frame()
    if frame is None:
        return {"error": "无法获取画面"}, 500
    
    return {
        "success": True,
        "fire": detect_fire_by_color(frame, fire_threshold),
        "smoke": detect_smoke_by_color(frame, smoke_threshold),
        "oil": detect_oil_by_color(frame, oil_threshold)
    }