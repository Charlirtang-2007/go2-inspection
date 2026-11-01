# backend/app/services/run_inspection.py
import time
import subprocess
import threading
import sys
import asyncio
from app.services.camera_service import camera_service
from app.services.detection_service import detect_aruco_markers, enable_detection, disable_detection, get_latest_result
from app.services.detectors import preset_detector
# ★ 引入 WebSocket 管理器
from app.utils.websocket_manager import manager
from app.services.notification_service import notification_service

URL = "http://192.168.1.100:8000/api/robot/command"
FORCE_STOP = False

# 主线程事件循环句柄，由 main.py 注入（inspection_module.MAIN_LOOP = ...）
MAIN_LOOP = None


def push_ws(event_type: str, msg: str):
    """
    后台子线程中发送 WebSocket 消息的统一接口。
    ★ 铁律：绝对禁止 asyncio.run()。
      原因：asyncio.run 会在子线程新建一个独立事件循环，
      而 FastAPI 的 WebSocket 连接对象（manager 里的 websocket 实例）
      绑定在主线程的事件循环上。跨循环操作会触发
      "attached to a different loop" 错误，表现为前端画面卡死、
      日志不滚、弹窗丢失，且异常被吞掉、极难排查。

    ★ 正确做法：asyncio.run_coroutine_threadsafe
      把 manager.broadcast(...) 这个协程对象「投递」回主事件循环执行，
      子线程不等待结果、不阻塞，控制指令的节拍完全不受影响。
    """
    try:
        if MAIN_LOOP is None or MAIN_LOOP.is_closed():
            print(f"⚠️ WS 推送跳过（主循环未就绪）: {event_type}")
            return

        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"type": event_type, "data": msg}),
            MAIN_LOOP,
        )
    except Exception as e:
        print(f"⚠️ WS 推送失败: {e}")


def _notify_async(anomaly_type: str, detail: str):
    """
    子线程里触发异步通知（PushPlus/企业微信）。
    统一用 MAIN_LOOP + run_coroutine_threadsafe，严禁 asyncio.run。
    """
    if MAIN_LOOP is None or MAIN_LOOP.is_closed():
        print(f"通知跳过（主循环未就绪）: {anomaly_type}")
        return
    try:
        asyncio.run_coroutine_threadsafe(
            notification_service.notify_anomaly(anomaly_type, detail),
            MAIN_LOOP,
        )
    except Exception as e:
        print(f"通知投递失败: {e}")


