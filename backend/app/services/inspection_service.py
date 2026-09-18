# app/services/inspection_service.py
# 巡检任务服务：负责视频录制、异常检测、异常图片保存、巡检日志（JSON）生成，
# 以及将异常事件通过 WebSocket 广播给前端（anomaly 消息）。

import os
import time
import json
import asyncio
import threading
import cv2
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.utils.websocket_manager import manager
from app.services.camera_service import get_shared_camera
from app.services.detection_service import (
    detect_fire_by_color,
    detect_smoke_by_color,
    detect_oil_by_color,
)

# 巡检产物根目录：backend/data/inspections/{inspection_id}/
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "inspections"
)

# 异常类型 → 默认紧急程度
LEVEL_MAP = {"火焰": "高", "烟雾": "中", "漏油": "中"}
# 模拟热点区域（检测函数只返回 bool，这里按次序轮换一个“大概区域”）
AREA_SEQ = ["A区", "B区", "C区"]


def _inspection_dir(inspection_id: str) -> str:
    return os.path.join(DATA_DIR, inspection_id)


def _video_path(inspection_id: str) -> str:
    return os.path.join(_inspection_dir(inspection_id), "video.mp4")


def _log_path(inspection_id: str) -> str:
    return os.path.join(_inspection_dir(inspection_id), "log.json")


def _log_txt_path(inspection_id: str) -> str:
    return os.path.join(_inspection_dir(inspection_id), "log.txt")


class InspectionService:
    """巡检会话管理（单例）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        self.running: bool = False
        self.inspection_id: Optional[str] = None
        self.started_at: Optional[float] = None
        self.ended_at: Optional[float] = None
        self.events: List[Dict[str, Any]] = []
        self._writer: Optional[cv2.VideoWriter] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """由 FastAPI lifespan 在事件循环启动时注入，供后台线程安全广播使用。"""
        self._loop = loop

    # ============ 会话控制 ============

    def start(self) -> Dict[str, Any]:
        with self._lock:
            if self.running:
                return self._status_payload()
            self.inspection_id = "inspection_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs(_inspection_dir(self.inspection_id), exist_ok=True)
            self.events = []
            self._writer = None
            self.started_at = time.time()
            self.ended_at = None
            self._stop_event.clear()
            self.running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            print(f"🎥 [Inspection] 开始录制，inspection_id={self.inspection_id}")
            return self._status_payload()

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            if not self.running:
                return self._status_payload()
            inspection_id = self.inspection_id
            self.running = False
            self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

        self.ended_at = time.time()
        self._release_writer()
        self._write_log()
        print(f"⏹️ [Inspection] 录制结束，inspection_id={inspection_id}")
        return self._status_payload()

    def status(self) -> Dict[str, Any]:
        return self._status_payload()

    def _status_payload(self) -> Dict[str, Any]:
        if self.running and self.inspection_id:
            return {
                "recording": True,
                "inspection_id": self.inspection_id,
                "video_url": "",
                "log_url": "",
            }
        if self.inspection_id:
            return {
                "recording": False,
                "inspection_id": self.inspection_id,
                "video_url": f"/api/download/video/{self.inspection_id}",
                "log_url": f"/api/download/log/{self.inspection_id}",
            }
        return {
            "recording": False,
            "inspection_id": "",
            "video_url": "",
            "log_url": "",
        }

    # ============ 后台录制 + 检测循环 ============

    def _run(self) -> None:
        camera = get_shared_camera()
        last_detect = 0.0
        try:
            while not self._stop_event.is_set():
                frame = camera.read_frame()
                if frame is None:
                    time.sleep(0.05)
                    continue

                self._write_frame(frame)

                now = time.time()
                if now - last_detect >= 2.0:
                    last_detect = now
                    self._detect_and_alert(frame)
        finally:
            self._release_writer()

    def _write_frame(self, frame) -> None:
        if not self.inspection_id:
            return
        if self._writer is None:
            h, w = frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self._writer = cv2.VideoWriter(
                _video_path(self.inspection_id), fourcc, 15.0, (w, h)
            )
        self._writer.write(frame)

    def _release_writer(self) -> None:
        if self._writer is not None:
            try:
                self._writer.release()
            except Exception:
                pass
            self._writer = None

    def _detect_and_alert(self, frame) -> None:
        fire = detect_fire_by_color(frame)
        smoke = detect_smoke_by_color(frame)
        oil = detect_oil_by_color(frame)

        anomaly_type: Optional[str] = None
        if fire:
            anomaly_type = "火焰"
        elif smoke:
            anomaly_type = "烟雾"
        elif oil:
            anomaly_type = "漏油"

        if anomaly_type:
            self._record_anomaly(frame, anomaly_type)

    def _record_anomaly(self, frame, anomaly_type: str) -> None:
        if not self.inspection_id:
            return
        idx = len(self.events)
        ts = int(time.time())
        level = LEVEL_MAP.get(anomaly_type, "中")
        area = AREA_SEQ[idx % len(AREA_SEQ)]
        filename = f"{ts}_{anomaly_type}.jpg"
        filepath = os.path.join(_inspection_dir(self.inspection_id), filename)
        cv2.imwrite(filepath, frame)

        event = {
            "timestamp": ts,
            "type": anomaly_type,
            "level": level,
            "area": area,
            "record_time": self._elapsed_str(ts),
            "image": f"/api/download/image/{self.inspection_id}/{filename}",
        }
        self.events.append(event)
        self._write_log()
        print(f"🚨 [Inspection] 检测到异常: {anomaly_type} ({area}, {level})")
        self._broadcast_threadsafe({"type": "anomaly", "data": event})

    # ============ 日志生成 ============

    def _elapsed_str(self, ts: int) -> str:
        """把本次异常发生时间换算成录制已进行时长 HH:MM:SS。"""
        elapsed = max(0, ts - int(self.started_at or ts))
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _write_log(self) -> None:
        if not self.inspection_id:
            return
        payload = {
            "inspection_id": self.inspection_id,
            "started_at": (
                datetime.fromtimestamp(self.started_at).strftime("%Y-%m-%d %H:%M:%S")
                if self.started_at
                else ""
            ),
            "ended_at": (
                datetime.fromtimestamp(self.ended_at).strftime("%Y-%m-%d %H:%M:%S")
                if self.ended_at
                else ""
            ),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event_count": len(self.events),
            "events": self.events,
        }
        with open(_log_path(self.inspection_id), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        # 同时生成一份供人工阅读的 TXT 日志
        lines: List[str] = []
        lines.append(f"巡检日志 - {self.inspection_id}")
        lines.append(f"开始时间: {payload['started_at']}")
        lines.append(f"结束时间: {payload['ended_at'] or '进行中'}")
        lines.append(f"事件数: {payload['event_count']}")
        lines.append("-" * 48)
        for ev in self.events:
            ts = datetime.fromtimestamp(ev["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            lines.append(
                f"[{ts}] {ev['type']} ({ev['level']}, {ev['area']}) "
                f"录制时间 {ev.get('record_time', '--')} 图片 {ev.get('image', '')}"
            )
        with open(_log_txt_path(self.inspection_id), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def _broadcast_threadsafe(self, message: dict) -> None:
        loop = self._loop
        if loop and loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(manager.broadcast(message), loop)
            except Exception as e:
                print(f"⚠️ [Inspection] 异常广播失败: {e}")


# 单例
inspection_service = InspectionService()