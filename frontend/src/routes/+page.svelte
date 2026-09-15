<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  // ⚠️ 以下三个 import 涉及通信/状态，逻辑未改，仅用于读取和发送
  import { robotStore } from '$lib/stores/robot';        // 机器人状态 store（WS 推送写入）
  import { logStore } from '$lib/stores/log';            // 日志 store（WS 推送写入）
  import { wsService } from '$lib/services/websocket';   // ★ WebSocket 服务（连接/发送/断开）
  // 纯展示组件，不含通信
  import LogViewer from '$lib/components/LogViewer.svelte';
  import StatusPanel from '$lib/components/StatusPanel.svelte';
  import VideoStream from '$lib/components/VideoStream.svelte';

  // ===== 响应式状态（Svelte 5）=====
  // 这些值来自 robotStore 订阅，不是自己产生的
  let status = $state('待机');
  let battery = $state(85);

  // ===== 巡检状态（本地 UI 状态，不涉及通信）=====
  let inspectionRunning = $state(false);
  let inspectionProgress = $state(0);
  let inspectionStep = $state('');
  let inspectionTimer: any = null;
  let idleTimer: any = null;   // 30 秒无操控自动回到待机的定时器

  // ===== 标签页状态（纯 UI，不涉及通信）=====
  type TabKey = 'overview' | 'control';
  let activeTab: TabKey = $state('overview');
  const tabs: { key: TabKey; label: string; icon: string }[] = [
    { key: 'overview', label: '总览', icon: '📊' },
    { key: 'control',  label: '操控', icon: '🎮' }
  ];

  // ===== 订阅 robotStore（接收 WS 推送的状态）=====
  // ⚠️ 通信接收端：WS 收到 status_update 后写入 robotStore，这里再同步到本地变量
  const unsubscribe = robotStore.subscribe((value) => {
    status = value.status;
    battery = value.battery;
  });

  // ===== 30 秒无操控自动回到待机 =====
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

  // ===== 发送控制指令 =====
  // ★ 通信发送端：把指令通过 wsService 发出去，逻辑与原版完全一致
  function sendCommand(cmd: string) {
    console.log('📩 指令:', cmd);
    wsService.send({ type: 'command', data: { cmd } });

    // 根据指令更新状态显示：运动→移动，停止/站立/坐下→待机
    if (['forward', 'backward', 'left', 'right'].includes(cmd)) {
      setMoving();
    } else if (['stop', 'standup', 'sit'].includes(cmd)) {
      status = '待机';
      clearIdle();
    }
  }

  // ===== 键盘控制（WASD / 方向键 / 空格）=====
  function handleKeydown(event: KeyboardEvent) {
    const target = event.target as HTMLElement | null;
    const tag = target?.tagName?.toLowerCase();
    // 忽略输入框、文本域、下拉选择或可编辑元素，避免干扰用户输入
    if (target && (tag === 'input' || tag === 'textarea' || tag === 'select' || target.isContentEditable)) {
      return;
    }

    const keyMap: Record<string, string> = {
      w: 'forward',
      arrowup: 'forward',
      s: 'backward',
      arrowdown: 'backward',
      a: 'left',
      arrowleft: 'left',
      d: 'right',
      arrowright: 'right'
    };

    const key = event.key.toLowerCase();
    const cmd = key === ' ' ? 'stop' : keyMap[key];
    if (cmd) {
      // 拦截默认行为（页面滚动 / 焦点移动），避免按键触发标签页切换
      event.preventDefault();
      event.stopPropagation();
      sendCommand(cmd);

      // 记录反馈：写入总览日志 + 操控页最近指令
      const labels: Record<string, string> = {
        forward: '前进', backward: '后退', left: '左转', right: '右转', stop: '停止'
      };
      const name = labels[cmd] ?? cmd;
      const time = new Date().toLocaleTimeString();
      logStore.update(logs => [
        { time, level: 'info', message: `⌨️ 键盘控制：${name} (${cmd})` },
        ...logs
      ]);
    }
  }

  // ===== 开始巡检 =====
  function startInspection() {
    if (inspectionRunning) return;

    // ★ 通信发送端：通知后端开始巡检
    wsService.send({ type: 'command', data: { cmd: 'start_inspection' } });

    startLocalSimulation(); // 本地模拟进度（不涉及通信）

    status = '巡检中';
    clearIdle();
    inspectionRunning = true;
    inspectionProgress = 0;
    inspectionStep = '初始化巡检...';
    // 写本地日志 store（LogViewer 订阅它）
    logStore.update(logs => [
      { time: new Date().toLocaleTimeString(), level: 'info', message: '🚀 开始巡检任务' },
      ...logs
    ]);
  }

  // ===== 本地模拟巡检（纯本地，不发消息）=====
  function startLocalSimulation() {
    const steps = [
      { progress: 10, step: '前往设备区 A' },
      { progress: 25, step: '识别仪表盘读数' },
      { progress: 40, step: '前往设备区 B' },
      { progress: 60, step: '扫描火源/烟雾' },
      { progress: 80, step: '检测设备温度' },
      { progress: 95, step: '生成巡检报告' }
    ];

    let index = 0;
    if (inspectionTimer) clearInterval(inspectionTimer);

    inspectionTimer = setInterval(() => {
      if (index >= steps.length) {
        inspectionRunning = false;
        inspectionProgress = 100;
        inspectionStep = '✅ 巡检完成！';
        status = '待机';
        clearIdle();
        logStore.update(logs => [
          { time: new Date().toLocaleTimeString(), level: 'success', message: '✅ 巡检任务完成，共发现 1 处异常' },
          ...logs
        ]);
        clearInterval(inspectionTimer);
        inspectionTimer = null;
        return;
      }

      const step = steps[index];
      inspectionProgress = step.progress;
      inspectionStep = step.step;

      logStore.update(logs => [
        { time: new Date().toLocaleTimeString(), level: 'info', message: `🔄 ${step.step}...` },
        ...logs
      ]);

      if (index === 3 && Math.random() > 0.5) {
        logStore.update(logs => [
          { time: new Date().toLocaleTimeString(), level: 'error', message: '🔥 警告：发现火焰！' },
          ...logs
        ]);
      }
      if (index === 1 && Math.random() > 0.7) {
        logStore.update(logs => [
          { time: new Date().toLocaleTimeString(), level: 'warning', message: '⚠️ 仪表读数异常（压力超限）' },
          ...logs
        ]);
      }

      index++;
    }, 2000);
  }

  // ===== 紧急停止 =====
  function emergencyStop() {
    // ★ 通信发送端：发送急停指令
    sendCommand('emergency_stop');

    if (inspectionTimer) {
      clearInterval(inspectionTimer);
      inspectionTimer = null;
    }
    inspectionRunning = false;
    inspectionProgress = 0;
    inspectionStep = '⛔ 已紧急停止';
    status = '待机';
    clearIdle();
    logStore.update(logs => [
      { time: new Date().toLocaleTimeString(), level: 'error', message: '⛔ 紧急停止触发，巡检中断' },
      ...logs
    ]);
  }

  // ===== 生命周期 =====
  onMount(() => {
    // ★ 通信入口：页面挂载时建立 WebSocket 连接
    wsService.connect();
    window.addEventListener('keydown', handleKeydown, { capture: true });
  });

  onDestroy(() => {
    // ★ 通信出口：页面卸载时断开 WebSocket + 取消订阅 + 清定时器 + 移除键盘监听
    wsService.disconnect();
    unsubscribe();
    if (typeof window !== 'undefined') {
      window.removeEventListener('keydown', handleKeydown, { capture: true });
    }
    if (inspectionTimer) clearInterval(inspectionTimer);
    if (idleTimer) clearTimeout(idleTimer);
  });

  // ===== 状态 → 颜色（纯 UI 映射）=====
  function statusAccent() {
    if (status === '移动')   return { dot: 'bg-neon-green', ring: 'bg-neon-green', chip: 'border-neon-green/30 bg-neon-green/10 text-neon-green' };
    if (status === '巡检中') return { dot: 'bg-neon-blue',  ring: 'bg-neon-blue',  chip: 'border-neon-blue/30 bg-neon-blue/10 text-neon-blue' };
    return                          { dot: 'bg-slate-400', ring: 'bg-slate-400', chip: 'border-white/10 bg-white/5 text-slate-400' };
  }
  const accent = $derived(statusAccent());
