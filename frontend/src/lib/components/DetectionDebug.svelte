<!-- frontend/src/lib/components/DetectionDebug.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { wsService } from '$lib/services/websocket';

  let pollCount = 0;
  let lastPollTime = '';
  let lastResponse = '未轮询';
  let lastError = '';
  let consecutiveErrors = 0;

  onMount(() => {
    const timer = setInterval(async () => {
      const base = wsService.getBackendBase();
      pollCount++;
      lastPollTime = new Date().toLocaleTimeString();

      if (!base) {
        lastResponse = '⏸ backendBase 为空';
        return;
      }

      try {
        const res = await fetch(`${base}/api/detection/anomaly`);
        const data = await res.json();
        lastResponse = `has=${data.has_anomaly}, n=${data.anomalies?.length || 0}`;
        lastError = '';
        consecutiveErrors = 0;
      } catch (e: any) {
        lastError = e.message || '请求失败';
        consecutiveErrors++;
      }
    }, 3000);

    return () => clearInterval(timer);
  });
</script>

<div class="debug-panel">
  <div>轮询次数: {pollCount}</div>
  <div>上次: {lastPollTime || '—'}</div>
  <div>响应: {lastResponse}</div>
  {#if lastError}
    <div class="error">错误: {lastError}（连续 {consecutiveErrors} 次）</div>
  {/if}
</div>

<style>
  .debug-panel {
    position: fixed;
    bottom: 8px;
    right: 8px;
    background: rgba(0, 0, 0, 0.75);
    color: #0f0;
    font-family: monospace;
    font-size: 12px;
    padding: 8px 12px;
    border-radius: 4px;
    z-index: 9999;
    pointer-events: none;
    line-height: 1.4;
  }
  .error { color: #f66; }
</style>