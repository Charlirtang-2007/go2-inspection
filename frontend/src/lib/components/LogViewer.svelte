<script lang="ts">
  import { logStore, type LogEntry } from '$lib/stores/log';
  import { onDestroy } from 'svelte';

  let logs: LogEntry[] = $state([]);
  const unsubscribe = logStore.subscribe((value) => {
    logs = value;
  });

  onDestroy(unsubscribe);

  // 展开状态：记录哪些异常日志卡片被展开
  let expanded = $state<Set<string>>(new Set());
  // 图片放大预览（lightbox）
  let lightbox = $state<{ image: string; caption: string } | null>(null);

  function logKey(log: LogEntry): string {
    return `${log.timestamp ?? ''}-${log.time}-${log.message}`;
  }

  function toggleExpand(log: LogEntry) {
    const key = logKey(log);
    expanded = new Set(expanded);
    if (expanded.has(key)) expanded.delete(key);
    else expanded.add(key);
  }

  function isExpanded(log: LogEntry): boolean {
    return expanded.has(logKey(log));
  }

  function openLightbox(image: string, caption: string) {
    lightbox = { image, caption };
  }

  function getLevelIcon(level: string): string {
    switch (level) {
      case 'anomaly': return '🚨';
      case 'error':   return '❌';
      case 'warning': return '⚠️';
      case 'success': return '✅';
      default:        return 'ℹ️';
    }
  }

  function getLevelClass(level: string): string {
    switch (level) {
      case 'anomaly': return 'text-red-400 border-red-400/30 bg-red-400/10';
      case 'error':   return 'text-neon-red border-neon-red/30 bg-neon-red/10';
      case 'warning': return 'text-neon-amber border-neon-amber/30 bg-neon-amber/10';
      case 'success': return 'text-neon-green border-neon-green/30 bg-neon-green/10';
      default:        return 'text-neon-blue border-neon-blue/30 bg-neon-blue/10';
    }
  }

  // 是否为异常日志（按 kind 或 level 判断）
  function isAnomaly(log: LogEntry): boolean {
    return (
      log.kind === 'anomaly' ||
      log.level === 'anomaly' ||
      log.level === 'error' ||
      log.level === 'warning'
    );
  }

  function severityLabel(severity?: string): string {
    switch (severity) {
      case 'high':   return '高';
      case 'medium': return '中';
      case 'low':    return '低';
      default:       return '';
    }
  }

  function severityClass(severity?: string): string {
    switch (severity) {
      case 'high':   return 'text-red-400 border-red-400/30 bg-red-400/10';
      case 'medium': return 'text-amber-300 border-amber-300/30 bg-amber-300/10';
      case 'low':    return 'text-yellow-300 border-yellow-300/30 bg-yellow-300/10';
      default:       return 'text-slate-300 border-white/10 bg-white/5';
    }
  }

  // ESC 关闭图片预览
  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape' && lightbox) lightbox = null;
  }
</script>

<svelte:window onkeydown={onKeydown} />

