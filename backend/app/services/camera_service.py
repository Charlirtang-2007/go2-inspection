# app/services/camera_service.py
# 📁 摄像头服务 (K2B 网关版)
# 职责：单例 + 后台采集 K2B 透传的 MJPEG 流 + 发布订阅

import cv2
import os
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

        # 兼容原参数，K2B 网关模式下不需要本地网卡直连狗
        self.network_interface = network_interface
        self._cap = None  # OpenCV 的 VideoCapture 对象
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

        # 1. 从环境变量读取 K2B 的 IP
        k2b_ip = os.getenv("K2B_IP", "192.168.62.240")
        stream_url = f"http://{k2b_ip}:8000/api/camera/video"
        
        print(f"📷 尝试连接 K2B 视频流: {stream_url}...")
        
        try:
            # 2. 使用 OpenCV 的原生网络流功能拉取 MJPEG
            self._cap = cv2.VideoCapture(stream_url)
            
            # 设置缓冲区大小，减少延迟
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if not self._cap.isOpened():
                print("❌ 无法打开 K2B 视频流，请检查网关是否启动、IP 是否正确")
                return False
            
            print("✅ 成功连接 K2B 视频流")
        except Exception as e:
            print(f"❌ 初始化视频流异常: {e}")
            return False

        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        self._is_running = True
        return True

    def stop(self):
        if not self._is_running:
            return
        self._stop_flag.set()
        if self._thread:
            self._thread.join(timeout=3)
        
        # 释放 OpenCV 网络流
        if self._cap:
            self._cap.release()
            self._cap = None
            
        self._is_running = False
        self._thread = None
        print("🛑 CameraService: K2B 视频流已断开")

    # ========== 订阅接口（保持不变） ==========

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

    # ========== 采集循环（核心改动） ==========

    def _capture_loop(self):
        """从 K2B 网络流拉帧"""
        while not self._stop_flag.is_set():
            if self._cap is None or not self._cap.isOpened():
                break

            try:
                # OpenCV 自动在底层处理 MJPEG 解析，直接返回 BGR 帧
                ret, frame = self._cap.read()
                
                if not ret or frame is None:
                    # 网络波动或没拿到帧，稍微歇一下防死循环
                    time.sleep(0.05)
                    continue

            except Exception as e:
                print(f"⚠️ CameraService 拉流失败: {e}")
                time.sleep(0.1)
                continue

            # 保存最新帧
            with self._frame_lock:
                self._latest_frame = frame

            # 广播给订阅者（MJPEG/录制/检测）
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
            
            # 控制帧率，K2B 是 15Hz，这里稍微限制一下，防止 CPU 空转
            time.sleep(1 / 15)

    # ========== 兼容旧接口（保持不变） ==========

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


# 全局单例（K2B 模式下 network_interface 参数不再影响主逻辑）
camera_service = CameraService(network_interface="enp2s0")
