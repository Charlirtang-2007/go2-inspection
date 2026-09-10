<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { robotStore } from '$lib/stores/robot';
  import { logStore } from '$lib/stores/log';
  import { wsService } from '$lib/services/websocket';
  import LogViewer from '$lib/components/LogViewer.svelte';

  // ===== 响应式状态（Svelte 5） =====
  let status = $state('待命');
  let battery = $state(85);
  let task = $state('无');

  // ===== 巡检状态 =====
  let inspectionRunning = $state(false);
  let inspectionProgress = $state(0);
  let inspectionStep = $state('');
  let inspectionTimer: any = null;

  // ===== 订阅 robotStore =====
  const unsubscribe = robotStore.subscribe((value) => {
    status = value.status;
    battery = value.battery;
    task = value.current_task || '无';
  });

  // ===== 发送控制指令 =====
  function sendCommand(cmd: string) {
    console.log('📩 指令:', cmd);
    wsService.send({ type: 'command', data: { cmd } });
  }

  // ===== 开始巡检 =====
  function startInspection() {
    if (inspectionRunning) return;

    // 1. 通过 WebSocket 发送开始指令（后端若有实现会接管）
    wsService.send({ type: 'command', data: { cmd: 'start_inspection' } });

    // 2. 本地模拟巡检流程（若后端未实现，则前端模拟）
    startLocalSimulation();

    // 3. 更新本地状态
    inspectionRunning = true;
    inspectionProgress = 0;
    inspectionStep = '初始化巡检...';
    logStore.update(logs => [
      { time: new Date().toLocaleTimeString(), level: 'info', message: '🚀 开始巡检任务' },
      ...logs
    ]);
  }

  // ===== 本地模拟巡检（降级方案） =====
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
        // 巡检完成
        inspectionRunning = false;
        inspectionProgress = 100;
        inspectionStep = '✅ 巡检完成！';
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
      
      // 正常步骤日志
      logStore.update(logs => [
        { time: new Date().toLocaleTimeString(), level: 'info', message: `🔄 ${step.step}...` },
        ...logs
      ]);

      // 随机触发异常（在特定步骤增加报警）
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
    }, 2000); // 每2秒推进一个步骤
  }

  // ===== 紧急停止（同时停止巡检） =====
  function emergencyStop() {
    sendCommand('emergency_stop');
    if (inspectionTimer) {
      clearInterval(inspectionTimer);
      inspectionTimer = null;
    }
    inspectionRunning = false;
    inspectionProgress = 0;
    inspectionStep = '⛔ 已紧急停止';
    logStore.update(logs => [
      { time: new Date().toLocaleTimeString(), level: 'error', message: '⛔ 紧急停止触发，巡检中断' },
      ...logs
    ]);
  }

  onMount(() => {
    wsService.connect();
  });

  onDestroy(() => {
    wsService.disconnect();
    unsubscribe();
    if (inspectionTimer) clearInterval(inspectionTimer);
  });
</script>

