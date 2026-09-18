import { writable, derived } from 'svelte/store';

export type AlertLevel = 'critical' | 'warning' | 'info';
export type AlertSource = 'modal' | 'fullscreen';

export type Alert = {
  id: string;
  level: AlertLevel;
  type: string;
  area: string;
  detail: string;
  timestamp: string;
  confirmed: boolean;
  source: AlertSource;
};

// ===== 全局全屏状态 =====
export const isFullscreen = writable(false);

function createAlertStore() {
  const { subscribe, update, set } = writable<Alert[]>([]);

  return {
    subscribe,

    /** 新增告警：自动打上 source 标签 */
    push(alert: Omit<Alert, 'id' | 'confirmed' | 'source'>) {
      let fs = false;
      const unsub = isFullscreen.subscribe(v => fs = v);
      unsub();

      const newAlert: Alert = {
        ...alert,
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        confirmed: false,
        source: fs ? 'fullscreen' : 'modal'
      };
      update(alerts => [newAlert, ...alerts].slice(0, 50));
      return newAlert;
    },

    confirm(id: string) {
      update(alerts => alerts.map(a => a.id === id ? { ...a, confirmed: true } : a));
    },

    confirmAll() {
      update(alerts => alerts.map(a => ({ ...a, confirmed: true })));
    },

    /** 按来源确认所有告警 */
    confirmAllBySource(source: AlertSource) {
      update(alerts => alerts.map(a =>
        a.source === source ? { ...a, confirmed: true } : a
      ));
    },

    clearConfirmed() {
      update(alerts => alerts.filter(a => !a.confirmed));
    },

    clear() {
      set([]);
    }
  };
}

export const alertStore = createAlertStore();

/** 所有未确认 */
export const activeAlerts = derived(alertStore, $a => $a.filter(x => !x.confirmed));
/** 未确认 + modal 来源（AlertModal 用） */
export const modalAlerts = derived(alertStore, $a => $a.filter(x => !x.confirmed && x.source === 'modal'));
/** 未确认 + fullscreen 来源（FullscreenAlert 用） */
export const fullscreenAlerts = derived(alertStore, $a => $a.filter(x => !x.confirmed && x.source === 'fullscreen'));

// ===== 开发模式：暴露到 window，方便控制台测试 =====
if (typeof window !== 'undefined' && import.meta.env.DEV) {
  (window as any).__alertStore = alertStore;
  (window as any).__fullscreen = isFullscreen;
  console.log('🔧 测试工具已就绪：');
  console.log('   __alertStore.push({level:"critical",type:"🔥 火焰",area:"区域C",detail:"测试"})');
  console.log('   __alertStore.clear()');
}