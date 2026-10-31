# backend/app/services/run_inspection.py
import time
import subprocess
import threading
import sys
import asyncio
from app.services.camera_service import camera_service
from app.services.detection_service import detect_aruco_markers, enable_detection, disable_detection, get_latest_result
from app.services.detectors import preset_detector
# ★ 引入 WebSocket 管理器（路径需根据你实际的 websocket_manager 位置调整）
from app.utils.websocket_manager import manager
from app.services.notification_service import notification_service 

URL = "http://192.168.1.100:8000/api/robot/command"
FORCE_STOP = False

# 主线程事件循环句柄，由 main.py 注入（inspection_module.MAIN_LOOP = ...）
MAIN_LOOP = None


def push_ws(event_type: str, msg: str):
    # 后台子线程中发送 WebSocket 消息。
    # 铁律：严禁 asyncio.run()。子线程新建 loop 会与主 loop 上的 WS 对象冲突，
    #       表现为前端画面卡死、日志不滚、弹窗丢失，异常还被吞掉。
    # 必须 run_coroutine_threadsafe 把协程投递回主事件循环。
    # data 直接传字符串，与前端 websocket.ts 的 msg.data 用法严格对齐。
    try:
        if MAIN_LOOP is None or MAIN_LOOP.is_closed():
            print(f"WS 推送跳过（主循环未就绪）: {event_type}")
            return
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"type": event_type, "data": msg}),
            MAIN_LOOP,
        )
    except Exception as e:
        print(f"WS 推送失败: {e}")


