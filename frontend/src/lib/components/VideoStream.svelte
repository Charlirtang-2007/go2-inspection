<script lang="ts">
  // 后端地址（改成你的AI机台IP）
  const API_BASE = import.meta.env.VITE_API_BASE || 'http://192.168.3.137:8000';
  const videoUrl = `${API_BASE}/api/camera/video?width=640&height=480`;

  let status = $state<'connecting' | 'connected' | 'error'>('connecting');

  function handleLoad() {
    status = 'connected';
  }

  function handleError() {
    status = 'error';
  }
</script>

<div class="video-container">
  <div class="video-header">
    <span>📷 实时监控</span>
    <span class="status-badge status-{status}">
      {status === 'connecting' ? '● 连接中' : status === 'connected' ? '● 已连接' : '● 连接失败'}
    </span>
  </div>

  <div class="video-body">
    {#if status === 'error'}
      <div class="error-placeholder">
        <span>⚠️ 视频流加载失败</span>
        <button onclick={() => location.reload()}>重试</button>
      </div>
    {:else}
      <img
        src={videoUrl}
        alt="机器狗摄像头画面"
        onload={handleLoad}
        onerror={handleError}
      />
    {/if}
  </div>
</div>

<style>
  .video-container {
    background: #1a1a2e;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  }

  .video-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    background: #252540;
    color: #fff;
    font-size: 14px;
  }

  .status-badge {
    font-size: 12px;
    padding: 2px 10px;
    border-radius: 12px;
  }

  .status-connecting { background: #ffc107; color: #333; }
  .status-connected { background: #28a745; color: #fff; }
  .status-error { background: #dc3545; color: #fff; }

  .video-body {
    display: flex;
    align-items: center;
    justify-content: center;
    background: #1a1a2e;
    min-height: 300px;
  }

  .video-body img {
    width: 100%;
    height: auto;
    max-height: 400px;
    object-fit: contain;
    display: block;
  }

  .error-placeholder {
    color: #888;
    text-align: center;
    padding: 40px;
  }

  .error-placeholder button {
    margin-top: 12px;
    padding: 6px 20px;
    background: #2196F3;
    color: #fff;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }
</style>