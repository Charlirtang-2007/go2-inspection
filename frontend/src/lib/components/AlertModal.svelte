<script lang="ts">
  import { alertStore, modalAlerts, activeAlerts } from '$lib/stores/alert';
  import { onMount, onDestroy } from 'svelte';

  // ===== 音频元素 =====
  let alarmAudio: HTMLAudioElement | null = null;
  let muted = $state(false);
  let audioReady = $state(false);

  onMount(() => {
    // 创建音频对象（只创建一次）
    alarmAudio = new Audio('/sounds/alarm.mp3');
    alarmAudio.loop = true;      // 循环播放
    alarmAudio.volume = 0.6;     // 音量 60%

    // 首次用户交互时激活音频
    const activate = () => {
      audioReady = true;
      window.removeEventListener('click', activate);
      window.removeEventListener('keydown', activate);
      window.removeEventListener('touchstart', activate);
      console.log('🔊 音频已激活，可播放报警音');
    };
    window.addEventListener('click', activate);
    window.addEventListener('keydown', activate);
    window.addEventListener('touchstart', activate);
  });

  onDestroy(() => {
    if (alarmAudio) {
      alarmAudio.pause();
      alarmAudio = null;
    }
  });

  // ===== 有未确认告警 → 循环播放；确认后 → 停止 =====
  $effect(() => {
    const hasUnconfirmed = $activeAlerts.length > 0;

    if (!alarmAudio) return;

    if (hasUnconfirmed && !muted) {
      alarmAudio.play().catch(e => {
        console.warn('播放报警音失败（可能未交互）:', e);
      });
    } else {
      alarmAudio.pause();
      alarmAudio.currentTime = 0;
    }
  });

  // ===== 静音切换时，同步控制音量 =====
  $effect(() => {
    if (alarmAudio) {
      alarmAudio.volume = muted ? 0 : 0.6;
    }
  });

  // ===== 紧急程度映射 =====
  function getLevelInfo(level: string) {
    switch (level) {
      case 'critical':
        return { label: '严重', barBg: 'bg-red-500', border: 'border-red-500', pulse: 'rgba(239, 68, 68, 0.7)' };
      case 'warning':
        return { label: '警告', barBg: 'bg-yellow-500', border: 'border-yellow-500', pulse: 'rgba(234, 179, 8, 0.7)' };
      default:
        return { label: '提示', barBg: 'bg-blue-500', border: 'border-blue-500', pulse: 'rgba(59, 130, 246, 0.7)' };
    }
  }
</script>

{#if $modalAlerts.length > 0}
  <!-- 全屏遮罩 -->
  <div class="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
    <div class="w-full max-w-2xl flex flex-col gap-3 max-h-[90vh] overflow-y-auto">

      <!-- 顶部工具条：静音开关 -->
      <div class="flex justify-end">
        <button
          type="button"
          onclick={() => muted = !muted}
          class="px-3 py-1.5 rounded-lg text-xs font-medium
                 bg-white/10 text-white border border-white/20
                 hover:bg-white/20 transition-all flex items-center gap-1.5"
        >
          {muted ? '🔇 静音中' : '🔊 声音已开'}
        </button>
      </div>

      {#each $activeAlerts as alert (alert.id)}
        {@const info = getLevelInfo(alert.level)}
        <div
          class="rounded-2xl border-2 {info.border} bg-ink-800 shadow-2xl overflow-hidden"
          style="animation: alert-pulse 1.5s infinite; --pulse-color: {info.pulse};"
        >
          <!-- 头部 -->
          <div class="{info.barBg} px-5 py-3 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <span class="text-2xl animate-bounce">⚠️</span>
              <div>
                <h3 class="text-white font-bold text-lg">巡检异常告警</h3>
                <p class="text-white/85 text-xs">紧急程度：{info.label}</p>
              </div>
            </div>
            <span class="text-white/75 text-xs font-mono">{alert.timestamp}</span>
          </div>

          <!-- 内容 -->
          <div class="p-5 space-y-3">
            <div class="flex items-start gap-3">
              <span class="text-slate-500 text-sm w-20 shrink-0">异常类型</span>
              <span class="text-white font-semibold text-base">{alert.type}</span>
            </div>
            <div class="flex items-start gap-3">
              <span class="text-slate-500 text-sm w-20 shrink-0">大概区域</span>
              <span class="text-white">{alert.area}</span>
            </div>
            {#if alert.detail}
              <div class="flex items-start gap-3">
                <span class="text-slate-500 text-sm w-20 shrink-0">详情</span>
                <span class="text-slate-300 text-sm">{alert.detail}</span>
              </div>
            {/if}
          </div>

          <!-- 底部按钮 -->
          <div class="px-5 pb-5">
            <button
              type="button"
              onclick={() => alertStore.confirm(alert.id)}
              class="w-full py-3 rounded-xl font-semibold text-white
                     bg-gradient-to-r from-red-500 to-orange-500
                     hover:from-red-600 hover:to-orange-600
                     transition-all active:scale-95 shadow-lg"
            >
              ✅ 已知晓，正在处理
            </button>
          </div>
        </div>
      {/each}

      <!-- 多条告警时显示"全部确认" -->
      {#if $activeAlerts.length > 1}
        <button
          type="button"
          onclick={() => alertStore.confirmAll()}
          class="py-2 rounded-xl text-sm font-medium
                 bg-white/10 text-white border border-white/20
                 hover:bg-white/20 transition-all"
        >
          全部确认（{$activeAlerts.length} 条）
        </button>
      {/if}
    </div>
  </div>
{/if}

<style>
  @keyframes alert-pulse {
    0%, 100% {
      box-shadow: 0 0 0 0 var(--pulse-color);
    }
    50% {
      box-shadow: 0 0 0 12px transparent;
    }
  }
</style>