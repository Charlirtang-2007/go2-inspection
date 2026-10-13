# app/services/detectors/vlm_detector.py
import base64
import json
import os
import cv2
from datetime import datetime
from volcenginesdkarkruntime import Ark

# 初始化客户端（模块级，只做一次）
_client = None

def _get_client():
    global _client
    if _client is None:
        _client = Ark(
            base_url='https://ark.cn-beijing.volces.com/api/v3',
            api_key=os.getenv('ARK_API_KEY'),
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
    api_key = os.getenv('ARK_API_KEY')
    if not api_key:
        print("[vlm] ARK_API_KEY 未配置")
        return {"has_anomaly": False, "anomalies": [], "error": "no api key"}

    # 编码
    _, buf = cv2.imencode('.jpg', frame)
    b64 = base64.b64encode(buf).decode()

    try:
        client = _get_client()
        response = client.responses.create(
            model="doubao-seed-2-1-pro-260628",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{b64}",
                        },
                        {
                            "type": "input_text",
                            "text": PROMPT,
                        },
                    ],
                }
            ],
        )
    except Exception as e:
        import traceback
        print(f"[vlm] 调用失败: {type(e).__name__}: {e}")
        traceback.print_exc()
        return {"has_anomaly": False, "anomalies": [], "error": str(e)}

    # 解析输出（responses API 的输出结构不同）
    text = _extract_text(response)
    print(f"[vlm] raw output: {text[:200]}")

    # 解析 JSON
    cleaned = text.strip().replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(cleaned)
    except Exception:
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
    """从 responses API 的返回里提取文本"""
    try:
        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        return content.text
    except Exception as e:
        print(f"[vlm] 解析 response 失败: {e}")
    return ""