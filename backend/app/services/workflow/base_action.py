# backend/app/services/workflow/base_action.py
import time
import requests

K2B_URL = "http://192.168.1.100:8000/api/robot/command"

class BaseAction:
    @staticmethod
    def send_cmd(cmd, duration=0.0):
        try:
            requests.post(K2B_URL, json={"cmd": cmd}, timeout=0.5)
            if duration > 0:
                time.sleep(duration)
                requests.post(K2B_URL, json={"cmd": "stop"}, timeout=0.5)
        except Exception:
            pass

    @staticmethod
    def turn(direction, duration=1.3):
        print(f"🔄 执行转向: {direction.upper()} ({duration}秒)")
        BaseAction.send_cmd(direction, duration=duration)
        time.sleep(0.5)

    @staticmethod
    def blind_move(direction="forward", duration=2.5):
        """盲走几步（方便后续统一微调步长）"""
        print(f"🚶 盲走: {direction.upper()} ({duration}秒)")
        BaseAction.send_cmd(direction, duration=duration)
        time.sleep(0.5)
