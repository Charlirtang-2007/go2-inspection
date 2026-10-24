# backend/app/services/straight_mover.py
import time
import requests
import threading
from app.services.camera_service import camera_service
from app.services.detection_service import detect_aruco_markers

class StraightMover:
    """
    【直线逼近器】
    第一性原理：放弃复杂的视觉转向闭环，只走直线，到达距离阈值即停。
    核心机制：
    1. 独立发送线程以 10Hz 维持 Go2 的底层心跳，防止原地蠕动。
    2. 指令信箱模式：视觉线程暴力覆盖最新指令，保证绝无积压。
    """
    def __init__(self, k2b_ip="192.168.1.100", target_id=0, target_size=1500, timeout=20.0):
        self.k2b_url = f"http://{k2b_ip}:8000/api/robot/command"
        self.target_id = target_id
        self.target_size = target_size
        self.timeout = timeout # 超时保护：防止目标丢失导致狗一直走
        
        self.is_running = False
        self._sender_thread = None
        
        # 指令信箱
        self.latest_cmd = "stop"
        self.cmd_lock = threading.Lock()

    def _send_cmd(self, cmd):
        """底层发送 HTTP 请求，带极短超时防卡死"""
        try:
            requests.post(self.k2b_url, json={"cmd": cmd}, timeout=0.3)
        except Exception:
            pass

    def _update_cmd(self, new_cmd):
        """视觉线程调用：加锁覆盖最新指令"""
        with self.cmd_lock:
            if self.latest_cmd != new_cmd:
                # print(f"[Mover] 指令更新: {self.latest_cmd} -> {new_cmd}")
                self.latest_cmd = new_cmd

    def _sender_loop(self):
        """发送线程：10Hz 频率读取信箱，维持运动心跳"""
        while self.is_running:
            with self.cmd_lock:
                current_cmd = self.latest_cmd
            
            # forward 需要持续发维持心跳，stop 发一次就行
            if current_cmd != "stop":
                self._send_cmd(current_cmd)
            
            time.sleep(0.1)

        # 退出循环时，确保发一次 stop
        self._send_cmd("stop")

    def start(self):
        """
        启动直线逼近（阻塞方法）
        直到到达 size 阈值、超时、或手动调用 stop() 才会返回。
        """
        print(f"🎬 [StraightMover] 开始逼近 ID:{self.target_id}，目标尺寸:{self.target_size}")
        self.is_running = True
        self._update_cmd("stop")
        
        # 启动发送线程
        self._sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self._sender_thread.start()
        
        start_time = time.time()
        
        # 主线程：视觉检测循环
        while self.is_running:
            # 超时保护
            if time.time() - start_time > self.timeout:
                print(f"⏰ [StraightMover] 超过 {self.timeout} 秒未到达，强制停止。")
                break
            
            frame = camera_service.read_frame()
            if frame is None:
                time.sleep(0.05)
                continue
            
            markers = detect_aruco_markers(frame)
            target = next((m for m in markers if m["id"] == self.target_id), None)
            
            if target is not None:
                size = target["size"]
                # print(f"👀 size: {size:.0f} / {self.target_size}")
                
                if size >= self.target_size:
                    print(f"🎯 [StraightMover] 到达尺寸 {size:.0f} >= {self.target_size}，刹车。")
                    break # 退出循环
                else:
                    self._update_cmd("forward")
            else:
                # 没看到目标，停下等待
                self._update_cmd("stop")
                
            time.sleep(0.05)
            
        self.stop()

    def stop(self):
        """强制停止"""
        self.is_running = False
        self._update_cmd("stop")
        if self._sender_thread and self._sender_thread.is_alive():
            self._sender_thread.join(timeout=1.0)
        print("🛑 [StraightMover] 已停止。")
