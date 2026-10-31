<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import AlertModal from '$lib/components/AlertModal.svelte';
  import AlertTester from '$lib/components/AlertTester.svelte';

  // ============================================================
  // ⚠️ 通信相关 import
  // ============================================================
  import { robotStore } from '$lib/stores/robot';        
  import { logStore } from '$lib/stores/log';            
  import { wsService } from '$lib/services/websocket';   

  // ============================================================
  // 纯展示组件
  // ============================================================
  import LogViewer from '$lib/components/LogViewer.svelte';
  import StatusPanel from '$lib/components/StatusPanel.svelte';
  import VideoStream from '$lib/components/VideoStream.svelte';

  // ============================================================
  // 响应式状态（Svelte 5）
  // ============================================================
  let status = $state('待机');
  let battery = $state(85);
  let videoUrl = $state('');

  let inspectionRunning = $state(false);   
  let inspectionProgress = $state(0);      
  let inspectionStep = $state('');         
  let idleTimer: any = null;               

  let activeDirection = $state('');   
  let stopRippleKey = $state(0);      

  let lastWsSendTime = 0;
  let wsThrottleTimer: any = null;
  let pendingKeyboardCmd: string | null = null;

  const KEY_CMD: Record<string, string> = {
    w: 'forward',  arrowup:    'forward',
    s: 'backward', arrowdown:  'backward',
    a: 'left',     arrowleft:  'left',
    d: 'right',    arrowright: 'right'
  };

  function resolveKeyCmd(eventKey: string): string {
    const key = eventKey.toLowerCase();
    if (key === ' ' || key === 'spacebar') return 'stop';
    return KEY_CMD[key] ?? '';
  }

  type TabKey = 'overview' | 'control';
  let activeTab: TabKey = $state('overview');
  const tabs: { key: TabKey; label: string; icon: string }[] = [
    { key: 'overview', label: '总览', icon: '📊' },
    { key: 'control',  label: '操控', icon: '🎮' }
  ];

  const unsubscribe = robotStore.subscribe((value) => {
    status = value.status;
    battery = value.battery;
  });

  const unsubStatus = wsService.status.subscribe((s) => {
    if (s === 'connected') {
      const base = wsService.getBackendBase();
      videoUrl = `${base}/api/camera/video?width=640&height=480`;
      console.log('📷 视频流地址:', videoUrl);
    } else {
      videoUrl = '';
    }
  });

  function setMoving() {
    status = '移动';
    clearIdle();
    idleTimer = setTimeout(() => {
      status = '待机';
      idleTimer = null;
    }, 30000);
  }

  function clearIdle() {
    if (idleTimer) {
      clearTimeout(idleTimer);
      idleTimer = null;
    }
  }

  function emitCommand(cmd: string) {
    wsService.send({ type: 'command', data: { cmd } });
    if (['forward', 'backward', 'left', 'right'].includes(cmd)) {
      setMoving();
    } else if (['stop', 'standup', 'sit'].includes(cmd)) {
      status = '待机';
      clearIdle();
    }
  }

  function sendCommand(cmd: string) {
    console.log('📩 指令:', cmd);
    emitCommand(cmd);
  }

  function stopCommand() {
    sendCommand('stop');
    stopRippleKey++;
  }

  function handlePadKey(cmd: string, event: KeyboardEvent) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      if (cmd === 'stop') stopCommand();
      else sendCommand(cmd);
    }
  }

  function sendKeyboardCommand(cmd: string) {
    const now = Date.now();
    pendingKeyboardCmd = cmd;
    const THROTTLE_MS = 50;

    if (now - lastWsSendTime >= THROTTLE_MS) {
      flushKeyboardCommand();
    } else if (wsThrottleTimer == null) {
      wsThrottleTimer = setTimeout(
        flushKeyboardCommand,
        THROTTLE_MS - (now - lastWsSendTime)
      );
    }
  }

  function flushKeyboardCommand() {
    wsThrottleTimer = null;
    if (pendingKeyboardCmd == null) return;
    const cmd = pendingKeyboardCmd;
    pendingKeyboardCmd = null;
    lastWsSendTime = Date.now();
    console.log('📩 指令:', cmd);
    emitCommand(cmd);
  }

  function handleKeydown(event: KeyboardEvent) {
    const target = event.target as HTMLElement | null;
    const tag = target?.tagName?.toLowerCase();
    if (target && (tag === 'input' || tag === 'textarea' || tag === 'select' || target.isContentEditable)) return;

    const cmd = resolveKeyCmd(event.key);
    if (!cmd) return;

    event.preventDefault();
    event.stopPropagation();
    activeDirection = cmd;
    sendKeyboardCommand(cmd);

    if (cmd === 'stop') stopRippleKey++;
  }

  function handleKeyup(event: KeyboardEvent) {
    const cmd = resolveKeyCmd(event.key);
    if (cmd && cmd === activeDirection) {
      activeDirection = '';
      console.log('📩 松开，发停止指令');
      wsService.send({ type: 'command', data: { cmd: 'stop' } });
    }
  }

  // ============================================================
  // ★ 重写：开始巡检（发送 HTTP 请求给后端）
  // ============================================================
  async function startInspection() {
    if (inspectionRunning) return;
    
    // 本地状态立即锁定
    inspectionRunning = true;
    status = '巡检中';
    clearIdle();
    inspectionProgress = 0;
    inspectionStep = '正在下发巡检任务...';

    logStore.update(logs => [
      { time: new Date().toLocaleTimeString(), level: 'info', message: '🚀 正在向后端下发巡检任务...' },
      ...logs
    ].slice(0, 200));

    try {
      const base = wsService.getBackendBase();
      const res = await fetch(`${base}/api/inspection/start`, { method: 'POST' });
      const data = await res.json();
      
      if (!data.success) {
        alert(data.msg);
        inspectionRunning = false;
        status = '待机';
        inspectionStep = '';
      } else {
        inspectionStep = '正在执行自动化巡检...';
      }
    } catch (e) {
      console.error(e);
      alert('请求后端失败');
      inspectionRunning = false;
      status = '待机';
      inspectionStep = '';
    }
  }

  // ============================================================
  // ★ 重写：紧急停止（发送 HTTP 请求给后端）
  // ============================================================
  async function emergencyStop() {
    inspectionRunning = false;
    inspectionProgress = 0;
    inspectionStep = '⛔ 已紧急停止';
    status = '待机';
    clearIdle();

    logStore.update(logs => [
      { time: new Date().toLocaleTimeString(), level: 'error', message: '⛔ 紧急停止触发，正在通知后端刹车...' },
      ...logs
    ].slice(0, 200));

    try {
      const base = wsService.getBackendBase();
      await fetch(`${base}/api/inspection/stop`, { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
  }

  // ============================================================
  // 生命周期
  // ============================================================
  onMount(() => {
    wsService.connect();
    // ★ 移除了原有的 startDetectionPolling 逻辑（现已全走WS推送）

    if (typeof window !== 'undefined') {
      window.addEventListener('keydown', handleKeydown, { capture: true });
      window.addEventListener('keyup', handleKeyup);
    }
  });

  onDestroy(() => {
    wsService.disconnect();
    unsubscribe();
    unsubStatus();   

    if (typeof window !== 'undefined') {
      window.removeEventListener('keydown', handleKeydown, { capture: true });
      window.removeEventListener('keyup', handleKeyup);
    }

    if (idleTimer) clearTimeout(idleTimer);
    if (wsThrottleTimer) clearTimeout(wsThrottleTimer);
    activeDirection = '';
  });

  function statusAccent() {
    if (status === '移动')   return { dot: 'bg-neon-green', ring: 'bg-neon-green', chip: 'border-neon-green/30 bg-neon-green/10 text-neon-green' };
    if (status === '巡检中') return { dot: 'bg-neon-blue',  ring: 'bg-neon-blue',  chip: 'border-neon-blue/30 bg-neon-blue/10 text-neon-blue' };
    return                          { dot: 'bg-slate-400', ring: 'bg-slate-400', chip: 'border-white/10 bg-white/5 text-slate-400' };
  }
  const accent = $derived(statusAccent());

  const PAD_C = 110;   
  const R_OUT = 104;   
  const R_IN = 46;     
  const GAP = 2.5;     
  const SEG_HALF = 45 - GAP / 2;

  function polar(cx: number, cy: number, r: number, deg: number) {
    const a = (deg * Math.PI) / 180;
    return { x: +(cx + r * Math.cos(a)).toFixed(2), y: +(cy + r * Math.sin(a)).toFixed(2) };
  }

  function sectorPath(startDeg: number, endDeg: number) {
    const p1 = polar(PAD_C, PAD_C, R_OUT, startDeg);
    const p2 = polar(PAD_C, PAD_C, R_OUT, endDeg);
    const p3 = polar(PAD_C, PAD_C, R_IN, endDeg);
    const p4 = polar(PAD_C, PAD_C, R_IN, startDeg);
    return `M ${p1.x} ${p1.y} A ${R_OUT} ${R_OUT} 0 0 1 ${p2.x} ${p2.y} L ${p3.x} ${p3.y} A ${R_IN} ${R_IN} 0 0 0 ${p4.x} ${p4.y} Z`;
  }

  const sectors = [
    { cmd: 'forward',  label: '前进', icon: '↑', center: -90, vert: true  },
    { cmd: 'right',    label: '右转', icon: '→', center: 0,   vert: false },
    { cmd: 'backward', label: '后退', icon: '↓', center: 90,  vert: true  },
    { cmd: 'left',     label: '左转', icon: '←', center: 180, vert: false }
  ].map((s) => {
    const mid = (R_OUT + R_IN) / 2;
    const lp = polar(PAD_C, PAD_C, mid, s.center);
    return {
      cmd: s.cmd,
      label: s.label,
      icon: s.icon,
      vert: s.vert,
      d: sectorPath(s.center - SEG_HALF, s.center + SEG_HALF),
      lx: lp.x,
      ly: lp.y
    };
  });
</script>

<div class="page-enter max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
  <!-- 顶部标题 -->
  <header class="flex items-center justify-between gap-4 mb-6">
    <div class="flex items-center gap-3 min-w-0">
      <div class="relative shrink-0">
        <img src="/logo.png" alt="Go2 智能巡检" class="w-11 h-11 rounded-xl object-cover" />
        <span class="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full {accent.dot} animate-glow-pulse"></span>
      </div>
      <div class="min-w-0">
        <h1 class="text-lg sm:text-xl font-bold tracking-tight text-white truncate">
          Go2 智能巡检
        </h1>
        <p class="text-[11px] text-slate-500 font-mono uppercase tracking-[0.2em]">
          Inspection System · v2.0
        </p>
      </div>
    </div>
    <div class="flex items-center gap-2">
      <span class="hidden sm:inline-flex chip">
        <span class="w-1.5 h-1.5 rounded-full bg-neon-green animate-glow-pulse"></span>
        WS LINK
      </span>
    </div>
  </header>

  <!-- 标签导航 -->
  <nav class="mb-5">
    <div class="flex gap-1.5 p-1.5 rounded-2xl bg-ink-800/60 border border-white/5 backdrop-blur-xl overflow-x-auto scrollbar-thin">
      {#each tabs as tab}
        <button type="button" onclick={() => activeTab = tab.key} class="tab {activeTab === tab.key ? 'tab-active' : ''}">
          <span class="text-base leading-none">{tab.icon}</span>
          <span>{tab.label}</span>
          {#if tab.key === 'overview' && $logStore.length > 0}
            <span class="ml-1 px-1.5 py-0.5 text-[10px] rounded-full bg-neon-cyan/20 text-neon-cyan font-mono">
              {$logStore.length}
            </span>
          {/if}
        </button>
      {/each}
    </div>
  </nav>

  <!-- 标签内容 -->
  <div class="relative">
    <div class="animate-tab-in">
      <!-- 总览 -->
      {#if activeTab === 'overview'}
        <div class="flex flex-col gap-4">
          <StatusPanel {status} {battery} progress={inspectionProgress} step={inspectionStep} running={inspectionRunning} />
          <div class="card p-5">
            <div class="flex items-center justify-between mb-3">
              <h2 class="text-xs font-semibold text-slate-400 uppercase tracking-[0.18em]">📋 巡检日志</h2>
              <span class="chip">{$logStore.length} ENTRIES</span>
            </div>
            <LogViewer />
          </div>
        </div>

      <!-- 操控 -->
      {:else if activeTab === 'control'}
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <VideoStream {videoUrl} />
          <div class="flex flex-col gap-4">
            <div class="card card-hover p-5">
              <div class="flex items-center justify-between mb-4">
                <h2 class="text-xs font-semibold text-slate-400 uppercase tracking-[0.18em]">🎮 运动控制</h2>
                <span class="chip">WASD / 方向键</span>
              </div>
              <div class="control-pad">
                <svg viewBox="0 0 220 220" class="w-full h-full" aria-label="运动控制盘">
                  {#each sectors as s (s.cmd)}
                    <g class="seg-group {s.vert ? 'seg-v' : 'seg-h'} {activeDirection === s.cmd ? 'is-pressed' : ''}"
                       onclick={() => sendCommand(s.cmd)} onkeydown={(e) => handlePadKey(s.cmd, e)}
                       role="button" tabindex="0" aria-label={s.label}>
                      <path class="seg" d={s.d} />
                      <text x={s.lx} y={s.ly - 8} text-anchor="middle" class="seg-icon">{s.icon}</text>
                      <text x={s.lx} y={s.ly + 12} text-anchor="middle" class="seg-label">{s.label}</text>
                    </g>
                  {/each}
                  <g class="stop-btn {activeDirection === 'stop' ? 'is-pressed' : ''}"
                     onclick={stopCommand} onkeydown={(e) => handlePadKey('stop', e)}
                     role="button" tabindex="0" aria-label="停止">
                    {#if stopRippleKey > 0}
                      {#key stopRippleKey}
                        <circle cx="110" cy="110" r="42" class="stop-ripple" vector-effect="non-scaling-stroke" />
                      {/key}
                    {/if}
                    <circle cx="110" cy="110" r="42" class="stop-face" fill="#ef4444" />
                    <text x="110" y="107" text-anchor="middle" class="stop-icon">⏹</text>
                    <text x="110" y="130" text-anchor="middle" class="stop-label">停止</text>
                  </g>
                </svg>
              </div>
            </div>

            <div class="card card-hover p-5 flex flex-col gap-3">
              <div class="flex items-center justify-between">
                <h2 class="text-xs font-semibold text-slate-400 uppercase tracking-[0.18em]">⚙️ 动作 / 任务</h2>
                <span class="chip">ACTION</span>
              </div>
              <div class="flex flex-wrap gap-2">
                <button type="button" onclick={() => sendCommand('standup')} class="ctrl-chip">🧍 站立</button>
                <button type="button" onclick={() => sendCommand('sit')} class="ctrl-chip">🪑 坐下</button>
                <button type="button" onclick={emergencyStop} class="ctrl-chip ctrl-chip-danger">⛔ 紧急停止</button>
              </div>
              <button type="button" onclick={startInspection} disabled={inspectionRunning}
                class="mt-auto w-full py-3 rounded-xl text-sm font-semibold transition-all duration-300
                  {inspectionRunning ? 'bg-ink-600 text-slate-500 cursor-not-allowed' : 'bg-gradient-to-r from-neon-green/90 to-neon-cyan/90 text-ink-900 hover:shadow-glow-green hover:-translate-y-0.5 active:translate-y-0'}">
                {inspectionRunning ? '⏳ 巡检执行中...' : '🚀 开始巡检'}
              </button>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>
<AlertModal />
<AlertTester />
<DetectionDebug />

<style>
  /* ============ 纯样式（完全保留你原来的） ============ */
  .control-pad { width: 220px; height: 220px; margin: 0 auto; user-select: none; }
  .control-pad svg { display: block; }
  .seg-group, .stop-btn { cursor: pointer; outline: none; -webkit-tap-highlight-color: transparent; }
  .seg-group:focus-visible .seg, .stop-btn:focus-visible .stop-face { filter: brightness(1.12); }
  .seg { transition: fill 0.18s ease, filter 0.18s ease; }
  .seg-v .seg { fill: rgba(96, 165, 250, 0.14); }
  .seg-h .seg { fill: rgba(34, 211, 238, 0.14); }
  .seg-v:hover .seg { fill: rgba(96, 165, 250, 0.3); }
  .seg-h:hover .seg { fill: rgba(34, 211, 238, 0.3); }
  .seg-group:hover .seg-icon, .seg-group:hover .seg-label { filter: brightness(1.25); }
  .seg-icon, .seg-label { pointer-events: none; font-family: inherit; }
  .seg-icon { font-size: 22px; font-weight: 700; }
  .seg-label { font-size: 11px; font-weight: 600; }
  .seg-v .seg-icon { fill: #93c5fd; }
  .seg-v .seg-label { fill: #60a5fa; }
  .seg-h .seg-icon { fill: #67e8f9; }
  .seg-h .seg-label { fill: #22d3ee; }
  .seg-group.is-pressed .seg { filter: brightness(1.45) drop-shadow(0 0 10px rgba(147, 197, 253, 0.5)); }
  .seg-group.is-pressed.seg-v .seg { fill: rgba(96, 165, 250, 0.42); }
  .seg-group.is-pressed.seg-h .seg { fill: rgba(34, 211, 238, 0.42); }
  .stop-btn { transform-box: view-box; transform-origin: 110px 110px; transition: transform 0.15s ease; }
  .stop-face { fill: #ef4444; transition: filter 0.15s ease; }
  .stop-btn:hover { transform: scale(1.08); }
  .stop-btn:hover .stop-face { filter: brightness(1.1) drop-shadow(0 0 14px rgba(239, 68, 68, 0.85)); }
  .stop-btn:active, .stop-btn.is-pressed { transform: scale(0.92); }
  .stop-btn:active .stop-face, .stop-btn.is-pressed .stop-face { filter: brightness(0.88) saturate(1.25) drop-shadow(0 0 20px rgba(239, 68, 68, 0.95)); }
  .stop-ripple { fill: none; stroke: rgba(255, 255, 255, 0.65); stroke-width: 3; pointer-events: none; transform-box: view-box; transform-origin: 110px 110px; animation: stop-ripple 0.3s ease-out forwards; }
  @keyframes stop-ripple { 0% { transform: scale(1); opacity: 0.9; } 100% { transform: scale(2.4); opacity: 0; } }
  .stop-icon { font-size: 18px; fill: #ffffff; pointer-events: none; font-family: inherit; }
  .stop-label { font-size: 12px; font-weight: 700; fill: #ffffff; pointer-events: none; font-family: inherit; }
  .ctrl-chip { @apply px-3.5 py-1.5 rounded-lg text-xs font-medium bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10 hover:text-white transition-all duration-200 active:scale-95; }
  .ctrl-chip-danger { @apply bg-red-400/10 border-red-400/30 text-red-400 hover:bg-red-400/20; }
</style>