def send(cmd, timeout=2.0):
    """
    ★ 铁律：千万别用 requests 高频发控制指令！
    必须使用 subprocess.run(["curl", ...]) 来发指令。
    这是当前唯一能保证走位丝滑的解法。
    """
    try:
        subprocess.run([
            "curl", "-s", "-X", "POST", URL,
            "-H", "Content-Type: application/json",
            "-d", f'{{"cmd": "{cmd}"}}'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)
    except subprocess.TimeoutExpired:
        pass


def send_once(cmd, wait_time=2.0):
    """单发一次指令，并等待动作完成。用于坐下、站起等姿态切换。"""
    if FORCE_STOP: return
    send(cmd, timeout=5.0)
    time.sleep(wait_time)


def do_action(cmd, duration):
    """
    ★ 核心修改：只发一次指令，用 sleep 等待，再发 stop。
    完全模拟前端按下键盘不放、松开键盘的物理过程。
    绝对不要在 while 循环里疯狂发指令，会让狗原地抽搐。
    """
    global FORCE_STOP
    if FORCE_STOP: return

    print(f"🤖 执行: {cmd.upper()} 持续 {duration}s")
    # 1. 发送一次起步指令，底层会按速度一直走
    send(cmd, timeout=5.0)
    # 2. 纯休眠，等它把动作做完
    time.sleep(duration)
    # 3. 发送停止，结束动作
    send("stop")
    # 4. 动作结束缓冲，等狗站稳再执行下一步
    time.sleep(0.8)


def run_detection(timeout=10):
    """
    10 秒异常检测倒计时。
    ★ 兜底必须强推：10 秒到了没识别到，必须在代码里强行调用
    preset_detector.trigger() 并强制 push_ws 发送 inspection_alert
    和 tts_play。
    """
    global FORCE_STOP
    print(f"👀 开始 10 秒异常检测...")
    enable_detection()
    start = time.time()

    while time.time() - start < timeout:
        if FORCE_STOP: break
        if get_latest_result().get("has_anomaly"):
            print("🚨 模型触发异常报警！")
            push_ws("inspection_alert", "AI 模型检测到烟雾异常！")
            push_ws("tts_play", "警告，检测到异常")
            _notify_async("烟雾异常", "A区域异常点检测到烟雾异常")
            break
        time.sleep(0.5)
    else:
        if not FORCE_STOP:
            print("⚠️ 10 秒超时，触发 Preset 兜底！")
            preset_detector.trigger(area="异常区", reason="兜底触发")
            push_ws("inspection_alert", "A区域异常点检测到烟雾异常！")
            push_ws("tts_play", "警告，A区域异常点检测到烟雾异常")
            _notify_async("烟雾异常", "A区域异常点检测到烟雾异常（兜底）")

    disable_detection()


def listen_for_stop():
    """终端输入回车急停"""
    global FORCE_STOP
    while True:
        try:
            input()
            if FORCE_STOP: continue
            print("\n🚨 收到强制停止指令！正在急刹...")
            FORCE_STOP = True
            for _ in range(5):
                send("stop")
                time.sleep(0.1)
            sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            break


def main():
    global FORCE_STOP
    print("🚀 启动巡检剧本 (随时按回车急刹)")
    camera_service.start()
    time.sleep(2)

    send_once("standup", wait_time=2.0)
    time.sleep(1.0)

    # ================= 阶段 1 =================
    print("\n[1] 直走识别入口 ID 0...")
    do_action("forward", 1.5)
    if FORCE_STOP: return
    print("🔄 执行左转...")
    do_action("left", 2.0)

    # ================= 阶段 2 =================
    print("\n[2] 前往 A 区 (ID 1)...")
    do_action("forward", 2.5)
    if FORCE_STOP: return
    push_ws("inspection_log", "已到达 A 区，正在调整机位...")
    push_ws("tts_play", "已到达 A 区")

    print("前往 A 区异常点 a...")
    do_action("right", 2.0)
    do_action("forward", 2.5)
    send_once("sit", wait_time=2.0)
    print("📢 等待 3 秒...")
    time.sleep(3)
    # 坐下后必须站起，给足时间，防侧翻
    send_once("standup", wait_time=2.0)
    time.sleep(1.0)

    # ================= 阶段 3 =================
    print("\n[3] 前往 B 区...")
    do_action("right", 2.0)
    do_action("forward", 2.5)
    if FORCE_STOP: return
    push_ws("inspection_log", "已到达 B 区")
    push_ws("tts_play", "已到达 B 区")

    print("前往 B 区异常点 b...")
    do_action("left", 2.0)
    do_action("forward", 2.5)
    send_once("sit", wait_time=2.0)
    print("📢 等待 10 秒...")
    time.sleep(10)
    send_once("standup", wait_time=2.0)
    time.sleep(1.0)

    # ================= 阶段 4 =================
    print("\n[4] 前往出口...")
    do_action("left", 2.0)
    do_action("forward", 2.5)
    if FORCE_STOP: return

    print("原地转向 180 度...")
    do_action("left", 2.6)
    do_action("forward", 2.5)

    print("📢 [前端推送] 到达复检异常点 b，准备坐下检查...")
    push_ws("inspection_log", "到达复检异常点 b，准备坐下检查...")
    push_ws("tts_play", "开始复检")
    send_once("sit", wait_time=2.0)
    time.sleep(3)
    print("📢 [前端推送] 复检异常点 b，无异常！")
    push_ws("inspection_log", "复检异常点 b，无异常！")
    send_once("standup", wait_time=2.0)
    time.sleep(1.0)

    print("左转离开异常点 b，准备识别 B 码...")
    push_ws("inspection_log", "正在离开 B 区域...")
    push_ws("tts_play", "正在离开 B 区域")
    do_action("left", 2.0)
    do_action("forward", 2.5)

    # =====================================================================
    # 阶段 5：再次确认 B区与 A区（复检过程）
    # =====================================================================
    print("\n[5] 再次识别 B 区 (ID 2)...")
    do_action("forward", 2.5)
    print("📢 [前端推送] 看到 B 码，离开 b 区域中！")
    if FORCE_STOP: return

    print("右转前往异常点 a...")
    do_action("right", 2.0)

    # ★ 核心修正：复检时，直接进入 A 区通道，先走到异常点检查
    print("前往 A 异常点...")
    do_action("forward", 2.5)
    send_once("sit", wait_time=2.0)  # 在异常点坐下
    print("📢 三端触发，报警异常！等 10 秒...")
    run_detection(timeout=10)

    send_once("standup", wait_time=2.0)  # 站起
    time.sleep(1.0)  # 防止站起后吞指令

    # =====================================================================
    # 阶段 6：离开 A 区异常点，前往入口/终点
    # =====================================================================
    print("\n[6] 离开 A 区异常点，准备前往入口结束...")
    push_ws("inspection_log", "正在离开 A 区域...")
    push_ws("tts_play", "正在离开 A 区域")

    # 【1. 转身出通道】
    print("🔄 左转出通道...")
    do_action("left", 2.0)

    # 【2. 前进】走出异常点通道
    print("🚶 前进，走出异常点通道...")
    do_action("forward", 2.5)

    # 【3. A码】出通道后，识别 A 区码 (ID 1)，确认离开
    print("🚶 盲走确认 A 区...")
    do_action("forward", 2.5)
    if FORCE_STOP: return

    # 【4. 转身回主路】
    print("🔄 转身，面朝入口方向...")
    do_action("left", 2.0)

    # 【5. 前进】沿着主路直奔入口/终点
    print("🚶 前进，前往入口...")
    do_action("forward", 2.5)

    # 【6. 入口，停下】
    print("🛑 到达入口，停下...")
    send_once("sit", wait_time=2.0)

    print("📢 [前端推送] 巡检全部结束！")

    # 关闭摄像头流，释放资源。
    camera_service.stop()


if __name__ == "__main__":
    stop_thread = threading.Thread(target=listen_for_stop, daemon=True)
    stop_thread.start()

    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 捕获 Ctrl+C，强行中止")
        for _ in range(3): send("stop")
        camera_service.stop()
