import { writable } from 'svelte/store';
import { robotStore } from '$lib/stores/robot';
import { logStore } from '$lib/stores/log';

type WSMessage = {
  type: 'status_update' | 'log' | 'command_ack';
  data: any;
};

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  public status = writable<'connecting' | 'connected' | 'disconnected'>('disconnected');

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket('ws://localhost:8000/ws');
    this.status.set('connecting');

    this.ws.onopen = () => {
      console.log('✅ WebSocket 连接成功');
      this.status.set('connected');
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    };

    this.ws.onclose = () => {
      console.log('⚠️ WebSocket 断开，尝试重连...');
      this.status.set('disconnected');
      if (!this.reconnectTimer) {
        this.reconnectTimer = setTimeout(() => this.connect(), 3000);
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
      case 'status_update':
        robotStore.set(msg.data);
        break;
      case 'log':
        logStore.update(logs => [msg.data, ...logs].slice(0, 100));
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

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}

export const wsService = new WebSocketService();
