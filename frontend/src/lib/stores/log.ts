import { writable } from 'svelte/store';

export interface LogEntry {
  time: string;             // 精确到秒的显示时间（YYYY-MM-DD HH:MM:SS）
  level: string;            // info | warning | error | success | anomaly
  message: string;
  // ---- 异常日志扩展字段 ----
  kind?: string;            // 'anomaly' | 'normal'（异常日志用 'anomaly'）
  type?: string;            // 异常类型（火焰/烟雾/漏油）
  location?: string;        // 具体位置（区域/点位）
  image?: string;           // 异常图片 base64 或 URL
  recordTime?: string;      // 录制时间戳，如 "00:02:35"
  severity?: 'high' | 'medium' | 'low';  // 紧急程度
  timestamp?: number;       // 绝对时间戳（秒）
}

export const logStore = writable<LogEntry[]>([]);

// ---- 异常报警事件（驱动全屏弹幕 / 非全屏模态 + 频闪 + 报警声） ----
export interface AnomalyEvent {
  type: string;       // 异常类型
  level: string;      // 紧急程度：高/中/低
  area: string;       // 大概区域
  image: string;      // 图片 URL 或 base64
  timestamp: number;  // 绝对时间戳（秒）
}

export const anomalyStore = writable<AnomalyEvent | null>(null);

// ---- 巡检录制 / 下载状态 ----
export interface InspectionState {
  recording: boolean;
  inspection_id: string;
  video_url: string;
  log_url: string;
}

export const inspectionStore = writable<InspectionState>({
  recording: false,
  inspection_id: '',
  video_url: '',
  log_url: ''
});

// 将秒级时间戳转为 HH:MM:SS（前端展示用）
export function formatTimestamp(ts?: number): string {
  if (!ts) return new Date().toLocaleTimeString();
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString('zh-CN', { hour12: false });
}

// 将秒级时间戳转为完整日期时间 YYYY-MM-DD HH:MM:SS
export function formatFullDateTime(ts?: number): string {
  const d = ts ? new Date(ts * 1000) : new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}