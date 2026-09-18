<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import AlertModal from '$lib/components/AlertModal.svelte';
  import AlertTester from '$lib/components/AlertTester.svelte';
  // ============================================================
  // ⚠️ 通信相关 import —— 以下逻辑全程未改
  // ============================================================
  import { robotStore } from '$lib/stores/robot';        // 机器人状态 store（WS 推送写入）
  import { logStore } from '$lib/stores/log';            // 日志 store（WS 推送写入）
  import { inspectionStore, type InspectionState } from '$lib/stores/log';  // 巡检录制/下载状态
  import { wsService } from '$lib/services/websocket';   // ★ WebSocket 服务（连接/发送/断开）

  // ============================================================
  // 纯展示组件（内部不碰网络）
  // ============================================================
  import LogViewer from '$lib/components/LogViewer.svelte';
  import StatusPanel from '$lib/components/StatusPanel.svelte';
  import VideoStream from '$lib/components/VideoStream.svelte';

  // ============================================================
  // 响应式状态（Svelte 5）
  // 这些值来源于 robotStore 订阅，不是组件自己产生的
  // ============================================================
  let status = $state('待机');
  let battery = $state(85);
  let inspection = $state<InspectionState>({ recording: false, inspection_id: '', video_url: '', log_url: '' });

  // ============================================================
  // 本地巡检记录兜底：点击「开始巡检」时立即生成本地 ID，
  // 避免后端尚未推送 inspection_id 时下载按钮一直处于禁用态。
  // 后端推送真实 inspection_id 后会被覆盖（见 unsubInspection）。
  // ============================================================
  let inspectionId = $state('');
  let inspectionFinished = $state(false);

  // ============================================================
  // ★ 视频流地址（由 wsService 连接成功后自动赋值）
  // ============================================================
  let videoUrl = $state('');

  // ★ 兜底后端地址：当 WebSocket 未连接或未返回地址时，仍然尝试连接本机后端
  const DEFAULT_BACKEND = 'http://localhost:8000';

  // 下载地址的 host：优先使用 WebSocket 发现到的后端地址，否则兜底 localhost
  function downloadBase(): string {
    return wsService.getBackendBase() || DEFAULT_BACKEND;
  }

  // ============================================================
  // 巡检状态（纯本地 UI 状态，不涉及网络）
  // ============================================================
  let inspectionRunning = $state(false);   // 是否正在巡检
  let inspectionProgress = $state(0);      // 巡检进度 0-100
  let inspectionStep = $state('');         // 当前巡检步骤文字
  let inspectionTimer: any = null;         // 巡检模拟定时器
  let idleTimer: any = null;               // 30 秒无操控自动回到待机的定时器

  // ============================================================
  // 键盘控制视觉反馈状态
  // ============================================================
  let activeDirection = $state('');   // 当前按下的方向（forward/backward/left/right/stop），松开后清空
  let stopRippleKey = $state(0);      // 停止按钮波纹重放计数：每次递增触发一次 ripple 动画

  // 下载提示（短暂显示，如“视频下载中...”）
  let downloadNote = $state('');
  let downloadNoteTimer: any = null;
  function notifyDownload(msg: string) {
    downloadNote = msg;
    if (downloadNoteTimer) clearTimeout(downloadNoteTimer);
    downloadNoteTimer = setTimeout(() => {
      downloadNote = '';
      downloadNoteTimer = null;
    }, 3000);
  }

  // ============================================================
  // 节流：100ms 内最多发一条移动/停止指令，避免高频 WebSocket 消息
  // ============================================================
  let lastWsSendTime = 0;
  let wsThrottleTimer: any = null;
  let pendingKeyboardCmd: string | null = null;

  // 键位 → 指令映射（空格在 resolveKeyCmd 中单独处理）
  // 同时支持 WASD 和方向键
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

  // ============================================================
  // 标签页状态（纯 UI，不涉及通信）
  // ============================================================
  type TabKey = 'overview' | 'control';
  let activeTab: TabKey = $state('overview');
  const tabs: { key: TabKey; label: string; icon: string }[] = [
    { key: 'overview', label: '总览', icon: '📊' },
    { key: 'control',  label: '操控', icon: '🎮' }
  ];

  // ============================================================
  // 订阅 robotStore
  // ⚠️ 通信接收端：WS 收到 status_update 后写入 robotStore，
  //    这里再同步到本地变量，供模板渲染
  // ============================================================
  const unsubscribe = robotStore.subscribe((value) => {
    status = value.status;
    battery = value.battery;
  });

  // 巡检录制/下载状态（由后端 inspection_status 消息驱动）
  const unsubInspection = inspectionStore.subscribe((v) => {
    inspection = v;
    // 后端推送真实 inspection_id 时覆盖本地兜底 ID，保证下载地址正确
    if (v.inspection_id) {
      inspectionId = v.inspection_id;
    }
  });

  // ============================================================
  // ★ 订阅 WebSocket 连接状态
  //    一旦连接成功，就获取后端地址，拼出视频流 URL
  //    连接断开时用兜底地址，避免显示"死图"或"搜索中"
  // ============================================================
  const unsubStatus = wsService.status.subscribe((s) => {
    if (s === 'connected') {
      const base = wsService.getBackendBase() || DEFAULT_BACKEND;
      videoUrl = `${base}/api/camera/video?width=640&height=480`;
      console.log('📷 视频流地址:', videoUrl);
    } else {
      // 兜底：WebSocket 未连接时也尝试用默认地址拉流
      videoUrl = `${DEFAULT_BACKEND}/api/camera/video?width=640&height=480`;
      console.log('📷 视频流地址（兜底）:', videoUrl);
    }
  });

  // ============================================================
  // 30 秒无操控自动回到待机
  // ============================================================
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

  // ============================================================
  // 实际发送一条指令（WS + 本地状态），鼠标点击和键盘共用
  // ★ 通信发送端：把指令通过 wsService 发出去
  // ============================================================
  function emitCommand(cmd: string) {
    wsService.send({ type: 'command', data: { cmd } });

    // 根据指令更新状态显示：运动→移动，停止/站立/坐下→待机
    if (['forward', 'backward', 'left', 'right'].includes(cmd)) {
      setMoving();
    } else if (['stop', 'standup', 'sit'].includes(cmd)) {
      status = '待机';
      clearIdle();
    }
  }

  // 鼠标点击入口，加一行日志方便调试
  function sendCommand(cmd: string) {
    console.log('📩 指令:', cmd);
    emitCommand(cmd);
  }

  // 控制盘键盘可达性：聚焦后用 Enter / 空格触发（配合 role="button" + tabindex）
  // 停止按钮：发送指令并触发一次波纹反馈（点击与键盘共用）
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

  // ============================================================
  // 键盘指令节流
  // 100ms 窗口内只发最后一条，避免长按方向键狂发消息
  // ============================================================
  function sendKeyboardCommand(cmd: string) {
    const now = Date.now();
    pendingKeyboardCmd = cmd;
    if (now - lastWsSendTime >= 100) {
      flushKeyboardCommand();
    } else if (wsThrottleTimer == null) {
      wsThrottleTimer = setTimeout(flushKeyboardCommand, 100 - (now - lastWsSendTime));
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

  // ============================================================
  // 键盘按下
  // ⚠️ 注意：这里【不再写日志】，避免高频日志更新卡住主线程
  //    从而保证标签切换始终流畅
  // ============================================================
  function handleKeydown(event: KeyboardEvent) {
    const target = event.target as HTMLElement | null;
    const tag = target?.tagName?.toLowerCase();

    // 忽略输入框、文本域、下拉选择或可编辑元素，避免干扰用户输入
    if (target && (tag === 'input' || tag === 'textarea' || tag === 'select' || target.isContentEditable)) {
      return;
    }

    const cmd = resolveKeyCmd(event.key);
    if (!cmd) return;

    // 拦截默认行为（页面滚动 / 焦点移动）
    event.preventDefault();
    event.stopPropagation();

    // 按住不放产生的自动重复事件直接忽略，避免高频触发
    if (event.repeat) return;

    // 视觉反馈：记录当前按下的方向（keyup 时清空）
    activeDirection = cmd;

    // 节流发送 WebSocket 指令
    sendKeyboardCommand(cmd);

    // 停止指令额外触发波纹反馈
    if (cmd === 'stop') stopRippleKey++;
  }

  // ============================================================
  // 键盘松开 → 清除视觉高亮
  // ============================================================
  function handleKeyup(event: KeyboardEvent) {
    const cmd = resolveKeyCmd(event.key);
    if (cmd && cmd === activeDirection) {
      activeDirection = '';
    }
  }

  // ============================================================
  // 开始巡检
  // ============================================================
  function startInspection() {
    if (inspectionRunning) return;

    // ★ 通信发送端：通知后端开始巡检
    wsService.send({ type: 'command', data: { cmd: 'start_inspection' } });

    // 生成本地巡检 ID（兜底）：后端推送真实 inspection_id 前，用它拼下载地址
    const now = new Date();
    const p = (n: number) => String(n).padStart(2, '0');
    inspectionId = `inspection_${now.getFullYear()}${p(now.getMonth() + 1)}${p(now.getDate())}_${p(now.getHours())}${p(now.getMinutes())}${p(now.getSeconds())}`;
    inspectionFinished = false;

    startLocalSimulation(); // 本地模拟进度（不涉及通信）

    status = '巡检中';
    clearIdle();
    inspectionRunning = true;
    inspectionProgress = 0;
    inspectionStep = '初始化巡检...';

    // 写本地日志 store（LogViewer 订阅它）
    // slice(0, 200) 限制条数，避免日志无限增长拖慢渲染
    logStore.update(logs => [
      { time: new Date().toLocaleTimeString(), level: 'info', message: '🚀 开始巡检任务' },
      ...logs
    ].slice(0, 200));
  }

  // ============================================================
  // 本地模拟巡检（纯本地，不发消息）
  // ============================================================
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
      // 全部步骤完成
      if (index >= steps.length) {
        inspectionRunning = false;
        inspectionFinished = true;
        inspectionProgress = 100;
        inspectionStep = '✅ 巡检完成！';
        status = '待机';
        clearIdle();
        // 结束录制：通知后端停止录制并生成视频/日志文件
        wsService.send({ type: 'command', data: { cmd: 'stop_inspection' } });
        logStore.update(logs => [
          { time: new Date().toLocaleTimeString(), level: 'success', message: '✅ 巡检任务完成，共发现 1 处异常' },
          ...logs
        ].slice(0, 200));
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
      ].slice(0, 200));

      // 随机插入异常事件
      if (index === 3 && Math.random() > 0.5) {
        logStore.update(logs => [
          { time: new Date().toLocaleTimeString(), level: 'error', message: '🔥 警告：发现火焰！' },
          ...logs
        ].slice(0, 200));
      }
      if (index === 1 && Math.random() > 0.7) {
        logStore.update(logs => [
          { time: new Date().toLocaleTimeString(), level: 'warning', message: '⚠️ 仪表读数异常（压力超限）' },
          ...logs
        ].slice(0, 200));
      }

      index++;
    }, 2000);
  }

  // ============================================================
  // 紧急停止
  // ============================================================
  function emergencyStop() {
    // ★ 通信发送端：发送急停指令
    sendCommand('emergency_stop');
    // 若正在录制，也一并停止
    wsService.send({ type: 'command', data: { cmd: 'stop_inspection' } });

    if (inspectionTimer) {
      clearInterval(inspectionTimer);
      inspectionTimer = null;
    }
    inspectionRunning = false;
    inspectionFinished = true;
    inspectionProgress = 0;
    inspectionStep = '⛔ 已紧急停止';
    status = '待机';
    clearIdle();

    logStore.update(logs => [
      { time: new Date().toLocaleTimeString(), level: 'error', message: '⛔ 紧急停止触发，巡检中断' },
      ...logs
    ].slice(0, 200));
  }

  // ============================================================
  // 生命周期
  // ============================================================
  onMount(() => {
    // ★ 通信入口：页面挂载时建立 WebSocket 连接
    wsService.connect();

    // 绑定键盘监听（SSR 阶段没有 window，需要判断）
    if (typeof window !== 'undefined') {
      window.addEventListener('keydown', handleKeydown, { capture: true });
      window.addEventListener('keyup', handleKeyup);
    }
  });

  onDestroy(() => {
    // ★ 通信出口：页面卸载时断开 WebSocket + 取消订阅 + 清定时器 + 移除键盘监听
    wsService.disconnect();
    unsubscribe();
    unsubStatus();   // ★ 取消 WebSocket 状态订阅
    unsubInspection();

    if (typeof window !== 'undefined') {
      window.removeEventListener('keydown', handleKeydown, { capture: true });
      window.removeEventListener('keyup', handleKeyup);
    }

    if (inspectionTimer) clearInterval(inspectionTimer);
    if (idleTimer) clearTimeout(idleTimer);
    if (wsThrottleTimer) clearTimeout(wsThrottleTimer);
    activeDirection = '';
  });

  // ============================================================
  // 状态 → 颜色（纯 UI 映射）
  // ============================================================
  function statusAccent() {
    if (status === '移动')   return { dot: 'bg-neon-green', ring: 'bg-neon-green', chip: 'border-neon-green/30 bg-neon-green/10 text-neon-green' };
    if (status === '巡检中') return { dot: 'bg-neon-blue',  ring: 'bg-neon-blue',  chip: 'border-neon-blue/30 bg-neon-blue/10 text-neon-blue' };
    return                          { dot: 'bg-slate-400', ring: 'bg-slate-400', chip: 'border-white/10 bg-white/5 text-slate-400' };
  }
  const accent = $derived(statusAccent());

  // ============================================================
  // 环形扇形控制盘（SVG 几何计算）
  // ============================================================
  const PAD_C = 110;   // 圆心
  const R_OUT = 104;   // 外半径
  const R_IN = 46;     // 内半径（环绕中心停止按钮）
  const GAP = 2.5;     // 扇形之间的角度间隙（度）
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

  // 顺时针：上(前进) → 右(右转) → 下(后退) → 左(左转)
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

  <!-- ============ 顶部标题（纯展示） ============ -->
  <header class="flex items-center justify-between gap-4 mb-6">
    <div class="flex items-center gap-3 min-w-0">
      <div class="relative shrink-0">
        <img src="/logo.png" alt="Go2 智能巡检" class="w-11 h-11 rounded-xl object-cover" />
        <!-- 状态指示点：跟随 status 变色 -->
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
      <!-- 静态显示 WS LINK，没有实际连接状态判断 -->
      <span class="hidden sm:inline-flex chip">
        <span class="w-1.5 h-1.5 rounded-full bg-neon-green animate-glow-pulse"></span>
        WS LINK
      </span>
    </div>
  </header>

  <!-- ============ 标签导航（纯 UI，只切 activeTab） ============ -->
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
          <!-- 总览标签上显示日志条数徽章 -->
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

  <!-- ============ 标签内容 ============ -->
  <!-- ⚠️ 这里去掉了 {#key activeTab}，避免每次切换都销毁重建 VideoStream / LogViewer -->
  <div class="relative">
    <div class="animate-tab-in">

      <!-- ===== 总览：状态面板 + 日志列表 ===== -->
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

      <!-- ===== 操控：视频流 + 运动/动作控制 ===== -->
      {:else if activeTab === 'control'}
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <!-- ★ 把 videoUrl 传给 VideoStream，由它负责渲染画面 -->
          <VideoStream {videoUrl} />

          <div class="flex flex-col gap-4">
            <!-- 运动方向控制 -->
            <div class="card card-hover p-5">
              <div class="flex items-center justify-between mb-4">
                <h2 class="text-xs font-semibold text-slate-400 uppercase tracking-[0.18em]">
                  🎮 运动控制
                </h2>
                <span class="chip">WASD / 方向键</span>
              </div>

              <div class="control-pad">
                <svg viewBox="0 0 220 220" class="w-full h-full" aria-label="运动控制盘">
                  <!-- 四个扇形：上前进 / 右右转 / 下后退 / 左左转 -->
                  {#each sectors as s (s.cmd)}
                    <g
                      class="seg-group {s.vert ? 'seg-v' : 'seg-h'} {activeDirection === s.cmd ? 'is-pressed' : ''}"
                      onclick={() => sendCommand(s.cmd)}
                      onkeydown={(e) => handlePadKey(s.cmd, e)}
                      role="button"
                      tabindex="0"
                      aria-label={s.label}
                    >
                      <path class="seg" d={s.d} />
                      <text x={s.lx} y={s.ly - 8} text-anchor="middle" class="seg-icon">{s.icon}</text>
                      <text x={s.lx} y={s.ly + 12} text-anchor="middle" class="seg-label">{s.label}</text>
                    </g>
                  {/each}

                  <!-- 中心停止按钮 -->
                  <g
                    class="stop-btn {activeDirection === 'stop' ? 'is-pressed' : ''}"
                    onclick={stopCommand}
                    onkeydown={(e) => handlePadKey('stop', e)}
                    role="button"
                    tabindex="0"
                    aria-label="停止"
                  >
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

            <!-- 姿态 / 任务控制 -->
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

              <!-- 开始巡检 -->
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

              <!-- 录制中指示 -->
              {#if inspection.recording}
                <div class="flex items-center justify-center gap-2 text-xs text-red-400 font-mono">
                  <span class="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
                  正在录制巡检视频...
                </div>
              {/if}

              <!-- 下载巡检产物：后端真实 url 优先，否则用本地 inspectionId 拼接兜底 -->
              <div class="flex gap-2">
                <a
                  href={inspection.video_url || (inspectionId ? `${downloadBase()}/api/download/video/${inspectionId}` : '#')}
                  download
                  onclick={() => notifyDownload('⬇️ 视频下载中，请稍候...')}
                  class="flex-1 py-2.5 rounded-xl text-sm font-medium text-center border border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan hover:bg-neon-cyan/20 transition-colors {inspection.video_url || inspectionId ? '' : 'opacity-50 cursor-not-allowed pointer-events-none'}"
                  aria-disabled={!inspection.video_url && !inspectionId}
                >
                  📹 下载巡检视频
                </a>

                <a
                  href={inspection.log_url || (inspectionId ? `${downloadBase()}/api/download/log/${inspectionId}` : '#')}
                  download
                  onclick={() => notifyDownload('⬇️ 日志下载中，请稍候...')}
                  class="flex-1 py-2.5 rounded-xl text-sm font-medium text-center border border-neon-purple/30 bg-neon-purple/10 text-neon-purple hover:bg-neon-purple/20 transition-colors {inspection.log_url || inspectionId ? '' : 'opacity-50 cursor-not-allowed pointer-events-none'}"
                  aria-disabled={!inspection.log_url && !inspectionId}
                >
                  📋 下载巡检日志
                </a>
              </div>

              {#if downloadNote}
                <p class="text-center text-xs text-slate-400 animate-pulse">{downloadNote}</p>
              {:else if !inspectionId && !inspection.video_url && !inspection.log_url}
                <p class="text-center text-xs text-slate-500">
                  暂无巡检记录，点击「开始巡检」并在巡检结束后即可下载视频与日志。
                </p>
              {:else if !inspectionFinished}
                <p class="text-center text-xs text-amber-300">巡检进行中，结束后即可下载。</p>
              {:else}
                <p class="text-center text-xs text-green-400">✅ 巡检已完成，可下载视频与日志。</p>
              {/if}
            </div>
          </div>
        </div>
      {/if}

    </div>
  </div>
</div>
<AlertModal />
<AlertTester />
<style>
  /* ============ 纯样式，无通信 ============ */

  /* ============ 环形扇形控制盘（SVG） ============ */
  .control-pad {
    width: 220px;
    height: 220px;
    margin: 0 auto;
    user-select: none;
  }
  .control-pad svg { display: block; }

  .seg-group,
  .stop-btn {
    cursor: pointer;
    outline: none;
    -webkit-tap-highlight-color: transparent;
  }
  .seg-group:focus-visible .seg,
  .stop-btn:focus-visible .stop-face {
    filter: brightness(1.12);
  }

  /* 扇形本体：上/下（前进/后退）蓝，左/右（左转/右转）青 */
  .seg {
    transition: fill 0.18s ease, filter 0.18s ease;
  }
  .seg-v .seg { fill: rgba(96, 165, 250, 0.14); }
  .seg-h .seg { fill: rgba(34, 211, 238, 0.14); }

  /* 悬停变亮 */
  .seg-v:hover .seg { fill: rgba(96, 165, 250, 0.3); }
  .seg-h:hover .seg { fill: rgba(34, 211, 238, 0.3); }
  .seg-group:hover .seg-icon,
  .seg-group:hover .seg-label { filter: brightness(1.25); }

  /* 图标与文字 */
  .seg-icon,
  .seg-label {
    pointer-events: none;
    font-family: inherit;
  }
  .seg-icon { font-size: 22px; font-weight: 700; }
  .seg-label { font-size: 11px; font-weight: 600; }
  .seg-v .seg-icon { fill: #93c5fd; }
  .seg-v .seg-label { fill: #60a5fa; }
  .seg-h .seg-icon { fill: #67e8f9; }
  .seg-h .seg-label { fill: #22d3ee; }

  /* 键盘按下：发光 + 变亮 */
  .seg-group.is-pressed .seg { filter: brightness(1.45) drop-shadow(0 0 10px rgba(147, 197, 253, 0.5)); }
  .seg-group.is-pressed.seg-v .seg { fill: rgba(96, 165, 250, 0.42); }
  .seg-group.is-pressed.seg-h .seg { fill: rgba(34, 211, 238, 0.42); }

  /* 中心停止按钮：简洁扁平鲜艳红色圆形（无 3D 质感） */
  .stop-btn {
    transform-box: view-box;
    transform-origin: 110px 110px;
    transition: transform 0.15s ease;
  }
  .stop-face {
    fill: #ef4444;
    transition: filter 0.15s ease;
  }

  /* 悬停：轻微放大 + 更亮 + 红色光晕 */
  .stop-btn:hover {
    transform: scale(1.08);
  }
  .stop-btn:hover .stop-face {
    filter: brightness(1.1) drop-shadow(0 0 14px rgba(239, 68, 68, 0.85));
  }

  /* 按下 / 键盘停止：轻微缩小 + 颜色加深 + 更强光晕 */
  .stop-btn:active,
  .stop-btn.is-pressed {
    transform: scale(0.92);
  }
  .stop-btn:active .stop-face,
  .stop-btn.is-pressed .stop-face {
    filter: brightness(0.88) saturate(1.25) drop-shadow(0 0 20px rgba(239, 68, 68, 0.95));
  }

  /* 波纹扩散光晕：半透明白色光圈，从中心向外扩散一圈 */
  .stop-ripple {
    fill: none;
    stroke: rgba(255, 255, 255, 0.65);
    stroke-width: 3;
    pointer-events: none;
    transform-box: view-box;
    transform-origin: 110px 110px;
    animation: stop-ripple 0.3s ease-out forwards;
  }
  @keyframes stop-ripple {
    0%   { transform: scale(1);   opacity: 0.9; }
    100% { transform: scale(2.4); opacity: 0; }
  }

  .stop-icon {
    font-size: 18px;
    fill: #ffffff;
    pointer-events: none;
    font-family: inherit;
  }
  .stop-label {
    font-size: 12px;
    font-weight: 700;
    fill: #ffffff;
    pointer-events: none;
    font-family: inherit;
  }

  /* 小芯片按钮（站立/坐下/急停） */
  .ctrl-chip {
    @apply px-3.5 py-1.5 rounded-lg text-xs font-medium
           bg-white/5 border border-white/10 text-slate-300
           hover:bg-white/10 hover:text-white transition-all duration-200
           active:scale-95;
  }
  .ctrl-chip-danger {
    @apply bg-red-400/10 border-red-400/30 text-red-400
           hover:bg-red-400/20;
  }
</style>