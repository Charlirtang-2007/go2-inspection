# app/services/detection_service.py
import cv2
import cv2.aruco as aruco
import numpy as np
import threading
import time
from datetime import datetime
from pathlib import Path

# ========== ArUco 检测（保留不动） ==========

def detect_aruco_markers(frame):
    """检测画面中的 ArUco 标记"""
    if frame is None:
        return []

    try:
        aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
        parameters = aruco.DetectorParameters()
        detector = aruco.ArucoDetector(aruco_dict, parameters)
        corners, ids, _ = detector.detectMarkers(frame)
    except AttributeError:
        aruco_dict = aruco.Dictionary_get(aruco.DICT_4X4_50)
        params = aruco.DetectorParameters_create()
        corners, ids, _ = aruco.detectMarkers(frame, aruco_dict, parameters=params)

    results = []
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            corner = corners[i][0]
            center_x = int((corner[0][0] + corner[2][0]) / 2)
            center_y = int((corner[0][1] + corner[2][1]) / 2)
            size = np.linalg.norm(corner[0] - corner[1])
            results.append({
                "id": int(marker_id),
                "center": {"x": center_x, "y": center_y},
                "size": float(size)
            })
    return results


# ========== YOLO 检测（替换颜色检测） ==========

# 配置
MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "smoke.pt"
CONF_THRESHOLD = 0.5
ACTIVE_CLASSES = ["smoke"]   # 先只跑烟雾
ANOMALY_DIR = Path(__file__).parent.parent.parent / "recordings" / "anomalies"
ANOMALY_DIR.mkdir(parents=True, exist_ok=True)

# 单例模型
_model = None
_model_lock = threading.Lock()

def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from ultralytics import YOLO
                print(f"[detection] loading YOLO model: {MODEL_PATH}")
                _model = YOLO(str(MODEL_PATH))
                print(f"[detection] model loaded, classes: {_model.names}")
    return _model


# 共享结果（前端轮询读）
_latest_result = {
    "has_anomaly": False,
    "anomalies": [],
    "last_update": 0.0,
}
_result_lock = threading.Lock()

def get_latest_result():
    with _result_lock:
        return {
            "has_anomaly": _latest_result["has_anomaly"],
            "anomalies": list(_latest_result["anomalies"]),
            "last_update": _latest_result["last_update"],
        }


# 后台推理线程
_worker_thread = None
_worker_stop = threading.Event()
_frame_source = None

def start_worker(frame_source):
    """frame_source: callable，返回 BGR 帧或 None"""
    global _worker_thread, _frame_source
    _frame_source = frame_source
    _worker_stop.clear()
    _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
    _worker_thread.start()
    print("[detection] YOLO worker started")

def stop_worker():
    _worker_stop.set()
    if _worker_thread:
        _worker_thread.join(timeout=3)
    print("[detection] YOLO worker stopped")


def _worker_loop():
    model = _get_model()
    interval = 1.0  # 每秒推理一次
    while not _worker_stop.is_set():
        t0 = time.time()
        try:
            frame = _frame_source() if _frame_source else None
            if frame is not None:
                result = _infer(model, frame)
                with _result_lock:
                    _latest_result["has_anomaly"] = result["has_anomaly"]
                    _latest_result["anomalies"] = result["anomalies"]
                    _latest_result["last_update"] = time.time()
        except Exception as e:
            print(f"[detection] worker error: {e}")
        elapsed = time.time() - t0
        time.sleep(max(0.0, interval - elapsed))


def _infer(model, frame):
    results = model.predict(frame, conf=CONF_THRESHOLD, verbose=False, device="cpu")
    anomalies = []
    annotated = frame.copy()

    for r in results:
        if r.boxes is None:
            continue
        for box in r.boxes:
            cls_id = int(box.cls[0].item())
            cls_name = model.names.get(cls_id, str(cls_id))
            conf = float(box.conf[0].item())

            if cls_name not in ACTIVE_CLASSES:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 3)
            cv2.putText(annotated, f"{cls_name} {conf:.2f}",
                        (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            anomalies.append({
                "type": cls_name,
                "confidence": round(conf, 3),
                "bbox": [x1, y1, x2, y2],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

    has = len(anomalies) > 0

    if has:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        img_path = ANOMALY_DIR / f"anomaly_{ts}.jpg"
        cv2.imwrite(str(img_path), annotated)
        for a in anomalies:
            a["image"] = img_path.name

    return {"has_anomaly": has, "anomalies": anomalies}