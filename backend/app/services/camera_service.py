# app/services/camera_service.py
# 📁 摄像头服务 (K2B 网关版)
# 职责：从 K2B 拉取 MJPEG 流，保证视觉模型拿到的是最新、最完整的帧。

import cv2
import os
import time
import queue
import threading
import numpy as np
from typing import Optional, Tuple


class CameraService:
    """摄像头服务（单例 + 后台采集 + 发布订阅）"""

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
        self._cap = None 
        self._is_running = False

        self._latest_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()

        # 订阅者字典 {name: Queue}，maxsize默认2，保证队列内只有最新帧
        self._subscribers: dict = {}
        self._sub_lock = threading.Lock()

        self._thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()

        self._initialized = True

    def start(self) -> bool:
        if self._is_running:
            return True

        k2b_ip = os.getenv("K2B_IP", "192.168.1.100")
        stream_url = f"http://{k2b_ip}:8000/api/camera/video"
        self._stream_url = stream_url  # 供 _capture_loop 断流重连
        
        print(f"📷 尝试连接 K2B 视频流: {stream_url}...")
        
        try:
            self._cap = cv2.VideoCapture(stream_url)
            # [核心] 强制底层只保留1帧，防止FFmpeg内部严重积压导致高延迟
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
        
        if self._cap:
            self._cap.release()
            self._cap = None
            
        self._is_running = False
        self._thread = None
        print("🛑 CameraService: K2B 视频流已断开")

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

    def _capture_loop(self):
        """采集循环：防止画面滞后，确保视觉模型拿到最新帧"""
        while not self._stop_flag.is_set():
            if self._cap is None or not self._cap.isOpened():
                break

            try:
                # [核心] grab() 快速抓取并丢弃底层积压的旧帧，不解码，极快
                ok = self._cap.grab()
                if not ok:
                    # grab 失败时再调 retrieve 会刷 FFmpeg 的 Picture does not contain data
                    self._grab_fail = getattr(self, "_grab_fail", 0) + 1
                    if self._grab_fail >= 100:  # 约 1 秒连续失败，重连视频流
                        print(f"CameraService 连续 {self._grab_fail} 次 grab 失败，重连视频流...")
                        self._grab_fail = 0
                        try:
                            self._cap.release()
                        except Exception:
                            pass
                        time.sleep(0.5)
                        self._cap = cv2.VideoCapture(self._stream_url)
                        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    time.sleep(0.01)
                    continue
                self._grab_fail = 0
                
                # [核心] retrieve() 只解码刚刚抓到的最后一帧，保证画面清晰、实时
                ret, frame = self._cap.retrieve()
                
                if not ret or frame is None:
                    time.sleep(0.01)
                    continue

            except Exception as e:
                print(f"⚠️ CameraService 拉流失败: {e}")
                time.sleep(0.1)
                continue

            # 保存最新帧（YOLO/VLM 调 read_frame 时拿到的就是它）
            with self._frame_lock:
                self._latest_frame = frame

            # 广播给订阅者
            with self._sub_lock:
                subscribers = list(self._subscribers.items())

            for name, q in subscribers:
                try:
                    q.put_nowait(frame.copy())
                except queue.Full:
                    # [核心] 队列满了说明消费者（比如YOLO）处理慢。
                    # 直接扔掉队首的旧帧，塞入最新帧，绝对不让模型吃“旧饭”。
                    try:
                        q.get_nowait()
                        q.put_nowait(frame.copy())
                    except (queue.Empty, queue.Full):
                        pass
            
            # [核心] 限制最高抓取频率为100fps，防CPU空转（100fps远超摄像头实际帧率，不影响实时性）
            time.sleep(0.01)

    def read_frame(self) -> Optional[np.ndarray]:
        """供视觉模型读取最新画面"""
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            # 返回 copy 防止模型在处理时把原图覆盖
            return self._latest_frame.copy()

    def get_frame_for_detection(self) -> Optional[np.ndarray]:
        return self.read_frame()

    def generate_mjpeg_stream(self, quality: int = 80, resize: Tuple[int, int] = None):
        """提供前端 Web 显示的 MJPEG 流"""
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

                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
                if not ret:
                    continue

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       jpeg.tobytes() + b'\r\n')
        finally:
            self.unsubscribe("mjpeg")

    def is_running(self) -> bool:
        return self._is_running


camera_service = CameraService(network_interface="enp2s0")
