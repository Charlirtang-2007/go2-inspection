<script lang="ts">
  // 后端地址（只填主机，不带路径） 记得改
  const API_BASE = import.meta.env.VITE_API_BASE || 'http://192.168.169.127:8000';
  const videoUrl = `${API_BASE}/api/camera/video?width=640&height=480`;

  let status = $state<'connecting' | 'connected' | 'error'>('connecting');

  function handleLoad()  { status = 'connected'; }
  function handleError() { status = 'error'; }
</script>

<div class="card p-4">
  <div class="flex items-center justify-between mb-3">
    <div class="flex items-center gap-2">
      <h2 class="text-xs font-semibold text-slate-400 uppercase tracking-[0.18em]">
        📷 实时监控
      </h2>
      <span class="chip">
        {status === 'connecting' ? '● 连接中' : status === 'connected' ? '● 已连接' : '● 连接失败'}
      </span>
    </div>

    <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono
                 border border-neon-red/30 bg-neon-red/10 text-neon-red">
      <span class="relative flex w-1.5 h-1.5">
        <span class="absolute inset-0 rounded-full bg-neon-red animate-pulse-ring"></span>
        <span class="relative w-1.5 h-1.5 rounded-full bg-neon-red"></span>
      </span>
      LIVE
    </span>
  </div>

  <div class="relative aspect-video rounded-xl overflow-hidden bg-ink-900
              border border-white/5 shadow-glow-soft">
    <!-- 扫描线 -->
    <div class="pointer-events-none absolute inset-0 z-10">
      <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-neon-cyan/60 to-transparent"></div>
    </div>

    {#if status === 'error'}
      <div class="absolute inset-0 flex flex-col items-center justify-center gap-3 text-slate-400">
        <span class="text-3xl">⚠️</span>
        <span class="text-sm">视频流加载失败</span>
        <button
          type="button"
          onclick={() => location.reload()}
          class="px-4 py-1.5 rounded-lg text-xs font-medium
                 bg-neon-blue/15 border border-neon-blue/30 text-neon-blue
                 hover:bg-neon-blue/25 transition-colors"
        >
          重试
        </button>
      </div>
    {:else}
      <img
        src={videoUrl}
        alt="机器狗摄像头画面"
        onload={handleLoad}
        onerror={handleError}
        class="w-full h-full object-contain"
      />
    {/if}
  </div>
</div>