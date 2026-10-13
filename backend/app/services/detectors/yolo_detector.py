# app/services/detectors/yolo_detector.py
import cv2
from datetime import datetime
from pathlib import Path
import threading

MODEL_PATH = Path(__file__).parent.parent.parent.parent / "models" / "smoke.pt"
CONF_THRESHOLD = 0.1        # ★ 降阈值，先拿值
IMGSZ = 1280                # ★ 调大输入尺寸
ACTIVE_CLASSES = ["smoke"]

_model = None
_model_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from ultralytics import YOLO
                print(f"[yolo] loading model: {MODEL_PATH}")
                _model = YOLO(str(MODEL_PATH))
                print(f"[yolo] loaded, classes: {_model.names}")
    return _model


def detect(frame):
    """
    输入：BGR frame
    输出：{"has_anomaly": bool, "anomalies": [...]}
    """
    model = _get_model()
    results = model.predict(
        frame,
        conf=CONF_THRESHOLD,
        imgsz=IMGSZ,
        verbose=False,
        device="cpu",
    )

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
                "source": "yolo",
            })

    return {
        "has_anomaly": len(anomalies) > 0,
        "anomalies": anomalies,
        "annotated": annotated if anomalies else None,
    }
