/**
 * 异常检测服务
 * 定期轮询后端 /api/detection/anomaly 接口
 */

import { logStore } from '$lib/stores/log';
import { alertStore, type AlertLevel } from '$lib/stores/alert';

let lastAnomalyState = '';
let detectionTimer: number | null = null;

/** 判断紧急程度 */
function getLevel(anomalies: string[]): AlertLevel {
  if (anomalies.some(a => a.includes('火焰'))) return 'critical';
  if (anomalies.some(a => a.includes('烟雾'))) return 'warning';
  if (anomalies.some(a => a.includes('漏油'))) return 'warning';
  return 'info';
}

async function checkOnce(backendBase: string) {
  if (!backendBase) return;

  try {
    const res = await fetch(`${backendBase}/api/detection/anomaly`);
    const data = await res.json();

    if (!data.success) return;

    const currentState = (data.anomalies || []).sort().join('|');

    // 状态未变，跳过
    if (currentState === lastAnomalyState) return;

    if (data.has_anomaly) {
      const anomalies: string[] = data.anomalies || [];
      const level = getLevel(anomalies);

      // 1. 触发弹窗告警
      alertStore.push({
        level,
        type: anomalies.join('、'),
        area: '巡检区域 C',   // 暂时写死，后续可从后端传
        detail: `系统检测到 ${anomalies.length} 处异常，请立即处理`,
        timestamp: new Date().toLocaleTimeString()
      });

      // 2. 写日志：检测到异常
      logStore.update(logs => [{
        time: new Date().toLocaleTimeString(),
        level: 'error',
        message: `⚠️ 检测到异常: ${anomalies.join('、')}`
      }, ...logs].slice(0, 200));

      // 3. 写日志：已通知
      if (data.notified && data.notify_channels?.length > 0) {
        logStore.update(logs => [{
          time: new Date().toLocaleTimeString(),
          level: 'info',
          message: `📱 已通过 ${data.notify_channels.join(' / ')} 通知值班人员`
        }, ...logs].slice(0, 200));
      }
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