# backend/app/services/workflow/main_workflow.py
import time
from .base_action import BaseAction
from .area_node import AreaNode
from .config import ID_START, ID_AREA_A, ID_AREA_B, ID_END
from app.services.straight_mover import StraightMover

class InspectionWorkflow:
    def __init__(self):
        self.area_a = AreaNode(name="A区", aruco_id=ID_AREA_A, turn_dir="left", has_anomaly_check=True)
        self.area_b = AreaNode(name="B区", aruco_id=ID_AREA_B, turn_dir="right", has_anomaly_check=False)

    def start(self):
        print("🚀 [主控] 启动完整巡检路线！")
        BaseAction.send_cmd("standup")
        time.sleep(2)
        
        print("\n📍 正在前往巡检入口...")
        entry_mover = StraightMover(target_id=ID_START, target_size=1200)
        entry_mover.start()
        
        self.area_a.run()
        self.area_b.run()
        
        print("\n📍 正在前往终点集合...")
        end_mover = StraightMover(target_id=ID_END, target_size=1200)
        end_mover.start()
        
        print("\n🎉 [主控] 本次巡检全部执行完毕！")
