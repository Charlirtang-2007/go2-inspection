<script lang="ts">
  // ============================================================
  // VideoStream 组件
  // 职责：显示视频流画面 / 加载中提示，并提供全屏、画中画
  // 数据来源：父组件传入的 videoUrl（MJPEG 流地址）
  // ============================================================
  import FullscreenAlert from '$lib/components/FullscreenAlert.svelte';
  import { onMount, onDestroy } from 'svelte';
  import { isFullscreen as globalFullscreen, alertStore } from '$lib/stores/alert';
  import type { WebviewWindow } from '@tauri-apps/api/webviewWindow';

  let { videoUrl = '' } = $props();

  const PIP_LABEL = 'pip';

  // ---- 元素引用 ----
  let cardEl = $state<HTMLDivElement | null>(null);
  let imgEl = $state<HTMLImageElement | null>(null);
  let canvasEl = $state<HTMLCanvasElement | null>(null);
  let pipVideoEl = $state<HTMLVideoElement | null>(null);

  // ---- 响应式状态 ----
  let isFullscreen = $state(false);
  let isPip = $state(false);
  let pipAvailable = $state(false);
  let streamReady = $state(false);
  let pipMessage = $state('');

  // ---- 时间水印 ----
  let currentTime = $state('');
  let currentDate = $state('');
  let timeTimer: number | null = null;

  // ---- 画中画资源 ----
  let pipStream: MediaStream | null = null;
  let rafId: number | null = null;
  let pipWindow: WebviewWindow | null = null;
  let pipMessageTimer: number | null = null;

  // ============================================================
  // 时间水印：每秒更新
  // ============================================================
  function updateTime() {
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');

    currentTime = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
    currentDate = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  }

  // ============================================================
  // 环境/能力检测
  // ============================================================
  function isTauri(): boolean {
    return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
  }

  function supportsNativePip(): boolean {
    return (
      typeof document !== 'undefined' &&
      typeof HTMLVideoElement !== 'undefined' &&
      document.pictureInPictureEnabled === true &&
      typeof HTMLVideoElement.prototype.requestPictureInPicture === 'function'
    );
  }

  // ============================================================
  // 用户可见提示
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
    }
  }

  function onFullscreenChange() {
    const wasFullscreen = isFullscreen;
    isFullscreen = !!document.fullscreenElement;
    globalFullscreen.set(isFullscreen);

    // 从全屏 → 非全屏：视为用户"已知晓"，自动确认全屏来源的告警
    if (wasFullscreen && !isFullscreen) {
      alertStore.confirmAllBySource('fullscreen');
      console.log('✅ 退出全屏，已自动确认全屏告警');
    }
  }

  // ============================================================
  // 画中画相关（保持不变）
  // ============================================================
  function drawFrame() {
    const img = imgEl;
    const canvas = canvasEl;
    if (!img || !canvas) {
      rafId = null;
      return;
    }

    const w = img.naturalWidth || canvas.width || 640;
    const h = img.naturalHeight || canvas.height || 480;
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }

    const ctx = canvas.getContext('2d');
    if (ctx) ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    rafId = requestAnimationFrame(drawFrame);
  }

  function startNativePip() {
    if (!canvasEl || !pipVideoEl || !imgEl) return;

    if (typeof canvasEl.captureStream !== 'function') {
      showPipMessage('当前环境不支持画中画');
      return;
    }

    canvasEl.width = imgEl.naturalWidth || canvasEl.width || 640;
    canvasEl.height = imgEl.naturalHeight || canvasEl.height || 480;
    drawFrame();
    if (rafId == null) rafId = requestAnimationFrame(drawFrame);

    pipStream = canvasEl.captureStream(30);
    pipVideoEl.srcObject = pipStream;
    pipVideoEl.muted = true;
    pipVideoEl.playsInline = true;

    pipVideoEl.play().catch(() => {});

    pipVideoEl
      .requestPictureInPicture()
      .then(() => {
        isPip = true;
        if (rafId == null) rafId = requestAnimationFrame(drawFrame);
      })
      .catch((e: unknown) => {
        console.error('画中画启动失败:', e);
        teardownPip();
        showPipMessage(pipErrorMessage(e));
      });
  }

  function pipErrorMessage(e: unknown): string {
    const name = e instanceof DOMException ? e.name : '';
    if (name === 'NotAllowedError') return '画中画需要用户手势触发，请重试';
    if (name === 'NotSupportedError' || name === 'InvalidStateError') return '当前环境不支持画中画';
    return '画中画启动失败';
  }

  async function openTauriPip() {
    const { WebviewWindow: WW } = await import('@tauri-apps/api/webviewWindow');

    const win = new WW(PIP_LABEL, {
      url: videoUrl,
      title: '画中画',
      width: 660,
      height: 540,
      resizable: true,
      alwaysOnTop: true,
      skipTaskbar: true,
      focus: true
    });

    pipWindow = win;

    win.onCloseRequested(() => {
      pipWindow = null;
      isPip = false;
    }).catch(() => {});

    win.once('tauri://error', (e) => {
      console.error('画中画窗口创建失败:', e);
      pipWindow = null;
      isPip = false;
      showPipMessage('画中画窗口创建失败');
    }).catch(() => {});

    isPip = true;
  }

  async function toggleTauriPip() {
    if (pipWindow) {
      try {
        await pipWindow.close();
      } catch (e) {
        console.warn('关闭画中画窗口失败:', e);
      }
      pipWindow = null;
      isPip = false;
      return;
    }

    try {
      await openTauriPip();
    } catch (e) {
      console.error('打开画中画窗口失败:', e);
      showPipMessage('当前环境不支持画中画');
    }
  }

  async function togglePip() {
    if (!streamReady) {
      showPipMessage('视频流未连接');
      return;
    }

    if (isTauri()) {
      await toggleTauriPip();
      return;
    }

    if (isPip) {
      await exitPip();
    } else {
      startNativePip();
    }
  }

  async function exitPip() {
    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture();
      }
    } catch (e) {
      console.warn('退出画中画失败:', e);
    }
  }

  function teardownPip() {
    if (rafId != null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
    if (pipStream) {
      pipStream.getTracks().forEach((t) => t.stop());
      pipStream = null;
    }
    if (pipVideoEl) pipVideoEl.srcObject = null;
    isPip = false;
  }

  function onLeavePip() {
    teardownPip();
  }

  // ============================================================
  // 生命周期
  // ============================================================
  onMount(() => {
    document.addEventListener('fullscreenchange', onFullscreenChange);
    pipVideoEl?.addEventListener('leavepictureinpicture', onLeavePip);

    pipAvailable = isTauri() || supportsNativePip();

    // 启动时间水印更新
    updateTime();
    timeTimer = window.setInterval(updateTime, 1000);
  });

  onDestroy(() => {
    document.removeEventListener('fullscreenchange', onFullscreenChange);
    pipVideoEl?.removeEventListener('leavepictureinpicture', onLeavePip);

    if (pipMessageTimer) {
      window.clearTimeout(pipMessageTimer);
      pipMessageTimer = null;
    }

    // 清理时间水印定时器
    if (timeTimer !== null) {
      clearInterval(timeTimer);
      timeTimer = null;
    }

    teardownPip();

    if (pipWindow) pipWindow.close().catch(() => {});

    if (document.fullscreenElement === cardEl) {
      document.exitFullscreen?.();
    }
  });

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
    if (isTauri()) return '画中画（独立小窗）';
    return '画中画';
  }
