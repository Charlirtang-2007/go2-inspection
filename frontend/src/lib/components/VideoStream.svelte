<script lang="ts">
  // ============================================================
  // VideoStream 组件
  // 职责：显示视频流画面 / 加载中提示
  // 数据来源：父组件传入的 videoUrl
  // ============================================================

  // 从父组件接收 videoUrl
  let { videoUrl = '' } = $props();
</script>

<div class="card p-3 h-full flex flex-col">
  <!-- 卡片头：标题 + LIVE 徽章 -->
  <div class="flex items-center justify-between mb-2">
    <span class="text-sm font-medium text-slate-300">📷 实时监控</span>
    <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs
                 bg-neon-red/10 text-neon-red border border-neon-red/25">
      <span class="w-1.5 h-1.5 rounded-full bg-neon-red animate-pulse"></span>
      LIVE
    </span>
  </div>

  <!-- 视频区域：有地址显示画面，无地址显示搜索提示 -->
  <div class="aspect-video bg-ink-900 rounded-lg overflow-hidden flex items-center justify-center">
    {#if videoUrl}
      <img
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
</div>