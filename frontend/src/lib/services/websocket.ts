import { writable } from 'svelte/store';
import { robotStore } from '$lib/stores/robot';
import { logStore, anomalyStore, inspectionStore, formatFullDateTime } from '$lib/stores/log';
import { discoverBackend } from '$lib/services/discovery';

type WSMessage = {
  type:
    | 'status_update'
    | 'log'
    | 'command_ack'
    | 'subscribed'
    | 'error'
    | 'anomaly'
    | 'inspection_started'
    | 'inspection_finished'
    | 'inspection_status';
  data?: any;
  topics?: string[];
  message?: string;
};

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private backendBase: string = '';
  public status = writable<'connecting' | 'connected' | 'disconnected'>('disconnected');

  async connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;

    // 发现后端
    if (!this.backendBase) {
      try {
        this.backendBase = await discoverBackend();
      } catch (e) {
        console.error('❌ 无法发现后端:', e);
        this.status.set('disconnected');
        return;
      }
    }

    const wsUrl = this.backendBase.replace(/^http/, 'ws') + '/ws';
    console.log('🔌 连接WebSocket:', wsUrl);

    this.ws = new WebSocket(wsUrl);
    this.status.set('connecting');

    this.ws.onopen = () => {
      console.log('✅ WebSocket 连接成功');
      this.status.set('connected');
      this.send({ type: 'subscribe', topics: ['status', 'log', 'command'] });
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    };

    this.ws.onclose = () => {
      console.log('⚠️ WebSocket 断开，3秒后重连...');
      this.status.set('disconnected');
      this.ws = null;
      this.backendBase = ''; // 清空让重连时重新发现
      if (!this.reconnectTimer) {
        this.reconnectTimer = window.setTimeout(() => this.connect(), 3000);
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        this.handleMessage(msg);
      } catch (e) {
        console.warn('无法解析消息:', e);
      }
    };
  }

  private handleMessage(msg: WSMessage) {
    switch (msg.type) {
      case 'status_update': {
        if (msg.data) robotStore.set(msg.data);
        break;
      }

      // 系统日志：只接收后端主动推送的事件 / 告警
      case 'log': {
        if (msg.data) logStore.update(logs => [msg.data, ...logs].slice(0, 100));
        break;
      }

      // ============================================================
      // ★ 修复点：命令回执不再写入日志
      // ============================================================
      // 后端每收到一条 command（比如方向键发来的 forward），
      // 都会回推一条 command_ack 表示"执行成功/失败"。
      // 这是正常的协议设计，后端没问题。
      //
      // 但前端【不能】把 command_ack 当成日志写进 logStore：
      //   1. 方向键/WASD 是高频操作，每按一次后端回一条 ack
      //   2. 每条 ack 触发一次 logStore.update()
      //   3. LogViewer 订阅了 logStore，于是每次按键都重渲染
      //   4. 连按方向键 → 高频重渲染 → 主线程卡死 → 标签切不动
      //
      // 按键的视觉反馈由 +page.svelte 里的 activeDirection 负责，
      // 不需要通过日志再反馈一次。
      //
      // 所以这里直接 break，不做任何 logStore 写入。
      // ============================================================
      case 'command_ack': {
        break;
      }

      // 异常报警：写入 anomalyStore（驱动全屏弹幕/模态弹窗 + 频闪 + 报警声）
      // 并追加一条异常日志（保留在 logStore 中，供 LogViewer 展示 + 图片下载）
      case 'anomaly': {
        if (msg.data) {
          const raw = msg.data;
          // 兼容两种等级写法：中文（高/中/低）或英文（high/medium/low），统一为中文
          const level =
            raw.level === 'high' || raw.level === '高' ? '高'
            : raw.level === 'medium' || raw.level === '中' ? '中'
            : raw.level === 'low' || raw.level === '低' ? '低'
            : '高';
          // 兼容字段名：location/area、recordTime/record_time
          const area = raw.location ?? raw.area ?? '未知区域';
          const recordTime = raw.recordTime ?? raw.record_time ?? '';
          const image = this.resolveUrl(raw.image);
          // 触发报警（弹幕/模态/频闪），统一中文等级与字段
          anomalyStore.set({ ...raw, level, area, image, recordTime });
          const severity: 'high' | 'medium' | 'low' =
            level === '高' ? 'high' : level === '中' ? 'medium' : 'low';
          logStore.update(logs => [
            {
              time: formatFullDateTime(raw.timestamp),
              level: 'error',
              message: `🚨 ${raw.type}告警（${level}级）· ${area}`,
              kind: 'anomaly',
              type: raw.type,
              location: area,
              image,
              recordTime,
              severity,
              timestamp: raw.timestamp
            },
            ...logs
          ].slice(0, 200));
        }
        break;
      }

      // 巡检开始：后端推送唯一 inspection_id
      case 'inspection_started': {
        if (msg.data) {
          inspectionStore.update(s => ({
            ...s,
            recording: true,
            inspection_id: msg.data.inspection_id ?? s.inspection_id
          }));
        }
        break;
      }

      // 巡检结束：后端推送下载链接
      case 'inspection_finished': {
        if (msg.data) {
          inspectionStore.set({
            recording: false,
            inspection_id: msg.data.inspection_id ?? '',
            video_url: this.resolveUrl(msg.data.video_url),
            log_url: this.resolveUrl(msg.data.log_url)
          });
        }
        break;
      }

      // 巡检录制状态：开始/结束录制、下载链接
      case 'inspection_status': {
        if (msg.data) {
          inspectionStore.set({
            recording: !!msg.data.recording,
            inspection_id: msg.data.inspection_id ?? '',
            video_url: this.resolveUrl(msg.data.video_url),
            log_url: this.resolveUrl(msg.data.log_url)
          });
        }
        break;
      }

      case 'subscribed':
        console.log('✅ 已订阅:', msg.topics);
        break;

      case 'error':
        console.error('❌ 服务端错误:', msg.message);
        break;

      default:
        console.log('未知消息类型:', msg);
    }
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket 未连接，无法发送消息');
    }
  }

  getBackendBase(): string {
    return this.backendBase;
  }

  // 把后端返回的相对路径（如 /api/download/...）补全为绝对地址，
  // 否则在开发环境（前端 5173 / 后端 8000）会请求到错误源。
  private resolveUrl(path: string): string {
    if (!path) return path;
    if (/^https?:\/\//i.test(path) || path.startsWith('data:')) return path;
    const base = this.backendBase || 'http://localhost:8000';
    return base.replace(/\/$/, '') + path;
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.backendBase = '';
  }
}

export const wsService = new WebSocketService();