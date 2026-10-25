# app/services/detection_service.py
"""
检测调度服务

职责：
- 管理多个检测器（preset / yolo / vlm），通过统一接口调用
- 后台 worker 循环，定期从 camera_service 拿帧检测
- 检测结果写入 _latest_result 共享变量（前端轮询读）
- 状态翻转（无异常 → 有异常）时触发 on_anomaly 回调

设计原则：
- 不直接依赖 notification_service，通过回调解耦
- 不直接依赖 camera_service，通过 frame_source 回调解耦
- 检测器通过 detect(frame) -> dict 统一接口调用

对外接口：
- start_worker(frame_source, interval, on_anomaly)  启动
- stop_worker()                                      停止
- get_latest_result()                                读结果
- detect_aruco_markers(frame)                        ArUco 检测
"""
import os
import cv2
import cv2.aruco as aruco
import numpy as np
import threading
import time
from datetime import datetime
from pathlib import Path

from app.services.detectors import yolo_detector, vlm_detector, preset_detector

# 在文件顶部的 import 之后加上
_detection_enabled = False

def enable_detection():
    global _detection_enabled
    _detection_enabled = True
    print("🟢 [Detection] AI 检测已开启！")

def disable_detection():
    global _detection_enabled
    _detection_enabled = False
    print("🔴 [Detection] AI 检测已关闭。")


# ============ ArUco 检测（保留不动） ============
def detect_aruco_markers(frame):
    """检测画面中的 ArUco 标记，返回 [{id, center, size, bbox}, ...]"""
    if frame is None:
        return []
    try:
        aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
        params = aruco.DetectorParameters()
        detector = aruco.ArucoDetector(aruco_dict, params)
        corners, ids, _ = detector.detectMarkers(frame)
    except AttributeError:
        aruco_dict = aruco.Dictionary_get(aruco.DICT_4X4_50)
        params = aruco.DetectorParameters_create()
        corners, ids, _ = aruco.detectMarkers(frame, aruco_dict, parameters=params)

    results = []
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            corner = corners[i][0]
            cx = int((corner[0][0] + corner[2][0]) / 2)
            cy = int((corner[0][1] + corner[2][1]) / 2)
            size = float(np.linalg.norm(corner[0] - corner[1]))
            x1, y1 = int(corner[0][0]), int(corner[0][1])
            x2, y2 = int(corner[2][0]), int(corner[2][1])
            results.append({
                "id": int(marker_id),
                "center": {"x": cx, "y": cy},
                "size": size,
                "bbox": [x1, y1, x2, y2],
            })
    return results


# ============ 配置 ============
ENGINE = os.getenv("DETECTION_ENGINE", "yolo").lower()
ANOMALY_DIR = Path(__file__).parent.parent.parent / "recordings" / "anomalies"
ANOMALY_DIR.mkdir(parents=True, exist_ok=True)

# ArUco ID 映射（按实际调整）
ARUCO_A_AREA = 1
ARUCO_B_AREA = 2

# ============ 共享结果 ============
_latest_result = {"has_anomaly": False, "anomalies": [], "last_update": 0.0}
_result_lock = threading.Lock()


def get_latest_result():
    """前端轮询读这个，不触发推理"""
    with _result_lock:
        return {
            "has_anomaly": _latest_result["has_anomaly"],
            "anomalies": list(_latest_result["anomalies"]),
            "last_update": _latest_result["last_update"],
            "engine": ENGINE,
        }


# ============ 三路检测调度 ============
def _infer(frame):
    """
    调用三路检测器，合并结果。
    - 检测到 ArUco 时自动触发 preset（B区）
    - 用 ArUco bbox 作为 preset 的红框
    """
    results = []
    annotated = frame.copy()
    has_bbox = False


    # 2. 三路检测（按 ENGINE 组合）
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

    # 4. 统一画框（有 bbox 就画）
    for a in anomalies:
        bbox = a.get("bbox")
        if bbox:
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 3)
            cv2.putText(
                annotated,
                f"{a.get('type', '?')} {a.get('confidence', 0):.2f}",
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
            )
            has_bbox = True

    # 5. 保存截图
    if has:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        img_path = ANOMALY_DIR / f"anomaly_{ts}.jpg"
        img_to_save = annotated if has_bbox else frame
        cv2.imwrite(str(img_path), img_to_save)
        for a in anomalies:
            a["image"] = img_path.name

    return {"has_anomaly": has, "anomalies": anomalies}


# ============ 后台 worker ============
_worker_thread = None
_worker_stop = threading.Event()
_frame_source = None
_on_anomaly = None          # 状态翻转时回调
_prev_has = False


def start_worker(frame_source, interval=2.0, on_anomaly=None):
    """
    frame_source: callable，返回 BGR 帧或 None
    interval: 推理间隔（秒）
    on_anomaly: callable(anomalies)，状态 false→true 时调用
    """
    global _worker_thread, _frame_source, _on_anomaly
    _frame_source = frame_source
    _on_anomaly = on_anomaly
    _worker_stop.clear()
    _worker_thread = threading.Thread(target=_worker_loop, args=(interval,), daemon=True)
    _worker_thread.start()
    print(f"[detection] worker started, engine={ENGINE}, interval={interval}s, "
          f"on_anomaly={'set' if on_anomaly else 'none'}")


def stop_worker():
    _worker_stop.set()
    if _worker_thread:
        _worker_thread.join(timeout=3)
    print("[detection] worker stopped")


def _worker_loop(interval):
    global _prev_has
    while not _worker_stop.is_set():
        # ★ 新增：如果没开启，就不推理，不花钱
        if not _detection_enabled:
            time.sleep(0.5)
            continue
        t0 = time.time()
        try:
            frame = _frame_source() if _frame_source else None
            if frame is not None:
                result = _infer(frame)
                has = result["has_anomaly"]
                anomalies = result["anomalies"]

                with _result_lock:
                    _latest_result["has_anomaly"] = has
                    _latest_result["anomalies"] = anomalies
                    _latest_result["last_update"] = time.time()

                # ★ 状态翻转：false → true 时触发回调
                if has and not _prev_has and _on_anomaly:
                    print(f"[detection] 状态翻转 false→true，触发回调")
                    try:
                        _on_anomaly(anomalies)
                    except Exception as e:
                        print(f"[detection] 回调失败: {e}")
                _prev_has = has
        except Exception as e:
            print(f"[detection] worker error: {e}")
        elapsed = time.time() - t0
        time.sleep(max(0.0, interval - elapsed))
