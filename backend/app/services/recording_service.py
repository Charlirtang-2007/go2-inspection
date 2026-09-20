# app/services/recording_service.py
# 📁 录制服务
# 职责：从 camera_service 拿帧，写入 mp4，烧录时间戳，管理文件保留。

import cv2
import os
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from app.services.camera_service import camera_service


class RecordingService:
    """录制服务（单例）"""

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, output_dir: str = "recordings", max_files: int = 5,
                 fps: int = 25, width: int = 1280, height: int = 720):
        if getattr(self, "_initialized", False):
            return

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_files = max_files
        self.fps = fps
        self.width = width
        self.height = height

        self._thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()
        self._lock = threading.Lock()
        self._current_file: Optional[str] = None
        self._writer: Optional[cv2.VideoWriter] = None

        self._initialized = True

    def is_recording(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        """开始录制"""
        if self.is_recording():
            print("⚠️ 已在录制中")
            return False

        if not camera_service.is_running():
            if not camera_service.start():
                print("❌ 录制：摄像头未就绪")
                return False

        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> Optional[str]:
        """停止录制"""
        if not self.is_recording():
            return None

        self._stop_flag.set()
        self._thread.join(timeout=5)

        with self._lock:
            if self._writer is not None:
                self._writer.release()
                self._writer = None
            path = self._current_file
            self._current_file = None

        if path:
            print(f"✅ 录制完成: {path}")
            self._cleanup_old_files()
        return path

    def _record_loop(self):
        """录制主循环"""
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_inspection.mp4"
        filepath = self.output_dir / filename

        with self._lock:
            self._current_file = str(filepath)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self._writer = cv2.VideoWriter(
                str(filepath), fourcc, self.fps, (self.width, self.height)
            )

        print(f"🎬 开始录制: {filepath}")

        while not self._stop_flag.is_set():
            frame = camera_service.read_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            if frame.shape[1] != self.width or frame.shape[0] != self.height:
                frame = cv2.resize(frame, (self.width, self.height))

            self._draw_timestamp(frame)

            with self._lock:
                if self._writer is not None:
                    self._writer.write(frame)

        print("🎬 录制循环退出")

    def _draw_timestamp(self, frame):
        """烧录时间戳（左上角，和前端水印风格一致）"""
        now = datetime.now()
        line1 = now.strftime("%H:%M:%S")
        line2 = now.strftime("%Y-%m-%d")

        font = cv2.FONT_HERSHEY_SIMPLEX

        # 时间（大）
        cv2.putText(frame, line1, (16, 30), font, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(frame, line1, (16, 30), font, 0.7, (255, 255, 255), 1, cv2.LINE_AA)

        # 日期（小）
        cv2.putText(frame, line2, (16, 52), font, 0.45, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, line2, (16, 52), font, 0.45, (220, 220, 220), 1, cv2.LINE_AA)

    def _cleanup_old_files(self):
        """保留最近 N 个文件"""
        files = sorted(
            self.output_dir.glob("*.mp4"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        for old in files[self.max_files:]:
            try:
                old.unlink()
                print(f"🗑️ 删除旧录制: {old.name}")
            except Exception as e:
                print(f"⚠️ 删除失败 {old.name}: {e}")

    def list_recordings(self) -> List[Dict]:
        """列出所有录制文件"""
        files = sorted(
            self.output_dir.glob("*.mp4"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        result = []
        for f in files:
            stat = f.stat()
            result.append({
                "filename": f.name,
                "size": stat.st_size,
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "download_url": f"/api/recording/download/{f.name}"
            })
        return result

    def get_path(self, filename: str) -> Optional[str]:
        """安全获取文件路径（防路径穿越）"""
        safe = os.path.basename(filename)
        path = self.output_dir / safe
        if path.exists() and path.is_file():
            return str(path)
        return None


# 全局单例
recording_service = RecordingService(
    output_dir="recordings",
    max_files=5,
    fps=25,
    width=1280,
    height=720,
)