# app/services/camera_service.py
# 📁 摄像头服务
# 职责：单例 + 后台采集狗自带摄像头 + 发布订阅，各消费者独立队列

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

    def __init__(self, network_interface: str = "enp2s0"):
        if getattr(self, "_initialized", False):
            return

        self.network_interface = network_interface
        self._video_client = None
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

        # 初始化 VideoClient（连接狗自带摄像头）
        try:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize
            from unitree_sdk2py.go2.video.video_client import VideoClient

            print(f"📷 初始化 VideoClient（网卡: {self.network_interface}）...")
            ChannelFactoryInitialize(0, self.network_interface)

            self._video_client = VideoClient()
            self._video_client.SetTimeout(1.0)
            self._video_client.Init()
            print("✅ VideoClient 初始化成功")
        except Exception as e:
            print(f"❌ VideoClient 初始化失败: {e}")
            return False

        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        self._is_running = True
        print("✅ CameraService: 狗摄像头已启动")
        return True

    def stop(self):
        if not self._is_running:
            return
        self._stop_flag.set()
        if self._thread:
            self._thread.join(timeout=3)
        self._video_client = None
        self._is_running = False
        self._thread = None
        print("🛑 CameraService: 狗摄像头已停止")

    # ========== 订阅接口 ==========

    def subscribe(self, name: str, maxsize: int = 2) -> queue.Queue:
        with self._sub_lock:
            q = queue.Queue(maxsize=maxsize)
            self._subscribers[name] = q
        print(f"📥 CameraService: '{name}' 已订阅")
        return q

    def unsubscribe(self, name: str):
        with self._sub_lock:
            self._subscribers.pop(name, None)
        print(f"📤 CameraService: '{name}' 已取消订阅")

    # ========== 采集循环 ==========

    def _capture_loop(self):
        """从狗自带摄像头拉帧"""
        while not self._stop_flag.is_set():
            if self._video_client is None:
                break

            try:
                # GetImageSample 返回 (ret, data)
                # ret == 0 成功，data 是 JPEG 字节（可能是 list 或 bytes）
                ret, data = self._video_client.GetImageSample()
                if ret != 0 or data is None:
                    time.sleep(0.02)
                    continue

                # data 可能是 list，转成 bytes
                if isinstance(data, list):
                    data = bytes(data)

                # JPEG 解码为 numpy array
                img_array = np.frombuffer(data, dtype=np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if frame is None:
                    time.sleep(0.02)
                    continue
            except Exception as e:
                print(f"⚠️ CameraService 取帧失败: {e}")
                time.sleep(0.1)
                continue

            # 保存最新帧
            with self._frame_lock:
                self._latest_frame = frame

            # 广播给订阅者
            with self._sub_lock:
                subscribers = list(self._subscribers.items())

            for name, q in subscribers:
                try:
                    q.put_nowait(frame.copy())
                except queue.Full:
                    try:
                        q.get_nowait()
                        q.put_nowait(frame.copy())
                    except (queue.Empty, queue.Full):
                        pass

    # ========== 兼容旧接口 ==========

    def read_frame(self) -> Optional[np.ndarray]:
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def get_frame_for_detection(self) -> Optional[np.ndarray]:
        return self.read_frame()

    def generate_mjpeg_stream(self, quality: int = 80, resize: Tuple[int, int] = None):
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


# 全局单例（网卡名按实际情况改）
camera_service = CameraService(network_interface="enp2s0")