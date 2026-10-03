import { writable } from 'svelte/store';
import { robotStore } from '$lib/stores/robot';
import { logStore } from '$lib/stores/log';
import { discoverBackend, clearBackendCache } from '$lib/services/discovery';

type WSMessage = {
  type: 'status_update' | 'log' | 'command_ack' | 'subscribed' | 'error';
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
        if (!this.reconnectTimer) {
          this.reconnectTimer = window.setTimeout(() => this.connect(), 3000);
        }
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
      this.backendBase = '';
      clearBackendCache();
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

      case 'log': {
        if (msg.data) logStore.update(logs => [msg.data, ...logs].slice(0, 100));
        break;
      }

      // ============================================================
      // command_ack 处理
      // ============================================================
      // 成功时不写日志，避免方向键高频刷屏导致重渲染卡顿。
      // 失败时必须写日志，否则用户看不到"指令为什么没反应"。
      // ============================================================
      case 'command_ack': {
        const data = msg.data;
        if (!data) break;

        if (data.status !== 'executed') {
          const level: 'error' = 'error';
          const reason = data.detail?.error || data.error || '未知错误';
          logStore.update(logs => [{
            time: new Date().toLocaleTimeString(),
            level,
            message: `指令 ${data.cmd} 失败: ${reason}`
          }, ...logs].slice(0, 100));
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