</script>

<div class="card p-3 h-full flex flex-col video-card" bind:this={cardEl}>

  <!-- 卡片头 -->
  <div class="flex items-center justify-between mb-2 video-card-header">
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

      <!-- 画中画 -->
      {#if pipAvailable}
        <button
          type="button"
          onclick={togglePip}
          class={btnClass(isPip)}
          disabled={!streamReady}
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

  <!-- 视频区域 -->
  <div class="video-area relative aspect-video bg-ink-900 rounded-lg overflow-hidden flex items-center justify-center">
    {#if videoUrl}
      <img
        bind:this={imgEl}
        src={videoUrl}
        alt="机器狗摄像头画面"
        class="w-full h-full object-contain"
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

    <!-- ============================================================ -->
    <!-- 时间水印（左上角） -->
    <!-- ============================================================ -->
    {#if videoUrl}
      <div class="absolute top-2 left-2 z-40 pointer-events-none
                  px-2.5 py-1 rounded-md bg-black/60 backdrop-blur-sm
                  border border-white/10">
        <div class="text-white font-mono text-xs leading-tight tracking-wider">
          {currentTime}
        </div>
        <div class="text-slate-400 font-mono text-[10px] leading-tight">
          {currentDate}
        </div>
      </div>
    {/if}

    <!-- ============================================================ -->
    <!-- 录制中标识（右下角） -->
    <!-- ============================================================ -->
    {#if videoUrl}
      <div class="absolute bottom-2 right-2 z-40 pointer-events-none
                  px-2.5 py-1 rounded-md bg-red-600/85 backdrop-blur-sm
                  border border-red-400/40
                  flex items-center gap-1.5">
        <span class="w-2 h-2 rounded-full bg-white animate-pulse"></span>
        <span class="text-white text-xs font-semibold tracking-wider">
          REC 录制中
        </span>
      </div>
    {/if}

    <!-- 全屏告警弹幕 + 频闪 -->
    <FullscreenAlert active={isFullscreen} />

    {#if pipMessage}
      <div class="absolute bottom-2 inset-x-0 flex justify-center px-3 pointer-events-none z-[70]">
        <span class="px-3 py-1.5 rounded-lg bg-ink-900/90 border border-white/10 text-xs text-amber-300 shadow-lg">
          {pipMessage}
        </span>
      </div>
    {/if}
  </div>

  <!-- 画中画用的隐藏 canvas 与 video -->
  <canvas bind:this={canvasEl} class="hidden" aria-hidden="true"></canvas>
  <video bind:this={pipVideoEl} class="hidden" muted playsinline aria-hidden="true"></video>
</div>

<style>
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

  /* 全屏时时间水印和 REC 标识放大一些，方便远处看清楚 */
  .video-card:fullscreen .video-area :global(.absolute.top-2.left-2) {
    top: 1.5rem;
    left: 1.5rem;
    padding: 0.75rem 1.25rem;
  }
  .video-card:fullscreen .video-area :global(.absolute.bottom-2.right-2) {
    bottom: 1.5rem;
    right: 1.5rem;
    padding: 0.75rem 1.25rem;
  }
</style>