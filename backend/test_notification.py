"""
通知服务测试脚本
用途：独立验证 PushPlus 和企业微信通知是否正常工作
不依赖摄像头和异常检测
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# 加载 .env
load_dotenv()

# 检查环境变量
print("=" * 50)
print("📋 环境变量检查")
print("=" * 50)
pushplus = os.getenv("PUSHPLUS_TOKEN", "").strip()
wecom = os.getenv("WECOM_WEBHOOK", "").strip()

print(f"PUSHPLUS_TOKEN: {'✅ 已配置 (' + pushplus[:8] + '...)' if pushplus else '❌ 未配置'}")
print(f"WECOM_WEBHOOK: {'✅ 已配置 (' + wecom[:40] + '...)' if wecom else '❌ 未配置'}")

if not pushplus and not wecom:
    print("\n⚠️ 两个凭证都没配置，请先编辑 .env 文件")
    sys.exit(1)

# 导入通知服务
from app.services.notification_service import notification_service

async def run_test():
    print()
    print("=" * 50)
    print("🚀 开始发送测试通知")
    print("=" * 50)

    # 测试1：单次通知
    print("\n【测试1】发送一条普通告警...")
    result = await notification_service.notify_anomaly(
        anomaly_type="🔥 火焰",
        detail="测试消息 - 摄像头检测到火焰特征"
    )
    print(f"结果: {result}")

    # 测试2：等冷却时间（默认 5 分钟，这里只等 2 秒演示）
    print("\n【测试2】立即再发一条相同异常（触发冷却）...")
    result2 = await notification_service.notify_anomaly(
        anomaly_type="🔥 火焰",
        detail="测试消息 - 应该被冷却拦截"
    )
    print(f"结果: {result2}")

    # 测试3：不同类型异常（不受冷却限制）
    print("\n【测试3】发送不同类型异常（烟雾）...")
    result3 = await notification_service.notify_anomaly(
        anomaly_type="💨 烟雾",
        detail="测试消息 - 检测到烟雾"
    )
    print(f"结果: {result3}")

    print()
    print("=" * 50)
    print("✅ 测试完成")
    print("=" * 50)
    print("请检查：")
    print("  1. 微信是否收到 PushPlus 通知")
    print("  2. 企业微信群是否收到机器人消息")
    print("  3. 测试2 应该被冷却机制拦截（返回 reason: cooldown）")

if __name__ == "__main__":
    asyncio.run(run_test())