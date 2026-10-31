import { writable } from 'svelte/store';
import { robotStore } from '$lib/stores/robot';
import { logStore } from '$lib/stores/log';
import { alertStore } from '$lib/stores/alert'; // ★ 新增：用于处理报警弹窗
import { discoverBackend, clearBackendCache } from '$lib/services/discovery';

type WSMessage = {
  // ★ 新增：补充后端推流类型
  type: 'status_update' | 'log' | 'command_ack' | 'subscribed' | 'error' | 'inspection_log' | 'inspection_alert' | 'tts_play';
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

      // ★★★ 以下为新增的巡检业务推送处理 ★★★

      case 'inspection_log': {
        // 普通巡检日志，直接推入日志队列
        if (msg.data) {
          logStore.update(logs => [{
            time: new Date().toLocaleTimeString(),
            level: 'info',
            message: msg.data
          }, ...logs].slice(0, 100));
        }
        break;
      }

      case 'inspection_alert': {
        // 严重报警，触发弹窗并写入红色日志
        if (msg.data) {
          alertStore.push({ 
            level: 'critical', 
            type: '巡检异常', 
            area: '现场', 
            detail: msg.data, 
            timestamp: new Date().toLocaleTimeString() 
          });
          logStore.update(logs => [{
            time: new Date().toLocaleTimeString(),
            level: 'error',
            message: `🚨 ${msg.data}`
          }, ...logs].slice(0, 100));
        }
        break;
      }

      case 'tts_play': {
        // 调用浏览器原生 TTS 进行语音播报
        if (msg.data && typeof window !== 'undefined' && 'speechSynthesis' in window) {
          const utterance = new SpeechSynthesisUtterance(msg.data);
          utterance.lang = 'zh-CN';
          window.speechSynthesis.speak(utterance);
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
