<script lang="ts">
  // ============================================================
  // VideoStream 组件
  // 职责：显示视频流画面 / 加载中提示，并提供全屏、画中画
  // 数据来源：父组件传入的 videoUrl（MJPEG 流地址）
  // ============================================================
  import { onMount, onDestroy } from 'svelte';
  import type { WebviewWindow } from '@tauri-apps/api/webviewWindow';
  import { anomalyStore, inspectionStore, formatTimestamp, type AnomalyEvent } from '$lib/stores/log';

  let { videoUrl = '' } = $props();

  // 画中画降级小窗的 label（Tauri WebviewWindow）
  const PIP_LABEL = 'pip';

  // ---- 元素引用 ----
  let cardEl = $state<HTMLDivElement | null>(null);
  let imgEl = $state<HTMLImageElement | null>(null);

  // ---- 响应式状态 ----
  let isFullscreen = $state(false);
  let isPip = $state(false);
  let pipAvailable = $state(false);     // 是否有可用画中画方案（Tauri 或浏览器 window.open）
  let streamReady = $state(false);      // 视频流是否已加载出有效帧
  let pipMessage = $state('');          // 用户可见的瞬时提示

  // ---- 画中画资源 ----
  let pipWindow: WebviewWindow | null = null;   // Tauri 降级窗口引用
  let browserPipWindow: Window | null = null;   // 浏览器 window.open 小窗引用
  let browserPipTimer: number | null = null;    // 轮询检测浏览器小窗是否已关闭
  let pipMessageTimer: number | null = null;

  // ============================================================
  // 环境检测
  // ============================================================
  function isTauri(): boolean {
    return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
  }

  // ============================================================
  // 用户可见提示（自动消失）
  // ============================================================
  function showPipMessage(msg: string) {
    pipMessage = msg;
    if (pipMessageTimer) window.clearTimeout(pipMessageTimer);
    pipMessageTimer = window.setTimeout(() => {
      pipMessage = '';
      pipMessageTimer = null;
    }, 3000);
  }

  // ============================================================
  // 全屏
  // ============================================================
  function toggleFullscreen() {
    if (!cardEl) return;

    if (document.fullscreenElement) {
      document.exitFullscreen?.();
      return;
    }

    const el = cardEl as HTMLDivElement & {
      webkitRequestFullscreen?: () => void;
    };

    if (el.requestFullscreen) {
      el.requestFullscreen().catch(() => {
        console.warn('全屏被拒绝');
      });
    } else if (el.webkitRequestFullscreen) {
      el.webkitRequestFullscreen();
    } else {
      console.warn('当前浏览器不支持全屏');
    }
  }

  function onFullscreenChange() {
    isFullscreen = !!document.fullscreenElement;
  }

  // ============================================================
  // Tauri / WebView2：始终置顶、不占任务栏的独立小窗。
  // 直接把流地址作为页面打开会以“单张图”居中渲染，全屏时四周留黑边；
  // 这里把流包进一个铺满窗口、object-fit: cover 的 HTML，全屏可填满屏幕。
  // ============================================================
  function buildPipHtml(): string {
    const src = String(videoUrl)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;');
    return `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>画中画</title>
  <style>
    html, body {
      margin: 0;
      padding: 0;
      width: 100%;
      height: 100%;
      background: #000;
      overflow: hidden;
    }
    img {
      width: 100vw;
      height: 100vh;
      object-fit: cover;
      display: block;
    }
  </style>
</head>
<body>
  <img src="${src}" alt="机器狗监控画面">
  <div id="time-overlay" style="position:fixed; left:8px; bottom:8px; padding:4px 8px; background:rgba(0,0,0,0.6); color:#fff; font-family:monospace; font-size:12px; border-radius:4px; z-index:9999;"></div>
  <script>
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' || e.key === 'Esc') {
        try {
          if (window.__TAURI_INTERNALS__ && window.__TAURI_INTERNALS__.invoke) {
            window.__TAURI_INTERNALS__.invoke('plugin:window|close');
          } else {
            window.close();
          }
        } catch (err) {
          window.close();
        }
      }
    });

    // 实时时间（左下角，每秒更新）
    (function () {
      function updateTime() {
        var d = new Date();
        var pad = function (n) { return String(n).padStart(2, '0'); };
        document.getElementById('time-overlay').textContent =
          d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' +
          pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
      }
      updateTime();
      setInterval(updateTime, 1000);
    })();
  <\/script>
</body>
</html>`;
  }

  async function openTauriWindow(): Promise<boolean> {
    try {
      // 动态加载，避免在纯浏览器环境下引入 Tauri 模块
      const { WebviewWindow: WW } = await import('@tauri-apps/api/webviewWindow');
      const pipUrl = 'data:text/html;charset=utf-8,' + encodeURIComponent(buildPipHtml());

      const win = new WW(PIP_LABEL, {
        url: pipUrl,
        title: '画中画',
        width: 660,
        height: 540,
        resizable: true,
        alwaysOnTop: true,
        skipTaskbar: true,
        focus: true
      });

      pipWindow = win;

      // 用户手动关闭小窗时同步状态，避免按钮卡在“退出画中画”
      win.onCloseRequested(() => {
        pipWindow = null;
        isPip = false;
      }).catch(() => {});

      win.once('tauri://error', (e) => {
        console.error('[PiP] Tauri 窗口创建失败，详细错误:', e);
        console.error('[PiP] 请检查 src-tauri/capabilities/default.json 是否包含 core:webview:allow-create-webview-window 权限');
        pipWindow = null;
        isPip = false;
        showPipMessage('画中画窗口创建失败');
      }).catch(() => {});

      isPip = true;
      return true;
    } catch (e) {
      console.error('[PiP] Tauri 独立小窗打开失败，详细错误:', e);
      console.error('[PiP] 请检查 src-tauri/capabilities/default.json 是否包含 core:webview:allow-create-webview-window 权限');
      showPipMessage('画中画窗口创建失败');
      return false;
    }
  }

  // 普通浏览器：用 window.open 打开独立窗口显示 MJPEG 流（最稳定方案）。
  function openBrowserPip(): void {
    const win = window.open(
      '',
      'go2-pip',
      'width=640,height=480,alwaysRaised=yes,menubar=no,toolbar=no,location=no'
    );

    if (!win) {
      console.error('[PiP] 失败: 浏览器拦截了弹窗');
      showPipMessage('浏览器拦截了画中画窗口，请允许弹出窗口');
      return;
    }

    // HTML 转义，避免 videoUrl 里的特殊字符破坏标签
    const src = String(videoUrl)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    const html = `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>画中画 - Go2 智能巡检</title>
  <style>
    html, body { margin: 0; padding: 0; width: 100%; height: 100%; background: #000; overflow: hidden; }
    img { width: 100vw; height: 100vh; object-fit: contain; display: block; }
  </style>
</head>
<body>
  <img src="${src}" alt="机器狗监控画面">
  <div id="time-overlay" style="position:fixed; left:8px; bottom:8px; padding:4px 8px; background:rgba(0,0,0,0.6); color:#fff; font-family:monospace; font-size:12px; border-radius:4px; z-index:9999;"></div>
  <script>
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' || e.key === 'Esc') {
        try {
          if (window.__TAURI_INTERNALS__ && window.__TAURI_INTERNALS__.invoke) {
            window.__TAURI_INTERNALS__.invoke('plugin:window|close');
          } else {
            window.close();
          }
        } catch (err) {
          window.close();
        }
      }
    });

    // 实时时间（左下角，每秒更新）
    (function () {
      function updateTime() {
        var d = new Date();
        var pad = function (n) { return String(n).padStart(2, '0'); };
        document.getElementById('time-overlay').textContent =
          d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' +
          pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
      }
      updateTime();
      setInterval(updateTime, 1000);
    })();
  <\/script>
</body>
</html>`;

    try {
      win.document.open();
      win.document.write(html);
      win.document.close();
    } catch (e) {
      // 跨域限制等导致 document 不可写时，退化为直接加载流地址
      console.warn('[PiP] document.write 失败，改为直接加载视频流:', e);
      try {
        win.location.href = videoUrl;
      } catch (e2) {
        console.error('[PiP] 失败:', e2);
        showPipMessage('画中画启动失败，请检查控制台');
        return;
      }
    }

    browserPipWindow = win;
    isPip = true;
    console.log('[PiP] 已打开独立窗口');

    // 轮询检测小窗是否被用户关闭，及时重置状态
    if (browserPipTimer) window.clearInterval(browserPipTimer);
    browserPipTimer = window.setInterval(() => {
      if (win.closed) {
        if (browserPipTimer) window.clearInterval(browserPipTimer);
        browserPipTimer = null;
        browserPipWindow = null;
        isPip = false;
      }
    }, 500);
  }

  // ============================================================
  // 统一关闭画中画（原生 PiP / Tauri 小窗 / 浏览器弹窗）
  // ============================================================
  async function closePip() {
    if (!isPip) return;

    // 原生浏览器画中画（若当前环境/某种路径下存在）
    if (document.pictureInPictureElement) {
      try {
        await document.exitPictureInPicture();
      } catch (e) {
        console.warn('退出原生画中画失败:', e);
      }
    }

    // Tauri 独立小窗
    if (pipWindow) {
      try {
        await pipWindow.close();
      } catch (e) {
        console.warn('关闭画中画窗口失败:', e);
      }
      pipWindow = null;
    }

    // 浏览器 window.open 弹窗
    if (browserPipWindow && !browserPipWindow.closed) {
      browserPipWindow.close();
    }
    browserPipWindow = null;

    if (browserPipTimer) {
      window.clearInterval(browserPipTimer);
      browserPipTimer = null;
    }

    isPip = false;
  }

  // ESC 关闭画中画：不 preventDefault，避免影响全屏退出等默认行为
  function handlePipKeydown(e: KeyboardEvent) {
    if (e.key !== 'Escape' && e.key !== 'Esc') return;
    if (!isPip) return;

    // 已开启但实际资源已关闭（如用户手动关掉弹窗）→ 仅同步状态
    const nativeActive = !!document.pictureInPictureElement;
    const tauriActive = !!pipWindow;
    const browserActive = !!browserPipWindow && !browserPipWindow.closed;
    if (!nativeActive && !tauriActive && !browserActive) {
      isPip = false;
      if (browserPipTimer) {
        window.clearInterval(browserPipTimer);
        browserPipTimer = null;
      }
      return;
    }

    void closePip();
  }

  // ============================================================
  // 统一切换入口
  // ============================================================
  async function togglePip() {
    console.log('[PiP] 点击', { isTauri: isTauri(), streamReady, hasWindow: !!browserPipWindow });

    // 未就绪：给出明确提示，不静默失败
    if (!streamReady) {
      showPipMessage('视频流未连接');
      return;
    }

    // 已打开：关闭
    if (isPip) {
      await closePip();
      return;
    }

    // 打开：按运行环境选择方案
    if (isTauri()) {
      await openTauriWindow();
    } else {
      openBrowserPip();
    }
  }

  // ============================================================
  // 生命周期
  // ============================================================
  onMount(() => {
    document.addEventListener('fullscreenchange', onFullscreenChange);
    window.addEventListener('keydown', handlePipKeydown);

    // 能力检测：Tauri 用独立小窗，普通浏览器用 window.open
    pipAvailable = isTauri() || typeof window.open === 'function';

    // 实时时钟：每秒刷新
    nowTime = formatNow();
    timeTimer = window.setInterval(() => (nowTime = formatNow()), 1000);

    // 订阅异常事件：驱动报警 UI
    anomalyUnsub = anomalyStore.subscribe((ev) => {
      if (ev) triggerAlert(ev);
    });

    // 订阅巡检状态：录制中指示
    inspectionUnsub = inspectionStore.subscribe((s) => {
      recording = !!s.recording;
    });
  });

  onDestroy(() => {
    document.removeEventListener('fullscreenchange', onFullscreenChange);
    window.removeEventListener('keydown', handlePipKeydown);

    if (timeTimer) {
      window.clearInterval(timeTimer);
      timeTimer = null;
    }

    if (anomalyUnsub) anomalyUnsub();
    if (inspectionUnsub) inspectionUnsub();
    stopAlarm();
    if (alertTimer) {
      window.clearTimeout(alertTimer);
      alertTimer = null;
    }
    if (audioCtx) {
      audioCtx.close().catch(() => {});
      audioCtx = null;
    }

    if (pipMessageTimer) {
      window.clearTimeout(pipMessageTimer);
      pipMessageTimer = null;
    }

    // 关闭 Tauri 降级小窗
    if (pipWindow) pipWindow.close().catch(() => {});

    // 关闭浏览器小窗并清理轮询定时器
    if (browserPipWindow) browserPipWindow.close();
    if (browserPipTimer) {
      window.clearInterval(browserPipTimer);
      browserPipTimer = null;
    }

    if (document.fullscreenElement === cardEl) {
      document.exitFullscreen?.();
    }
  });

  // 视频地址变化时重置就绪标记；真实帧到达后由 img 的 onload 置回 true
  $effect(() => {
    if (!videoUrl) streamReady = false;
  });

  function btnClass(active: boolean) {
    return `p-1.5 rounded-lg border transition-all duration-200 active:scale-95 ${
      active
        ? 'bg-neon-cyan/10 border-neon-cyan/30 text-neon-cyan'
        : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10 hover:text-white'
    }`;
  }

  function pipButtonTitle(): string {
    if (!streamReady) return '视频流未连接';
    if (isPip) return '退出画中画';
    return '画中画';
  }

  // ============================================================
  // 实时时间显示（每秒更新，全屏与非全屏均显示）
  // ============================================================
  let nowTime = $state('');
  let timeTimer: number | null = null;

  function formatNow(): string {
    const d = new Date();
    const p = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  }

  // ============================================================
  // 异常报警（全屏弹幕 + 非全屏模态 + 频闪 + 报警声 + 静音）
  // ============================================================
  let activeAlert = $state<AnomalyEvent | null>(null);
  let bulletVisible = $state(true);      // 全屏弹幕是否可见（3 分钟后自动隐藏）
  let alertMuted = $state(false);        // 静音状态
  let recording = $state(false);         // 是否正在录制（来自巡检状态）
  let modalImage = $state<string | null>(null);  // 非全屏弹窗图片放大预览

  let audioCtx: AudioContext | null = null;
  let alarmInterval: number | null = null;
  let alertTimer: number | null = null;
  let anomalyUnsub: (() => void) | null = null;
  let inspectionUnsub: (() => void) | null = null;

  function startAlarm() {
    if (alertMuted || alarmInterval) return;
    try {
      audioCtx = audioCtx || new AudioContext();
      const ctx = audioCtx;
      if (ctx.state === 'suspended') ctx.resume().catch(() => {});
      const beep = () => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'square';
        osc.frequency.value = 880;
        gain.gain.value = 0.08;
        osc.connect(gain);
        gain.connect(ctx.destination);
        const t = ctx.currentTime;
        osc.start(t);
        osc.stop(t + 0.25);
      };
      alarmInterval = window.setInterval(beep, 1000);
    } catch (e) {
      console.warn('[报警] 报警声播放失败:', e);
    }
  }

  function stopAlarm() {
    if (alarmInterval) {
      window.clearInterval(alarmInterval);
      alarmInterval = null;
    }
  }

  function toggleMute() {
    alertMuted = !alertMuted;
    if (alertMuted) stopAlarm();
    else if (activeAlert) startAlarm();
  }

  function triggerAlert(ev: AnomalyEvent) {
    activeAlert = ev;
    bulletVisible = true;
    startAlarm();

    // 全屏弹幕 3 分钟后自动消失（日志仍保留）；
    // 非全屏模态需用户手动确认，不做自动关闭。
    if (alertTimer) window.clearTimeout(alertTimer);
    alertTimer = window.setTimeout(() => {
      if (isFullscreen) clearAlert();
      alertTimer = null;
    }, 3 * 60 * 1000);
  }

  function confirmAlert() {
    clearAlert();
  }

  function clearAlert() {
    activeAlert = null;
    bulletVisible = true;
    alertMuted = false;
    modalImage = null;
    stopAlarm();
    if (alertTimer) {
      window.clearTimeout(alertTimer);
      alertTimer = null;
    }
  }

  // 弹幕按紧急程度变色：高=红、中=橙、低=黄
  function alertLevelTheme(level: string): string {
    switch (level) {
      case '高': return 'border-red-500/80 text-red-300';
      case '中': return 'border-amber-500/80 text-amber-300';
      case '低': return 'border-yellow-400/80 text-yellow-300';
      default:  return 'border-red-500/80 text-red-300';
    }
  }
