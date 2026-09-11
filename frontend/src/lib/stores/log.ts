import { writable } from 'svelte/store';

export interface LogEntry {
  time: string;
  level: 'info' | 'warning' | 'error' | 'success';
  message: string;
}

export const logStore = writable<LogEntry[]>([]);