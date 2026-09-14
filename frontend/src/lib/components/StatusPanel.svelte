<script lang="ts">
  let {
    status = '待命',
    battery = 0,
    task = '无',
    progress = 0,
    step = '',
    running = false
  } = $props();

  const statusTheme = $derived(
    status === '在线'
      ? { chip: 'border-neon-green/30 bg-neon-green/10 text-neon-green', dot: 'bg-neon-green' }
      : status === '巡检中'
      ? { chip: 'border-neon-blue/30 bg-neon-blue/10 text-neon-blue',   dot: 'bg-neon-blue' }
      : { chip: 'border-white/10 bg-white/5 text-slate-400',            dot: 'bg-slate-400' }
  );

  const batteryTheme = $derived(
    battery > 60
      ? 'from-neon-green/80 to-neon-cyan/80'
      : battery > 30
      ? 'from-neon-amber/80 to-neon-amber/60'
      : 'from-neon-red/90 to-neon-red/70'
  );

  const showProgress = $derived(running || progress > 0);
</script>

<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">

  <!-- 状态卡 -->
  <div class="card card-hover p-5 lg:col-span-2">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xs font-semibold text-slate-400 uppercase tracking-[0.18em]">
        📊 机器狗状态
      </h2>
      <span class="chip {statusTheme.chip}">
        <span class="relative flex w-2 h-2">
          <span class="absolute inset-0 rounded-full {statusTheme.dot} animate-pulse-ring"></span>
          <span class="relative w-2 h-2 rounded-full {statusTheme.dot}"></span>
        </span>
        {status}
      </span>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <!-- 电量 -->
      <div class="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs text-slate-400">🔋 电量</span>
          <span class="text-lg font-mono font-semibold text-white">{battery}<span class="text-xs text-slate-500 ml-0.5">%</span></span>
        </div>
        <div class="bar-track">
          <div class="bar-fill bg-gradient-to-r {batteryTheme}" style="width: {battery}%"></div>
        </div>
      </div>

      <!-- 当前任务 -->
      <div class="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs text-slate-400">📋 当前任务</span>
        </div>
        <p class="text-sm text-slate-200 truncate">{task}</p>
      </div>
    </div>

    {#if showProgress}
      <div class="mt-4 pt-4 border-t border-white/5">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs text-slate-400">🛰️ 巡检进度</span>
          <span class="text-sm font-mono font-semibold text-neon-cyan">{progress}%</span>
        </div>
        <div class="bar-track">
          <div
            class="bar-fill bg-gradient-to-r from-neon-cyan/90 to-neon-blue/90"
            style="width: {progress}%"
          ></div>
        </div>
        <p class="text-xs text-slate-500 mt-2 font-mono">{step || '—'}</p>
      </div>
    {/if}
  </div>

  <!-- 右侧指标 -->
  <div class="card card-hover p-5 flex flex-col gap-3">
    <h2 class="text-xs font-semibold text-slate-400 uppercase tracking-[0.18em]">
      ⚡ 实时指标
    </h2>

    <div class="flex items-center justify-between py-2 border-b border-white/5">
      <span class="text-xs text-slate-500">连接</span>
      <span class="text-sm font-mono text-slate-200">WS</span>
    </div>
    <div class="flex items-center justify-between py-2 border-b border-white/5">
      <span class="text-xs text-slate-500">模式</span>
      <span class="text-sm font-mono text-slate-200">手动</span>
    </div>
    <div class="flex items-center justify-between py-2">
      <span class="text-xs text-slate-500">版本</span>
      <span class="text-sm font-mono text-slate-200">v2.0</span>
    </div>

    <div class="mt-auto flex items-center gap-2 text-[11px] text-slate-500 font-mono">
      <span class="w-1.5 h-1.5 rounded-full bg-neon-cyan animate-glow-pulse"></span>
      SYSTEM ONLINE
    </div>
  </div>
</div>