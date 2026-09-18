<script lang="ts">
  import { fullscreenAlerts } from '$lib/stores/alert';
  import { untrack } from 'svelte';

  let { active = false } = $props();

  type Danmaku = {
    id: string;
    text: string;
    level: string;
    top: number;
    duration: number;
  };

  let danmakus = $state<Danmaku[]>([]);
  let danmakuTimer: number | null = null;
  let expireTimer: number | null = null;

  const DURATION_MS = 3 * 60 * 1000;

  // 用一个 derived 明确依赖，只关心"该不该跑"
  const shouldRun = $derived(active && $fullscreenAlerts.length > 0);

  $effect(() => {
    // 只读 shouldRun，建立依赖
    const run = shouldRun;

    // ⚠️ 用 untrack 包住所有副作用，避免被追踪
    untrack(() => {
      if (run) {
        startDanmaku();
      } else {
        stopDanmaku();
      }
    });

    return () => untrack(() => stopDanmaku());
  });

  function startDanmaku() {
    if (danmakuTimer !== null) return;

    pushDanmaku();
    danmakuTimer = window.setInterval(pushDanmaku, 1500);
    expireTimer = window.setTimeout(() => {
      stopDanmaku();
    }, DURATION_MS);
  }

  function stopDanmaku() {
    if (danmakuTimer !== null) {
      clearInterval(danmakuTimer);
      danmakuTimer = null;
    }
    if (expireTimer !== null) {
      clearTimeout(expireTimer);
      expireTimer = null;
    }
    if (danmakus.length > 0) {
      danmakus = [];
    }
  }

  function pushDanmaku() {
    const alerts = $fullscreenAlerts;
    if (alerts.length === 0) return;

    const alert = alerts[Math.floor(Math.random() * alerts.length)];
    const levelText =
      alert.level === 'critical' ? '🔴 严重' :
      alert.level === 'warning'  ? '🟡 警告' : '🔵 提示';

    const d: Danmaku = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      text: `${levelText} ｜ ${alert.type} ｜ ${alert.area}`,
      level: alert.level,
      top: 12 + Math.random() * 68,
      duration: 8 + Math.random() * 4
    };

    danmakus = [...danmakus, d];

    window.setTimeout(() => {
      danmakus = danmakus.filter(x => x.id !== d.id);
    }, d.duration * 1000 + 500);
  }

  function borderColor(level: string) {
    if (level === 'critical') return 'border-red-500/90';
    if (level === 'warning')  return 'border-yellow-500/90';
    return 'border-blue-500/90';
  }
  function textColor(level: string) {
    if (level === 'critical') return 'text-red-300';
    if (level === 'warning')  return 'text-yellow-300';
    return 'text-blue-300';
  }
</script>

{#if active && $fullscreenAlerts.length > 0}
  <!-- 频闪 -->
  <div class="flash-overlay absolute inset-0 pointer-events-none z-[60]"></div>

  <!-- 顶部告警条 -->
  <div class="absolute top-0 left-0 right-0 z-[61] pointer-events-none">
    <div class="bg-red-600/95 backdrop-blur text-white py-2.5 px-4
                flex items-center justify-center gap-3 flash-bar">
      <span class="text-lg animate-pulse">⚠️</span>
      <span class="font-bold tracking-wider text-lg">异常告警中 · 请立即处理</span>
      <span class="text-sm opacity-90">({$fullscreenAlerts.length} 条未确认)</span>
    </div>
  </div>

  <!-- 弹幕层 -->
  <div class="absolute inset-0 pointer-events-none z-[62] overflow-hidden">
    {#each danmakus as d (d.id)}
      <div
        class="danmaku absolute whitespace-nowrap px-4 py-2 rounded-full
               bg-black/65 backdrop-blur border {borderColor(d.level)}
               text-sm font-medium {textColor(d.level)} shadow-lg"
        style="top: {d.top}%; animation: danmaku-fly {d.duration}s linear forwards;"
      >
        {d.text}
      </div>
    {/each}
  </div>
{/if}

<style>
  .flash-overlay {
    animation: flash-pulse 1s infinite;
  }

  @keyframes flash-pulse {
    0%, 100% {
      box-shadow: inset 0 0 0 0 rgba(239, 68, 68, 0);
      background: rgba(239, 68, 68, 0);
    }
    50% {
      box-shadow: inset 0 0 100px 24px rgba(239, 68, 68, 0.75);
      background: rgba(239, 68, 68, 0.06);
    }
  }

  .flash-bar {
    animation: bar-pulse 1s infinite;
  }
  @keyframes bar-pulse {
    0%, 100% { opacity: 0.88; }
    50%      { opacity: 1; }
  }

  .danmaku {
    will-change: transform;
  }
  @keyframes danmaku-fly {
    from { transform: translateX(100vw); }
    to   { transform: translateX(-100%); }
  }
</style>