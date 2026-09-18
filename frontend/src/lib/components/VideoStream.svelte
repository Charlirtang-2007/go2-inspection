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
        console.error('画中画窗口创建失败:', e);
        pipWindow = null;
        isPip = false;
        showPipMessage('画中画窗口创建失败');
      }).catch(() => {});

      isPip = true;
      return true;
    } catch (e) {
      console.error('Tauri 独立小窗打开失败:', e);
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
      isPip = false;

      if (pipWindow) {
        try {
          await pipWindow.close();
        } catch (e) {
          console.warn('关闭画中画窗口失败:', e);
        }
        pipWindow = null;
      }

      if (browserPipWindow) {
        browserPipWindow.close();
        browserPipWindow = null;
      }

      if (browserPipTimer) {
        window.clearInterval(browserPipTimer);
        browserPipTimer = null;
      }
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

    // 能力检测：Tauri 用独立小窗，普通浏览器用 window.open
    pipAvailable = isTauri() || typeof window.open === 'function';
  });

  onDestroy(() => {
    document.removeEventListener('fullscreenchange', onFullscreenChange);

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