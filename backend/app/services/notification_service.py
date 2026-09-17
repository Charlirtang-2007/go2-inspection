# 后端通知文件


import httpx
import os
import asyncio
import time
from datetime import datetime
from typing import Optional


class NotificationService:
    """异常通知服务：PushPlus（微信） + 企业微信机器人"""

    def __init__(self):
        self.pushplus_token = os.getenv("PUSHPLUS_TOKEN", "").strip()
        self.wecom_webhook = os.getenv("WECOM_WEBHOOK", "").strip()
        # 去重缓存：{异常类型: 上次发送时间戳}
        self._last_notify = {}
        # 冷却时间：同一异常 5 分钟内只发一次
        self.cooldown = 300

    async def notify_anomaly(self, anomaly_type: str, detail: str = ""):
        """并发触发所有已配置的通知渠道"""
        # 去重检查
        now = time.time()
        last = self._last_notify.get(anomaly_type, 0)
        if now - last < self.cooldown:
            remain = int(self.cooldown - (now - last))
            print(f"⏳ {anomaly_type} 冷却中，剩余 {remain} 秒，跳过")
            return {"sent": False, "channels": [], "reason": "cooldown"}

        self._last_notify[anomaly_type] = now

        # 并发发送
        tasks = []
        channels = []
        if self.pushplus_token:
            tasks.append(self._send_pushplus(anomaly_type, detail))
            channels.append("PushPlus")
        if self.wecom_webhook:
            tasks.append(self._send_wecom(anomaly_type, detail))
            channels.append("企业微信")

        if not tasks:
            print("⚠️ 未配置任何通知渠道")
            return {"sent": False, "channels": []}

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计成功渠道
        success_channels = []
        for ch, r in zip(channels, results):
            if r is True:
                success_channels.append(ch)

        return {
            "sent": len(success_channels) > 0,
            "channels": success_channels,
            "timestamp": datetime.now().strftime('%H:%M:%S')
        }

    async def _send_pushplus(self, anomaly_type: str, detail: str) -> bool:
        """推送到微信（PushPlus）"""
        title = f"⚠️ 巡检异常：{anomaly_type}"
        content = f"""
## ⚠️ 巡检异常告警

- **异常类型**：{anomaly_type}
- **发现时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **详情**：{detail or '无'}

请值班人员立即处理。
        """.strip()

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://www.pushplus.plus/send",
                    json={
                        "token": self.pushplus_token,
                        "title": title,
                        "content": content,
                        "template": "markdown"
                    },
                    timeout=10.0
                )
                data = resp.json()
                if data.get("code") == 200:
                    print(f"✅ PushPlus 已发送: {anomaly_type}")
                    return True
                else:
                    print(f"❌ PushPlus 发送失败: {data}")
                    return False
        except Exception as e:
            print(f"❌ PushPlus 异常: {e}")
            return False

    async def _send_wecom(self, anomaly_type: str, detail: str) -> bool:
        """推送到企业微信群"""
        content = f"""## ⚠️ 巡检异常告警

> **异常类型**：<font color="warning">{anomaly_type}</font>
> **发现时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> **详情**：{detail or '无'}

请值班人员立即处理。"""

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.wecom_webhook,
                    json={
                        "msgtype": "markdown",
                        "markdown": {"content": content}
                    },
                    timeout=10.0
                )
                data = resp.json()
                if data.get("errcode") == 0:
                    print(f"✅ 企业微信 已发送: {anomaly_type}")
                    return True
                else:
                    print(f"❌ 企业微信 发送失败: {data}")
                    return False
        except Exception as e:
            print(f"❌ 企业微信 异常: {e}")
            return False


# 单例
notification_service = NotificationService()