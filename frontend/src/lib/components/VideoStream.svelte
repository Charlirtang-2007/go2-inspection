<script lang="ts">
  // ============================================================
  // VideoStream 组件
  // 职责：显示视频流画面 / 加载中提示，并提供全屏、画中画
  // 数据来源：父组件传入的 videoUrl
  // ============================================================
  import { onMount, onDestroy } from 'svelte';

  let { videoUrl = '' } = $props();

  // ---- 元素引用 ----
  let cardEl = $state<HTMLDivElement | null>(null);
  let imgEl = $state<HTMLImageElement | null>(null);
  let canvasEl = $state<HTMLCanvasElement | null>(null);
  let pipVideoEl = $state<HTMLVideoElement | null>(null);

  // ---- 响应式状态 ----
  let isFullscreen = $state(false);
  let isPip = $state(false);
  let pipSupported = $state(false);

  // ---- 画中画资源 ----
  let pipStream: MediaStream | null = null;
  let rafId: number | null = null;

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
  // 画中画（MJPEG 走 canvas.captureStream → 隐藏 video）
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

  async function startPip() {
    if (isPip || !canvasEl || !pipVideoEl) return;

    const img = imgEl;
    canvasEl.width = img?.naturalWidth || 640;
    canvasEl.height = img?.naturalHeight || 480;

    pipStream = canvasEl.captureStream(30);
    pipVideoEl.srcObject = pipStream;
    pipVideoEl.muted = true;

    try {
      await pipVideoEl.play();
      await pipVideoEl.requestPictureInPicture();
      isPip = true;
      if (rafId == null) rafId = requestAnimationFrame(drawFrame);
    } catch (e) {
      console.warn('画中画启动失败:', e);
      teardownPip();
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

  async function togglePip() {
    if (isPip) await exitPip();
    else await startPip();
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

  // 用户关闭画中画小窗时触发
  function onLeavePip() {
    teardownPip();
  }

  // ============================================================
  // 生命周期
  // ============================================================
  onMount(() => {
    document.addEventListener('fullscreenchange', onFullscreenChange);
    pipVideoEl?.addEventListener('leavepictureinpicture', onLeavePip);

    // 能力检测：仅当 <video> 支持 requestPictureInPicture 才显示画中画按钮
    pipSupported = typeof HTMLVideoElement.prototype.requestPictureInPicture === 'function';
  });

  onDestroy(() => {
    document.removeEventListener('fullscreenchange', onFullscreenChange);
    pipVideoEl?.removeEventListener('leavepictureinpicture', onLeavePip);

    // 组件销毁时回收画中画相关资源
    teardownPip();

    if (document.fullscreenElement === cardEl) {
      document.exitFullscreen?.();
    }
  });

  function btnClass(active: boolean) {
    return `p-1.5 rounded-lg border transition-all duration-200 active:scale-95 ${
      active
        ? 'bg-neon-cyan/10 border-neon-cyan/30 text-neon-cyan'
        : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10 hover:text-white'
    }`;
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

      <!-- 画中画（仅支持时显示） -->
      {#if pipSupported && videoUrl}
        <button
          type="button"
          onclick={togglePip}
          class={btnClass(isPip)}
          title={isPip ? '退出画中画' : '画中画'}
          aria-label={isPip ? '退出画中画' : '画中画'}
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
  <div class="video-area aspect-video bg-ink-900 rounded-lg overflow-hidden flex items-center justify-center">
    {#if videoUrl}
      <img
        bind:this={imgEl}
        src={videoUrl}
        alt="机器狗摄像头画面"
        class="w-full h-full object-contain"
      />
    {:else}
      <div class="text-slate-500 text-sm text-center px-4">
        <p class="text-2xl mb-2">🔍</p>
        <p>正在搜索后端服务...</p>
        <p class="text-xs mt-1 text-slate-600">请确保笔记本与AI机台在同一局域网</p>
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