<div class="min-h-screen bg-gray-50 p-4 flex flex-col">
  <!-- ===== 顶部标题 ===== -->
  <div class="flex-shrink-0 max-w-6xl mx-auto w-full mb-2">
    <div class="flex items-center justify-between">
      <h1 class="text-xl font-bold text-gray-800 flex items-center gap-2">
        <span class="text-2xl">🤖</span>
        Go2 巡检系统
      </h1>
      <span class="text-xs text-gray-400 bg-white px-2.5 py-0.5 rounded-full shadow-sm border border-gray-100">
        v2.0
      </span>
    </div>
  </div>

  <!-- ===== 主区域：状态 + 视频 ===== -->
  <div class="flex-shrink-0 max-w-6xl mx-auto w-full grid grid-cols-1 lg:grid-cols-3 gap-3">
    <div class="lg:col-span-1">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4 h-full">
        <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          📊 机器狗状态
        </h2>

        <div class="flex items-center justify-between py-1.5 border-b border-gray-50">
          <span class="text-gray-500 text-sm">状态</span>
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium 
            {status === '在线' ? 'bg-green-100 text-green-700' : 
             status === '巡检中' ? 'bg-blue-100 text-blue-700' : 
             'bg-gray-100 text-gray-600'}">
            <span class="w-1.5 h-1.5 rounded-full 
              {status === '在线' ? 'bg-green-500' : 
               status === '巡检中' ? 'bg-blue-500 animate-pulse' : 
               'bg-gray-400'}"></span>
            {status}
          </span>
        </div>

        <div class="py-1.5 border-b border-gray-50">
          <div class="flex justify-between items-center">
            <span class="text-gray-500 text-sm">🔋 电量</span>
            <span class="text-sm font-medium text-gray-700">{battery}%</span>
          </div>
          <div class="mt-0.5 w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div 
              class="h-full rounded-full transition-all duration-500 
                {battery > 60 ? 'bg-green-500' : battery > 30 ? 'bg-yellow-500' : 'bg-red-500'}"
              style="width: {battery}%">
            </div>
          </div>
        </div>

        <div class="flex items-center justify-between py-1.5">
          <span class="text-gray-500 text-sm">📋 当前任务</span>
          <span class="text-sm text-gray-700">{task}</span>
        </div>

        <!-- 巡检进度（仅在巡检中显示） -->
        {#if inspectionRunning || inspectionProgress > 0}
        <div class="mt-3 pt-3 border-t border-gray-100">
          <div class="flex justify-between items-center text-xs">
            <span class="text-gray-500">巡检进度</span>
            <span class="font-medium text-gray-700">{inspectionProgress}%</span>
          </div>
          <div class="mt-1 w-full h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              class="h-full rounded-full bg-blue-500 transition-all duration-500"
              style="width: {inspectionProgress}%">
            </div>
          </div>
          <p class="text-xs text-gray-600 mt-1">{inspectionStep}</p>
        </div>
        {/if}
      </div>
    </div>

    <div class="lg:col-span-2">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-3 h-full">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-medium text-gray-600">📷 实时监控</span>
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-600">
            <span class="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></span>
            LIVE
          </span>
        </div>
        <div class="aspect-video bg-gray-900 rounded-lg flex items-center justify-center text-gray-500 text-sm">
          <div class="text-center">
            <div class="text-4xl mb-1">🎥</div>
            <p class="text-xs">等待视频流...</p>
            <p class="text-xs text-gray-600 mt-0.5">后端启动后自动显示</p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ===== 底部区域：控制 + 日志 ===== -->
  <div class="flex-shrink-0 max-w-6xl mx-auto w-full mt-3 grid grid-cols-1 lg:grid-cols-3 gap-3">
    <div class="lg:col-span-1">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4 h-full flex flex-col">
        <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          🎮 运动控制
        </h2>

        <div class="flex flex-col items-center gap-1 max-w-[180px] mx-auto flex-1 justify-center">
          <button 
            onclick={() => sendCommand('forward')}
            class="w-14 h-14 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-600 font-bold text-sm transition-all hover:scale-105 active:scale-95 flex items-center justify-center border border-blue-100">
            ⬆ 前进
          </button>
          <div class="flex gap-1">
            <button 
              onclick={() => sendCommand('left')}
              class="w-14 h-14 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-600 font-bold text-sm transition-all hover:scale-105 active:scale-95 flex items-center justify-center border border-blue-100">
              ⬅ 左转
            </button>
            <button 
              onclick={() => sendCommand('stop')}
              class="w-14 h-14 rounded-xl bg-red-50 hover:bg-red-100 text-red-600 font-bold text-sm transition-all hover:scale-105 active:scale-95 flex items-center justify-center border border-red-100">
              ⏹ 停止
            </button>
            <button 
              onclick={() => sendCommand('right')}
              class="w-14 h-14 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-600 font-bold text-sm transition-all hover:scale-105 active:scale-95 flex items-center justify-center border border-blue-100">
              ➡ 右转
            </button>
          </div>
          <button 
            onclick={() => sendCommand('backward')}
            class="w-14 h-14 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-600 font-bold text-sm transition-all hover:scale-105 active:scale-95 flex items-center justify-center border border-blue-100">
            ⬇ 后退
          </button>
        </div>

        <!-- 功能按钮 -->
        <div class="flex flex-wrap gap-1.5 justify-center mt-2">
          <button 
            onclick={() => sendCommand('standup')}
            class="px-3 py-1 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs transition-colors">
            🧍 站立
          </button>
          <button 
            onclick={() => sendCommand('sit')}
            class="px-3 py-1 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs transition-colors">
            🪑 坐下
          </button>
          <button 
            onclick={emergencyStop}
            class="px-3 py-1 rounded-lg bg-red-500 hover:bg-red-600 text-white text-xs transition-colors">
            ⛔ 紧急停止
          </button>
        </div>

        <!-- 开始巡检按钮 -->
        <button 
          onclick={startInspection}
          disabled={inspectionRunning}
          class="mt-3 w-full py-2 rounded-lg text-sm font-medium transition-colors 
            {inspectionRunning ? 'bg-gray-300 text-gray-500 cursor-not-allowed' : 'bg-green-500 hover:bg-green-600 text-white'}"
        >
          {inspectionRunning ? '⏳ 巡检中...' : '🚀 开始巡检'}
        </button>
      </div>
    </div>

    <div class="lg:col-span-2">
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-4 h-full flex flex-col">
        <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          📋 巡检日志
        </h2>
        <LogViewer />
      </div>
    </div>
  </div>
</div>