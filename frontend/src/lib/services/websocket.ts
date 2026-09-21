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
        // 3 秒后重试
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
      clearBackendCache(); // ★ 清掉 mDNS 缓存，重连时重新发现
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