# app/services/camera_service.py
# 📁 摄像头服务
# 职责：单例模式管理摄像头，后台持续采集帧，供视频流/检测/录制共用。

import cv2
import time
import threading
import numpy as np
from typing import Optional, Tuple


class CameraService:
    """摄像头服务（单例 + 后台持续采集）"""

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, camera_index: int = 0):
        if getattr(self, "_initialized", False):
            return

        self.camera_index = camera_index
        self.cap: Optional[cv2.VideoCapture] = None
        self._is_running = False

        self._latest_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()

        self._thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()

        self._initialized = True

    def start(self) -> bool:
        """启动摄像头（后台持续采集）"""
        if self._is_running:
            return True

        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            self.cap = None
            return False

        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        self._is_running = True
        print("✅ CameraService: 摄像头已启动")
        return True

    def _capture_loop(self):
        """后台采集循环：不断读取最新帧"""
        while not self._stop_flag.is_set():
            if self.cap is None:
                break
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue
            with self._frame_lock:
                self._latest_frame = frame

    def read_frame(self) -> Optional[np.ndarray]:
        """读取最新一帧（线程安全）"""
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def get_frame_for_detection(self) -> Optional[np.ndarray]:
        """获取一帧用于检测（兼容旧接口）"""
        return self.read_frame()

    def generate_mjpeg_stream(self, quality: int = 80, resize: Tuple[int, int] = None):
        """生成 MJPEG 视频流"""
        if not self.start():
            return

        while self._is_running:
            frame = self.read_frame()
            if frame is None:
                time.sleep(0.05)
                continue

            if resize:
                frame = cv2.resize(frame, resize)

            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            if not ret:
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' +
                   jpeg.tobytes() + b'\r\n')

    def stop(self):
        """停止摄像头"""
        if not self._is_running:
            return
        self._stop_flag.set()
        if self._thread:
            self._thread.join(timeout=3)
        if self.cap:
            self.cap.release()
            self.cap = None
        self._is_running = False
        self._thread = None
        print("🛑 CameraService: 摄像头已停止")

    def is_running(self) -> bool:
        return self._is_running


# 全局单例
camera_service = CameraService(camera_index=0)