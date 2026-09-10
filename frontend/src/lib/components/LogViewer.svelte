<script lang="ts">
  import { logStore, type LogEntry } from '$lib/stores/log';
  import { onDestroy } from 'svelte';

  // 订阅日志 Store
  let logs: LogEntry[] = $state([]);
  const unsubscribe = logStore.subscribe((value) => {
    logs = value;
  });

  onDestroy(unsubscribe);

  function getLevelIcon(level: string): string {
    switch (level) {
      case 'error': return '❌';
      case 'warning': return '⚠️';
      case 'success': return '✅';
      default: return 'ℹ️';
    }
  }

  function getLevelColor(level: string): string {
    switch (level) {
      case 'error': return 'text-red-500';
      case 'warning': return 'text-yellow-500';
      case 'success': return 'text-green-500';
      default: return 'text-blue-500';
    }
  }
</script>

<div class="log-viewer">
  {#if logs.length === 0}
    <div class="empty-state">
      <span class="text-gray-400 text-sm">⏳ 等待日志...</span>
    </div>
  {:else}
    <div class="log-list">
      {#each logs as log (log.time + log.message)}
        <div class="log-entry">
          <span class="log-time">{log.time}</span>
          <span class="log-level {getLevelColor(log.level)}">
            {getLevelIcon(log.level)} {log.level}
          </span>
          <span class="log-message">{log.message}</span>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .log-viewer {
    height: 100%;
    min-height: 80px;
    max-height: 120px;
    overflow-y: auto;
    background: #f9fafb;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    font-family: 'Consolas', 'Monaco', monospace;
  }
  .log-viewer::-webkit-scrollbar {
    width: 4px;
  }
  .log-viewer::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 2px;
  }
  .log-viewer::-webkit-scrollbar-thumb {
    background: #d1d5db;
    border-radius: 2px;
  }
  .log-entry {
    display: flex;
    gap: 12px;
    padding: 2px 0;
    border-bottom: 1px solid #f3f4f6;
    line-height: 1.6;
  }
  .log-entry:last-child {
    border-bottom: none;
  }
  .log-time {
    color: #9ca3af;
    min-width: 80px;
    flex-shrink: 0;
    font-size: 12px;
  }
  .log-level {
    min-width: 80px;
    flex-shrink: 0;
    font-size: 12px;
  }
  .log-message {
    color: #374151;
    flex: 1;
    word-break: break-word;
  }
  .empty-state {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 60px;
  }
</style>
