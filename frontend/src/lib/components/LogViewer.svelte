<script lang="ts">
  import { logStore, type LogEntry } from '$lib/stores/log';
  import { onDestroy } from 'svelte';

  let logs: LogEntry[] = $state([]);
  const unsubscribe = logStore.subscribe((value) => {
    logs = value;
  });

  onDestroy(unsubscribe);

  function getLevelIcon(level: string): string {
    switch (level) {
      case 'error':   return '❌';
      case 'warning': return '⚠️';
      case 'success': return '✅';
      default:        return 'ℹ️';
    }
  }

  function getLevelClass(level: string): string {
    switch (level) {
      case 'error':   return 'text-neon-red border-neon-red/30 bg-neon-red/10';
      case 'warning': return 'text-neon-amber border-neon-amber/30 bg-neon-amber/10';
      case 'success': return 'text-neon-green border-neon-green/30 bg-neon-green/10';
      default:        return 'text-neon-blue border-neon-blue/30 bg-neon-blue/10';
    }
  }
</script>

<div class="log-viewer scrollbar-thin">
  {#if logs.length === 0}
    <div class="flex items-center justify-center h-24 text-slate-500 text-sm">
      ⏳ 等待日志...
    </div>
  {:else}
    <div class="flex flex-col gap-1.5">
      {#each logs as log (log.time + log.message)}
        <div class="log-entry animate-log-in">
          <span class="log-time">{log.time}</span>
          <span class="log-level {getLevelClass(log.level)}">
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
    max-height: 420px;
    overflow-y: auto;
    padding-right: 4px;
    font-size: 13px;
    font-family: 'JetBrains Mono', 'Consolas', 'Monaco', monospace;
  }

  .log-entry {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.04);
    transition: background 0.2s ease, border-color 0.2s ease;
  }
  .log-entry:hover {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(34, 211, 238, 0.2);
  }

  .log-time {
    color: #64748b;
    min-width: 88px;
    flex-shrink: 0;
    font-size: 11.5px;
  }

  .log-level {
    min-width: 84px;
    flex-shrink: 0;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 999px;
    border-width: 1px;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .log-message {
    color: #cbd5e1;
    flex: 1;
    word-break: break-word;
    font-size: 12.5px;
  }
</style>