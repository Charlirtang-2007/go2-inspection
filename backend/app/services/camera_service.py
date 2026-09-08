#管理摄像头视频流。
# app/services/camera_service.py

import cv2
import time
import numpy as np
from typing import Optional, Generator, Tuple

class CameraService:
    """摄像头服务（管理视频流采集）"""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.cap: Optional[cv2.VideoCapture] = None
        self._is_running = False

    def start(self) -> bool:
        """启动摄像头"""
        if self.cap is not None and self.cap.isOpened():
            return True
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            self.cap = None
            return False
        self._is_running = True
        return True
    
    def get_frame_for_detection(self):
        """获取一帧用于检测"""
        return self.read_frame()

    def read_frame(self) -> Optional[np.ndarray]:
        """读取一帧图像"""
        if self.cap is None or not self.cap.isOpened():
            return None
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

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
        self._is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    def get_frame_for_detection(self) -> Optional[np.ndarray]:
        """获取一帧用于检测"""
        return self.read_frame()