def _notify_async(anomaly_type: str, detail: str):
    # 子线程里触发异步通知（PushPlus/企业微信）。
    # 统一用 MAIN_LOOP + run_coroutine_threadsafe，严禁 asyncio.run。
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
    try:
        subprocess.run([
            "curl", "-s", "-X", "POST", URL,
            "-H", "Content-Type: application/json",
            "-d", f'{{"cmd": "{cmd}"}}'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)
    except subprocess.TimeoutExpired:
        pass

def send_once(cmd, wait_time=2.0):
    if FORCE_STOP: return
    send("stop")
    time.sleep(0.3)
    send(cmd, timeout=5.0)
    time.sleep(wait_time)

def do_action(cmd, duration):
    global FORCE_STOP
    if FORCE_STOP: return
    send("stop")
    time.sleep(0.4) 
    print(f"🤖 执行: {cmd.upper()} 持续 {duration}s")
    start = time.time()
    while time.time() - start < duration:
        if FORCE_STOP: break
        send(cmd)
        time.sleep(0.2)
    send("stop")
    time.sleep(0.8)

def find_target(marker_id):
    frame = camera_service.read_frame()
    if frame is None: return None
    markers = detect_aruco_markers(frame)
    return next((m for m in markers if m["id"] == marker_id), None)

def walk_to_marker(marker_id, timeout=15.0):
    global FORCE_STOP
    print(f"🎯 尝试寻找并逼近 ID: {marker_id}")
    start_time = time.time()

    while time.time() - start_time < timeout:
        if FORCE_STOP: return False

        target = find_target(marker_id)
        if target:
            if target["size"] >= 500:
                send("stop")
                print(f"✅ 成功到达 ID: {marker_id} (尺寸: {target['size']:.0f})")
                return True
            else:
                print("🚶 看到目标，大步前进...")
                do_action("forward", 1.0)
        else:
            send("stop")
            time.sleep(0.3)

    if not FORCE_STOP:
        print(f"⚠️ 超时未抵达 ID:{marker_id}，强行盲走 4.0 秒兜底...")
        do_action("forward", 4.0)
    return False

def run_detection(timeout=10):
    global FORCE_STOP
    print(f"👀 开始 10 秒异常检测...")
    enable_detection()
    start = time.time()
    while time.time() - start < timeout:
        if FORCE_STOP: break
        if get_latest_result().get("has_anomaly"):
            print("🚨 模型触发异常报警！")
            # ★ 推送报警和 TTS
            push_ws("inspection_alert", "AI 模型检测到烟雾异常！")
            push_ws("tts_play", "警告，检测到异常")
            _notify_async("烟雾异常", "A区域异常点检测到烟雾异常")
            break
        time.sleep(0.5)
    else:
        if not FORCE_STOP:
            print("⚠️ 10 秒超时，触发 Preset 兜底！")
            preset_detector.trigger(area="异常区", reason="兜底触发")
            # ★ 推送兜底报警
            push_ws("inspection_alert", "A区域异常点检测到烟雾异常！")
            push_ws("tts_play", "警告，A区域异常点检测到烟雾异常")
            _notify_async("烟雾异常", "A区域异常点检测到烟雾异常（兜底）")
    disable_detection()

def listen_for_stop():
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
    walk_to_marker(0)
    if FORCE_STOP: return
    print("🔄 执行左转...")
    do_action("left", 2.0)

    # ================= 阶段 2 =================
    print("\n[2] 前往 A 区 (ID 1)...")
    walk_to_marker(1)
    if FORCE_STOP: return
    # ★ 推送前端日志和 TTS
    push_ws("inspection_log", "已到达 A 区，正在调整机位...")
    push_ws("tts_play", "已到达 A 区")
    
    print("前往 A 区异常点 a...")
    do_action("right", 2.0)
    do_action("forward", 4.0) 
    send_once("sit", wait_time=2.0)
    print("📢 等待 3 秒...")
    time.sleep(3)
    send_once("standup", wait_time=2.0)
    time.sleep(1.0)

    # ================= 阶段 3 =================
    print("\n[3] 前往 B 区...")
    do_action("right", 2.0)
    walk_to_marker(2)
    if FORCE_STOP: return
    # ★ 推送前端日志和 TTS
    push_ws("inspection_log", "已到达 B 区")
    push_ws("tts_play", "已到达 B 区")
    
    print("前往 B 区异常点 b...")
    do_action("left", 2.0)
    do_action("forward", 4.0) 
    send_once("sit", wait_time=2.0)
    print("📢 等待 10 秒...")
    time.sleep(10)
    send_once("standup", wait_time=2.0)
    time.sleep(1.0)
    
    # ================= 阶段 4 =================
    print("\n[4] 前往出口...")
    do_action("left", 2.0) 
    walk_to_marker(3)
    if FORCE_STOP: return

    print("原地转向 180 度...")
    do_action("left", 2.6) 
    do_action("forward", 4.0) 
    
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
    do_action("forward", 4.0)       

    # =====================================================================
    # 阶段 5：再次确认 B区与 A区（复检过程）
    # =====================================================================
    print("\n[5] 再次识别 B 区 (ID 2)...")
    walk_to_marker(2)
    print("📢 [前端推送] 看到 B 码，离开 b 区域中！")
    if FORCE_STOP: return

    print("右转前往异常点 a...")
    do_action("right", 2.0)

    # ★ 核心修正：复检时，直接进入 A 区通道，先走到异常点检查
    print("前往 A 异常点...")
    do_action("forward", 4.0)  
    send_once("sit", wait_time=2.0) # 在异常点坐下
    print("📢 三端触发，报警异常！等 10 秒...")
    run_detection(timeout=10)  # 触发 10 秒报警检测
    
    send_once("standup", wait_time=2.0) # 站起
    time.sleep(1.0) # 防止站起后吞指令

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
    do_action("forward", 4.0)
    
    # 【3. A码】出通道后，识别 A 区码 (ID 1)，确认离开
    print("🎯 寻找 A 区码 (ID 1)...")
    walk_to_marker(1)
    if FORCE_STOP: return
    
    # 【4. 转身回主路】
    print("🔄 转身，面朝入口方向...")
    do_action("left", 2.0) 
    
    # 【5. 前进】沿着主路直奔入口/终点
    print("🚶 前进，前往入口...")
    do_action("forward", 4.0) 
    
    # 【6. 入口，停下】
    print("🛑 到达入口，停下...")
    send_once("sit", wait_time=2.0)
    
    print("📢 [前端推送] 巡检全部结束！")
    
    # 关闭摄像头流，释放资源。
    camera_service.stop()
    
    send_once("sit", wait_time=2.0)
    print("📢 [前端推送] 巡检全部结束！")
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
