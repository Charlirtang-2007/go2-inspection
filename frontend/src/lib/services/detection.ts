// frontend/src/lib/services/detection.ts
/**
 * 异常检测轮询服务
 *
 * 职责：
 * - 每 3 秒轮询 /api/detection/anomaly
 * - 状态变化时触发 alertStore（弹窗）
 * - 写 logStore（日志）
 *
 * 不负责：
 * - 推送（由后端 worker 直接触发）
 */
import { logStore } from '$lib/stores/log';
import { alertStore, type AlertLevel } from '$lib/stores/alert';

export interface Anomaly {
  type: string;
  confidence: number;
  bbox?: [number, number, number, number] | null;
  timestamp: string;
  image?: string;
  source?: string;
}

let lastAnomalyState = '';
let detectionTimer: number | null = null;

const TYPE_LABEL: Record<string, string> = {
  smoke: '烟雾',
  fire: '火焰',
  flame: '火焰',
  oil: '漏油',
  oil_leak: '漏油',
  drip: '滴漏',
  preset: '预设异常',
};

function labelOf(type: string): string {
  return TYPE_LABEL[type] || type;
}

function getLevel(anomalies: Anomaly[]): AlertLevel {
  const types = anomalies.map(a => a.type.toLowerCase());
  if (types.some(t => t.includes('fire') || t.includes('flame'))) return 'critical';
  if (types.some(t => t.includes('smoke'))) return 'warning';
  if (types.some(t => t.includes('oil') || t.includes('drip'))) return 'warning';
  return 'info';
}

function fingerprint(anomalies: Anomaly[]): string {
  return anomalies
    .map(a => `${a.type}:${(a.confidence || 0).toFixed(2)}`)
    .sort()
    .join('|');
}

async function checkOnce(backendBase: string) {
  if (!backendBase) {
    console.warn('[detection] backendBase 为空，跳过');
    return;
  }

  try {
    const res = await fetch(`${backendBase}/api/detection/anomaly`);
    const data = await res.json();

    console.log('[detection] 收到响应:', {
      has_anomaly: data.has_anomaly,
      anomalies_count: data.anomalies?.length || 0,
      last_update: data.last_update,
    });

    if (!data.success) return;

    const anomalies: Anomaly[] = data.anomalies || [];
    const currentState = fingerprint(anomalies);

    if (currentState === lastAnomalyState) return;

    if (data.has_anomaly && anomalies.length > 0) {
      const level = getLevel(anomalies);
      const labels = anomalies.map(a => labelOf(a.type));
      const maxConf = Math.max(...anomalies.map(a => a.confidence || 0));

      console.log('[detection] 触发告警:', anomalies);

      alertStore.push({
        level,
        type: labels.join('、'),
        area: '巡检区域',
        detail: `检测到 ${anomalies.length} 处异常（最高置信度 ${(maxConf * 100).toFixed(0)}%）`,
        timestamp: new Date().toLocaleTimeString(),
      });

      logStore.update(logs => [{
        time: new Date().toLocaleTimeString(),
        level: 'error',
        message: `⚠️ 检测到异常: ${labels.join('、')}（置信度 ${(maxConf * 100).toFixed(0)}%）`,
      }, ...logs].slice(0, 200));

    } else if (lastAnomalyState !== '') {
      logStore.update(logs => [{
        time: new Date().toLocaleTimeString(),
        level: 'success',
        message: '✅ 异常已恢复，画面正常',
      }, ...logs].slice(0, 200));
    }

    lastAnomalyState = currentState;
  } catch (e) {
    console.error('[detection] 请求失败:', e);
  }
}

export function startDetectionPolling(getBackendBase: () => string, intervalMs = 3000) {
  stopDetectionPolling();
  detectionTimer = window.setInterval(() => {
    checkOnce(getBackendBase());
  }, intervalMs);
  console.log('🔍 异常检测轮询已启动（间隔', intervalMs, 'ms）');
}

export function stopDetectionPolling() {
  if (detectionTimer) {
    clearInterval(detectionTimer);
    detectionTimer = null;
    console.log('🔍 异常检测轮询已停止');
  }
  lastAnomalyState = '';
}