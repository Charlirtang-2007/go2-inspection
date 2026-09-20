# app/routers/recording.py
# 📁 录制管理路由
# 职责：控制录制开始/停止，列出和下载录制文件。

# 接口列表
# 方法	路径	功能
# POST	/api/recording/start	开始录制
# POST	/api/recording/stop	停止录制
# GET	/api/recording/status	查询录制状态
# GET	/api/recording/list	列出所有录制文件
# GET	/api/recording/download/{filename}	下载指定文件


from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.services.recording_service import recording_service

router = APIRouter(prefix="/api/recording", tags=["recording"])


@router.post("/start")
async def start_recording():
    """开始录制"""
    ok = recording_service.start()
    return {"success": ok, "recording": recording_service.is_recording()}


@router.post("/stop")
async def stop_recording():
    """停止录制"""
    path = recording_service.stop()
    return {"success": True, "file": path}


@router.get("/status")
async def recording_status():
    """查询录制状态"""
    return {"recording": recording_service.is_recording()}


@router.get("/list")
async def list_recordings():
    """列出所有录制文件"""
    return {"success": True, "files": recording_service.list_recordings()}


@router.get("/download/{filename}")
async def download_recording(filename: str):
    """下载录制文件"""
    path = recording_service.get_path(filename)
    if not path:
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )