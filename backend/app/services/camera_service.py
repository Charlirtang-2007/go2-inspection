# app/services/camera_service.py
# 📁 摄像头服务
# 职责：单例 + 后台采集 + 发布订阅，各消费者独立队列

import cv2
import time
import queue
import threading
import numpy as np
from typing import Optional, Tuple


class CameraService:
    """摄像头服务（单例 + 后台采集 + 订阅分发）"""

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

        # 订阅者：名称 -> 队列
        self._subscribers: dict = {}
        self._sub_lock = threading.Lock()

        self._thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()

        self._initialized = True

    def start(self) -> bool:
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

    def stop(self):
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

    # ========== 订阅接口 ==========

    def subscribe(self, name: str, maxsize: int = 2) -> queue.Queue:
        """订阅帧流，返回队列（满了自动丢旧帧）"""
        with self._sub_lock:
            q = queue.Queue(maxsize=maxsize)
            self._subscribers[name] = q
        print(f"📥 CameraService: '{name}' 已订阅")
        return q

    def unsubscribe(self, name: str):
        """取消订阅"""
        with self._sub_lock:
            self._subscribers.pop(name, None)
        print(f"📤 CameraService: '{name}' 已取消订阅")

    # ========== 采集循环 ==========

    def _capture_loop(self):
        while not self._stop_flag.is_set():
            if self.cap is None:
                break

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            # 保存最新帧（给非订阅式消费者用）
            with self._frame_lock:
                self._latest_frame = frame

            # 广播给所有订阅者
            with self._sub_lock:
                subscribers = list(self._subscribers.items())

            for name, q in subscribers:
                try:
                    q.put_nowait(frame.copy())
                except queue.Full:
                    # 队列满：丢最旧的，放最新的
                    try:
                        q.get_nowait()
                        q.put_nowait(frame.copy())
                    except (queue.Empty, queue.Full):
                        pass

    # ========== 兼容旧接口 ==========

    def read_frame(self) -> Optional[np.ndarray]:
        """获取最新一帧（非订阅式，一次性读）"""
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def get_frame_for_detection(self) -> Optional[np.ndarray]:
        """兼容旧接口"""
        return self.read_frame()

    def generate_mjpeg_stream(self, quality: int = 80, resize: Tuple[int, int] = None):
        """生成 MJPEG 视频流（走订阅模式）"""
        if not self.start():
            return

        q = self.subscribe("mjpeg", maxsize=2)
        try:
            while self._is_running:
                try:
                    frame = q.get(timeout=0.2)
                except queue.Empty:
                    continue

                if resize:
                    frame = cv2.resize(frame, resize)

                ret, jpeg = cv2.imencode(
                    '.jpg', frame,
                    [cv2.IMWRITE_JPEG_QUALITY, quality]
                )
                if not ret:
                    continue

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       jpeg.tobytes() + b'\r\n')
        finally:
            self.unsubscribe("mjpeg")

    def is_running(self) -> bool:
        return self._is_running


# 全局单例
camera_service = CameraService(camera_index=0)