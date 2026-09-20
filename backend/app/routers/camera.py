# app/routers/camera.py
# 📁 2. app/routers/camera.py —— 视频流路由
# 职责：提供摄像头视频流和截图功能。

# 接口列表
# 方法	路径	功能
# GET	/api/camera/video	MJPEG 视频流（实时画面）
# GET	/api/camera/snapshot	获取一帧截图（Base64）


from fastapi import APIRouter, Response, Query
from fastapi.responses import StreamingResponse
from app.services.camera_service import camera_service
from typing import Optional
import base64
import cv2

router = APIRouter(prefix="/api/camera", tags=["camera"])


@router.get("/video")
async def video_stream(
    width: Optional[int] = Query(640, description="画面宽度"),
    height: Optional[int] = Query(480, description="画面高度")
):
    """MJPEG 视频流"""
    if not camera_service.start():
        return Response(status_code=500, content="Camera not available")

    return StreamingResponse(
        camera_service.generate_mjpeg_stream(resize=(width, height)),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/snapshot")
async def snapshot():
    """获取一帧快照"""
    frame = camera_service.get_frame_for_detection()
    if frame is None:
        return {"error": "无法获取画面"}, 500

    _, buffer = cv2.imencode('.jpg', frame)
    return {
        "success": True,
        "image": base64.b64encode(buffer).decode('utf-8')
    }