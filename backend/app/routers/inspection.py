# app/routers/inspection.py
# 📁 巡检下载路由
# 职责：提供巡检视频、日志文件、异常图片的下载/访问接口。

# 接口列表
# GET    /api/inspection/status                      当前巡检/录制状态
# GET    /api/inspections                            巡检记录列表
# GET    /api/download/video/{inspection_id}         下载巡检视频（MP4）
# GET    /api/download/log/{inspection_id}           下载巡检日志（JSON）
# GET    /api/download/logtxt/{inspection_id}        下载巡检日志（TXT）
# GET    /api/download/image/{inspection_id}/{name}  异常图片（供 <img> 与日志预览）


import os
import re
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.services.inspection_service import (
    inspection_service,
    DATA_DIR,
    _inspection_dir,
    _video_path,
    _log_path,
    _log_txt_path,
)

router = APIRouter(prefix="/api", tags=["inspection"])

# 巡检 ID 只允许字母/数字/下划线/连字符，防止目录穿越攻击
_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _check_id(inspection_id: str) -> str:
    if not _ID_RE.fullmatch(inspection_id):
        raise HTTPException(status_code=404, detail="巡检记录不存在")
    return inspection_id


@router.get("/inspection/status")
async def inspection_status():
    """当前巡检/录制状态"""
    return inspection_service.status()


@router.get("/inspections")
async def list_inspections():
    """列出所有巡检记录（含开始/结束时间、异常数、文件就绪状态）"""
    items = []
    if not os.path.isdir(DATA_DIR):
        return items
    for name in sorted(os.listdir(DATA_DIR)):
        dir_path = os.path.join(DATA_DIR, name)
        if not os.path.isdir(dir_path) or not _ID_RE.fullmatch(name):
            continue
        entry = {
            "inspection_id": name,
            "started_at": "",
            "ended_at": "",
            "event_count": 0,
            "video_ready": False,
            "log_ready": False,
        }
        log_file = _log_path(name)
        if os.path.isfile(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                entry["started_at"] = data.get("started_at", "")
                entry["ended_at"] = data.get("ended_at", "")
                entry["event_count"] = data.get("event_count", len(data.get("events", [])))
            except Exception:
                pass
        entry["video_ready"] = os.path.isfile(_video_path(name))
        entry["log_ready"] = os.path.isfile(log_file)
        items.append(entry)
    return items


@router.get("/download/video/{inspection_id}")
async def download_video(inspection_id: str):
    """下载巡检视频（MP4）"""
    inspection_id = _check_id(inspection_id)
    path = _video_path(inspection_id)
    if not os.path.isfile(path):
        return JSONResponse({"error": "视频文件不存在或尚未生成"}, status_code=404)
    return FileResponse(path, media_type="video/mp4", filename=f"{inspection_id}_video.mp4")


@router.get("/download/log/{inspection_id}")
async def download_log(inspection_id: str):
    """下载巡检日志（JSON）"""
    inspection_id = _check_id(inspection_id)
    path = _log_path(inspection_id)
    if not os.path.isfile(path):
        return JSONResponse({"error": "日志文件不存在或尚未生成"}, status_code=404)
    return FileResponse(
        path,
        media_type="application/json",
        filename=f"{inspection_id}_log.json",
    )


@router.get("/download/logtxt/{inspection_id}")
async def download_log_txt(inspection_id: str):
    """下载巡检日志（TXT，供人工阅读）"""
    inspection_id = _check_id(inspection_id)
    path = _log_txt_path(inspection_id)
    if not os.path.isfile(path):
        return JSONResponse({"error": "日志文件不存在或尚未生成"}, status_code=404)
    return FileResponse(
        path,
        media_type="text/plain; charset=utf-8",
        filename=f"{inspection_id}_log.txt",
    )


@router.get("/download/image/{inspection_id}/{filename}")
async def anomaly_image(inspection_id: str, filename: str):
    """异常图片（供前端 <img> 预览与下载）"""
    inspection_id = _check_id(inspection_id)
    safe_name = os.path.basename(filename)
    path = os.path.join(_inspection_dir(inspection_id), safe_name)
    if not os.path.isfile(path):
        return JSONResponse({"error": "图片不存在"}, status_code=404)
    return FileResponse(path, media_type="image/jpeg", filename=safe_name)