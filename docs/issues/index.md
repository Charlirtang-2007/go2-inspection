# 问题索引

> 最后更新：2026-11-16
> 负责人：Nain_an
> 用途：现象 → 状态 → 链接，快速定位历史问题
> 对应技术源：各 ISSUE 文件 + `git log`

## 索引表

| 编号 | 现象 | 状态 | 链接 |
| :--- | :--- | :--- | :--- |
| ISSUE-0001 | 子线程 asyncio.run 导致 WebSocket 跨事件循环死锁，前端卡死 | resolved | [ISSUE-0001](ISSUE-0001.md) |
| ISSUE-0002 | 坐下后起立导致侧翻 | resolved | [ISSUE-0002](ISSUE-0002.md) |
| ISSUE-0003 | ArUco 视觉定位不稳定，改固定时长盲走 | resolved（可能回归） | [ISSUE-0003](ISSUE-0003.md) |
| ISSUE-0004 | 盲走转弯角度不合适，复检转弯未完成 | open | [ISSUE-0004](ISSUE-0004.md) |
| ISSUE-0005 | 滴漏识别未实现，目前只有烟雾/异常识别 | open | [ISSUE-0005](ISSUE-0005.md) |
| ISSUE-0006 | K2B 视频流解码阻塞导致指令下发失败；需注意散热 | resolved / open | [ISSUE-0006](ISSUE-0006.md) |

## 状态说明

| 状态 | 含义 |
| :--- | :--- |
| open | 未解决 |
| investigating | 排查中 |
| resolved | 已解决 |
| wontfix | 不修，记录在案 |

## 新增问题模板

新建 `ISSUE-XXXX.md`，按以下字段填写：

- 状态
- 记录时间
- 影响范围
- 现象（可观察到的行为，不是猜测）
- 复现步骤
- 根因
- 解决方案
- 验证方式
- 预防措施
- 相关链接
