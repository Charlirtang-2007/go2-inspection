# app/services/detectors/vlm_detector.py
import base64
import json
import os
import cv2
import traceback
from datetime import datetime
from arkruntime import Ark

# 模块级单例客户端
_client = None
_client_lock = None

def _get_client():
    global _client, _client_lock
    if _client_lock is None:
        import threading
        _client_lock = threading.Lock()
    
    if _client is None:
        with _client_lock:
            if _client is None:
                api_key = os.getenv("ARK_API_KEY", "").strip()
                if not api_key:
                    raise ValueError("ARK_API_KEY 未配置，请在 .env 中设置")
                _client = Ark(
                    base_url="https://ark.cn-beijing.volces.com/api/v3",
                    api_key=api_key,
                )
    return _client


PROMPT = (
    '图中是否有烟雾？只返回JSON，格式：'
    '{"has_smoke": true/false, "confidence": 0.0-1.0, "location": "画面中央/左上/右下/无"}'
)


def detect(frame):
    """
    输入：BGR frame
    输出：{"has_anomaly": bool, "anomalies": [...]}
    """
    # 从环境变量读模型名
    model_name = os.getenv("VLM_MODEL", "doubao-seed-2-1-pro-260628")
    timeout = float(os.getenv("VLM_TIMEOUT", "30"))

    # 编码帧为 base64
    _, buf = cv2.imencode(".jpg", frame)
    b64 = base64.b64encode(buf).decode()
    image_data_url = f"data:image/jpeg;base64,{b64}"

    try:
        client = _get_client()
        response = client.responses.create(
            model=model_name,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_image", "image_url": image_data_url},
                        {"type": "input_text", "text": PROMPT},
                    ],
                }
            ],
            timeout=timeout,
        )
    except Exception as e:
        print(f"[vlm] 调用失败: {type(e).__name__}: {e}")
        traceback.print_exc()
        return {"has_anomaly": False, "anomalies": [], "error": str(e)}

    # 提取文本
    text = _extract_text(response)
    if not text:
        print(f"[vlm] 未提取到文本输出")
        return {"has_anomaly": False, "anomalies": [], "error": "empty output"}

    print(f"[vlm] 原始输出: {text[:200]}")

    # 解析 JSON
    cleaned = text.strip().replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        print(f"[vlm] JSON 解析失败: {text[:200]}")
        data = {"has_smoke": False, "confidence": 0.0, "location": "无"}

    has = bool(data.get("has_smoke", False))
    conf = float(data.get("confidence", 0.0))

    anomalies = []
    if has:
        anomalies.append({
            "type": "smoke",
            "confidence": round(conf, 3),
            "bbox": None,
            "location": data.get("location", "无"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "vlm",
        })

    return {"has_anomaly": has, "anomalies": anomalies, "annotated": None}


def _extract_text(response):
    """从 responses API 返回里提取文本"""
    try:
        for item in response.output or []:
            if getattr(item, "type", None) == "message":
                for content in getattr(item, "content", []):
                    if getattr(content, "type", None) == "output_text":
                        return getattr(content, "text", "")
    except Exception as e:
        print(f"[vlm] 解析 response 失败: {e}")
    return ""