# app/services/detectors/vlm_detector.py
import base64
import json
import os
import cv2
import traceback
from datetime import datetime
from openai import OpenAI

_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY 未配置，请在 .env 中设置")
        _client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    return _client


PROMPT = (
    '图中是否有烟雾？只返回JSON，格式：'
    '{"has_smoke": true/false, "confidence": 0.0-1.0}'
)


def detect(frame):
    """
    输入：BGR frame
    输出：{"has_anomaly": bool, "anomalies": [...]}
    """
    model_name = os.getenv("VLM_MODEL", "qwen-vl-plus")

    _, buf = cv2.imencode(".jpg", frame)
    b64 = base64.b64encode(buf).decode()
    image_data_url = f"data:image/jpeg;base64,{b64}"

    try:
        client = _get_client()
        completion = client.chat.completions.create(
            model=model_name,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                    {"type": "text", "text": PROMPT},
                ],
            }],
            max_tokens=100,
            temperature=0,
        )
    except Exception as e:
        print(f"[vlm] 调用失败: {type(e).__name__}: {e}")
        traceback.print_exc()
        return {"has_anomaly": False, "anomalies": [], "error": str(e)}

    text = completion.choices[0].message.content
    print(f"[vlm] 原始输出: {text[:200]}")

    cleaned = text.strip().replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        print(f"[vlm] JSON 解析失败: {text[:200]}")
        data = {"has_smoke": False, "confidence": 0.0}

    has = bool(data.get("has_smoke", False))
    conf = float(data.get("confidence", 0.0))

    anomalies = []
    if has:
        anomalies.append({
            "type": "smoke",
            "confidence": round(conf, 3),
            "bbox": None,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "vlm",
        })

    return {"has_anomaly": has, "anomalies": anomalies, "annotated": None}