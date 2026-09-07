 <!-- +page.svelte 就是对应某个 URL 的页面内容，类似于传统 MVC 中的 Index.cshtml 或 About.cshtml。 -->
<!-- +page.svelte 的角色就是页面级的组件集成器（Component Integrator），它负责把各个独立的 UI 组件组合成一个完整的页面。 -->

<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { wsService } from '$lib/services/websocket';
  import { robotStore } from '$lib/stores/robot';
  import StatusPanel from '$lib/components/StatusPanel.svelte';

  let status = '待命';
  let battery = 85;
  let task = '无';

  // 订阅 store 变化
  const unsubscribe = robotStore.subscribe((value) => {
    status = value.status;
    battery = value.battery;
  });

  function sendCommand(cmd: string) {
    console.log('发送指令:', cmd);
    wsService.send({ type: 'command', data: { cmd } });
  }

  onMount(() => {
    // 连接 WebSocket
    wsService.connect();
  });

  onDestroy(() => {
    wsService.disconnect();
    unsubscribe();
  });
</script>

<div class="container">
  <h1 class="text-3xl font-bold mb-6">🤖 Go2 巡检系统</h1>

  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    <div class="col-span-1">
      <StatusPanel {status} {battery} {task} />
    </div>
    <div class="col-span-2">
      <p class="text-gray-600">控制面板内容...</p>
    </div>
  </div>

  <div class="mt-6 space-x-2">
    <button on:click={() => sendCommand('forward')} class="btn">⬆ 前进</button>
    <button on:click={() => sendCommand('stop')} class="btn">⏹ 停止</button>
    <button on:click={() => sendCommand('backward')} class="btn">⬇ 后退</button>
  </div>
</div>

<style>
  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
  }
  .btn {
    padding: 8px 16px;
    border: 1px solid #ccc;
    border-radius: 4px;
    cursor: pointer;
    background: #f0f0f0;
  }
  .btn:hover {
    background: #e0e0e0;
  }
</style>