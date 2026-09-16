/**
 * 后端发现服务
 * - Tauri 环境：调用 Rust mDNS 命令
 * - 浏览器环境：降级到环境变量
 */

let cachedUrl = '';

function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

export async function discoverBackend(): Promise<string> {
  if (cachedUrl) return cachedUrl;

  // Tauri 环境：调用 Rust
  if (isTauri()) {
    try {
      console.log('🔍 [Tauri] 调用 Rust mDNS...');
      const { invoke } = await import('@tauri-apps/api/core');
      const url = await invoke<string>('discover_backend');
      cachedUrl = url;
      console.log('✅ [Tauri] 发现后端:', url);
      return url;
    } catch (e) {
      console.warn('⚠️ [Tauri] mDNS 失败:', e);
    }
  }

  // 浏览器环境：用环境变量
  const envUrl = import.meta.env.VITE_API_BASE as string | undefined;
  if (envUrl) {
    cachedUrl = envUrl;
    return envUrl;
  }

  throw new Error('无法发现后端：既非 Tauri 环境，也没有配置 VITE_API_BASE');
}

export function clearBackendCache() {
  cachedUrl = '';
}