<div class="log-viewer scrollbar-thin">
  {#if logs.length === 0}
    <div class="flex items-center justify-center h-24 text-slate-500 text-sm">
      ⏳ 等待日志...
    </div>
  {:else}
    <div class="flex flex-col gap-1.5">
      {#each logs as log (logKey(log))}
        {#if isAnomaly(log)}
          <!-- 异常日志：可展开卡片 -->
          <div class="anomaly-card">
            <button
              type="button"
              class="anomaly-header"
              onclick={() => toggleExpand(log)}
            >
              <span class="log-time">{log.time}</span>
              <span class="log-level {getLevelClass(log.level)}">
                {getLevelIcon(log.level)} 异常
              </span>
              {#if log.severity}
                <span class="severity-badge {severityClass(log.severity)}">
                  {severityLabel(log.severity)}危
                </span>
              {/if}
              <span class="anomaly-title">
                {log.type ?? '异常'} · {log.location ?? '未知区域'}
              </span>
              <span class="anomaly-chevron">{isExpanded(log) ? '▾' : '▸'}</span>
            </button>

            {#if isExpanded(log)}
              <div class="anomaly-body">
                <p class="anomaly-message">{log.message}</p>
                {#if log.recordTime}
                  <p class="anomaly-meta">录制时间：{log.recordTime}</p>
                {/if}
                {#if log.image}
                  <div class="anomaly-image-wrap">
                    <button
                      type="button"
                      class="anomaly-thumb-btn"
                      onclick={() => openLightbox(log.image!, `${log.type ?? '异常'} · ${log.location ?? ''}`)}
                      aria-label="放大预览异常图片"
                    >
                      <img src={log.image} alt={log.type ?? '异常图片'} class="anomaly-thumb" />
                    </button>
                    <a
                      href={log.image}
                      download
                      target="_blank"
                      rel="noreferrer"
                      class="anomaly-download"
                    >
                      ⬇️ 下载图片
                    </a>
                  </div>
                {/if}
              </div>
            {/if}
          </div>
        {:else}
          <!-- 普通日志条目 -->
          <div class="log-entry animate-log-in">
            <span class="log-time">{log.time}</span>
            <span class="log-level {getLevelClass(log.level)}">
              {getLevelIcon(log.level)} {log.level}
            </span>
            <span class="log-message">{log.message}</span>
          </div>
        {/if}
      {/each}
    </div>
  {/if}
</div>

<!-- 图片放大预览（lightbox） -->
{#if lightbox}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
    <button
      type="button"
      class="absolute inset-0 w-full h-full bg-black/80 backdrop-blur-sm"
      aria-label="关闭预览"
      onclick={() => lightbox = null}
    ></button>
    <div class="relative max-w-3xl w-full">
      <img src={lightbox.image} alt={lightbox.caption} class="w-full rounded-xl border border-white/10" />
      <div class="flex items-center justify-between mt-3">
        <span class="text-sm text-slate-300">{lightbox.caption}</span>
        <button
          type="button"
          class="px-3 py-1.5 rounded-lg bg-white/10 text-white text-sm hover:bg-white/20"
          onclick={() => lightbox = null}
        >
          关闭
        </button>
      </div>
    </div>
  </div>
{/if}

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

  /* ---- 异常日志卡片 ---- */
  .anomaly-card {
    border: 1px solid rgba(248, 113, 113, 0.25);
    background: rgba(248, 113, 113, 0.05);
    border-radius: 10px;
    overflow: hidden;
  }
  .anomaly-header {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 8px 12px;
    text-align: left;
    cursor: pointer;
    background: transparent;
    border: none;
    color: inherit;
  }
  .anomaly-header:hover {
    background: rgba(248, 113, 113, 0.08);
  }
  .anomaly-title {
    flex: 1;
    color: #fca5a5;
    font-size: 12.5px;
    word-break: break-word;
  }
  .anomaly-chevron {
    color: #94a3b8;
    font-size: 12px;
    flex-shrink: 0;
  }
  .severity-badge {
    flex-shrink: 0;
    font-size: 10.5px;
    padding: 1px 6px;
    border-radius: 999px;
    border: 1px solid;
    line-height: 1.4;
  }
  .anomaly-body {
    padding: 10px 12px 12px;
    border-top: 1px solid rgba(248, 113, 113, 0.15);
  }
  .anomaly-message {
    color: #fca5a5;
    font-size: 12.5px;
    margin-bottom: 6px;
  }
  .anomaly-meta {
    color: #94a3b8;
    font-size: 11px;
    margin-bottom: 8px;
  }
  .anomaly-image-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .anomaly-thumb-btn {
    padding: 0;
    margin: 0;
    border: none;
    background: transparent;
    cursor: zoom-in;
    line-height: 0;
  }
  .anomaly-thumb {
    width: 120px;
    height: 80px;
    object-fit: cover;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.12);
  }
  .anomaly-download {
    color: #67e8f9;
    font-size: 12px;
    text-decoration: none;
  }
  .anomaly-download:hover {
    text-decoration: underline;
  }
</style>