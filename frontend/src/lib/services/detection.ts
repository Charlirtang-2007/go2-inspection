/**
 * 异常检测服务
 * 定期轮询后端 /api/detection/anomaly 接口
 * 
 * 后端新返回格式：
 * {
 *   success: true,
 *   has_anomaly: true,
 *   anomalies: [
 *     { type: "smoke", confidence: 0.87, bbox: [...], timestamp: "...", image: "xxx.jpg" }
 *   ],
 *   notified: true,
 *   notify_channels: ["pushplus"],
 *   last_update: 1728483012.5
 * }
 */

import { logStore } from '$lib/stores/log';
import { alertStore, type AlertLevel } from '$lib/stores/alert';

/** 后端异常对象结构 */
export interface Anomaly {
  type: string;
  confidence: number;
  bbox: [number, number, number, number];
  timestamp: string;
  image?: string;   // 异常截图文件名
}

let lastAnomalyState = '';
let detectionTimer: number | null = null;

/** 类型 → 中文显示名 */
const TYPE_LABEL: Record<string, string> = {
  smoke: '烟雾',
  fire: '火焰',
  flame: '火焰',
  oil: '漏油',
  oil_leak: '漏油',
  drip: '滴漏',
};

function labelOf(type: string): string {
  return TYPE_LABEL[type] || type;
}

/** 判断紧急程度 */
function getLevel(anomalies: Anomaly[]): AlertLevel {
  const types = anomalies.map(a => a.type.toLowerCase());
  if (types.some(t => t.includes('fire') || t.includes('flame'))) return 'critical';
  if (types.some(t => t.includes('smoke'))) return 'warning';
  if (types.some(t => t.includes('oil') || t.includes('drip'))) return 'warning';
  return 'info';
}

/** 生成状态指纹，用于判断画面是否变化 */
function fingerprint(anomalies: Anomaly[]): string {
  return anomalies
    .map(a => `${a.type}:${a.confidence.toFixed(2)}`)
    .sort()
    .join('|');
}

async function checkOnce(backendBase: string) {
  if (!backendBase) return;

  try {
    const res = await fetch(`${backendBase}/api/detection/anomaly`);
    const data = await res.json();

    if (!data.success) return;

    const anomalies: Anomaly[] = data.anomalies || [];
    const currentState = fingerprint(anomalies);

    // 状态未变，跳过
    if (currentState === lastAnomalyState) return;

    if (data.has_anomaly && anomalies.length > 0) {
      const level = getLevel(anomalies);
      const labels = anomalies.map(a => labelOf(a.type));
      const maxConf = Math.max(...anomalies.map(a => a.confidence));

      // 1. 触发弹窗告警
      alertStore.push({
        level,
        type: labels.join('、'),
        area: '巡检区域 C',   // 暂时写死，后续可从后端传
        detail: `系统检测到 ${anomalies.length} 处异常（最高置信度 ${(maxConf * 100).toFixed(0)}%），请立即处理`,
        timestamp: new Date().toLocaleTimeString()
      });

      // 2. 写日志：检测到异常
      logStore.update(logs => [{
        time: new Date().toLocaleTimeString(),
        level: 'error',
        message: `⚠️ 检测到异常: ${labels.join('、')}（置信度 ${(maxConf * 100).toFixed(0)}%）`
      }, ...logs].slice(0, 200));

      // 3. 写日志：已通知
      if (data.notified && data.notify_channels?.length > 0) {
        logStore.update(logs => [{
          time: new Date().toLocaleTimeString(),
          level: 'info',
          message: `📱 已通过 ${data.notify_channels.join(' / ')} 通知值班人员`
        }, ...logs].slice(0, 200));
      }

      // 4. 如果有截图，可以在这里触发前端图片显示（后续接 UI 用）
      // 例如：alertStore.setImage(`${backendBase}/anomalies/${anomalies[0].image}`);
    } else if (lastAnomalyState !== '') {
      // 从异常恢复到正常
      logStore.update(logs => [{
        time: new Date().toLocaleTimeString(),
        level: 'success',
        message: '✅ 异常已恢复，画面正常'
      }, ...logs].slice(0, 200));
    }

    lastAnomalyState = currentState;
  } catch (e) {
    // 静默失败
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