<script lang="ts">
  import { alertStore } from '$lib/stores/alert';

  const isDev = import.meta.env.DEV;

  let countdown = $state(0);
  let countdownTimer: number | null = null;

  function trigger(level: 'critical' | 'warning' | 'info', type: string) {
    alertStore.push({
      level,
      type,
      area: '巡检区域 C',
      detail: `【测试】系统检测到 ${type}，请立即处理`,
      timestamp: new Date().toLocaleTimeString()
    });
  }

  /** 5 秒后触发，给你时间进全屏 */
  function triggerDelayed(level: 'critical' | 'warning' | 'info', type: string) {
    if (countdownTimer !== null) return;
    countdown = 5;
    countdownTimer = window.setInterval(() => {
      countdown -= 1;
      if (countdown <= 0) {
        if (countdownTimer !== null) {
          clearInterval(countdownTimer);
          countdownTimer = null;
        }
        trigger(level, type);
      }
    }, 1000);
  }
</script>

{#if isDev}
  <div class="fixed bottom-4 right-4 z-[9998] flex flex-col gap-2 p-3
              rounded-xl bg-black/80 border border-white/10 backdrop-blur max-w-[220px]">
    <div class="text-[10px] text-slate-400 font-mono uppercase tracking-wider">
      🔧 开发测试面板
    </div>

    <button
      type="button"
      onclick={() => trigger('critical', '🔥 火焰')}
      class="px-3 py-1.5 rounded-lg text-xs font-medium
             bg-red-500/20 text-red-400 border border-red-500/40
             hover:bg-red-500/30 transition-all"
    >
      立即触发火焰
    </button>

    <button
      type="button"
      onclick={() => triggerDelayed('critical', '🔥 火焰')}
      disabled={countdown > 0}
      class="px-3 py-1.5 rounded-lg text-xs font-medium
             bg-orange-500/20 text-orange-400 border border-orange-500/40
             hover:bg-orange-500/30 transition-all
             disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {countdown > 0 ? `⏱ ${countdown} 秒后触发...` : '5秒后触发火焰'}
    </button>

    <button
      type="button"
      onclick={() => trigger('warning', '💨 烟雾')}
      class="px-3 py-1.5 rounded-lg text-xs font-medium
             bg-yellow-500/20 text-yellow-400 border border-yellow-500/40
             hover:bg-yellow-500/30 transition-all"
    >
      测试烟雾
    </button>

    <button
      type="button"
      onclick={() => trigger('warning', '💧 漏油')}
      class="px-3 py-1.5 rounded-lg text-xs font-medium
             bg-blue-500/20 text-blue-400 border border-blue-500/40
             hover:bg-blue-500/30 transition-all"
    >
      测试漏油
    </button>

    <button
      type="button"
      onclick={() => alertStore.clear()}
      class="px-3 py-1.5 rounded-lg text-xs font-medium
             bg-white/5 text-slate-400 border border-white/10
             hover:bg-white/10 transition-all"
    >
      清空所有告警
    </button>
  </div>
{/if}