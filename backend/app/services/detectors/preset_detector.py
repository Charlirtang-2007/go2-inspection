# app/services/detectors/preset_detector.py
import threading
from datetime import datetime

_triggered = False
_trigger_reason = ""
_trigger_area = ""
_trigger_time = 0.0
_trigger_bbox = None          # ★ 新增：用于画框
_lock = threading.Lock()


def trigger(area: str, reason: str = "预设异常", bbox=None):
    """
    bbox: [x1, y1, x2, y2]，由外部（ArUco位置）传入
    """
    global _triggered, _trigger_reason, _trigger_area, _trigger_time, _trigger_bbox
    with _lock:
        _triggered = True
        _trigger_area = area
        _trigger_reason = reason
        _trigger_time = datetime.now().timestamp()
        _trigger_bbox = bbox
    print(f"[preset] 触发: area={area}, reason={reason}, bbox={bbox}")


def clear():
    global _triggered, _trigger_reason, _trigger_area, _trigger_time, _trigger_bbox
    with _lock:
        _triggered = False
        _trigger_reason = ""
        _trigger_area = ""
        _trigger_time = 0.0
        _trigger_bbox = None
    print("[preset] 状态已清除")


def detect(frame=None):
    with _lock:
        triggered = _triggered
        reason = _trigger_reason
        area = _trigger_area
        ts = _trigger_time
        bbox = _trigger_bbox

    if not triggered:
        return {"has_anomaly": False, "anomalies": [], "annotated": None}

    anomalies = [{
        "type": "preset",
        "confidence": 1.0,
        "bbox": bbox,
        "area": area,
        "reason": reason,
        "timestamp": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
        "source": "preset",
    }]
    return {"has_anomaly": True, "anomalies": anomalies, "annotated": None}