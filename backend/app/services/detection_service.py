# app/services/detection_service.py
import os
import cv2
import cv2.aruco as aruco
import numpy as np
import threading
import time
from datetime import datetime
from pathlib import Path

from app.services.detectors import yolo_detector, vlm_detector, preset_detector

# ========== ArUco 检测 ==========
def detect_aruco_markers(frame):
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
            x1, y1 = int(corner[0][0]), int(corner[0][1])
            x2, y2 = int(corner[2][0]), int(corner[2][1])
            results.append({
                "id": int(marker_id),
                "center": {"x": center_x, "y": center_y},
                "size": float(size),
                "bbox": [x1, y1, x2, y2],
            })
    return results


# ========== 配置 ==========
ENGINE = os.getenv("DETECTION_ENGINE", "yolo").lower()
ANOMALY_DIR = Path(__file__).parent.parent.parent / "recordings" / "anomalies"
ANOMALY_DIR.mkdir(parents=True, exist_ok=True)

# ArUco ID 映射（按实际调整）
ARUCO_A_AREA = 1      # A区标识
ARUCO_B_AREA = 2      # B区标识

# 共享结果
_latest_result = {"has_anomaly": False, "anomalies": [], "last_update": 0.0}
_result_lock = threading.Lock()


def get_latest_result():
    with _result_lock:
        return {
            "has_anomaly": _latest_result["has_anomaly"],
            "anomalies": list(_latest_result["anomalies"]),
            "last_update": _latest_result["last_update"],
            "engine": ENGINE,
        }


# ========== 统一推理 ==========
def _infer(frame):
    results = []
    annotated = frame.copy()
    any_bbox = False

    # 1. 先检测 ArUco，用于自动触发 preset 和画框
    markers = detect_aruco_markers(frame)
    for m in markers:
        if m["id"] == ARUCO_B_AREA:
            preset_detector.trigger(
                area="B",
                reason="B区异常",
                bbox=m["bbox"]
            )
        # 可添加 A 区复检触发逻辑

    # 2. 三路检测
    if "preset" in ENGINE:
        try:
            r = preset_detector.detect(frame)
            if r.get("has_anomaly"):
                results.append(r)
        except Exception as e:
            print(f"[detect] preset failed: {e}")

    if "yolo" in ENGINE:
        try:
            results.append(yolo_detector.detect(frame))
        except Exception as e:
            print(f"[detect] yolo failed: {e}")

    if "vlm" in ENGINE:
        try:
            results.append(vlm_detector.detect(frame))
        except Exception as e:
            print(f"[detect] vlm failed: {e}")

    # 3. 合并结果
    has = any(r.get("has_anomaly") for r in results)
    anomalies = []
    for r in results:
        anomalies.extend(r.get("anomalies", []))

    # 4. 统一画框（如果有 bbox）
    for a in anomalies:
        bbox = a.get("bbox")
        if bbox:
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 3)
            cv2.putText(annotated, f"{a.get('type','?')} {a.get('confidence',0):.2f}",
                        (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            any_bbox = True

    # 5. 保存截图（有异常时）
    if has:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        img_path = ANOMALY_DIR / f"anomaly_{ts}.jpg"
        img_to_save = annotated if any_bbox else frame
        cv2.imwrite(str(img_path), img_to_save)
        for a in anomalies:
            a["image"] = img_path.name

    return {"has_anomaly": has, "anomalies": anomalies}


# ========== 后台线程 ==========
_worker_thread = None
_worker_stop = threading.Event()
_frame_source = None


def start_worker(frame_source, interval=2.0):
    global _worker_thread, _frame_source
    _frame_source = frame_source
    _worker_stop.clear()
    _worker_thread = threading.Thread(target=_worker_loop, args=(interval,), daemon=True)
    _worker_thread.start()
    print(f"[detection] worker started, engine={ENGINE}, interval={interval}s")


def stop_worker():
    _worker_stop.set()
    if _worker_thread:
        _worker_thread.join(timeout=3)
    print("[detection] worker stopped")


def _worker_loop(interval):
    while not _worker_stop.is_set():
        t0 = time.time()
        try:
            frame = _frame_source() if _frame_source else None
            if frame is not None:
                result = _infer(frame)
                with _result_lock:
                    _latest_result["has_anomaly"] = result["has_anomaly"]
                    _latest_result["anomalies"] = result["anomalies"]
                    _latest_result["last_update"] = time.time()
        except Exception as e:
            print(f"[detection] worker error: {e}")
        elapsed = time.time() - t0
        time.sleep(max(0.0, interval - elapsed))