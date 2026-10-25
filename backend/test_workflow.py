# backend/test_workflow.py
import time
from app.services.camera_service import camera_service
from app.services.workflow import InspectionWorkflow
from app.services.workflow.base_action import BaseAction

if __name__ == "__main__":
    print("📷 正在启动视频流...")
    camera_service.start()
    time.sleep(2)
    
    workflow = InspectionWorkflow()
    
    input("👉 场地布置好了吗？狗摆正了吗？按回车开始 A/B 区完整巡检测试...")
    try:
        workflow.start()
    except KeyboardInterrupt:
        print("\n🛑 手动中止！")
    finally:
        print("🛑 强制停车，断开视频流。")
        BaseAction.send_cmd("stop")
        camera_service.stop()
