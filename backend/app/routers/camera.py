# app/routers/camera.py
# 📁 2. app/routers/camera.py —— 视频流路由
# 职责：提供摄像头视频流和截图功能。

# 接口列表
# 方法	路径	功能
# GET	/api/camera/video	MJPEG 视频流（实时画面）
# GET	/api/camera/snapshot	获取一帧截图（Base64）


# app/routers/camera.py

from fastapi import APIRouter, Response, Query
from app.services.camera_service import CameraService, get_shared_camera
from typing import Optional
from fastapi.responses import StreamingResponse
router = APIRouter(prefix="/api/camera", tags=["camera"])

# 全局摄像头服务实例（懒加载，与录制/异常检测共享）
def get_camera() -> CameraService:
    return get_shared_camera()

@router.get("/video")
async def video_stream(
    width: Optional[int] = Query(640, description="画面宽度"),
    height: Optional[int] = Query(480, description="画面高度")
):
    """MJPEG 视频流"""
    camera = get_camera()
    if not camera.start():
        return Response(status_code=500, content="Camera not available")
    
    return StreamingResponse( #记得同步
        camera.generate_mjpeg_stream(resize=(width, height)),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/snapshot")
async def snapshot():
    """获取一帧快照"""
    camera = get_camera()
    frame = camera.get_frame_for_detection()
    if frame is None:
        return {"error": "无法获取画面"}, 500
    
    import base64
    import cv2
    _, buffer = cv2.imencode('.jpg', frame)
    return {
        "success": True,
        "image": base64.b64encode(buffer).decode('utf-8')
    }