</script>

<div class="page-enter max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">

  <!-- ===== 顶部标题（纯展示）===== -->
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
      <!-- 这里只是静态显示 WS 字样，没有实际连接判断 -->
      <span class="hidden sm:inline-flex chip">
        <span class="w-1.5 h-1.5 rounded-full bg-neon-green animate-glow-pulse"></span>
        WS LINK
      </span>
    </div>
  </header>

  <!-- ===== 标签导航（纯 UI，只切 activeTab）===== -->
  <nav class="mb-5">
    <div class="flex gap-1.5 p-1.5 rounded-2xl bg-ink-800/60 border border-white/5
                backdrop-blur-xl overflow-x-auto scrollbar-thin">
      {#each tabs as tab}
        <button
          type="button"
          onclick={() => activeTab = tab.key}
          class="tab {activeTab === tab.key ? 'tab-active' : ''}"
        >
          <span class="text-base leading-none">{tab.icon}</span>
          <span>{tab.label}</span>
          {#if tab.key === 'overview' && $logStore.length > 0}
            <span class="ml-1 px-1.5 py-0.5 text-[10px] rounded-full
                         bg-neon-cyan/20 text-neon-cyan font-mono">
              {$logStore.length}
            </span>
          {/if}
        </button>
      {/each}
    </div>
  </nav>

  <!-- ===== 标签内容 ===== -->
  <div class="relative">
    {#key activeTab}
      <div class="animate-tab-in">

        <!-- 总览：状态数据传给展示组件 + 日志列表 -->
        {#if activeTab === 'overview'}
          <div class="flex flex-col gap-4">
            <StatusPanel
              {status}
              {battery}
              progress={inspectionProgress}
              step={inspectionStep}
              running={inspectionRunning}
            />

            <div class="card p-5">
              <div class="flex items-center justify-between mb-3">
                <h2 class="text-xs font-semibold text-slate-400 uppercase tracking-[0.18em]">
                  📋 巡检日志
                </h2>
                <span class="chip">{$logStore.length} ENTRIES</span>
              </div>
              <LogViewer />
            </div>
          </div>

        <!-- 操控：视频流 + 运动/动作控制 -->
        {:else if activeTab === 'control'}
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <VideoStream />

            <div class="flex flex-col gap-4">
              <div class="card card-hover p-5">
                <div class="flex items-center justify-between mb-4">
                  <h2 class="text-xs font-semibold text-slate-400 uppercase tracking-[0.18em]">
                    🎮 运动控制
                  </h2>
                  <span class="chip">WASD / 方向键</span>
                </div>

                <div class="flex flex-col items-center gap-2 py-2">
                  <button type="button" onclick={() => sendCommand('forward')} class="ctrl-btn ctrl-blue w-20 h-14">⬆ 前进</button>
                  <div class="flex gap-2">
                    <button type="button" onclick={() => sendCommand('left')}  class="ctrl-btn ctrl-blue w-20 h-14">⬅ 左转</button>
                    <button type="button" onclick={() => sendCommand('stop')}  class="ctrl-btn ctrl-red  w-20 h-14">⏹ 停止</button>
                    <button type="button" onclick={() => sendCommand('right')} class="ctrl-btn ctrl-blue w-20 h-14">➡ 右转</button>
                  </div>
                  <button type="button" onclick={() => sendCommand('backward')} class="ctrl-btn ctrl-blue w-20 h-14">⬇ 后退</button>
                </div>
              </div>

              <div class="card card-hover p-5 flex flex-col gap-3">
                <div class="flex items-center justify-between">
                  <h2 class="text-xs font-semibold text-slate-400 uppercase tracking-[0.18em]">
                    ⚙️ 动作 / 任务
                  </h2>
                  <span class="chip">ACTION</span>
                </div>

                <div class="flex flex-wrap gap-2">
                  <button type="button" onclick={() => sendCommand('standup')} class="ctrl-chip">🧍 站立</button>
                  <button type="button" onclick={() => sendCommand('sit')}     class="ctrl-chip">🪑 坐下</button>
                  <button type="button" onclick={emergencyStop}               class="ctrl-chip ctrl-chip-danger">⛔ 紧急停止</button>
                </div>

                <button
                  type="button"
                  onclick={startInspection}
                  disabled={inspectionRunning}
                  class="mt-auto w-full py-3 rounded-xl text-sm font-semibold transition-all duration-300
                    {inspectionRunning
                      ? 'bg-ink-600 text-slate-500 cursor-not-allowed'
                      : 'bg-gradient-to-r from-neon-green/90 to-neon-cyan/90 text-ink-900 hover:shadow-glow-green hover:-translate-y-0.5 active:translate-y-0'}"
                >
                  {inspectionRunning ? '⏳ 巡检执行中...' : '🚀 开始巡检'}
                </button>
              </div>
            </div>
          </div>
        {/if}

      </div>
    {/key}
  </div>
</div>

<style>
  /* 纯样式，无通信 */
  .ctrl-btn {
    @apply rounded-xl text-sm font-semibold transition-all duration-200
           border flex items-center justify-center select-none;
  }
  .ctrl-blue {
    @apply bg-neon-blue/10 border-neon-blue/25 text-neon-blue
           hover:bg-neon-blue/20 hover:shadow-glow-blue hover:-translate-y-0.5
           active:translate-y-0 active:scale-95;
  }
  .ctrl-red {
    @apply bg-neon-red/10 border-neon-red/25 text-neon-red
           hover:bg-neon-red/20 hover:shadow-glow-red hover:-translate-y-0.5
           active:translate-y-0 active:scale-95;
  }
  .ctrl-chip {
    @apply px-3.5 py-1.5 rounded-lg text-xs font-medium
           bg-white/5 border border-white/10 text-slate-300
           hover:bg-white/10 hover:text-white transition-all duration-200
           active:scale-95;
  }
  .ctrl-chip-danger {
    @apply bg-neon-red/10 border-neon-red/30 text-neon-red
           hover:bg-neon-red/20;
  }
</style>