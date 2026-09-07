<!-- // （状态面板）
//StatusPanel.svelte 就是状态面板组件。

//它的作用是：

//📊 显示机器狗的实时状态（在线/离线、电量、当前任务）

//🎯 集中展示关键信息，让操作员一目了然

//🔄 未来通过 WebSocket 或 API 更新数据（目前是静态示例）

//📦 它在项目中的位置
//text
//src/lib/components/StatusPanel.svelte   ← 组件文件
//src/routes/+page.svelte                 ← 使用它的页面
//🔄 数据流向
//text
//后端（FastAPI/WebSocket） → 前端 stores → StatusPanel.svelte → 页面显示
//目前数据是硬编码的，后续我们会：

//搭建 FastAPI 后端，提供 /api/status 接口

//建立 WebSocket 连接，实时推送状态更新

//在 Svelte stores 中管理状态，自动更新组件 -->




<script lang="ts">
  // Svelte 5 的 $props() 语法，替代 export let
  let { status = '待命', battery = 85, task = '无' } = $props();
</script>

<div class="status-panel">
  <h3>🤖 机器狗状态</h3>
  <p>状态：<span class="badge">{status}</span></p>
  <p>电量：{battery}%</p>
  <p>当前任务：{task}</p>
</div>

<style>
  .status-panel {
    background: #1a1a2e;
    color: #fff;
    padding: 1.5rem;
    border-radius: 8px;
    min-width: 200px;
  }
  .badge {
    display: inline-block;
    padding: 2px 12px;
    border-radius: 12px;
    background: #4CAF50;
    font-size: 0.85rem;
  }
</style>