import { writable } from 'svelte/store';

export interface RobotStatus {
  status: string;
  battery: number;
  mode: string;
}

export const robotStore = writable<RobotStatus>({
  status: '待命',
  battery: 85,
  mode: '手动'
});