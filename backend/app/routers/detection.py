# app/routers/detection.py
# 📁 视觉检测路由
# 职责：ArUco 识别 + YOLO 异常结果读取（推理在后台线程）

from fastapi import APIRouter
from app.services.detection_service import (
    detect_aruco_markers,
    get_latest_result,
)
from app.services.camera_service import camera_service
from app.services.notification_service import notification_service

router = APIRouter(prefix="/api/detection", tags=["detection"])

# 用于做“边缘触发”的上一轮状态
_prev_has_anomaly = False


def get_camera_frame():
    return camera_service.get_frame_for_detection()


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
async def detect_anomaly():
    """读取后台 YOLO 推理的最新结果；状态从“无异常”翻转到“有异常”时触发通知"""
    global _prev_has_anomaly

    result = get_latest_result()
    has = result.get("has_anomaly", False)
    anomalies = result.get("anomalies", [])

    # ========== 边缘触发：无 → 有时通知 ==========
    notified = False
    notify_channels = []
    if has and not _prev_has_anomaly:
        types = "、".join([a.get("type", "unknown") for a in anomalies])
        try:
            nres = await notification_service.notify_anomaly(
                anomaly_type=types,
                detail=f"检测到 {len(anomalies)} 处异常",
            )
            notified = nres.get("sent", False)
            notify_channels = nres.get("channels", [])
        except Exception as e:
            print(f"⚠️ 通知发送失败: {e}")
    _prev_has_anomaly = has

    return {
        "success": True,
        "has_anomaly": has,
        "anomalies": anomalies,
        "notified": notified,
        "notify_channels": notify_channels,
        "last_update": result.get("last_update", 0.0),
    }