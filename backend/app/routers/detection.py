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
from app.services.notification_service import notification_service

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

    # 三项检测
    has_fire = detect_fire_by_color(frame, fire_threshold)
    has_smoke = detect_smoke_by_color(frame, smoke_threshold)
    has_oil = detect_oil_by_color(frame, oil_threshold)

    # 汇总异常
    anomalies = []
    if has_fire:
        anomalies.append("🔥 火焰")
    if has_smoke:
        anomalies.append("💨 烟雾")
    if has_oil:
        anomalies.append("💧 漏油")

    has_anomaly = len(anomalies) > 0

    # 检测到异常 → 触发通知
    notified = False
    notify_channels = []
    if has_anomaly:
        result = await notification_service.notify_anomaly(
            anomaly_type="、".join(anomalies),
            detail=f"检测到 {len(anomalies)} 处异常"
        )
        notified = result.get("sent", False)
        notify_channels = result.get("channels", [])

    return {
        "success": True,
        "fire": has_fire,
        "smoke": has_smoke,
        "oil": has_oil,
        "has_anomaly": has_anomaly,
        "anomalies": anomalies,
        "notified": notified,
        "notify_channels": notify_channels
    }