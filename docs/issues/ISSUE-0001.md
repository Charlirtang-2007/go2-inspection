# ISSUE-0001：子线程 asyncio.run 导致 WebSocket 跨事件循环死锁，前端卡死

- 状态：resolved
- 记录时间：2026-11-16
- 影响范围：前端所有 WebSocket 消息，表现为前端完全卡死
- 相关提交：`3f2b004`、`9a0d097`

## 现象

巡检运行中，前端突然收不到任何 WebSocket 消息，界面卡死，不再响应。

## 复现步骤

启动巡检流程，让巡检子线程运行到需要向前端广播状态的位置。

## 根因

巡检子线程中使用了 `asyncio.run(manager.broadcast(...))`。`asyncio.run` 会**新建一个独立事件循环**，而 FastAPI 的 WebSocket 对象绑定在**主线程的事件循环**上。跨事件循环使用同一个 WebSocket 对象，报 `attached to a different loop`，直接卡死前端。

## 解决方案

- 不在子线程里新建事件循环。
- 广播时把协程调度回主线程的事件循环（`asyncio.run_coroutine_threadsafe` 或统一在主循环中 await）。

## 验证方式

巡检运行期间，前端持续收到状态消息，不再卡死。

## 预防措施

- 禁止在子线程中调用 `asyncio.run`。
- 跨线程使用 asyncio 对象前，先确认对象绑定的事件循环。

## 相关链接

- `docs/architecture/overview.md`（通信链路）
- `9a0d097 fix: 修复子线程WS死锁与推流阻塞`
