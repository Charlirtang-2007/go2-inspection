<script lang="ts">
  // ============================================================
  // VideoStream 组件
  // 职责：显示视频流画面 / 加载中提示，并提供全屏、画中画
  // 数据来源：父组件传入的 videoUrl（MJPEG 流地址）
  // ============================================================
  import { onMount, onDestroy } from 'svelte';
  import type { WebviewWindow } from '@tauri-apps/api/webviewWindow';

  let { videoUrl = '' } = $props();

  // 画中画降级小窗的 label（Tauri WebviewWindow）
  const PIP_LABEL = 'pip';

  // ---- 元素引用 ----
  let cardEl = $state<HTMLDivElement | null>(null);
  let imgEl = $state<HTMLImageElement | null>(null);
  let canvasEl = $state<HTMLCanvasElement | null>(null);
  let pipVideoEl = $state<HTMLVideoElement | null>(null);

  // ---- 响应式状态 ----
  let isFullscreen = $state(false);
  let isPip = $state(false);
  let pipAvailable = $state(false);     // 是否有任一可用画中画方案（原生或 Tauri 降级）
  let streamReady = $state(false);      // 视频流是否已加载出有效帧
  let pipMessage = $state('');          // 用户可见的瞬时提示

  // ---- 画中画资源 ----
  let pipStream: MediaStream | null = null;
  let rafId: number | null = null;
  let pipWindow: WebviewWindow | null = null;   // Tauri 降级窗口引用
  let pipMessageTimer: number | null = null;

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
  // 画中画（MJPEG 走 img → 隐藏 canvas.captureStream → 隐藏 video）
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
      console.warn('当前环境不支持 canvas.captureStream');
      showPipMessage('当前环境不支持画中画');
      return;
    }

    // 先画一帧并启动绘制循环，确保捕获流已有内容
    canvasEl.width = imgEl.naturalWidth || canvasEl.width || 640;
    canvasEl.height = imgEl.naturalHeight || canvasEl.height || 480;
    drawFrame();
    if (rafId == null) rafId = requestAnimationFrame(drawFrame);

    pipStream = canvasEl.captureStream(30);
    pipVideoEl.srcObject = pipStream;
    pipVideoEl.muted = true;
    pipVideoEl.playsInline = true;

    // 触发播放（fire-and-forget），不 await，确保 requestPictureInPicture
    // 仍在用户手势（click）的同步执行流内调用，避免 NotAllowedError。
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

  // ============================================================
  // Tauri / WebView2 降级：WebView2 不支持原生 PiP，
  // 用始终置顶的独立 WebviewWindow 直接加载 MJPEG 流（multipart/x-mixed-replace）。
  // ============================================================
  async function openTauriPip() {
    // 动态加载，避免在纯浏览器环境下引入 Tauri 模块
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

    // 用户手动关闭小窗时同步状态，避免按钮卡在“退出画中画”
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
      // 已打开则关闭（onCloseRequested 会重置 pipWindow / isPip）
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

  // ============================================================
  // 统一切换入口
  // ============================================================
  async function togglePip() {
    // 未就绪：给出明确提示（按钮虽禁用，仍保留兜底）
    if (!streamReady) {
      showPipMessage('视频流未连接');
      return;
    }

    // Tauri / WebView2：走独立小窗降级方案
    if (isTauri()) {
      await toggleTauriPip();
      return;
    }

    // 原生 PiP
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

  // 用户关闭原生画中画小窗时触发
  function onLeavePip() {
    teardownPip();
  }

  // ============================================================
  // 生命周期
  // ============================================================
  onMount(() => {
    document.addEventListener('fullscreenchange', onFullscreenChange);
    pipVideoEl?.addEventListener('leavepictureinpicture', onLeavePip);

    // 能力检测：
    // - Tauri/WebView2：原生 PiP 不可靠，走独立窗口降级，仍视为“可用”
    // - 普通浏览器：仅当支持原生 requestPictureInPicture 才视为可用
    pipAvailable = isTauri() || supportsNativePip();
  });

  onDestroy(() => {
    document.removeEventListener('fullscreenchange', onFullscreenChange);
    pipVideoEl?.removeEventListener('leavepictureinpicture', onLeavePip);

    if (pipMessageTimer) {
      window.clearTimeout(pipMessageTimer);
      pipMessageTimer = null;
    }

    // 回收画中画相关资源
    teardownPip();

    // 关闭 Tauri 降级小窗
    if (pipWindow) pipWindow.close().catch(() => {});

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
    if (isTauri()) return '画中画（独立小窗）';
    return '画中画';
  }
</script>

<div class="card p-3 h-full flex flex-col video-card" bind:this={cardEl}>

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

      <!-- 画中画（有可用方案时显示；视频流未就绪时禁用） -->
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

  <!-- 视频区域：有地址显示画面，无地址显示搜索提示 -->
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

    {#if pipMessage}
      <div class="absolute bottom-2 inset-x-0 flex justify-center px-3 pointer-events-none">
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
</style>