import { writable } from 'svelte/store';

export interface RobotStatus {
  connected?: boolean;
  status: string;
  battery: number;
  mode: string;
  current_task?: string | null;
  current_state?: string;
}

export const robotStore = writable<RobotStatus>({
  connected: true,
  status: '待命',
  battery: 85,
  mode: '手动',
  current_task: null,
  current_state: '待命'
});