</script>

<div class="card p-3 flex flex-col video-card" bind:this={cardEl}>

  <!-- 卡片头：标题 + LIVE 徽章 + 全屏/画中画按钮 -->
  <div class="flex items-center justify-between mb-2">
    <span class="text-sm font-medium text-slate-300">📷 实时监控</span>

    <div class="flex items-center gap-2">
      <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs
                   bg-neon-red/10 text-neon-red border border-neon-red/25">
        <span class="w-1.5 h-1.5 rounded-full bg-neon-red animate-pulse"></span>
        LIVE
      </span>

      <!-- 全屏 -->
      <button
        type="button"
        onclick={toggleFullscreen}
        class={btnClass(isFullscreen)}
        title={isFullscreen ? '退出全屏' : '全屏'}
        aria-label={isFullscreen ? '退出全屏' : '全屏'}
      >
        {#if isFullscreen}
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="w-4 h-4">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 9V4.5M9 9H4.5M9 9 3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0 0 5.25 5.25" />
          </svg>
        {:else}
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="w-4 h-4">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15m11.25 5.25v-4.5m0 4.5h-4.5m4.5 0L15 15m5.25-11.25v4.5m0-4.5h-4.5m4.5 0L15 9" />
          </svg>
        {/if}
      </button>

      <!-- 画中画（有可用方案时显示；未就绪时点击给出提示） -->
      {#if pipAvailable}
        <button
          type="button"
          onclick={togglePip}
          class={btnClass(isPip)}
          title={pipButtonTitle()}
          aria-label={pipButtonTitle()}
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.6" stroke="currentColor" class="w-4 h-4">
            <rect x="2.75" y="5.5" width="18.5" height="13" rx="2.5" />
            <path d="M9.5 14h7.25a1.25 1.25 0 0 1 0 2.5H9.5a1.25 1.25 0 0 1 0-2.5Z" fill="currentColor" stroke="none" />
          </svg>
        </button>
      {/if}
    </div>
  </div>

  <!-- 视频区域：有地址显示画面，无地址显示搜索提示 -->
  <div class="video-area relative flex-1 min-h-0 bg-ink-900 rounded-lg overflow-hidden flex items-center justify-center">
    {#if videoUrl}
      <img
        bind:this={imgEl}
        src={videoUrl}
        alt="机器狗摄像头画面"
        class="w-full h-full object-cover block"
        onload={() => streamReady = true}
        onerror={() => streamReady = false}
      />
    {:else}
      <div class="text-slate-500 text-sm text-center px-4">
        <p class="text-2xl mb-2">🔍</p>
        <p>正在搜索后端服务...</p>
        <p class="text-xs mt-1 text-slate-600">请确保笔记本与AI机台在同一局域网</p>
      </div>
    {/if}

    {#if pipMessage}
      <div class="absolute bottom-2 inset-x-0 flex justify-center px-3 pointer-events-none">
        <span class="px-3 py-1.5 rounded-lg bg-ink-900/90 border border-white/10 text-xs text-amber-300 shadow-lg">
          {pipMessage}
        </span>
      </div>
    {/if}

    <!-- 异常报警：红色边框频闪覆盖层（全屏与非全屏均显示，直到确认/报警结束） -->
    {#if activeAlert}
      <div class="alert-flash absolute inset-0 pointer-events-none"></div>
    {/if}

    <!-- 录制中徽章（左上角） -->
    {#if recording}
      <div class="absolute top-2 left-2 flex items-center gap-1.5 px-2 py-1 rounded-md bg-red-600/80 text-white text-xs font-semibold shadow-lg">
        <span class="w-2 h-2 rounded-full bg-white animate-pulse"></span>
        REC 录制中
      </div>
    {/if}

    <!-- 实时时间（左下角，半透明） -->
    <div class="absolute bottom-2 left-2 px-2.5 py-1 rounded-md bg-black/60 text-white text-xs font-mono tabular-nums pointer-events-none select-none">
      {nowTime}
    </div>

    <!-- 全屏弹幕（右上角，3 分钟后自动消失） -->
    {#if isFullscreen && activeAlert && bulletVisible}
      <div class="bullet absolute top-3 right-3 max-w-xs px-3 py-2 rounded-lg bg-ink-900/85 border {alertLevelTheme(activeAlert.level)} text-xs shadow-lg pointer-events-none">
        <div class="flex items-center gap-1.5 font-semibold">
          <span>🚨 {activeAlert.type}告警</span>
          <span class="rounded bg-white/10 px-1.5 py-0.5">{activeAlert.level}级</span>
        </div>
        <div class="mt-0.5 text-white/80">区域：{activeAlert.area}</div>
      </div>
    {/if}

    <!-- 一键静音按钮（全屏报警进行时悬浮） -->
    {#if isFullscreen && activeAlert}
      <button
        type="button"
        onclick={toggleMute}
        class="absolute bottom-3 right-3 px-2.5 py-1.5 rounded-md bg-black/60 border border-white/20 text-white text-xs hover:bg-black/80 transition-colors"
        title={alertMuted ? '取消静音' : '一键静音'}
      >
        {alertMuted ? '🔇 已静音' : '🔊 静音'}
      </button>
    {/if}
  </div>

  <!-- 非全屏：异常报警模态弹窗（需用户确认才能关闭） -->
  {#if !isFullscreen && activeAlert}
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div class="w-full max-w-sm rounded-2xl border border-red-500/30 bg-ink-900 p-5 shadow-2xl">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-2xl">🚨</span>
          <h3 class="text-lg font-bold text-white">异常报警</h3>
        </div>
        <div class="space-y-1.5 text-sm text-slate-300 mb-4">
          <p>异常类型：<span class="text-red-400 font-medium">{activeAlert.type}</span></p>
          <p>紧急程度：<span class="text-amber-300 font-medium">{activeAlert.level}</span></p>
          <p>区域：<span class="text-neon-cyan font-medium">{activeAlert.area}</span></p>
          <p>时间：<span class="font-mono">{formatTimestamp(activeAlert.timestamp)}</span></p>
        </div>
        {#if activeAlert.image}
          <button
            type="button"
            class="w-full mb-4 group relative rounded-lg overflow-hidden border border-white/10"
            onclick={() => (modalImage = activeAlert!.image)}
            aria-label="放大预览异常图片"
          >
            <img src={activeAlert.image} alt="异常画面" class="w-full object-cover max-h-48" />
            <span class="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/60 text-white text-[10px] opacity-0 group-hover:opacity-100 transition-opacity">
              🔍 点击放大
            </span>
          </button>
        {/if}
        <div class="flex items-center gap-2">
          <button
            type="button"
            onclick={toggleMute}
            class="flex-1 py-2.5 rounded-xl text-sm font-medium border border-white/10 bg-white/5 text-slate-200 hover:bg-white/10 transition-colors"
          >
            {alertMuted ? '🔇 取消静音' : '🔊 静音'}
          </button>
          <button
            type="button"
            onclick={confirmAlert}
            class="flex-1 py-2.5 rounded-xl text-sm font-semibold bg-red-500 text-white hover:bg-red-400 transition-colors"
          >
            确认
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- 异常图片放大预览（lightbox） -->
  {#if modalImage}
    <div class="fixed inset-0 z-[60] flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <button
        type="button"
        class="absolute inset-0 w-full h-full bg-black/80 backdrop-blur-sm"
        aria-label="关闭预览"
        onclick={() => (modalImage = null)}
      ></button>
      <div class="relative max-w-3xl w-full">
        <img src={modalImage} alt="异常画面放大" class="w-full rounded-xl border border-white/10" />
        <button
          type="button"
          class="mt-3 px-3 py-1.5 rounded-lg bg-white/10 text-white text-sm hover:bg-white/20"
          onclick={() => (modalImage = null)}
        >
          关闭
        </button>
      </div>
    </div>
  {/if}
</div>

<style>
  /* 全屏时让卡片铺满屏幕，视频区域尽量填充并保持宽高比 */
  .video-card:fullscreen {
    width: 100vw;
    height: 100vh;
    border-radius: 0;
    background: #020617;
    padding: 1rem;
  }
  .video-card:fullscreen .video-area {
    flex: 1 1 auto;
    aspect-ratio: auto;
    min-height: 0;
  }

  /* 异常报警：红色边框与光晕频闪 */
  .alert-flash {
    border: 3px solid #ef4444;
    box-shadow:
      inset 0 0 32px rgba(239, 68, 68, 0.45),
      0 0 24px rgba(239, 68, 68, 0.55);
    animation: alert-flash 0.6s ease-in-out infinite;
  }
  @keyframes alert-flash {
    0%, 100% { border-color: #ef4444; box-shadow: inset 0 0 32px rgba(239,68,68,0.45), 0 0 24px rgba(239,68,68,0.55); }
    50%      { border-color: #fca5a5; box-shadow: inset 0 0 48px rgba(239,68,68,0.75), 0 0 40px rgba(239,68,68,0.85); }
  }

  /* 全屏弹幕入场动效 */
  .bullet {
    animation: bullet-in 0.35s ease-out;
  }
  @keyframes bullet-in {
    from { opacity: 0; transform: translateX(24px); }
    to   { opacity: 1; transform: translateX(0); }
  }
</style>