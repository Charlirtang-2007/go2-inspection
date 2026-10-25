# backend/app/services/workflow/area_node.py
import time
from .base_action import BaseAction
from .config import ID_AREA_A, ID_AREA_B
from app.services.straight_mover import StraightMover
from app.services.detectors import preset_detector
from app.services.detection_service import enable_detection, disable_detection, get_latest_result

class AreaNode:
    def __init__(self, name, aruco_id, turn_dir, has_anomaly_check=False):
        self.name = name
        self.aruco_id = aruco_id
        self.turn_dir = turn_dir 
        self.has_anomaly_check = has_anomaly_check

    def run(self):
        print(f"\n==== 📍 开始执行 {self.name} 巡检 ====")
        
        mover = StraightMover(target_id=self.aruco_id, target_size=1200)
        mover.start()
        
        print(f"📢 [前端推送] 已到达 {self.name}！正在调整机位...")
        time.sleep(1) 
        
        BaseAction.turn(self.turn_dir)
        
        if self.has_anomaly_check:
            enable_detection()
        
        BaseAction.blind_move("forward", duration=2.5)
        
        if self.has_anomaly_check:
            self._check_anomaly()
            disable_detection()
        else:
            print(f"⏩ {self.name} 为正常区域，直接路过。")
            time.sleep(1)
        
        BaseAction.blind_move("backward", duration=2.5)
        reverse_dir = "right" if self.turn_dir == "left" else "left"
        BaseAction.turn(reverse_dir)

    def _check_anomaly(self):
        print(f"🔍 开始检测，10 秒倒计时兜底...")
        start_time = time.time()
        detected = False
        
        while time.time() - start_time < 10.0:
            result = get_latest_result()
            if result.get("has_anomaly"):
                conf = result['anomalies'][0].get('confidence', 0)
                print(f"🚨 [模型触发] 成功检测到异常！置信度: {conf}")
                detected = True
                break
            time.sleep(0.5)
            
        if not detected:
            print(f"⚠️ [兜底触发] 10秒超时！强行启动 Preset 报警！")
            preset_detector.trigger(area=self.name, reason=f"{self.name}异常")
        else:
            preset_detector.clear()
