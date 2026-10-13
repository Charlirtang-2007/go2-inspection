# app/services/detectors/vlm_detector.py
import base64
import json
import os
import cv2
import requests
from datetime import datetime

VLM_API_KEY = os.getenv("VLM_API_KEY", "")
VLM_URL = os.getenv("VLM_URL", "")
VLM_MODEL = os.getenv("VLM_MODEL", "doubao-seed-1-6-vision")

PROMPT = (
    '图中是否有烟雾？只返回JSON，格式：'
    '{"has_smoke": true/false, "confidence": 0.0-1.0, "location": "画面中央/左上/右下/无"}'
)


def detect(frame):
    """
    输入：BGR frame
    输出：{"has_anomaly": bool, "anomalies": [...]}
    """
    if not VLM_API_KEY or not VLM_URL:
        return {"has_anomaly": False, "anomalies": [], "error": "VLM not configured"}

    _, buf = cv2.imencode(".jpg", frame)
    b64 = base64.b64encode(buf).decode()

    try:
        resp = requests.post(
            VLM_URL,
            headers={
                "Authorization": f"Bearer {VLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": VLM_MODEL,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                }],
                "max_tokens": 150,
                "temperature": 0,
            },
            timeout=30,
        )
        text = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[vlm] request failed: {e}")
        return {"has_anomaly": False, "anomalies": [], "error": str(e)}

    # 解析 JSON（容忍 ```json ``` 包裹）
    cleaned = text.strip().replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(cleaned)
    except Exception:
        print(f"[vlm] parse failed, raw: {text[:200]}")
        data = {"has_smoke": False, "confidence": 0.0, "location": "无"}

    has = bool(data.get("has_smoke", False))
    conf = float(data.get("confidence", 0.0))

    anomalies = []
    if has:
        anomalies.append({
            "type": "smoke",
            "confidence": round(conf, 3),
            "bbox": None,                          # VLM 不返回精确 bbox
            "location": data.get("location", "无"),  # 文字描述的位置
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "vlm",
        })

    return {"has_anomaly": has, "anomalies": anomalies, "annotated": None}
